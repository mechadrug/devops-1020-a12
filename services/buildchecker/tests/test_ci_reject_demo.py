"""Corrected oracle after the protected-branch rejection demonstration.

This restores the documented success exit code. The implementation is unchanged.
"""
from buildchecker.cli import main


def test_version_returns_success_exit_code():
    assert main(["version"]) == 0
