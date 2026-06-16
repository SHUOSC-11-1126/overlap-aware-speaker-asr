from __future__ import annotations

import argparse
from typing import Any

import numpy as np

from .audio_depth_router_common import PROJECT_ROOT, read_csv, read_wav_mono, rel, write_csv
from .audio_depth_systematic_common import stable_bucket, write_wav_mono
from .balanced_v2_common import V2_AUDIO, V2_MANIFEST, V2_POOL, V2_REFS, V2_ROOT, add_noise, duplicate_tail, smear
from .controlled_benchmark_common import INVENTORY_CSV, VERIFICATION_PACK_CSV, mix_pair, write_json


FAMILIES = ["mixed_win_anchor", "separated_win_anchor", "cleaned_win_anchor", "review_needed_anchor"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate balanced route-sensitive v2 candidates and benchmark.")
    parser.add_argument("--n-candidates", type=int, default=240)
    parser.add_argument("--n-final", type=int, default=120)
    return parser.parse_args()


def load_sources() -> list[dict[str, str]]:
    inv = read_csv(INVENTORY_CSV)
    verified = {row["utterance_id"]: row.get("verified_transcript", "").strip() for row in read_csv(VERIFICATION_PACK_CSV)} if VERIFICATION_PACK_CSV.exists() else {}
    rows = []
    for row in inv:
        if row.get("usable_for_benchmark") == "True":
            rows.append({**row, "benchmark_text": verified.get(row["utterance_id"]) or row["transcript_candidate"]})
    return rows


def candidate_rows(n_candidates: int) -> list[dict[str, Any]]:
    ratios = {
        "mixed_win_anchor": [0.0, 0.05, 0.1, 0.15],
        "separated_win_anchor": [0.55, 0.65, 0.75, 0.85],
        "cleaned_win_anchor": [0.25, 0.35, 0.45, 0.55],
        "review_needed_anchor": [0.3, 0.5, 0.7, 0.9],
    }
    rows = []
    for idx in range(1, n_candidates + 1):
        family = FAMILIES[(idx - 1) % len(FAMILIES)]
        rows.append(
            {
                "candidate_id": f"controlled_route_sensitive_v2_candidate_{idx:04d}",
                "intended_family": family,
                "expected_winner": family.split("_")[0] if family != "review_needed_anchor" else "review_needed",
                "overlap_ratio": ratios[family][((idx - 1) // len(FAMILIES)) % len(ratios[family])],
                "dominance_type": ["balanced", "speaker_A_dominant", "speaker_B_dominant"][((idx - 1) // 7) % 3],
                "stress_seed": idx * 13,
                "final_rank": ((idx * 37) % n_candidates),
            }
        )
    return rows


def transform_family(family: str, mixed: np.ndarray, spk1: np.ndarray, spk2: np.ndarray, sr: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    if family == "mixed_win_anchor":
        return mixed, add_noise(smear(spk1, 0.65), 0.018, seed), add_noise(smear(spk2, 0.65), 0.018, seed + 1), "separated_sources_noisy_smeared"
    if family == "separated_win_anchor":
        return add_noise(smear(mixed, 0.45), 0.02, seed), spk1, spk2, "mixed_overlap_noisy_sources_clean"
    if family == "cleaned_win_anchor":
        return add_noise(mixed, 0.006, seed), duplicate_tail(spk1, sr), duplicate_tail(spk2, sr), "separated_sources_repeat_tail_cleaned_can_suppress"
    return add_noise(smear(mixed, 0.9), 0.035, seed), add_noise(smear(spk1, 0.9), 0.035, seed + 1), add_noise(smear(spk2, 0.9), 0.035, seed + 2), "all_routes_stressed_review_needed"


def split(sample_id: str) -> str:
    bucket = stable_bucket(sample_id, 100)
    if bucket < 60:
        return "train"
    if bucket < 80:
        return "dev"
    return "test"


def main() -> None:
    args = parse_args()
    sources = load_sources()
    con = [row for row in sources if row["speaker_id"] == "con"]
    pro = [row for row in sources if row["speaker_id"] == "pro"]
    pool = candidate_rows(args.n_candidates)
    per_family = max(1, args.n_final // len(FAMILIES))
    selected = []
    by_family = {family: [row for row in pool if row["intended_family"] == family][:per_family] for family in FAMILIES}
    for pos in range(per_family):
        for family in FAMILIES:
            selected.append(by_family[family][pos])
    selected = selected[: args.n_final]
    V2_AUDIO.mkdir(parents=True, exist_ok=True)
    V2_REFS.mkdir(parents=True, exist_ok=True)
    manifest = []
    for idx, cand in enumerate(selected, start=1):
        spk1_row = con[(idx - 1) % len(con)]
        spk2_row = pro[(idx * 5 + idx // 3) % len(pro)]
        audio1, sr1 = read_wav_mono(PROJECT_ROOT / spk1_row["wav_path"])
        audio2, sr2 = read_wav_mono(PROJECT_ROOT / spk2_row["wav_path"])
        if sr1 != sr2:
            raise ValueError("sample-rate mismatch")
        mixed, spk1, spk2 = mix_pair(audio1, audio2, sr1, float(cand["overlap_ratio"]), cand["dominance_type"], "short")
        mixed, spk1, spk2, transform = transform_family(cand["intended_family"], mixed, spk1, spk2, sr1, int(cand["stress_seed"]))
        sid = f"controlled_route_sensitive_v2_{idx:04d}"
        paths = {
            "mixed_path": V2_AUDIO / f"{sid}_mixed.wav",
            "spk1_path": V2_AUDIO / f"{sid}_spk1.wav",
            "spk2_path": V2_AUDIO / f"{sid}_spk2.wav",
        }
        write_wav_mono(paths["mixed_path"], mixed, sr1)
        write_wav_mono(paths["spk1_path"], spk1, sr1)
        write_wav_mono(paths["spk2_path"], spk2, sr1)
        ref1, ref2 = spk1_row["benchmark_text"], spk2_row["benchmark_text"]
        reference_text = f"[SPEAKER_1] {ref1}\n[SPEAKER_2] {ref2}"
        ref_path = V2_REFS / f"{sid}.json"
        write_json(
            ref_path,
            {
                "sample_id": sid,
                "reference_type": "silver_plus_unverified",
                "reference_text": reference_text,
                "reference_spk1": ref1,
                "reference_spk2": ref2,
                "candidate_id": cand["candidate_id"],
                "intended_family": cand["intended_family"],
                "expected_winner": cand["expected_winner"],
            },
        )
        manifest.append(
            {
                "sample_id": sid,
                "split": split(sid),
                "candidate_id": cand["candidate_id"],
                "mixed_path": rel(paths["mixed_path"]),
                "spk1_path": rel(paths["spk1_path"]),
                "spk2_path": rel(paths["spk2_path"]),
                "reference_path": rel(ref_path),
                "reference_text": reference_text,
                "reference_spk1": ref1,
                "reference_spk2": ref2,
                "overlap_ratio": cand["overlap_ratio"],
                "dominance_type": cand["dominance_type"],
                "intended_family": cand["intended_family"],
                "expected_winner": cand["expected_winner"],
                "route_stress_transform": transform,
                "reference_type": "silver_plus_unverified",
                "source_utterance_ids": f"{spk1_row['utterance_id']}|{spk2_row['utterance_id']}",
                "sample_rate": sr1,
            }
        )
    write_csv(V2_POOL, pool)
    write_csv(V2_MANIFEST, manifest)
    (V2_ROOT / "README.md").write_text(
        "\n".join(
            [
                "# Controlled Route-Sensitive v2",
                "",
                f"Candidate pool: `{len(pool)}`.",
                f"Final benchmark: `{len(manifest)}`.",
                "Reference type: `silver_plus_unverified`; this is not gold transcription.",
                "Families: mixed-win, separated-win, cleaned-win, and review-needed anchors.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(pool)} candidates and {len(manifest)} v2 samples to {rel(V2_MANIFEST)}")


if __name__ == "__main__":
    main()
