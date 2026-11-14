import argparse
import json
from . import __version__
from .smoke import run_smoke
from .autobuild import auto_build

def build_parser():
    ap = argparse.ArgumentParser(prog="draft")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version")
    sp = sub.add_parser("smoke")
    sp.add_argument("--fixture", default="fixtures/draft")
    sp.add_argument("--tag", default="e4-smoke-broken:latest")
    sp = sub.add_parser("auto-build", help="Replay a manual candidate through builds and verification")
    sp.add_argument("--fixture", default="fixtures/draft")
    sp.add_argument("--candidate", required=True)
    sp.add_argument("--out", required=True)
    sp.add_argument("--expected-output", required=True)
    sp.add_argument("--timeout", type=int, default=300)
    sp.add_argument("--verify-timeout", type=int, default=30)
    return ap

def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "version":
        print(f"draft {__version__}")
        return 0
    if args.cmd == "smoke":
        result = run_smoke(args.fixture, args.tag)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 1
    try:
        result = auto_build(args.fixture, args.candidate, args.out, args.expected_output, args.timeout, args.verify_timeout)
    except (ValueError, OSError) as exc:
        result = {"status": "FAILED", "error": str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "SUCCEEDED" else 1
