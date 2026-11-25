"""Convert a verified E11-A incremental report into B's fixed-md input.

This is a classroom interface adapter. It does not claim that the two
capabilities are already deployed as separate services.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def checked_artifact(run_dir: Path, item: dict, job_id: str) -> Path:
    prefix = f"artifact://{job_id}/"
    uri = item["uri"]
    if not isinstance(uri, str) or not uri.startswith(prefix):
        raise ValueError("Artifact belongs to another job")
    path = (run_dir / uri[len(prefix) :]).resolve()
    if not path.is_relative_to(run_dir.resolve()) or not path.is_file():
        raise ValueError("Artifact path is missing or outside the run")
    if digest(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
        raise ValueError(f"Artifact hash or size mismatch: {path.name}")
    return path


def make_handoff(result_path: Path, target_sha: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", target_sha):
        raise ValueError("Target must be a complete lowercase Git SHA")
    run_dir = result_path.resolve().parent
    result = read_json(result_path)
    if result.get("schema_version") != "e11e12-1" or result.get("status") != "SUCCEEDED":
        raise ValueError("A task did not succeed with the expected schema")
    if result.get("target_commit") != target_sha:
        raise ValueError("A task belongs to another target commit")
    job_id, trace_id = result["job_id"], result["trace_id"]
    matches = [x for x in result["stages"] if x.get("name") == "incremental-check"]
    if len(matches) != 1:
        raise ValueError("Expected one incremental-check stage")
    stage_item = matches[0]["artifact"]
    stage_path = checked_artifact(run_dir, stage_item, job_id)
    if stage_path != (run_dir / "incremental-check.json").resolve():
        raise ValueError("Unexpected stage artifact path")
    stage = read_json(stage_path)
    if (
        stage.get("schema_version") != "e11e12-1"
        or stage.get("kind") != "incremental-check"
        or stage.get("status") != "SUCCEEDED"
        or stage.get("commit") != target_sha
        or stage.get("job_id") != job_id
        or stage.get("trace_id") != trace_id
        or stage.get("data", {}).get("commit") != target_sha
    ):
        raise ValueError("Incremental report identity or target mismatch")
    for item in stage.get("artifacts", []):
        checked_artifact(run_dir, item, job_id)
    return {
        "schema_version": "e11e12-1",
        "kind": "fixed-md",
        "status": "SUCCEEDED",
        "commit": target_sha,
        "data": stage["data"],
        "source_report": {
            "job_id": job_id,
            "trace_id": trace_id,
            "uri": stage_item["uri"],
            "sha256": stage_item["sha256"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a-result", required=True, type=Path)
    parser.add_argument("--target-sha", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Output already exists; preserve earlier evidence")
    report = make_handoff(args.a_result, args.target_sha)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("HANDOFF_READY", f"sha256={digest(args.out)}", f"source_job={report['source_report']['job_id']}")


if __name__ == "__main__":
    main()
