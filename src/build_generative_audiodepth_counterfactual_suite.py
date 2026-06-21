from __future__ import annotations

from pathlib import Path

import numpy as np

from .generative_audiodepth_common import PROJECT_ROOT, read_rows, safe_float, write_csv, write_markdown
from .generative_audiodepth_reliability_common import RELIABILITY_TEST, map_task_row, sample_rows, teacher_map_features


OUT_DIR = PROJECT_ROOT / "resources" / "generative_audiodepth_counterfactual_v1"
MANIFEST = PROJECT_ROOT / "results" / "tables" / "generative_audiodepth_counterfactual_manifest.csv"
SUMMARY = PROJECT_ROOT / "results" / "figures" / "generative_audiodepth_counterfactual_dataset.md"


def save_arr(path: Path, arr: np.ndarray) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, arr.astype(np.float32))
    return path.relative_to(PROJECT_ROOT).as_posix()


def base_maps(sample_id: str, dataset_rows: list[dict[str, str]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    arrays = []
    for task in ["OVERLAP_MAP", "DOMINANCE_MAP", "UNCERTAINTY_MAP"]:
        row = map_task_row(sample_id, task, dataset_rows)
        arrays.append(np.load(PROJECT_ROOT / row["target_path"]).astype(np.float32) if row else np.zeros((64, 96), dtype=np.float32))
    return arrays[0], arrays[1], arrays[2]


def shift_map(arr: np.ndarray, fraction: float) -> np.ndarray:
    return np.roll(arr, int(arr.shape[1] * fraction), axis=1)


def main() -> None:
    dataset_rows = read_rows(PROJECT_ROOT / "results" / "tables" / "generative_audiodepth_dataset.csv")
    test_rows = sorted({row["sample_id"]: row for row in read_rows(RELIABILITY_TEST)}.values(), key=lambda r: r["sample_id"])
    if not test_rows:
        test_rows = sample_rows()[-9:]
    seeds = test_rows[: min(6, len(test_rows))]
    rows: list[dict[str, object]] = []
    for seed_idx, row in enumerate(seeds):
        sample_id = row["sample_id"]
        overlap, dominance, uncertainty = base_maps(sample_id, dataset_rows)
        families = [
            ("overlap_sweep", [0.00, 0.05, 0.10, 0.20, 0.30, 0.50, 0.70]),
            ("dominance_sdr_sweep", [0, 3, 6, 12, 18]),
            ("backchannel_duration", [0.2, 0.5, 1.0, 2.0]),
            ("gain_noise", [0.0, 0.08, 0.18]),
            ("time_shift", [0.0, 0.15, 0.35, 0.55]),
        ]
        for family, values in families:
            for value in values:
                cf_id = f"cfv1_{seed_idx:02d}_{family}_{str(value).replace('.', 'p')}"
                if family == "overlap_sweep":
                    ov = np.clip(overlap * 0.25 + float(value), 0.0, 1.0)
                    dom = dominance
                    unc = np.clip(uncertainty + ov * 0.15, 0.0, 1.0)
                    expected = "overlap_mean_increase"
                elif family == "dominance_sdr_sweep":
                    strength = min(float(value) / 18.0, 1.0)
                    ov = overlap
                    dom = np.clip(0.5 + (dominance - 0.5) * (1.0 + strength), 0.0, 1.0)
                    unc = np.clip(uncertainty * (1.0 - 0.25 * strength), 0.0, 1.0)
                    expected = "dominance_concentration_increase"
                elif family == "backchannel_duration":
                    scale = min(float(value) / 2.0, 1.0)
                    ov = np.clip(overlap * (0.35 + 0.65 * scale), 0.0, 1.0)
                    dom = dominance
                    unc = np.clip(uncertainty * (0.75 + 0.25 * scale), 0.0, 1.0)
                    expected = "short_backchannel_stability"
                elif family == "gain_noise":
                    noise = np.random.default_rng(seed_idx).normal(0.0, float(value), size=overlap.shape).astype(np.float32)
                    ov = np.clip(overlap + noise, 0.0, 1.0)
                    dom = np.clip(dominance + noise * 0.4, 0.0, 1.0)
                    unc = np.clip(uncertainty + abs(noise) * 0.6, 0.0, 1.0)
                    expected = "gain_noise_route_stability"
                else:
                    ov = shift_map(overlap, float(value))
                    dom = shift_map(dominance, float(value))
                    unc = shift_map(uncertainty, float(value))
                    expected = "position_change_content_constant"
                stacked = np.stack([ov, dom, unc]).astype(np.float32)
                map_path = save_arr(OUT_DIR / family / f"{cf_id}.npy", stacked)
                rows.append(
                    {
                        "counterfactual_id": cf_id,
                        "base_sample_id": sample_id,
                        "source_utterance_ids": row.get("source_utterance_ids", ""),
                        "family": family,
                        "control_value": value,
                        "map_path": map_path,
                        "expected_behavior": expected,
                        "base_oracle_route": row.get("oracle_route", ""),
                        "base_mixed_cer": row.get("mixed_cer", ""),
                        "base_separated_cer": row.get("separated_cer", ""),
                        "base_route_gap": row.get("route_gap", ""),
                        "base_overlap_ratio": row.get("overlap_ratio", ""),
                        "base_dominance_type": row.get("dominance_type", ""),
                        "constructed_from_split": "reliability_test",
                        "audio_status": "map_level_counterfactual_no_asr_rerun",
                        "overlap_mean": round(float(np.mean(ov)), 6),
                        "dominance_mean": round(float(np.mean(dom)), 6),
                        "uncertainty_mean": round(float(np.mean(unc)), 6),
                    }
                )
    write_csv(MANIFEST, rows)
    lines = [
        "# Generative AudioDepth Counterfactual Dataset",
        "",
        "This suite is a map-level counterfactual reliability suite built from held-out reliability-test source groups.",
        "",
        f"- base held-out samples: {len(seeds)}",
        f"- generated counterfactual rows: {len(rows)}",
        "- audio ASR rerun: not performed",
        "- purpose: test generated-map monotonicity, ordering, and stability assumptions before scaling.",
        "",
        "The suite intentionally does not add these held-out counterfactuals to training data.",
    ]
    write_markdown(SUMMARY, lines)
    print(f"wrote {MANIFEST}")


if __name__ == "__main__":
    main()
