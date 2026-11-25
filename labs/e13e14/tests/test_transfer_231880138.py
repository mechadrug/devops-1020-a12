"""Transferred reports must retain both byte integrity and target identity."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'e11e12'))
from pipeline import Failure, fixed_report


class Transfer231880138(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'external.json'
        self.target = 'a' * 40
        self.envelope = {'schema_version': 'e11e12-1', 'kind': 'fixed-md',
                         'status': 'SUCCEEDED', 'commit': self.target,
                         'data': {'commit': self.target, 'findings': []},
                         'source_report': {'job_id': 'job-source', 'trace_id': 'trace-source'}}
        self.path.write_text(json.dumps(self.envelope), encoding='utf-8')
        self.request = {'fixed_report': str(self.path),
                        'fixed_report_sha256': hashlib.sha256(self.path.read_bytes()).hexdigest()}

    def reject(self, code):
        with self.assertRaises(Failure) as caught:
            fixed_report(self.request, self.target)
        self.assertEqual(caught.exception.code, code)

    def test_whitespace_tampering_rejected_before_json_is_consumed(self):
        self.path.write_bytes(self.path.read_bytes() + b'\n')
        self.reject('ARTIFACT_HASH_MISMATCH')

    def test_stale_inner_commit_rejected_even_with_recomputed_digest(self):
        self.envelope['data']['commit'] = 'b' * 40
        self.path.write_text(json.dumps(self.envelope), encoding='utf-8')
        self.request['fixed_report_sha256'] = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.reject('STALE_REPORT')

    def test_source_identity_retained_and_original_fixture_still_works(self):
        self.assertEqual(fixed_report(self.request, self.target), self.envelope)
        self.request.pop('fixed_report_sha256')
        self.assertEqual(fixed_report(self.request, self.target), self.envelope)

    def test_malformed_expected_digest_is_not_silently_ignored(self):
        self.request['fixed_report_sha256'] = 'invalid'
        self.reject('INVALID_REQUEST')
