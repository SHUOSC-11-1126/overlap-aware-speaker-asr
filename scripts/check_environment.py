from __future__ import annotations

import importlib.util
import platform
import sys
import argparse
from dataclasses import dataclass


RECOMMENDED_PYTHON = (3, 12)

CORE_IMPORTS = {
    "PyYAML": "yaml",
    "numpy": "numpy",
    "scipy": "scipy",
    "soundfile": "soundfile",
    "matplotlib": "matplotlib",
}

ASR_IMPORTS = {
    "openai-whisper": "whisper",
    "faster-whisper": "faster_whisper",
}

OPTIONAL_IMPORTS = {
    "torch": "torch",
    "sklearn": "sklearn",
    "librosa": "librosa",
}


@dataclass
class CheckRow:
    name: str
    status: str
    detail: str


def import_status(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def collect_report() -> tuple[list[CheckRow], bool]:
    rows: list[CheckRow] = []
    ok = True
    version = sys.version_info
    recommended = version.major == RECOMMENDED_PYTHON[0] and version.minor == RECOMMENDED_PYTHON[1]
    rows.append(
        CheckRow(
            "python",
            "ok" if recommended else "warn",
            f"running {platform.python_version()}; recommended {RECOMMENDED_PYTHON[0]}.{RECOMMENDED_PYTHON[1]}.x",
        )
    )
    in_venv = sys.prefix != sys.base_prefix
    rows.append(CheckRow("virtualenv", "ok" if in_venv else "warn", "active" if in_venv else "not detected"))

    for package, module in CORE_IMPORTS.items():
        present = import_status(module)
        ok = ok and present
        rows.append(CheckRow(package, "ok" if present else "missing", f"import {module}"))

    asr_present = False
    for package, module in ASR_IMPORTS.items():
        present = import_status(module)
        asr_present = asr_present or present
        rows.append(CheckRow(package, "ok" if present else "optional-missing", f"import {module}"))
    if not asr_present:
        rows.append(CheckRow("asr-runtime", "warn", "install openai-whisper or faster-whisper before real ASR reruns"))

    for package, module in OPTIONAL_IMPORTS.items():
        present = import_status(module)
        rows.append(CheckRow(package, "ok" if present else "optional-missing", f"import {module}"))

    rows.append(CheckRow("test-runner", "ok", "use python -m unittest discover; pytest is not required"))
    return rows, ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local project environment readiness.")
    parser.add_argument("--strict", action="store_true", help="exit non-zero when core dependencies are missing")
    args = parser.parse_args()
    rows, ok = collect_report()
    width = max(len(row.name) for row in rows)
    print("Environment doctor")
    print("==================")
    for row in rows:
        print(f"{row.name:<{width}}  {row.status:<16}  {row.detail}")
    if not ok and not args.strict:
        print("\nCore dependencies are missing; install requirements.txt before rerunning experiments.")
    return 0 if ok or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
