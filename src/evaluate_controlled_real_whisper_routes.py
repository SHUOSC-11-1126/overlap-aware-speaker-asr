from __future__ import annotations

import argparse
import time

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel, write_csv
from .controlled_benchmark_common import CER_CSV, RUNTIME_CSV, TRANSCRIPTS_CSV, clean_route_text, compute_route_cers
from .controlled_benchmark_common import MANIFEST_CSV
from .whisper_backend import transcribe_audio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate controlled benchmark routes with real Whisper.")
    parser.add_argument("--sample-limit", type=int, default=40)
    parser.add_argument("--model-size", default="base")
    parser.add_argument("--backend", default="auto")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_csv(MANIFEST_CSV)[: args.sample_limit]
    tx_rows = []
    cer_rows = []
    runtime_rows = []
    started_all = time.perf_counter()
    cache: dict[str, dict] = {}

    def transcribe(path: str, sample_id: str, route: str) -> dict:
        key = f"{path}|{args.model_size}|{args.backend}"
        if key not in cache:
            cache[key] = transcribe_audio(str(PROJECT_ROOT / path), model_size=args.model_size, backend=args.backend, language="zh")
        out = cache[key]
        tx_rows.append(
            {
                "sample_id": sample_id,
                "route": route,
                "wav_path": path,
                "backend": out.get("backend", args.backend),
                "model_size": out.get("model_size", args.model_size),
                "status": out.get("status", "failed"),
                "runtime_sec": out.get("runtime_sec", 0.0),
                "text": out.get("text", ""),
                "error": out.get("error", ""),
            }
        )
        return out

    for row in rows:
        t0 = time.perf_counter()
        mixed = transcribe(row["mixed_path"], row["sample_id"], "mixed")
        spk1 = transcribe(row["spk1_path"], row["sample_id"], "spk1")
        spk2 = transcribe(row["spk2_path"], row["sample_id"], "spk2")
        separated = f"[SPEAKER_1] {spk1.get('text', '')}\n[SPEAKER_2] {spk2.get('text', '')}"
        cleaned = clean_route_text(separated)
        tx_rows.append({**tx_rows[-1], "sample_id": row["sample_id"], "route": "separated", "wav_path": f"{row['spk1_path']}|{row['spk2_path']}", "text": separated, "status": "ok", "runtime_sec": round(float(spk1.get("runtime_sec", 0.0)) + float(spk2.get("runtime_sec", 0.0)), 4), "error": ""})
        tx_rows.append({**tx_rows[-1], "route": "cleaned", "text": cleaned})
        metrics = compute_route_cers(row["reference_text"], mixed.get("text", ""), separated, cleaned)
        cer_rows.append(
            {
                "sample_id": row["sample_id"],
                "split": row.get("split", ""),
                "overlap_ratio": row["overlap_ratio"],
                "dominance_type": row["dominance_type"],
                "style": row["style"],
                "duration": row["duration"],
                "reference_type": row["reference_type"],
                **metrics,
            }
        )
        runtime_rows.append({"sample_id": row["sample_id"], "sample_runtime_sec": round(time.perf_counter() - t0, 4), "model_size": args.model_size})
    runtime_rows.append({"sample_id": "__total__", "sample_runtime_sec": round(time.perf_counter() - started_all, 4), "model_size": args.model_size})
    write_csv(TRANSCRIPTS_CSV, tx_rows)
    write_csv(CER_CSV, cer_rows)
    write_csv(RUNTIME_CSV, runtime_rows)
    print(f"Wrote controlled route CER for {len(cer_rows)} samples to {rel(CER_CSV)}")


if __name__ == "__main__":
    main()
