"""Pytest wrapper — runs evals/run_evals.py and asserts all scenarios pass."""
import subprocess
import sys
from pathlib import Path

_EVALS_SCRIPT = Path(__file__).resolve().parent.parent.parent / "evals" / "run_evals.py"


def test_all_eval_scenarios_pass():
    result = subprocess.run(
        [sys.executable, str(_EVALS_SCRIPT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Evals failed:\n{result.stdout}\n{result.stderr}"
    )
