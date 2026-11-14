"""Assert saved before/after reports without rerunning the experiment."""
import argparse
import json
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    args = parser.parse_args()
    try:
        before = json.loads(Path(args.before).read_text(encoding="utf-8"))
        after = json.loads(Path(args.after).read_text(encoding="utf-8"))
        for label, report in (("before", before), ("after", after)):
            if report.get("status") != "SUCCEEDED" or report.get("clean_exit_code") != 0 or report.get("build_exit_code") != 0:
                raise ValueError(f"{label}: detection/clean/build did not succeed")
        expected = {("MISSING", "main.o", "config.h"), ("REDUNDANT", "main.o", "unused.h")}
        found = [(item["type"], item["target"], item["dependency"]) for item in before["findings"]]
        if len(found) != 2 or set(found) != expected:
            raise ValueError(f"Unexpected before findings: {found}")
        if after["findings"] != []:
            raise ValueError("Findings remain after repair")
        old, new = before["input_sha256"], after["input_sha256"]
        if set(old) != set(new):
            raise ValueError("Input file sets differ")
        changed = sorted(name for name in old if old[name] != new[name])
        if changed != ["Makefile"]:
            raise ValueError(f"Expected only Makefile to change, got {changed}")
        result = {"passed": True, "before_findings": 2, "after_findings": 0,
                  "changed_inputs": changed, "before_trace_id": before["trace_id"],
                  "after_trace_id": after["trace_id"],
                  "scope": "Saved report assertions; raw traces are not independently revalidated"}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
