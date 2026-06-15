from __future__ import annotations

import argparse
from collections import defaultdict

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel, write_csv
from .audio_depth_systematic_common import STRESS_MANIFEST_CSV, safe_float


OUT_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_stratified_sample_list.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select stratified AudioDepth stress samples for real ASR.")
    parser.add_argument("--n-samples", type=int, default=20)
    return parser.parse_args()


def bucket(row: dict[str, str]) -> str:
    ratio = safe_float(row.get("overlap_ratio"), 0.0)
    style = row.get("interruption_style", "")
    if "opposite" in style:
        return "opposite_debate"
    if ratio < 0.1:
        return "no_overlap"
    if ratio < 0.35:
        return "light"
    if ratio < 0.65:
        return "medium"
    return "heavy"


def main() -> None:
    args = parse_args()
    rows = read_csv(STRESS_MANIFEST_CSV)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[bucket(row)].append(row)
    selected = []
    buckets = ["no_overlap", "light", "medium", "heavy", "opposite_debate"]
    while len(selected) < args.n_samples and any(grouped.values()):
        for name in buckets:
            if grouped[name] and len(selected) < args.n_samples:
                row = grouped[name].pop(0)
                selected.append({**row, "stratum": name})
    write_csv(OUT_CSV, selected)
    print(f"Wrote {len(selected)} stratified samples to {rel(OUT_CSV)}")


if __name__ == "__main__":
    main()
