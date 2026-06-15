from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .audio_depth_router_common import (
    CER_COLUMNS,
    METHOD_TO_LABEL,
    PROJECT_ROOT,
    best_route_from_cers,
    read_csv,
    rel,
    write_csv,
    write_json,
)


OUTPUT_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_router_dataset.csv"
OUTPUT_JSON = PROJECT_ROOT / "results" / "tables" / "audio_depth_router_dataset.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build AudioDepth-Router dataset manifest from CER tables.")
    parser.add_argument("--representation-mode", default="deployable", choices=["deployable", "analysis"])
    return parser.parse_args()


def choose_cer_table() -> Path:
    preferred = [
        PROJECT_ROOT / "results" / "tables" / "synthetic_split_cer_results.csv",
        PROJECT_ROOT / "results" / "tables" / "synthetic_cer_results.csv",
        PROJECT_ROOT / "results" / "tables" / "cer_results.csv",
    ]
    for path in preferred:
        if path.exists():
            return path
    candidates = sorted((PROJECT_ROOT / "results" / "tables").glob("*synthetic*split*cer*.csv"))
    if candidates:
        return candidates[0]
    raise FileNotFoundError("No CER table found for AudioDepth-Router dataset construction.")


def pivot_cer_rows(cer_rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in cer_rows:
        sample_id = row.get("sample_id") or row.get("case_id")
        method = row.get("method", "")
        label = METHOD_TO_LABEL.get(method)
        if not sample_id or not label:
            continue
        entry = grouped.setdefault(
            sample_id,
            {
                "sample_id": sample_id,
                "split": row.get("split", "gold_sanity"),
                "overlap_tier": row.get("tier") or row.get("overlap_level") or "",
            },
        )
        entry[CER_COLUMNS[label]] = float(row.get("cer", "nan"))
    return grouped


def load_manifest_lookup() -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for path in [
        PROJECT_ROOT / "results" / "tables" / "synthetic_split_manifest.csv",
        PROJECT_ROOT / "results" / "tables" / "audio_manifest.csv",
    ]:
        if not path.exists():
            continue
        for row in read_csv(path):
            sample_id = row.get("sample_id") or row.get("case_id")
            if sample_id:
                lookup[sample_id] = row
    return lookup


def stable_split(sample_id: str, original_split: str) -> str:
    if original_split in {"train", "dev", "test"}:
        return original_split
    if original_split in {"dev", "test"}:
        return original_split
    if original_split == "gold_sanity":
        return "gold_sanity"
    bucket = sum(ord(ch) for ch in sample_id) % 100
    if bucket < 70:
        return "train"
    if bucket < 85:
        return "dev"
    return "test"


def map_path_for(sample_id: str, mode: str) -> str:
    return f"resources/audio_depth_maps/{mode}/{sample_id}.npy"


def build_dataset(representation_mode: str = "deployable") -> list[dict[str, Any]]:
    cer_path = choose_cer_table()
    manifest = load_manifest_lookup()
    grouped = pivot_cer_rows(read_csv(cer_path))
    rows: list[dict[str, Any]] = []
    for sample_id, entry in sorted(grouped.items()):
        if not all(column in entry for column in CER_COLUMNS.values()):
            continue
        source = manifest.get(sample_id, {})
        split = stable_split(sample_id, str(entry.get("split", "")))
        audio_path = source.get("mixed_path") or source.get("path") or f"resources/mixed_audio/{sample_id}.wav"
        spk1_path = source.get("spk1_path", "")
        spk2_path = source.get("spk2_path", "")
        if not (PROJECT_ROOT / audio_path).exists():
            continue
        best_label = best_route_from_cers(entry)
        label_source = "synthetic_split_cer_argmin" if "Synthetic" in sample_id else "gold_sanity_cer_argmin"
        row = {
            "sample_id": sample_id,
            "split": split,
            "overlap_tier": source.get("tier") or entry.get("overlap_tier", ""),
            "audio_path": audio_path,
            "spk1_path": spk1_path,
            "spk2_path": spk2_path,
            "mixed_cer": entry["mixed_cer"],
            "separated_cer": entry["separated_cer"],
            "cleaned_cer": entry["cleaned_cer"],
            "best_route_label": best_label,
            "label_source": label_source,
            "representation_mode": representation_mode,
            "map_path": map_path_for(sample_id, representation_mode),
        }
        rows.append(row)
    return rows


def main() -> None:
    args = parse_args()
    rows = build_dataset(args.representation_mode)
    fields = [
        "sample_id",
        "split",
        "overlap_tier",
        "audio_path",
        "spk1_path",
        "spk2_path",
        "mixed_cer",
        "separated_cer",
        "cleaned_cer",
        "best_route_label",
        "label_source",
        "representation_mode",
        "map_path",
    ]
    write_csv(OUTPUT_CSV, rows, fields)
    write_json(OUTPUT_JSON, rows)
    print(f"Wrote {len(rows)} rows to {rel(OUTPUT_CSV)}")


if __name__ == "__main__":
    main()
