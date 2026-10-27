"""E4 冒烟测试：确认容器内的 make、gcc、strace 能配合工作。

做法：把样例复制到临时目录（不改动原样例），用 strace 跟踪一次 clean build，
然后只做最简单的检查：跟踪记录里能看到 config.h 被打开。
这不是 BuildChecker 的检测算法；按进程归属、比较声明依赖是 E5/E6 的内容。
"""
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout + p.stderr


def files_opened(trace_text, name):
    """返回跟踪记录中打开了 name 的行（open/openat）。"""
    pat = re.compile(r'\bopen(?:at)?\(.*"(?:[^"]*/)?' + re.escape(name) + r'"')
    return [line for line in trace_text.splitlines() if pat.search(line)]


def run_smoke(fixture):
    src = Path(fixture)
    with tempfile.TemporaryDirectory(prefix="e4-smoke-") as tmp:
        work = Path(tmp) / src.name
        shutil.copytree(src, work)
        tools = {name: run([name, "--version"], work)[1].splitlines()[0] for name in ("make", "gcc", "strace")}
        code, out = run(["strace", "-f", "-o", "trace.txt", "-e", "trace=%file,%process", "make"], work)
        trace = (work / "trace.txt").read_text() if (work / "trace.txt").exists() else ""
        _, app_out = run(["./app"], work) if code == 0 else (None, "")
        config = files_opened(trace, "config.h")
        unused = files_opened(trace, "unused.h")
    return {
        "fixture": str(src),
        "tools": tools,
        "make_exit_code": code,
        "make_output": out.strip().splitlines()[-5:],
        "app_output": app_out.strip(),
        "trace_lines": len(trace.splitlines()),
        "config_h_opened": config[:3],
        "unused_h_opened": unused[:3],
        "passed": code == 0 and bool(config),
        "note": "只说明环境可用；config.h / unused.h 的结论留到 E5 由各组自己推导",
    }
