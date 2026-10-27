"""Small, auditable GNU Make/strace detector for the E6 teaching profile.

The execution model uses successful read-open observations, not proof of byte
reads. Unsupported trace patterns fail explicitly. This is not the paper tool.
"""
import ast
import hashlib
import json
import os
import posixpath
import re
import shlex
import shutil
import signal
import subprocess
import time
import uuid
from pathlib import Path

VERSION = "0.2.0-teaching"
QUOTED = re.compile(r'"(?:\\.|[^"\\])*"')
CALL = re.compile(r'^(\w+)\((.*)\)\s+=\s+(-?\d+)(?:\s|$)')


class Unsupported(ValueError):
    pass


def split_args(text):
    """Split syscall args without splitting quoted strings or nested structures."""
    result, start, depth, quoted, escaped = [], 0, 0, False, False
    for i, char in enumerate(text):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            result.append(text[start:i].strip())
            start = i + 1
    result.append(text[start:].strip())
    return result


def quoted_path(text):
    match = QUOTED.search(text)
    if not match:
        raise Unsupported("Path string unavailable or truncated")
    return ast.literal_eval(match.group())


def project_path(path, cwd, root):
    absolute = posixpath.normpath(path if path.startswith("/") else posixpath.join(cwd, path))
    root = posixpath.normpath(root)
    if absolute == root or not absolute.startswith(root.rstrip("/") + "/"):
        return None
    return posixpath.relpath(absolute, root)


def trace_events(path):
    """Merge unfinished/resumed syscalls, retaining the original start line."""
    events, pending = [], None
    for number, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if "<unfinished ...>" in raw:
            if pending:
                raise Unsupported(f"Nested unfinished syscall in {path.name}")
            pending = (number, raw.split("<unfinished ...>")[0])
            continue
        if " resumed>" in raw:
            if not pending:
                raise Unsupported(f"Resumed syscall without start in {path.name}")
            number, before = pending
            raw = before + raw.split(" resumed>", 1)[1]
            pending = None
        match = CALL.match(raw)
        if match:
            events.append({"call": match[1], "args": split_args(match[2]),
                           "return": int(match[3]), "line": number, "raw": raw})
    if pending:
        raise Unsupported(f"Incomplete syscall at end of {path.name}")
    return events


def load_processes(trace_dir):
    processes, parent = {}, {}
    for path in sorted(Path(trace_dir).iterdir()):
        match = re.fullmatch(r"t\.(\d+)", path.name)
        if not match:
            continue
        pid = int(match[1])
        processes[pid] = {"pid": pid, "trace_file": path.name,
                          "events": trace_events(path), "executables": []}
    if not processes:
        raise Unsupported("No per-process t.PID trace files found")
    for pid, proc in processes.items():
        for event in proc["events"]:
            name, args, ret = event["call"], event["args"], event["return"]
            if name in {"clone", "clone3", "fork", "vfork"} and ret > 0:
                if ret in parent and parent[ret] != pid:
                    raise Unsupported("Ambiguous process parent")
                if "CLONE_FS" in event["raw"]:
                    raise Unsupported("Shared-thread working directory is outside the teaching profile")
                parent[ret] = pid
            if name in {"execve", "execveat"} and ret == 0:
                proc["executables"].append(quoted_path(args[0 if name == "execve" else 1]))
    for child in parent:
        if child not in processes:
            raise Unsupported(f"Missing trace for child PID {child}")
    make_pids = {pid for pid, proc in processes.items()
                 if any(posixpath.basename(exe) in {"make", "gmake"} for exe in proc["executables"])}
    if len(make_pids) != 1:
        raise Unsupported("Teaching profile requires one Make process; recursive Make is not yet supported")
    return processes, parent, make_pids


