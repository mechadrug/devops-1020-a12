import importlib.util
from pathlib import Path
import unittest

gate_path = next(parent / "scripts/run_e7_a_gate.py" for parent in Path(__file__).resolve().parents
                 if (parent / "scripts/run_e7_a_gate.py").is_file())
spec = importlib.util.spec_from_file_location("gate", gate_path)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def successful(findings):
    return {"trace_id": "test", "status": "SUCCEEDED", "build_exit_code": 0, "clean_exit_code": 0, "findings": findings}

class OracleTests(unittest.TestCase):
    def test_exact_errors_rejected_by_cli(self):
        findings = [{"type": t, "target": target, "dependency": dep, "evidence": ["test"]} for t, target, dep in gate.EXPECTED]
        gate.evaluate("original-1", 1, successful(findings))
        with self.assertRaises(ValueError):
            gate.evaluate("original-1", 0, successful(findings))

    def test_empty_broken_report_does_not_pass(self):
        with self.assertRaises(ValueError):
            gate.evaluate("original-1", 1, successful([]))

    def test_fixed_passes(self):
        gate.evaluate("fixed", 0, successful([]))

    def test_failed_build_not_counted_as_fixed(self):
        with self.assertRaises(ValueError):
            gate.evaluate("fixed", 0, {"trace_id": "test", "status": "FAILED", "findings": []})

    def test_explicit_unsupported(self):
        gate.evaluate("unsupported", 1, {"trace_id": "test", "status": "FAILED", "error_code": "UNSUPPORTED", "build_exit_code": 0})

    def test_timeout_requires_failure_exit(self):
        report = {"trace_id": "test", "status": "TIMED_OUT", "error_code": "TIMEOUT"}
        gate.evaluate("timeout", 1, report)
        with self.assertRaises(ValueError):
            gate.evaluate("timeout", 0, report)

if __name__ == "__main__":
    unittest.main()
