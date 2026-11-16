"""Run real container checks against explicit, small teaching oracles."""
import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess

EXPECTED = {("MISSING", "main.o", "config.h"), ("REDUNDANT", "main.o", "unused.h")}

def evaluate(name, code, report):
    if not report.get("trace_id"):
        raise ValueError("Missing trace_id")
    if name.startswith("original-") or name == "fixed":
        if report.get("status") != "SUCCEEDED" or report.get("build_exit_code") != 0 or report.get("clean_exit_code") != 0:
            raise ValueError("Expected successful clean-build detection")
        findings = report.get("findings")
        if not isinstance(findings, list):
            raise ValueError("Missing findings list")
        rows = [(f["type"], f["target"], f["dependency"]) for f in findings]
        expected = EXPECTED if name.startswith("original-") else set()
        if len(rows) != len(expected) or set(rows) != expected:
            raise ValueError(f"Oracle mismatch: expected {sorted(expected)}, got {rows}")
        if code != (1 if expected else 0):
            raise ValueError("CLI exit code does not enforce findings gate")
        for finding in findings:
            if not finding.get("evidence"):
                raise ValueError("Finding has no evidence anchor")
    elif name == "build-failed":
        if code != 1 or report.get("status") != "FAILED" or report.get("error_code") != "CHECK_FAILED" or report.get("build_exit_code") in (None, 0):
            raise ValueError("Failed build was not reported correctly")
    elif name == "unsupported":
        if code != 1 or report.get("status") != "FAILED" or report.get("error_code") != "UNSUPPORTED" or report.get("build_exit_code") != 0:
            raise ValueError("Multiple outputs were not explicitly rejected")
    elif name == "timeout":
        if code != 1 or report.get("status") != "TIMED_OUT" or report.get("error_code") != "TIMEOUT":
            raise ValueError("Timeout was not reported correctly")
    else:
        raise ValueError(f"Unknown oracle: {name}")

def run_logged(command, folder, timeout=180):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "command.json").write_text(json.dumps(command, indent=2), encoding="utf-8")
    with (folder / "stdout.log").open("w", encoding="utf-8") as out, (folder / "stderr.log").open("w", encoding="utf-8") as err:
        try:
            return subprocess.run(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            cid = folder / "container-id.txt"
            if cid.exists():
                subprocess.run(["docker", "rm", "-f", cid.read_text().strip()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            raise ValueError("Outer Docker command timed out; inspect logs")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="e6-buildchecker:ta1020001")
    parser.add_argument("--out", required=True)
    parser.add_argument("--inject-bad-oracle", action="store_true", help="Teaching demonstration: require a finding for the repaired sample")
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("Run this gate in Ubuntu/WSL, using the host Docker CLI")
    root = Path(__file__).resolve().parents[1]
    output = Path(args.out).resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("Use a fresh empty output directory")
    fixture = root / "fixtures/md-rd"
    if not fixture.is_dir() or fixture == output or fixture in output.parents:
        parser.error("Fixture missing or output is inside fixture")
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    try:
        if run_logged(["docker", "image", "inspect", args.image], output / "image") != 0:
            raise ValueError("Image unavailable: start Docker and check image tag")
        print("[unit-tests] Running existing service tests...", flush=True)
        unit_dir = output / "unit-tests"
        unit_dir.mkdir()
        code = run_logged(["docker", "run", "--rm", "--network", "none", "--cidfile", str(unit_dir / "container-id.txt"), args.image, "pytest"], unit_dir)
        rows.append({"case": "unit-tests", "passed": code == 0, "exit_code": code})
        if code != 0:
            raise ValueError("Service unit tests failed")
        for name in ("original-1", "original-2", "original-3", "fixed", "build-failed", "unsupported", "timeout"):
            print(f"[{name}] Running real build/check...", flush=True)
            case = output / name
            source, evidence = case / "fixture", case / "evidence"
            case.mkdir()
            shutil.copytree(fixture, source)
            evidence.mkdir()
            makefile = source / "Makefile"
            if name == "fixed":
                contents = makefile.read_text()
                if "main.o: main.c unused.h" not in contents:
                    raise ValueError("Fixture declaration has changed; review oracle")
                makefile.write_text(contents.replace("main.o: main.c unused.h", "main.o: main.c config.h"))
            elif name == "build-failed":
                (source / "config.h").unlink()
            elif name == "unsupported":
                makefile.write_text("app: main.c\n\tcp main.c one; cp main.c two\n.PHONY: clean\nclean:\n\trm -f one two\n")
            elif name == "timeout":
                makefile.write_text("app: main.c\n\tsleep 10\n\tcp main.c app\n.PHONY: clean\nclean:\n\trm -f app\n")
            command = ["docker", "run", "--rm", "--network", "none", "--user", f"{os.getuid()}:{os.getgid()}",
                       "-e", "HOME=/tmp", "--cap-add", "SYS_PTRACE", "--cidfile", str(case / "container-id.txt"),
                       "--mount", f"type=bind,src={source},dst=/fixture,readonly",
                       "--mount", f"type=bind,src={evidence},dst=/evidence", args.image,
                       "python3", "-m", "buildchecker", "full-check", "--fixture", "/fixture", "--out", "/evidence",
                       "--fail-on-findings", "--timeout", "1" if name == "timeout" else "30"]
            code = run_logged(command, case)
            row = {"case": name, "passed": False, "exit_code": code}
            try:
                report = json.loads((evidence / "findings.json").read_text(encoding="utf-8"))
                evaluate(name, code, report)
                if report["status"] == "SUCCEEDED":
                    for artifact in ("actual-graph.json", "declared-graph.json", "processes.json", "make-db.txt"):
                        if not (evidence / artifact).is_file():
                            raise ValueError(f"Missing artifact {artifact}")
                    if not list((evidence / "trace").glob("t.*")):
                        raise ValueError("Missing raw trace")
                if args.inject_bad_oracle and name == "fixed":
                    raise ValueError("Intentional failing oracle: repaired fixture was required to have a finding")
                row.update(passed=True, detector_status=report["status"], trace_id=report["trace_id"])
            except (ValueError, OSError, KeyError, TypeError) as exc:
                row["error"] = str(exc)
            rows.append(row)
            print(f"[{name}] {'PASS' if row['passed'] else 'FAIL'}; tool exit={code}", flush=True)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        rows.append({"case": "runner", "passed": False, "error": str(exc)})
    passed = bool(rows) and all(row["passed"] for row in rows) and len(rows) == 8
    summary = {"passed": passed, "image": args.image, "cases": rows,
               "oracle_scope": "Small explicit teaching fixtures; not full paper benchmark",
               "repeated_original_cases": 3, "intentional_failure": args.inject_bad_oracle}
    (output / "gate-result.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = ["case", "passed", "exit_code", "detector_status", "trace_id", "error"]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return 0 if passed else 1

if __name__ == "__main__":
    raise SystemExit(main())
