from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .io_helpers import read_csv_rows


MANIFEST_COLUMNS_EXTRA = [
    "reference_status",
    "reference_path",
    "silver_reference_path",
    "placeholder_reference_path",
    "overlap_level_numeric",
]

TIER_TO_LEVEL = {
    "SyntheticNoOverlap": 0,
    "SyntheticLightOverlap": 1,
    "SyntheticMidOverlap": 2,
    "SyntheticHeavyOverlap": 3,
    "SyntheticOppositeOverlap": 4,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build silver references for synthetic overlap benchmarks.")
    parser.add_argument(
        "--dataset",
        choices=["synthetic_overlap", "synthetic_overlap_v2"],
        default="synthetic_overlap",
        help="Synthetic benchmark dataset to process.",
    )
    return parser.parse_args()
def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path.relative_to(PROJECT_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def snippet_transcript_path(snippet_id: str) -> Path:
    return PROJECT_ROOT / "results" / "snippet_transcripts" / f"{snippet_id}_whisper.json"


def load_snippet_text(snippet_name: str) -> tuple[str, dict[str, Any]]:
    snippet_id = Path(snippet_name).stem
    path = snippet_transcript_path(snippet_id)
    if not path.exists():
        raise FileNotFoundError(
            f"Missing snippet transcript for '{snippet_id}': {path.relative_to(PROJECT_ROOT)}"
        )
    payload = read_json(path)
    return str(payload.get("text", "")).strip(), payload


def build_turns(con_source: str, pro_source: str, con_text: str, pro_text: str) -> list[dict[str, Any]]:
    return [
        {"speaker": "SPEAKER_1", "source": con_source, "text": con_text, "start_order": 0},
        {"speaker": "SPEAKER_2", "source": pro_source, "text": pro_text, "start_order": 1},
    ]


def dataset_paths(dataset: str) -> tuple[Path, Path, str]:
    if dataset == "synthetic_overlap":
        return (
            PROJECT_ROOT / "results" / "tables" / "synthetic_manifest.csv",
            PROJECT_ROOT / "resources" / "synthetic_overlap" / "references",
            "synthetic_overlap",
        )
    if dataset == "synthetic_overlap_v2":
        return (
            PROJECT_ROOT / "results" / "tables" / "synthetic_split_manifest.csv",
            PROJECT_ROOT / "resources" / "synthetic_overlap_v2" / "references",
            "synthetic_overlap_v2",
        )
    raise ValueError(f"Unsupported dataset: {dataset}")


def build_silver_reference(row: dict[str, Any], reference_dir: Path) -> tuple[dict[str, Any], str]:
    sample_id = str(row["sample_id"])
    tier = str(row["tier"])
    split = str(row.get("split", "")).strip()
    con_source = str(row["con_source"])
    pro_source = str(row["pro_source"])
    con_text, con_payload = load_snippet_text(con_source)
    pro_text, pro_payload = load_snippet_text(pro_source)

    turns = build_turns(con_source, pro_source, con_text, pro_text)
    full_text = "\n".join(f"[{turn['speaker']}] {turn['text']}" for turn in turns)
    silver_path = reference_dir / f"{sample_id}_silver_reference.json"
    silver_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "sample_id": sample_id,
        "tier": tier,
        "split": split,
        "overlap_level": TIER_TO_LEVEL.get(tier, 0),
        "overlap_ratio": float(row.get("overlap_ratio", 0.0)),
        "status": "silver_reference",
        "reference_type": "silver_reference",
        "source_files": [con_source, pro_source],
        "source_transcripts": [
            con_payload.get(
                "transcript_path",
                snippet_transcript_path(Path(con_source).stem).relative_to(PROJECT_ROOT).as_posix(),
            ),
            pro_payload.get(
                "transcript_path",
                snippet_transcript_path(Path(pro_source).stem).relative_to(PROJECT_ROOT).as_posix(),
            ),
        ],
        "speaker_1_label": "con",
        "speaker_2_label": "pro",
        "speaker_1_source": con_source,
        "speaker_2_source": pro_source,
        "speaker_1_text": con_text,
        "speaker_2_text": pro_text,
        "turns": turns,
        "full_text": full_text,
        "text": full_text,
        "notes": "Silver reference built from Whisper transcriptions of source snippets.",
    }
    silver_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload, silver_path.relative_to(PROJECT_ROOT).as_posix()


def main() -> None:
    args = parse_args()
    _ = load_config()
    manifest_path, reference_dir, _ = dataset_paths(args.dataset)
    rows = read_csv_rows(manifest_path)
    updated_rows: list[dict[str, Any]] = []

    for row in rows:
        payload, silver_rel_path = build_silver_reference(row, reference_dir)
        placeholder_rel_path = str(row.get("reference_path", "")).strip()
        updated = dict(row)
        updated["reference_status"] = "silver_reference"
        updated["placeholder_reference_path"] = placeholder_rel_path
        updated["silver_reference_path"] = silver_rel_path
        updated["reference_path"] = silver_rel_path
        updated["overlap_level_numeric"] = payload["overlap_level"]
        updated_rows.append(updated)

    fieldnames = list(rows[0].keys()) if rows else []
    for extra in MANIFEST_COLUMNS_EXTRA:
        if extra not in fieldnames:
            fieldnames.append(extra)

    with manifest_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print(f"Updated synthetic manifest: {manifest_path.relative_to(PROJECT_ROOT)}")
    print(f"Silver references written: {len(updated_rows)}")


if __name__ == "__main__":
    main()
