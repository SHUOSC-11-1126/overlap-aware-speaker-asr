"""Quality-gate orchestrator -- the npm-scripts composition analogue.

code-tape composes its gates with npm scripts (quality:predev / precommit /
ci / local). This repo has no npm, so this module is the single source of
truth that the git hooks and the Makefile both delegate to.

  predev     install hooks + refresh GitNexus index + contract (advisory)
  precommit  fast gate: the full unittest suite (~2s, deterministic, clean)
  ci         precommit gate + project_harness smoke (CI / manual only)
  local      pre-push gate: contract (local) + the fast gate

Interpreter resolution: a git hook runs with whatever ``python3`` is on PATH,
which may not be the project virtualenv. To run the test suite with the right
dependencies we prefer, in order: an active VIRTUAL_ENV, the repo's ``.venv``,
then the current interpreter.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contract_check  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def resolve_python():
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        candidate = Path(venv) / "bin" / "python3"
        if candidate.exists():
            return str(candidate)
    local_venv = REPO_ROOT / ".venv" / "bin" / "python3"
    if local_venv.exists():
        return str(local_venv)
    return sys.executable or "python3"


def run(cmd, label):
    print(f"\n>>> {label}\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    if result.returncode != 0:
        print(f"!!! {label} failed (exit {result.returncode})", file=sys.stderr)
    return result.returncode


def run_tests():
    py = resolve_python()
    return run(
        [py, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-q"],
        "unit test suite",
    )


def run_harness_smoke():
    py = resolve_python()
    return run([py, "-m", "src.project_harness"], "project_harness smoke")


def run_contract(mode):
    print(f"\n>>> contract ({mode})")
    return contract_check.run_contract(mode)


def run_entropy_guard():
    """Advisory research-workspace hygiene signal. Warns (never fails) when the
    working-tree diff adds ceremony files faster than research substance. Any
    error here is swallowed so it can never block the pre-dev flow."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import entropy_guard  # noqa: E402

        entropy_guard.run_guard()
    except Exception as err:  # pragma: no cover - advisory must never block
        print(f"research-entropy guard skipped: {err}")


def cmd_predev():
    rc = contract_check.run_bootstrap()
    rc |= run_contract("local")
    run_entropy_guard()  # advisory only; intentionally does not affect rc
    return rc


def cmd_precommit():
    return run_tests()


def cmd_ci():
    rc = run_tests()
    rc |= run_harness_smoke()
    return rc


def cmd_local():
    rc = run_contract("local")
    rc |= run_tests()
    return rc


COMMANDS = {
    "predev": cmd_predev,
    "precommit": cmd_precommit,
    "ci": cmd_ci,
    "local": cmd_local,
}


def main(argv):
    command = argv[1] if len(argv) > 1 else "precommit"
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"unknown quality command: {command} (choose from {', '.join(COMMANDS)})", file=sys.stderr)
        return 2
    return 1 if handler() else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
