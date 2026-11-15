"""Independent E11-E12 contract test for student 231880398.

Covers the server restart rule in the classroom API contract: unfinished jobs
become FAILED/SERVER_RESTARTED, while completed jobs remain queryable.
"""
import json
import tempfile
import unittest
from pathlib import Path

import server


class Student231880398Contracts(unittest.TestCase):
    def write_state(self, root, job_id, status):
        path = root / job_id / "state.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({
            "schema_version": "e11e12-1",
            "job_id": job_id,
            "status": status,
            "idempotency_key": "key-" + job_id,
            "request_hash": "hash-" + job_id,
        }))

    def test_server_restart_marks_unfinished_failed_and_keeps_completed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.write_state(root, "job-queued", "QUEUED")
            self.write_state(root, "job-running", "RUNNING")
            self.write_state(root, "job-done", "SUCCEEDED")

            store = server.Store(root)

            self.assertEqual(store.jobs["job-queued"]["status"], "FAILED")
            self.assertEqual(store.jobs["job-running"]["status"], "FAILED")
            self.assertEqual(
                store.jobs["job-running"]["error"]["code"],
                "SERVER_RESTARTED",
            )
            self.assertEqual(store.jobs["job-done"]["status"], "SUCCEEDED")
            store.pool.shutdown()


if __name__ == "__main__":
    unittest.main()
