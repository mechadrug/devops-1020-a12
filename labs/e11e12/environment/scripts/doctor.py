#!/usr/bin/env python3
"""E4 服务器与 Git 身份自检，结果写成 env.json。

用法：python3 scripts/doctor.py [--out work/<时间>/env.json]
必需项缺失时退出码为 1；“建议”项只给出提示。
编译器、strace 等工具在服务镜像里，宿主机只需要 Docker、Git、Make、Python。
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

MIN = {"cpus": 2, "mem_gib": 4, "disk_gib": 40}        # 最低
REC = {"cpus": 4, "mem_gib": 8, "disk_gib": 100}       # 建议（DRAFT 后续要构建真实项目）

TOOLS = [  # (名称, 版本命令, 是否必需)
    ("docker", ["docker", "version", "--format", "{{.Server.Version}}"], True),
    ("compose", ["docker", "compose", "version", "--short"], True),
    ("buildx", ["docker", "buildx", "version"], False),
    ("git", ["git", "--version"], True),
    ("make", ["make", "--version"], True),
    ("python3", ["python3", "--version"], True),
]
SOCK = "/var/run/docker.sock"


def sh(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return p.returncode, (p.stdout or p.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


def os_release():
    try:
        text = Path("/etc/os-release").read_text()
        return dict(re.findall(r'^(\w+)="?([^"\n]*)"?$', text, re.M)).get("PRETTY_NAME", "unknown")
    except OSError:
        return platform.platform()


def mem_gib():
    try:
        kb = int(re.search(r"MemTotal:\s+(\d+)", Path("/proc/meminfo").read_text()).group(1))
        return round(kb / 1024 / 1024, 1)
    except (OSError, AttributeError):
        return None


def git_identity(env):
    """每人在自己的克隆目录里用 git config（不加 --global）设置学号。"""
    _, name = sh(["git", "config", "--local", "user.name"])
    _, email = sh(["git", "config", "--local", "user.email"])
    _, global_name = sh(["git", "config", "--global", "user.name"])
    env["git"] = {"user.name": name or None, "user.email": email or None}
    if not name or not email:
        env["problems"].append("本仓库未设置提交身份：git config user.name <学号>；git config user.email <邮箱>（不要加 --global）")
    elif not re.fullmatch(r"[A-Za-z]{0,3}\d{6,12}", name):
        env["warnings"].append(f"user.name={name} 看起来不是学号，课程要求统一使用学号")
    if global_name:
        env["warnings"].append(f"服务器上设置了全局身份 user.name={global_name}；组员共用一个登录账号，建议删除：git config --global --unset user.name")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="env.json 输出路径")
    args = ap.parse_args()

    disk = shutil.disk_usage("/var/lib/docker" if os.path.isdir("/var/lib/docker") else "/")
    spec = {"cpus": os.cpu_count(), "mem_gib": mem_gib(), "disk_gib": round(disk.free / 2**30, 1)}
    env = {"time": datetime.now(timezone.utc).isoformat(), "hostname": platform.node(),
           "os": os_release(), "kernel": platform.release(), "arch": platform.machine(),
           "spec": spec, "tools": {}, "problems": [], "warnings": []}

    if platform.system() != "Linux":
        env["problems"].append("不是 Linux：课程命令需要在分配的 Linux 服务器上执行")
    for key, low in MIN.items():
        if spec[key] is not None and spec[key] < low:
            env["problems"].append(f"{key}={spec[key]} 低于最低要求 {low}")
        elif spec[key] is not None and spec[key] < REC[key]:
            env["warnings"].append(f"{key}={spec[key]} 低于建议值 {REC[key]}")

    for name, cmd, required in TOOLS:
        code, out = sh(cmd)
        env["tools"][name] = out.splitlines()[0] if code == 0 and out else None
        if code != 0:
            msg = f"{name} 不可用：{out.splitlines()[-1] if out else 'not found'}"
            if name == "docker" and "permission denied" in out.lower():
                msg = "当前用户无权访问 Docker：执行 sudo usermod -aG docker $USER，然后重新登录"
            (env["problems"] if required else env["warnings"]).append(msg)

    env["docker_sock_gid"] = os.stat(SOCK).st_gid if os.path.exists(SOCK) else None
    code, info = sh(["docker", "info", "--format", "{{json .RegistryConfig.Mirrors}}"])
    env["registry_mirrors"] = json.loads(info) if code == 0 and info.startswith("[") else None
    if code == 0 and not env["registry_mirrors"]:
        env["warnings"].append("Docker 未配置镜像加速，拉取基础镜像可能很慢（见 setup/bootstrap_ubuntu.sh）")

    git_identity(env)

    text = json.dumps(env, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    print("\n环境自检：" + ("通过" if not env["problems"] else f"{len(env['problems'])} 个必需项未满足"))
    raise SystemExit(1 if env["problems"] else 0)


if __name__ == "__main__":
    main()
