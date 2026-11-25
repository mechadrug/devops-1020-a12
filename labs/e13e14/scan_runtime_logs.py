"""Scan E13/E14 work evidence for likely secrets without printing full values.

Usage: python3 scan_runtime_logs.py work/e13-pair-01 [work/e14-real-01 ...]
Exit: 0 = no hits, 1 = hits, 2 = no readable text or incomplete scan.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PATTERNS = (
    ("LLM/API Key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("secret assignment", re.compile(r"(?i)\b[\w.-]*(?:api[_-]?key|secret|token|passw(?:or)?d)\b\s*[:=]\s*[\"']?([^\s\"'#,;]{12,})")),
)
PLACEHOLDER = re.compile(r"(?i)replace|your[_-]|example|changeme|xxxx|<[^>]*>|\$\{|\$\(|\*\*\*")


def candidates(root: Path):
    if root.is_symlink():
        return
    if root.is_file():
        yield root
    elif root.is_dir():
        for path in sorted(root.rglob("*")):
            if path.is_file() and not path.is_symlink() and ".git" not in path.parts:
                yield path


def mask(value: str) -> str:
    return value[:4] + "***" if len(value) > 4 else "***"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Scan text evidence directories for likely secrets")
    parser.add_argument("paths", nargs="+", type=Path, help="work directories or text log files")
    args = parser.parse_args(argv)
    hits = 0
    checked = 0
    errors = 0
    for root in args.paths:
        if not root.exists():
            print(f"SCAN_ERROR missing path: {root}", file=sys.stderr)
            errors += 1
            continue
        for path in candidates(root):
            try:
                with path.open("rb") as raw:
                    if b"\x00" in raw.read(4096):
                        continue
                with path.open("r", encoding="utf-8", errors="replace") as stream:
                    checked += 1
                    for lineno, line in enumerate(stream, 1):
                        for name, pattern in PATTERNS:
                            for match in pattern.finditer(line):
                                value = match.group(match.lastindex or 0)
                                if name == "secret assignment":
                                    # Parser source may assign a token pointer from a
                                    # function call or array. That is code, not a
                                    # hard-coded credential.
                                    if PLACEHOLDER.search(value) or value.startswith("&") or "(" in value or "[" in value:
                                        continue
                                print(f"FOUND {path}:{lineno} {name} {mask(value)}")
                                hits += 1
            except OSError as exc:
                print(f"SCAN_ERROR {path}: {exc.__class__.__name__}", file=sys.stderr)
                errors += 1
    print(f"runtime log scan: text_files={checked} hits={hits} errors={errors}")
    if errors or checked == 0:
        return 2
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
