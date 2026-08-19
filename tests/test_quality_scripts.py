from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.bench_quality_gate import run_tests


class TestBenchQualityGate(unittest.TestCase):
    def test_zero_exit_with_failed_transcript_is_rejected(self) -> None:
        with (
            contextlib.redirect_stdout(io.StringIO()),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            run_tests(
                [sys.executable, "-c", "print('FAILED (errors=1)')"],
                cwd=Path.cwd(),
                env=dict(),
            )

    def test_transcript_without_terminal_ok_is_rejected(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
            run_tests(
                [sys.executable, "-c", "print('Ran 1 test')"],
                cwd=Path.cwd(),
                env=dict(),
            )

    def test_terminal_ok_is_accepted(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            run_tests(
                [sys.executable, "-c", "print('Ran 1 test\\n\\nOK')"],
                cwd=Path.cwd(),
                env=dict(),
            )


if __name__ == "__main__":
    unittest.main()
