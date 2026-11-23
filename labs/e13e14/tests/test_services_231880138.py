"""The HTTP role must stop at the transfer boundary before a repair can write."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/'labs/e8e10'), str(ROOT/'services/buildchecker')]
spec = importlib.util.spec_from_file_location('e14_service_contract', ROOT/'labs/e13e14/service.py')
service = importlib.util.module_from_spec(spec)
with patch.dict(os.environ, {'E14_ROLE':'mdfixer'}):
    spec.loader.exec_module(service)


class ServiceBoundary231880138(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.report = self.root/'work/job-test/incremental.json'
        self.report.parent.mkdir(parents=True)
        self.target = 'a'*40
        self.document = {'schema_version':'e11e12-1','kind':'incremental-check','status':'SUCCEEDED',
                         'commit':self.target,'job_id':'job-test','trace_id':'trace-test',
                         'data':{'commit':self.target,'findings':[]}}
        self.report.write_text(json.dumps(self.document), encoding='utf-8')
        self.output = self.root/'work/job-test/repair'
        self.request = {'project':str(self.root/'work/job-test/target'), 'out':str(self.output),
                        'report':str(self.report), 'report_sha256':hashlib.sha256(self.report.read_bytes()).hexdigest(),
                        'target_commit':self.target, 'job_id':'job-test','trace_id':'trace-test'}

    def rejected_without_writes(self, message):
        with patch.object(service,'ROOT',self.root), patch.object(service,'ROLE','mdfixer'):
            with self.assertRaisesRegex(ValueError,message):
                service.run(self.request)
        self.assertFalse(self.output.exists())

    def test_valid_json_with_changed_bytes_cannot_reach_repair(self):
        self.report.write_bytes(self.report.read_bytes()+b'\n')
        self.rejected_without_writes('transfer hash mismatch')

    def test_valid_digest_does_not_allow_another_job_report(self):
        self.document['job_id']='job-other'
        self.report.write_text(json.dumps(self.document), encoding='utf-8')
        self.request['report_sha256']=hashlib.sha256(self.report.read_bytes()).hexdigest()
        self.rejected_without_writes('identity mismatch')

    def test_health_remains_responsive_during_a_long_role_request(self):
        entered, release = threading.Event(), threading.Event()
        def long_job(data):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('Test did not release the worker')
            return {'status':'SUCCEEDED'}
        httpd=service.HTTPServer(('127.0.0.1',0),service.Handler)
        url='http://127.0.0.1:'+str(httpd.server_address[1])
        runner=threading.Thread(target=httpd.serve_forever,daemon=True)
        errors=[]
        def post():
            try:
                request=urllib.request.Request(url+'/v1/run',data=b'{}')
                with urllib.request.urlopen(request,timeout=8) as response:
                    response.read()
            except Exception as error:errors.append(error)
        with patch.object(service,'run',long_job):
            runner.start()
            client=threading.Thread(target=post,daemon=True)
            client.start()
            try:
                self.assertTrue(entered.wait(2))
                with urllib.request.urlopen(url+'/health',timeout=.5) as response:
                    self.assertEqual(json.load(response)['status'],'ok')
            finally:
                release.set()
                client.join(timeout=8)
                httpd.shutdown()
                httpd.server_close()
                runner.join(timeout=2)
        self.assertFalse(errors)
