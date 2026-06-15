from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .audio_depth_router_common import PROJECT_ROOT, rel


TABLE_PATH = PROJECT_ROOT / "results" / "tables" / "whisper_env_diagnosis.json"
FIGURE_PATH = PROJECT_ROOT / "results" / "figures" / "whisper_env_diagnosis.md"


def module_status(name: str) -> dict[str, Any]:
    spec = importlib.util.find_spec(name)
    info: dict[str, Any] = {"available": bool(spec)}
    if not spec:
        return info
    try:
        module = __import__(name)
        info["version"] = getattr(module, "__version__", "unknown")
    except Exception as exc:  # pragma: no cover - diagnostic path
        info["available"] = False
        info["error"] = str(exc)
    return info


def command_output(cmd: list[str]) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
        return {"returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}
    except Exception as exc:  # pragma: no cover - diagnostic path
        return {"returncode": -1, "stdout": "", "stderr": str(exc)}


def choose_backend(faster: dict[str, Any], openai: dict[str, Any]) -> str:
    if faster.get("available"):
        return "faster-whisper"
    if openai.get("available"):
        return "openai-whisper"
    return "unavailable"


def main() -> None:
    ffmpeg = shutil.which("ffmpeg")
    faster = module_status("faster_whisper")
    openai = module_status("whisper")
    torch = module_status("torch")
    soundfile = module_status("soundfile")
    payload = {
        "python_version": sys.version,
        "python_executable": sys.executable,
        "which_python": shutil.which("python"),
        "ffmpeg_path": ffmpeg,
        "ffmpeg_available": bool(ffmpeg),
        "torch": torch,
        "openai_whisper": openai,
        "faster_whisper": faster,
        "soundfile": soundfile,
        "selected_backend": choose_backend(faster, openai),
        "checks": {
            "python_version": command_output([sys.executable, "--version"]),
            "ffmpeg_version": command_output([ffmpeg, "-version"]) if ffmpeg else {"returncode": 127, "stdout": "", "stderr": "ffmpeg not found"},
        },
    }
    missing = []
    if not ffmpeg:
        missing.append("system ffmpeg command is not available; faster-whisper can still use PyAV, openai-whisper usually needs ffmpeg")
    if not faster.get("available") and not openai.get("available"):
        missing.append("no Whisper backend is importable")
    payload["missing_or_limitations"] = missing
    TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TABLE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Whisper Environment Diagnosis",
        "",
        f"- Python: `{sys.executable}`",
        f"- Python version: `{sys.version.split()[0]}`",
        f"- ffmpeg: `{ffmpeg or 'missing'}`",
        f"- torch: `{torch.get('available')}` version `{torch.get('version', '')}`",
        f"- faster-whisper: `{faster.get('available')}` version `{faster.get('version', '')}`",
        f"- openai-whisper: `{openai.get('available')}` version `{openai.get('version', '')}`",
        f"- soundfile: `{soundfile.get('available')}` version `{soundfile.get('version', '')}`",
        f"- selected backend: `{payload['selected_backend']}`",
        "",
        "## Missing Or Limitations",
        "",
    ]
    lines.extend([f"- {item}" for item in missing] or ["- none for faster-whisper sampled validation"])
    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIGURE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote diagnosis to {rel(TABLE_PATH)} and {rel(FIGURE_PATH)}")


if __name__ == "__main__":
    main()
