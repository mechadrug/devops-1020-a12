"""Deliberately wrong oracle for the protected-branch teaching demonstration.

Capture failed CI and merge rejection before correcting the expected code.
"""
from buildchecker.cli import main


def test_intentionally_wrong_version_exit_code():
    assert main(["version"]) == 1, "Intentional teaching fault: version actually returns zero"
