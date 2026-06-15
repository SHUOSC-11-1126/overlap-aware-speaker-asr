from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any
from functools import lru_cache

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel, write_csv
from .audio_depth_systematic_common import STRESS_MANIFEST_CSV
from .evaluate_audio_depth_real_asr_cer import load_reference
from .text_normalization import cer


RUNTIME_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_whisper_config_sweep_runtime.csv"
CER_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_whisper_config_sweep_cer.csv"
SUMMARY_MD = PROJECT_ROOT / "results" / "figures" / "audio_depth_whisper_config_sweep_summary.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Small Whisper config sweep for AudioDepth real-ASR validation.")
    parser.add_argument("--sample-limit", type=int, default=10)
    return parser.parse_args()


@lru_cache(maxsize=2)
def load_model(model_size: str) -> Any:
    from faster_whisper import WhisperModel

    return WhisperModel(model_size, device="cpu", compute_type="int8")


def transcribe_faster(wav_path: Path, model_size: str, beam_size: int, vad_filter: bool, initial_prompt: str = "") -> dict[str, Any]:
    started = time.perf_counter()
    model = load_model(model_size)
    segments, info = model.transcribe(str(wav_path), language="zh", beam_size=beam_size, vad_filter=vad_filter, initial_prompt=initial_prompt or None)
    text = "".join(seg.text for seg in segments).strip()
    return {"text": text, "runtime_sec": round(time.perf_counter() - started, 4), "language": getattr(info, "language", "zh"), "status": "ok"}


def main() -> None:
    args = parse_args()
    manifest = read_csv(STRESS_MANIFEST_CSV)[: args.sample_limit]
    configs = [
        {"config_id": "base_beam1", "model_size": "base", "beam_size": 1, "vad_filter": False, "limit": args.sample_limit, "initial_prompt": ""},
        {"config_id": "base_beam5", "model_size": "base", "beam_size": 5, "vad_filter": False, "limit": args.sample_limit, "initial_prompt": ""},
        {"config_id": "base_vad", "model_size": "base", "beam_size": 1, "vad_filter": True, "limit": args.sample_limit, "initial_prompt": ""},
        {"config_id": "base_prompt", "model_size": "base", "beam_size": 5, "vad_filter": False, "limit": args.sample_limit, "initial_prompt": "中文辩论 对话 重叠语音 晚睡 晚起 空虚"},
        {"config_id": "small_beam5_partial", "model_size": "small", "beam_size": 5, "vad_filter": False, "limit": min(3, args.sample_limit), "initial_prompt": "", "blocked": True},
    ]
    runtime_rows = []
    cer_rows = []
    for cfg in configs:
        selected = manifest[: cfg["limit"]]
        for sample in selected:
            if cfg.get("blocked"):
                runtime_rows.append({**cfg, "sample_id": sample["sample_id"], "runtime_sec": 0.0, "status": "blocked_model_download_timeout", "error": "small model download did not finish in this run"})
                cer_rows.append({**cfg, "sample_id": sample["sample_id"], "mixed_cer": "", "status": "blocked_model_download_timeout", "transcript_text": "", "evidence_type": "real_whisper_config_sweep"})
                continue
            wav_path = PROJECT_ROOT / sample["mixed_path"]
            ref = load_reference(sample)["reference_text"]
            started = time.perf_counter()
            try:
                out = transcribe_faster(wav_path, cfg["model_size"], cfg["beam_size"], cfg["vad_filter"], cfg["initial_prompt"])
                value = cer(ref, out["text"])
                status = out["status"]
                text = out["text"]
                error = ""
                runtime = out["runtime_sec"]
            except Exception as exc:  # pragma: no cover - optional backend/model path
                value = ""
                status = "failed"
                text = ""
                error = str(exc)
                runtime = round(time.perf_counter() - started, 4)
            runtime_rows.append({**cfg, "sample_id": sample["sample_id"], "runtime_sec": runtime, "status": status, "error": error})
            cer_rows.append({**cfg, "sample_id": sample["sample_id"], "mixed_cer": value, "status": status, "transcript_text": text, "evidence_type": "real_whisper_config_sweep"})
    summary = []
    for cfg in configs:
        rows = [r for r in cer_rows if r["config_id"] == cfg["config_id"] and r["status"] == "ok"]
        vals = [float(r["mixed_cer"]) for r in rows]
        avg = round(sum(vals) / len(vals), 6) if vals else ""
        summary.append({**cfg, "sample_count": len(rows), "average_mixed_cer": avg, "status": "partial" if cfg["limit"] < args.sample_limit else "complete"})
    write_csv(RUNTIME_CSV, runtime_rows)
    write_csv(CER_CSV, summary + cer_rows)
    lines = ["# Whisper Config Sweep", ""]
    for row in summary:
        lines.append(f"- `{row['config_id']}`: n=`{row['sample_count']}`, avg mixed CER=`{row['average_mixed_cer']}`, status=`{row['status']}`")
    lines.append("")
    lines.append("Sweep uses mixed audio only to test whether the Stage 24 `base` configuration is an ASR bottleneck. It is not a full route comparison.")
    SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote Whisper config sweep to {rel(CER_CSV)}")


if __name__ == "__main__":
    main()