def execution_graph(trace_dir, root):
    processes, parent, make_pids = load_processes(trace_dir)
    if not root.startswith("/"):
        raise ValueError("Project root must be an absolute Linux path")
    root = posixpath.normpath(root)
    jobs, visited = {}, set()

    def job_for(pid):
        if pid in make_pids:
            return None
        seen, current = set(), pid
        while current in parent:
            if current in seen:
                raise Unsupported("Process parent cycle")
            seen.add(current)
            if parent[current] in make_pids:
                return current
            current = parent[current]
        return None

    def visit(pid, inherited_cwd):
        if pid in visited:
            return
        visited.add(pid)
        proc, cwd, job_id = processes[pid], inherited_cwd, job_for(pid)
        job = jobs.setdefault(job_id, {"reads": {}, "writes": {}, "produced": set(), "pids": set()}) if job_id is not None else None
        if job:
            job["pids"].add(pid)
        for event in proc["events"]:
            name, args, ret = event["call"], event["args"], event["return"]
            if ret < 0:
                continue  # Failed probes never become dependencies or children.
            evidence = {"source": "system_call", "trace_file": proc["trace_file"],
                        "line": event["line"], "pid": pid, "operation": name}
            if name == "chdir" and ret == 0:
                cwd = posixpath.normpath(posixpath.join(cwd, quoted_path(args[0])))
            elif name == "fchdir" and ret == 0:
                raise Unsupported("fchdir requires descriptor tracking, not yet implemented")
            elif name in {"clone", "clone3", "fork", "vfork"} and ret > 0:
                visit(ret, cwd)  # Inherit cwd at the fork, not the parent's final cwd.
            elif name in {"open", "openat", "openat2", "creat"}:
                index = 1 if name in {"openat", "openat2"} else 0
                path = quoted_path(args[index])
                if index == 1 and not path.startswith("/") and args[0] != "AT_FDCWD":
                    raise Unsupported("Relative openat with numeric directory FD is not yet supported")
                relative = project_path(path, cwd, root)
                if relative is None:
                    continue
                flags = args[index + 1] if len(args) > index + 1 else ""
                if name == "creat":
                    flags = "O_WRONLY|O_CREAT|O_TRUNC"
                if "O_DIRECTORY" in flags or "O_PATH" in flags:
                    continue
                is_write = any(flag in flags for flag in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC"))
                if job is None:
                    if is_write:
                        raise Unsupported("Make itself wrote project files outside a recipe process")
                    continue  # Make reading its database inputs is not compiler input.
                if is_write:
                    job["writes"].setdefault(relative, evidence)
                    job["produced"].add(relative)
                elif "O_RDONLY" in flags:
                    job["reads"].setdefault(relative, evidence)
            elif name in {"rename", "renameat", "renameat2"} and job:
                source_i, target_i = (0, 1) if name == "rename" else (1, 3)
                for fd_i, path_i in ((0, 1), (2, 3)) if name != "rename" else ():
                    if args[fd_i] != "AT_FDCWD" and not quoted_path(args[path_i]).startswith("/"):
                        raise Unsupported("Numeric-directory-FD rename is not yet supported")
                old = project_path(quoted_path(args[source_i]), cwd, root)
                new = project_path(quoted_path(args[target_i]), cwd, root)
                if old:
                    job["writes"].pop(old, None)
                    job["produced"].add(old)
                if new:
                    job["writes"][new] = evidence
                    job["produced"].add(new)
            elif name in {"unlink", "unlinkat"} and job:
                index = 0 if name == "unlink" else 1
                path = quoted_path(args[index])
                if name == "unlinkat" and args[0] != "AT_FDCWD" and not path.startswith("/"):
                    raise Unsupported("Numeric-directory-FD unlink is not yet supported")
                relative = project_path(path, cwd, root)
                if relative:
                    job["writes"].pop(relative, None)
        proc["final_cwd"] = cwd

    roots = [pid for pid in processes if pid not in parent]
    if len(roots) != 1 or roots[0] not in make_pids:
        raise Unsupported("Trace is not one complete Make process tree")
    visit(roots[0], root)
    if len(visited) != len(processes):
        raise Unsupported("Disconnected trace processes")
    targets = {}
    for job_id, job in jobs.items():
        if not job["writes"]:
            continue
        if len(job["writes"]) > 1:
            raise Unsupported(f"Recipe job {job_id} has multiple final outputs; needs a richer attribution model")
        target, output_evidence = next(iter(job["writes"].items()))
        if target in targets:
            raise Unsupported(f"Multiple jobs write the same target: {target}")
        deps = {path: evidence for path, evidence in job["reads"].items()
                if path not in job["produced"] and path != target}
        targets[target] = {"dependencies": deps, "output_evidence": output_evidence,
                           "job_pid": job_id, "processes": sorted(job["pids"])}
    if not targets:
        raise Unsupported("No project output targets observed; cannot claim a complete successful check")
    process_summary = [{"pid": pid, "parent": parent.get(pid),
                        "executables": processes[pid]["executables"], "job_pid": job_for(pid)}
                       for pid in sorted(processes)]
    return targets, process_summary


def declaration_graph(database, root):
    targets, phony, in_files, seen_files, not_target = {}, set(), False, False, False
    for number, line in enumerate(Path(database).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if line.strip() == "# Files":
            in_files, seen_files = True, True
            continue
        if in_files and line.startswith("# files hash-table stats"):
            in_files = False
        if not in_files:
            continue
        if line.startswith("# Not a target:"):
            not_target = True
            continue
        if not line or line.startswith(("#", "\t", " ")):
            continue
        parts = re.split(r"(?<!\\):", line, maxsplit=1)
        if len(parts) != 2:
            continue
        names, right = parts[0], parts[1].lstrip(":")
        skip, not_target = not_target, False
        if "%" in names or "$(" in names or "${" in names:
            continue
        try:
            raw_names, deps = shlex.split(names), shlex.split(right)
        except ValueError as exc:
            raise Unsupported(f"Unresolved Make database syntax on line {number}: {exc}")
        if raw_names == [".PHONY"]:
            phony.update(deps)
            continue
        if skip:
            continue
        order_only = deps[deps.index("|") + 1:] if "|" in deps else []
        regular = deps[:deps.index("|")] if "|" in deps else deps
        for name in raw_names:
            target = project_path(name, root, root)
            if target:
                entry = targets.setdefault(target, {"dependencies": {}, "order_only": [], "raw_name": name})
                entry["order_only"].extend(order_only)
                for dep in regular:
                    relative = project_path(dep, root, root)
                    if relative:
                        entry["dependencies"][relative] = {
                            "source": "make_database", "artifact": "make-db.txt",
                            "line": number, "declaration": line}
    if not seen_files or not targets:
        raise Unsupported("No parseable Files section in Make database")
    normalized_phony = {project_path(name, root, root) for name in phony}

    def expand(dep, trail):
        if dep not in normalized_phony:
            return {dep}
        if dep in trail:
            raise Unsupported("Cycle in phony prerequisites")
        result = set()
        for child in targets.get(dep, {}).get("dependencies", {}):
            result.update(expand(child, trail | {dep}))
        return result

    for target, entry in targets.items():
        expanded = {}
        for dep, evidence in entry["dependencies"].items():
            for leaf in expand(dep, set()):
                expanded.setdefault(leaf, evidence)
        entry["dependencies"] = expanded
    return {target: entry for target, entry in targets.items() if target not in normalized_phony}


def analyze(trace_dir, database, root):
    actual, processes = execution_graph(trace_dir, root)
    declared = declaration_graph(database, root)
    findings = []
    for target, item in sorted(actual.items()):
        observed = item["dependencies"]
        specified = declared.get(target, {}).get("dependencies", {})
        for dep in sorted(set(observed) - set(specified)):
            findings.append({"type": "MISSING", "target": target, "dependency": dep,
                             "evidence": [observed[dep], item["output_evidence"]],
                             "declared_dependencies": sorted(specified)})
        for dep in sorted(set(specified) - set(observed)):
            findings.append({"type": "REDUNDANT", "target": target, "dependency": dep,
                             "evidence": [specified[dep]],
                             "scope": "Not observed in this recipe job under this build configuration"})
    actual_edges = [{"target": target, "dependency": dep, "kind": "ACTUAL_READ_OPEN",
                     "evidence": evidence}
                    for target, item in sorted(actual.items())
                    for dep, evidence in sorted(item["dependencies"].items())]
    declared_edges = [{"target": target, "dependency": dep, "kind": "DECLARED",
                       "evidence": evidence}
                      for target, item in sorted(declared.items())
                      for dep, evidence in sorted(item["dependencies"].items())]
    return {"findings": findings, "actual_graph": actual_edges,
            "declared_graph": declared_edges, "processes": processes,
            "observed_targets": sorted(actual), "filter": "Project-local paths only"}


def execute(argv, cwd, stdout_path, stderr_path, timeout):
    with open(stdout_path, "w", encoding="utf-8") as out, open(stderr_path, "w", encoding="utf-8") as err:
        proc = subprocess.Popen(argv, cwd=cwd, stdout=out, stderr=err, start_new_session=True)
        try:
            return proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise TimeoutError(f"Command exceeded {timeout}s; process group was killed")


def full_check(fixture, output, clean_command="make clean", build_command="make app", timeout=120):
    if os.name != "posix":
        raise ValueError("Full collection requires Linux; offline analyze is portable")
    fixture, output = Path(fixture).resolve(), Path(output).resolve()
    if not fixture.is_dir():
        raise ValueError("Fixture directory does not exist")
    if output == fixture or fixture in output.parents:
        raise ValueError("Output must be outside the fixture")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a fresh empty output directory to preserve old evidence")
    if any(path.is_symlink() for path in fixture.rglob("*")):
        raise Unsupported("Symlink-aware resolution is not yet in this teaching profile")
    build = shlex.split(build_command)
    clean = shlex.split(clean_command)
    if not clean or not build or posixpath.basename(build[0]) not in {"make", "gmake"}:
        raise ValueError("Nonempty clean command and a GNU Make build command are required")
    output.mkdir(parents=True, exist_ok=True)
    report = {"status": "RUNNING", "detector": "BUILDCHECKER_TEACHING", "detector_version": VERSION,
              "trace_id": "e6-" + uuid.uuid4().hex, "findings": [],
              "scope": "Single Make process; one final output per recipe job; successful read-open observations",
              "build_command": build, "clean_command": clean}
    start = time.monotonic()
    try:
        project, traces = output / "project", output / "trace"
        shutil.copytree(fixture, project, ignore=shutil.ignore_patterns(".git", ".env", ".env.*", "work", "__pycache__"))
        traces.mkdir()
        report["input_sha256"] = {path.relative_to(project).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                                  for path in sorted(project.rglob("*")) if path.is_file()}
        report["clean_exit_code"] = execute(clean, project, output / "clean.log", output / "clean-stderr.log", timeout)
        if report["clean_exit_code"] != 0:
            raise ValueError("Clean command failed; cannot claim a clean-build analysis")
        database = output / "make-db.txt"
        traced = ["strace", "-ff", "-s", "4096", "-o", str(traces / "t"),
                  "-e", "trace=%file,%process", build[0], "-p", *build[1:]]
        report["trace_command"] = traced
        report["build_exit_code"] = execute(traced, project, database, output / "build-stderr.log", timeout)
        if report["build_exit_code"] != 0:
            raise ValueError("Traced build failed; partial traces are not a successful dependency check")
        result = analyze(traces, database, project.as_posix())
        report.update({"status": "SUCCEEDED", "findings": result["findings"],
                       "observed_targets": result["observed_targets"]})
        for name, key in [("actual-graph.json", "actual_graph"), ("declared-graph.json", "declared_graph"), ("processes.json", "processes")]:
            (output / name).write_text(json.dumps(result[key], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["artifacts"] = {"actual_graph": "actual-graph.json", "declared_graph": "declared-graph.json",
                               "processes": "processes.json", "make_database": "make-db.txt", "trace_directory": "trace"}
    except TimeoutError as exc:
        report.update(status="TIMED_OUT", error_code="TIMEOUT", error=str(exc))
    except (ValueError, OSError) as exc:
        report.update(status="FAILED", error_code="UNSUPPORTED" if isinstance(exc, Unsupported) else "CHECK_FAILED", error=str(exc))
    report["elapsed_ms"] = round((time.monotonic() - start) * 1000)
    (output / "findings.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
