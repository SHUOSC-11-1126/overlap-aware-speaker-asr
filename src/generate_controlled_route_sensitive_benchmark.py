from __future__ import annotations

import argparse
from pathlib import Path

from .audio_depth_router_common import PROJECT_ROOT, read_csv, read_wav_mono, rel, write_csv
from .audio_depth_systematic_common import stable_bucket, write_wav_mono
from .controlled_benchmark_common import (
    CONTROLLED_AUDIO_DIR,
    CONTROLLED_REF_DIR,
    CONTROLLED_ROOT,
    INVENTORY_CSV,
    MANIFEST_CSV,
    VERIFICATION_PACK_CSV,
    mix_pair,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate controlled route-sensitive benchmark.")
    parser.add_argument("--mode", choices=["silver-plus", "verified"], default="silver-plus")
    parser.add_argument("--n-samples", type=int, default=80)
    return parser.parse_args()


def load_sources(mode: str) -> tuple[list[dict[str, str]], str, str]:
    inv = read_csv(INVENTORY_CSV)
    verified: dict[str, str] = {}
    if VERIFICATION_PACK_CSV.exists():
        for row in read_csv(VERIFICATION_PACK_CSV):
            if row.get("verified_transcript", "").strip():
                verified[row["utterance_id"]] = row["verified_transcript"].strip()
    rows = []
    if mode == "verified" and verified:
        for row in inv:
            if row["utterance_id"] in verified:
                rows.append({**row, "benchmark_text": verified[row["utterance_id"]]})
        return rows, "verified_micro_gold", "verified"
    for row in inv:
        if row.get("usable_for_benchmark") == "True":
            rows.append({**row, "benchmark_text": row["transcript_candidate"]})
    downgraded = "verified_requested_but_insufficient_downgraded_to_silver_plus" if mode == "verified" else "silver_plus"
    return rows, "silver_plus_unverified", downgraded


def main() -> None:
    args = parse_args()
    sources, reference_type, mode_status = load_sources(args.mode)
    con = [row for row in sources if row["speaker_id"] == "con"]
    pro = [row for row in sources if row["speaker_id"] == "pro"]
    ratios = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    dominance = ["speaker_A_dominant", "speaker_B_dominant", "balanced"]
    styles = ["clean_turn_taking", "short_backchannel", "medium_overlap", "heavy_overlap", "debate_opposite"]
    durations = ["short", "medium"]
    rows = []
    CONTROLLED_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    CONTROLLED_REF_DIR.mkdir(parents=True, exist_ok=True)
    for idx in range(1, args.n_samples + 1):
        ratio = ratios[(idx - 1) % len(ratios)]
        dom = dominance[((idx - 1) // len(ratios)) % len(dominance)]
        style = styles[((idx - 1) // (len(ratios) * len(dominance))) % len(styles)]
        duration = durations[((idx - 1) // (len(ratios) * len(dominance) * len(styles))) % len(durations)]
        spk1 = con[(idx - 1) % len(con)]
        pro_offset = ((idx - 1) // len(con)) + (idx - 1)
        spk2 = pro[pro_offset % len(pro)]
        sid = f"controlled_route_sensitive_v1_{idx:04d}"
        audio1, sr1 = read_wav_mono(PROJECT_ROOT / spk1["wav_path"])
        audio2, sr2 = read_wav_mono(PROJECT_ROOT / spk2["wav_path"])
        if sr1 != sr2:
            raise ValueError(f"sample-rate mismatch for {spk1['utterance_id']} and {spk2['utterance_id']}")
        mixed, track1, track2 = mix_pair(audio1, audio2, sr1, ratio, dom, duration)
        mixed_path = CONTROLLED_AUDIO_DIR / f"{sid}_mixed.wav"
        spk1_path = CONTROLLED_AUDIO_DIR / f"{sid}_spk1.wav"
        spk2_path = CONTROLLED_AUDIO_DIR / f"{sid}_spk2.wav"
        write_wav_mono(mixed_path, mixed, sr1)
        write_wav_mono(spk1_path, track1, sr1)
        write_wav_mono(spk2_path, track2, sr1)
        ref1, ref2 = spk1["benchmark_text"], spk2["benchmark_text"]
        reference_text = f"[SPEAKER_1] {ref1}\n[SPEAKER_2] {ref2}"
        ref_path = CONTROLLED_REF_DIR / f"{sid}.json"
        write_json(
            ref_path,
            {
                "sample_id": sid,
                "reference_type": reference_type,
                "reference_text": reference_text,
                "reference_spk1": ref1,
                "reference_spk2": ref2,
                "source_utterance_ids": f"{spk1['utterance_id']}|{spk2['utterance_id']}",
            },
        )
        split_bucket = stable_bucket(sid, 100)
        split = "train" if split_bucket < 60 else "dev" if split_bucket < 80 else "test"
        rows.append(
            {
                "sample_id": sid,
                "split": split,
                "mixed_path": rel(mixed_path),
                "spk1_path": rel(spk1_path),
                "spk2_path": rel(spk2_path),
                "reference_path": rel(ref_path),
                "reference_text": reference_text,
                "reference_spk1": ref1,
                "reference_spk2": ref2,
                "overlap_ratio": ratio,
                "dominance_type": dom,
                "style": style,
                "duration": duration,
                "reference_type": reference_type,
                "mode_status": mode_status,
                "source_utterance_ids": f"{spk1['utterance_id']}|{spk2['utterance_id']}",
                "sample_rate": sr1,
            }
        )
    write_csv(MANIFEST_CSV, rows)
    (CONTROLLED_ROOT / "README.md").write_text(
        f"# Controlled Route-Sensitive v1\n\nGenerated `{len(rows)}` samples with reference type `{reference_type}` and mode status `{mode_status}`.\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} controlled samples to {rel(MANIFEST_CSV)}")


if __name__ == "__main__":
    main()
