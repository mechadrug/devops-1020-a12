"""CLI keeps E4 version/smoke and adds the E6 full-check command."""
import argparse
import json
from . import __version__
from .smoke import run_smoke
from .fullcheck import full_check

def build_parser():
    parser = argparse.ArgumentParser(prog="buildchecker")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version")
    smoke = sub.add_parser("smoke")
    smoke.add_argument("--fixture", default="fixtures/md-rd")
    full = sub.add_parser("full-check")
    full.add_argument("--fixture", default="fixtures/md-rd")
    full.add_argument("--out", required=True)
    full.add_argument("--clean-command", default="make clean")
    full.add_argument("--build-command", default="make app")
    full.add_argument("--timeout", type=int, default=120)
    full.add_argument("--fail-on-findings", action="store_true")
    return parser

def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "version":
        print(f"buildchecker {__version__}")
        return 0
    if args.cmd == "smoke":
        result = run_smoke(args.fixture)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 1
    try:
        if args.timeout <= 0:
            raise ValueError("Timeout must be positive")
        result = full_check(args.fixture, args.out, args.clean_command, args.build_command, args.timeout)
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "FAILED", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "SUCCEEDED" and not (args.fail_on_findings and result["findings"]) else 1
