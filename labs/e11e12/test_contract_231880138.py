"""Personal transport-integrity and persisted-job recovery contracts."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pipeline
import server


class Contracts231880138(unittest.TestCase):
    def test_same_size_valid_json_tampering_rejected_by_original_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'report.json'
            original=b'{"commit":"aaaaaaaa"}\n'
            changed=b'{"commit":"bbbbbbbb"}\n'
            self.assertEqual(len(original),len(changed))
            path.write_bytes(original)
            digest=hashlib.sha256(original).hexdigest()
            self.assertEqual(pipeline.load_artifact(path,digest),{'commit':'aaaaaaaa'})
            path.write_bytes(changed)
            with self.assertRaises(pipeline.Failure) as caught:
                pipeline.load_artifact(path,digest)
            self.assertEqual(caught.exception.code,'ARTIFACT_HASH_MISMATCH')
            self.assertEqual(path.read_bytes(),changed)

    def test_restart_preserves_finished_job_and_fails_both_incomplete_states(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'jobs'
            request={'mode':'e11-a','repo':str(pipeline.ROOT/'data/recovery-fixture'),
                     'base':'a'*40,'target':'b'*40}
            digest=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()
            for name,status in [('finished','SUCCEEDED'),('queued','QUEUED'),('running','RUNNING')]:
                state={'schema_version':'e11e12-1','job_id':'job-'+name,'status':status,
                       'idempotency_key':name,'request_hash':digest}
                if name=='finished':state['trace_id']='trace-completed'
                pipeline.save(root/('job-'+name)/'state.json',state)
            store=server.Store(root)
            try:
                for name in ['queued','running']:
                    recovered=store.jobs['job-'+name]
                    self.assertEqual(recovered['status'],'FAILED')
                    self.assertEqual(recovered['error']['code'],'SERVER_RESTARTED')
                    self.assertEqual(json.loads((root/('job-'+name)/'state.json').read_text()),recovered)
                with patch.object(store.pool,'submit') as enqueue:
                    existing=store.submit(request,'finished')
                    self.assertEqual(existing['job_id'],'job-finished')
                    self.assertEqual(existing['status'],'SUCCEEDED')
                    self.assertEqual(existing['trace_id'],'trace-completed')
                    enqueue.assert_not_called()
                    with self.assertRaisesRegex(ValueError,'IDEMPOTENCY_CONFLICT'):
                        store.submit(dict(request,target='c'*40),'finished')
            finally:
                store.pool.shutdown(wait=True)


if __name__=='__main__':unittest.main()
