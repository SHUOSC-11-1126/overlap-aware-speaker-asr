from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel, write_csv
from .audio_depth_systematic_common import STRESS_MANIFEST_CSV
from .whisper_backend import transcribe_audio


TRANSCRIPT_DIR = PROJECT_ROOT / "results" / "transcripts_audio_depth_real_asr"
RUNTIME_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_runtime.csv"
TRANSCRIPTS_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_transcripts.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run sampled real Whisper ASR on AudioDepth stress benchmark.")
    parser.add_argument("--sample-limit", type=int, default=30)
    parser.add_argument("--backend", default="auto")
    parser.add_argument("--model-size", default="small")
    parser.add_argument("--language", default="zh")
    return parser.parse_args()


def clean_text(text: str) -> str:
    text = re.sub(r"\[SPEAKER_[12]\]", "", text)
    text = re.sub(r"\s+", "", text)
    return text.strip()


def write_transcript(sample_id: str, route: str, payload: dict[str, Any]) -> str:
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = TRANSCRIPT_DIR / f"{sample_id}_{route}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return rel(path)


def transcribe_route(sample: dict[str, str], route: str, wav_key: str, args: argparse.Namespace) -> dict[str, Any]:
    wav = PROJECT_ROOT / sample[wav_key]
    payload = transcribe_audio(str(wav), model_size=args.model_size, backend=args.backend, language=args.language)
    payload.update({"sample_id": sample["sample_id"], "route": route, "wav_path": sample[wav_key], "evidence_type": "real_whisper_asr"})
    output_path = write_transcript(sample["sample_id"], route, payload)
    return {
        "sample_id": sample["sample_id"],
        "route": route,
        "backend": payload.get("backend", args.backend),
        "model_size": payload.get("model_size", args.model_size),
        "language": payload.get("language", args.language),
        "status": payload.get("status", "failed"),
        "runtime_sec": payload.get("runtime_sec", 0.0),
        "wav_path": sample[wav_key],
        "transcript_path": output_path,
        "text": payload.get("text", ""),
        "error": payload.get("error", ""),
        "evidence_type": "real_whisper_asr",
    }


def main() -> None:
    args = parse_args()
    manifest = read_csv(STRESS_MANIFEST_CSV)
    if args.sample_limit:
        manifest = manifest[: args.sample_limit]
    transcript_rows: list[dict[str, Any]] = []
    runtime_rows: list[dict[str, Any]] = []
    started_all = time.perf_counter()
    for sample in manifest:
        sample_started = time.perf_counter()
        mixed = transcribe_route(sample, "mixed", "mixed_path", args)
        transcript_rows.append(mixed)
        if sample.get("spk1_path") and sample.get("spk2_path"):
            spk1 = transcribe_route(sample, "spk1", "spk1_path", args)
            spk2 = transcribe_route(sample, "spk2", "spk2_path", args)
            transcript_rows.extend([spk1, spk2])
            separated_text = f"[SPEAKER_1] {spk1.get('text', '')}\n[SPEAKER_2] {spk2.get('text', '')}".strip()
            separated_payload = {
                "sample_id": sample["sample_id"],
                "route": "separated",
                "backend": "merge:" + str(spk1.get("backend", args.backend)),
                "model_size": args.model_size,
                "language": args.language,
                "text": separated_text,
                "segments": [],
                "runtime_sec": round(float(spk1.get("runtime_sec") or 0.0) + float(spk2.get("runtime_sec") or 0.0), 4),
                "status": "ok" if spk1.get("status") == "ok" and spk2.get("status") == "ok" else "failed",
                "evidence_type": "real_whisper_asr_merged_speakers",
            }
            separated_path = write_transcript(sample["sample_id"], "separated", separated_payload)
            cleaned_payload = {**separated_payload, "route": "cleaned", "text": clean_text(separated_text), "evidence_type": "text_cleanup_from_real_whisper_separated"}
            cleaned_path = write_transcript(sample["sample_id"], "cleaned", cleaned_payload)
            transcript_rows.extend(
                [
                    {**separated_payload, "wav_path": f"{sample['spk1_path']}|{sample['spk2_path']}", "transcript_path": separated_path, "error": ""},
                    {**cleaned_payload, "wav_path": f"{sample['spk1_path']}|{sample['spk2_path']}", "transcript_path": cleaned_path, "error": ""},
                ]
            )
        else:
            transcript_rows.append(
                {
                    "sample_id": sample["sample_id"],
                    "route": "separated",
                    "backend": args.backend,
                    "model_size": args.model_size,
                    "language": args.language,
                    "status": "separated_missing",
                    "runtime_sec": 0.0,
                    "wav_path": "",
                    "transcript_path": "",
                    "text": "",
                    "error": "separated tracks missing",
                    "evidence_type": "real_whisper_asr_blocked",
                }
            )
        runtime_rows.append(
            {
                "sample_id": sample["sample_id"],
                "backend_request": args.backend,
                "model_size": args.model_size,
                "language": args.language,
                "sample_runtime_sec": round(time.perf_counter() - sample_started, 4),
                "routes_written": sum(1 for row in transcript_rows if row["sample_id"] == sample["sample_id"]),
            }
        )
    runtime_rows.append(
        {
            "sample_id": "__total__",
            "backend_request": args.backend,
            "model_size": args.model_size,
            "language": args.language,
            "sample_runtime_sec": round(time.perf_counter() - started_all, 4),
            "routes_written": len(transcript_rows),
        }
    )
    write_csv(TRANSCRIPTS_CSV, transcript_rows)
    write_csv(RUNTIME_CSV, runtime_rows)
    print(f"Wrote {len(transcript_rows)} transcript rows to {rel(TRANSCRIPTS_CSV)}")


if __name__ == "__main__":
    main()
