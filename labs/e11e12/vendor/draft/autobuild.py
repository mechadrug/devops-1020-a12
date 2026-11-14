"""Two-attempt teaching workflow; no autonomous model generation."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import uuid

def instructions(text):
    result, pending = [], ""
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.endswith("\\"):
            pending += stripped[:-1].strip() + " "
        else:
            result.append(" ".join((pending + stripped).split()))
            pending = ""
    if pending:
        raise ValueError("Incomplete line continuation")
    return result

def prepare_candidate(broken, candidate):
    original, proposed = instructions(broken), instructions(candidate)
    if not original or not proposed:
        raise ValueError("Empty Dockerfile")
    if not re.fullmatch(r"FROM \S+@sha256:[0-9a-f]{64}", proposed[0]):
        raise ValueError("Candidate must start with a digest-pinned FROM")
    if sum(line.upper().startswith("FROM ") for line in proposed) != 1:
        raise ValueError("Only single-stage candidates are supported")
    if original[0] != proposed[0].split("@", 1)[0]:
        raise ValueError("Candidate changed the original base image tag")
    baseline = [proposed[0], *original[1:]]
    cursor, added = 0, []
    for line in proposed:
        if cursor < len(baseline) and line == baseline[cursor]:
            cursor += 1
        elif line.startswith("RUN "):
            added.append(line)
        else:
            raise ValueError("Candidate changed required project/build/runtime instructions")
    if cursor != len(baseline) or not added:
        raise ValueError("Candidate omitted instructions or supplied no repair")
    return "\n".join(baseline) + "\n"

def execute(argv, stdout, stderr, timeout):
    with Path(stdout).open("w", encoding="utf-8") as out, Path(stderr).open("w", encoding="utf-8") as err:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise TimeoutError(f"Docker client command exceeded {timeout}s")

def classify_failure(text):
    if re.search(r"/bin/sh:.*\bmake: (?:not found|command not found)", text):
        return "MISSING_MAKE"
    if any(term in text.lower() for term in ("failed to resolve source metadata", "failed to do request", "connection reset", "no such host")):
        return "INFRASTRUCTURE"
    return "OTHER_BUILD_ERROR"

def auto_build(fixture, candidate, output, expected_output, timeout=300, verify_timeout=30):
    if os.name != "posix":
        raise ValueError("Run inside the Linux service container")
    fixture, candidate, output = Path(fixture).resolve(), Path(candidate).resolve(), Path(output).resolve()
    if timeout <= 0 or verify_timeout <= 0:
        raise ValueError("Timeouts must be positive")
    if not fixture.is_dir() or not candidate.is_file():
        raise ValueError("Fixture or candidate does not exist")
    if output == fixture or fixture in output.parents:
        raise ValueError("Output must be outside fixture")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a fresh empty output directory")
    if any(p.is_symlink() for p in fixture.rglob("*")):
        raise ValueError("Symlink fixtures are unsupported")
    text = candidate.read_text(encoding="utf-8")
    baseline = prepare_candidate((fixture / "Dockerfile.broken").read_text(encoding="utf-8"), text)
    output.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    report = {"status": "RUNNING", "detector": "DRAFT_TEACHING_REPLAY", "trace_id": "e6-b-" + run_id,
              "candidate_source": "Manual model response replay; no model/API call in this command",
              "candidate_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "attempts": []}
    started = time.monotonic()
    cid_path = output / "verify-container-id.txt"
    try:
        project = output / "project"
        shutil.copytree(fixture, project, ignore=shutil.ignore_patterns(".git", ".env", ".env.*", "work", "__pycache__", "Dockerfile.reference"))
        report["input_sha256"] = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(project.rglob("*")) if p.is_file()}
        for number, dockerfile in ((1, baseline), (2, text)):
            iteration = output / f"iter-{number:02d}"
            iteration.mkdir()
            path = iteration / "Dockerfile"
            path.write_text(dockerfile, encoding="utf-8")
            tag = f"e6-draft-replay:{run_id}-{number}"
            command = ["docker", "build", "--progress=plain", "-f", str(path), "-t", tag, str(project)]
            attempt = {"iteration": number, "tag": tag, "command": command}
            report["attempts"].append(attempt)
            code = execute(command, iteration / "build-stdout.log", iteration / "build-stderr.log", timeout)
            attempt["build_exit_code"] = code
            if number == 1:
                logs = (iteration / "build-stdout.log").read_text() + (iteration / "build-stderr.log").read_text()
                attempt["failure_class"] = classify_failure(logs)
                if code == 0 or attempt["failure_class"] != "MISSING_MAKE":
                    raise ValueError("Baseline did not reproduce missing make; infrastructure errors do not count")
                continue
            if code != 0:
                raise ValueError("Repair candidate build failed; inspect iter-02 logs")
            inspect_path = iteration / "image-inspect.json"
            code = execute(["docker", "image", "inspect", tag], inspect_path, iteration / "inspect-stderr.log", 30)
            if code != 0:
                raise ValueError("Cannot inspect built image")
            image_id = json.loads(inspect_path.read_text())[0]["Id"]
            attempt["image_id"] = image_id
            verify = ["docker", "run", "--rm", "--network", "none", "--cpus", "1", "--memory", "128m",
                      "--pids-limit", "64", "--cidfile", str(cid_path), image_id]
            code = execute(verify, output / "verify.log", output / "verify-stderr.log", verify_timeout)
            actual = (output / "verify.log").read_text(encoding="utf-8")
            report["verification"] = {"command": verify, "exit_code": code, "expected_output": expected_output,
                                      "actual_output": actual, "output_matches": actual.rstrip("\r\n") == expected_output}
            if code != 0 or not report["verification"]["output_matches"]:
                raise ValueError("Program verification failed: nonzero exit or unexpected output")
        report["status"] = "SUCCEEDED"
    except TimeoutError as exc:
        report.update(status="TIMED_OUT", error=str(exc))
    except (ValueError, OSError, KeyError, IndexError) as exc:
        report.update(status="FAILED", error=str(exc))
    finally:
        if cid_path.exists():
            cid = cid_path.read_text().strip()
            if re.fullmatch(r"[0-9a-f]{64}", cid):
                try:
                    execute(["docker", "rm", "-f", cid], output / "cleanup.log", output / "cleanup-stderr.log", 15)
                except (OSError, TimeoutError):
                    report["cleanup_warning"] = "Container cleanup did not finish; check saved container ID"
        report["elapsed_ms"] = round((time.monotonic() - started) * 1000)
        (output / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
