from __future__ import annotations

from pathlib import Path

from .generative_audiodepth_common import DATASET_CSV, read_rows, safe_float, unique_samples, write_csv


PAIRS_CSV = Path("results/tables/generative_audiodepth_counterfactual_pairs.csv")


def main() -> None:
    samples = unique_samples(read_rows(DATASET_CSV))
    by_source: dict[str, list[dict[str, str]]] = {}
    for row in samples:
        by_source.setdefault(row.get("source_utterance_ids", row["sample_id"]), []).append(row)
    pairs = []
    for source_id, group in by_source.items():
        ordered = sorted(group, key=lambda row: safe_float(row.get("overlap_ratio"), 0.0))
        for low, high in zip(ordered, ordered[1:]):
            if safe_float(high.get("overlap_ratio"), 0.0) <= safe_float(low.get("overlap_ratio"), 0.0):
                continue
            pairs.append(
                {
                    "pair_id": f"{low['sample_id']}__{high['sample_id']}",
                    "source_utterance_ids": source_id,
                    "low_sample_id": low["sample_id"],
                    "high_sample_id": high["sample_id"],
                    "low_overlap_ratio": low.get("overlap_ratio", ""),
                    "high_overlap_ratio": high.get("overlap_ratio", ""),
                    "pair_type": "source_disjoint_counterfactual" if len(group) > 1 else "none",
                }
            )
    if not pairs:
        # Controlled v2 usually uses unique source pairs. Fall back to a transparent
        # family-level monotonic probe rather than pretending exact counterfactuals exist.
        ordered = sorted(samples, key=lambda row: safe_float(row.get("overlap_ratio"), 0.0))
        for low, high in zip(ordered, ordered[1:]):
            if low.get("target_family") != high.get("target_family"):
                continue
            pairs.append(
                {
                    "pair_id": f"{low['sample_id']}__{high['sample_id']}",
                    "source_utterance_ids": "not_exact_counterfactual",
                    "low_sample_id": low["sample_id"],
                    "high_sample_id": high["sample_id"],
                    "low_overlap_ratio": low.get("overlap_ratio", ""),
                    "high_overlap_ratio": high.get("overlap_ratio", ""),
                    "pair_type": "family_level_proxy_not_same_source",
                }
            )
            if len(pairs) >= 20:
                break
    write_csv(PAIRS_CSV, pairs)
    print(f"Wrote {len(pairs)} counterfactual/proxy pairs")


if __name__ == "__main__":
    main()
