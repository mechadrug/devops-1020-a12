"""E13 handoff hardening and four-role deployment contract (231880224).

Adds cases the classroom baseline does not cover: artifact URIs that escape the
run directory or claim another job, duplicated incremental stages, strict
digest formatting, and the structural UID/GID and isolation guarantees of the
four-service Compose file.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "labs/e13e14"), str(ROOT / "labs/e11e12")]
from handoff_a_to_b import make_handoff
from pipeline import Failure, fixed_report


def artifact(path, root, job_id, uri=None):
    data = path.read_bytes()
    return {
        "uri": uri or f"artifact://{job_id}/{path.relative_to(root).as_posix()}",
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


class HandoffHardening231880224(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.job = "job-231880224"
        self.trace = "trace-231880224"
        self.sha = "a" * 40
        self.inside = self.root / "incremental-report.json"
        self.inside.write_text('{"findings": []}\n')
        self.stage = {
            "schema_version": "e11e12-1",
            "kind": "incremental-check",
            "status": "SUCCEEDED",
            "commit": self.sha,
            "job_id": self.job,
            "trace_id": self.trace,
            "data": {"commit": self.sha, "findings": []},
            "artifacts": [artifact(self.inside, self.root, self.job)],
        }
        self.stage_path = self.root / "incremental-check.json"
        self.result = {
            "schema_version": "e11e12-1",
            "status": "SUCCEEDED",
            "target_commit": self.sha,
            "job_id": self.job,
            "trace_id": self.trace,
            "stages": [],
        }
        self.result_path = self.root / "result.json"
        self.rewrite()

    def rewrite(self):
        self.stage_path.write_text(json.dumps(self.stage) + "\n")
        self.result["stages"] = [
            {"name": "incremental-check", "artifact": artifact(self.stage_path, self.root, self.job)}
        ]
        self.result_path.write_text(json.dumps(self.result) + "\n")

    def test_artifact_uri_escaping_the_run_is_rejected(self):
        outside = self.root.parent / "outside-231880224.json"
        outside.write_text("{}\n")
        self.addCleanup(outside.unlink)
        self.stage["artifacts"][0] = artifact(
            outside, self.root, self.job, uri=f"artifact://{self.job}/../outside-231880224.json"
        )
        self.rewrite()
        with self.assertRaisesRegex(ValueError, "outside the run|missing"):
            make_handoff(self.result_path, self.sha)

    def test_artifact_from_another_job_is_rejected(self):
        self.stage["artifacts"][0] = artifact(
            self.inside, self.root, self.job, uri="artifact://job-other/incremental-report.json"
        )
        self.rewrite()
        with self.assertRaisesRegex(ValueError, "another job"):
            make_handoff(self.result_path, self.sha)

    def test_duplicate_incremental_stages_are_rejected(self):
        self.rewrite()
        self.result["stages"].append(dict(self.result["stages"][0]))
        self.result_path.write_text(json.dumps(self.result) + "\n")
        with self.assertRaisesRegex(ValueError, "one incremental-check"):
            make_handoff(self.result_path, self.sha)


class TransferDigest231880224(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "external.json"
        self.target = "b" * 40
        self.document = {
            "schema_version": "e11e12-1",
            "kind": "fixed-md",
            "status": "SUCCEEDED",
            "commit": self.target,
            "data": {"commit": self.target, "findings": []},
        }
        self.path.write_text(json.dumps(self.document), encoding="utf-8")

    def reject(self, digest):
        request = {"fixed_report": str(self.path), "fixed_report_sha256": digest}
        with self.assertRaises(Failure) as caught:
            fixed_report(request, self.target)
        self.assertEqual(caught.exception.code, "INVALID_REQUEST")
        return caught.exception

    def test_uppercase_digest_is_not_treated_as_a_valid_transfer(self):
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest().upper()
        self.reject(digest)

    def test_digest_with_trailing_whitespace_is_rejected(self):
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest() + "\n"
        self.reject(digest)


class ComposeIdentity231880224(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "labs/e13e14/compose.yaml").read_text(encoding="utf-8")

    def test_roles_share_host_identity_and_drop_privileges(self):
        self.assertIn('user: "${E14_UID:-0}:${E14_GID:-0}"', self.text)
        self.assertIn("no-new-privileges:true", self.text)
        self.assertNotIn("privileged: true", self.text)

    def test_only_draft_gets_the_docker_socket(self):
        self.assertEqual(self.text.count("/var/run/docker.sock:/var/run/docker.sock"), 1)
        self.assertEqual(self.text.count("group_add:"), 1)
        socket_at = self.text.index("/var/run/docker.sock:/var/run/docker.sock")
        self.assertLess(self.text.index("  draft:"), socket_at)
        self.assertLess(socket_at, self.text.index("  mdfixer:"))

    def test_every_role_is_loopback_bound_with_a_healthcheck(self):
        self.assertEqual(self.text.count('ports: ["127.0.0.1:'), 4)
        self.assertEqual(self.text.count("healthcheck:"), 1)

    def test_role_resources_are_bounded(self):
        for limit in ("cpus: 1.0", "mem_limit: 768m", "pids_limit: 128"):
            self.assertIn(limit, self.text)


if __name__ == "__main__":
    unittest.main()
