from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config


CSV_COLUMNS = [
    "case_id",
    "method",
    "reference_type",
    "hypothesis_path",
    "reference_length",
    "hypothesis_length",
    "edit_distance",
    "cer",
]


def load_reference(case_id: str) -> dict[str, Any]:
    path = PROJECT_ROOT / "references" / "reference_transcripts.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing reference file: {path.relative_to(PROJECT_ROOT)}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if case_id not in data:
        raise KeyError(
            f"Missing verified reference for case '{case_id}' in references/reference_transcripts.json"
        )
    reference = data[case_id]
    if reference.get("status") != "verified_reference":
        raise ValueError(f"Reference for case '{case_id}' is not marked as verified_reference")
    return reference


def list_verified_cases() -> list[str]:
    path = PROJECT_ROOT / "references" / "reference_transcripts.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing reference file: {path.relative_to(PROJECT_ROOT)}")
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        case_id
        for case_id, reference in data.items()
        if reference.get("status") == "verified_reference"
    ]


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing transcript: {path.relative_to(PROJECT_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(text: str) -> str:
    text = re.sub(r"\[SPEAKER_\d+\]", "", text)
    text = text.replace("\n", "").replace("\r", "").replace(" ", "")
    # CER here compares character sequences, so we remove punctuation to avoid
    # counting punctuation-only differences as character errors.
    text = re.sub(r"[^\w\u4e00-\u9fff]", "", text)
    return text


def compute_cer(reference_text: str, hypothesis_text: str) -> dict[str, Any]:
    ref_norm = normalize_text(reference_text)
    hyp_norm = normalize_text(hypothesis_text)
    distance = levenshtein_distance(ref_norm, hyp_norm)
    reference_length = len(ref_norm)
    cer = round(distance / reference_length, 6) if reference_length else 0.0
    return {
        "normalized_reference": ref_norm,
        "normalized_hypothesis": hyp_norm,
        "reference_length": reference_length,
        "hypothesis_length": len(hyp_norm),
        "edit_distance": distance,
        "cer": cer,
    }


def levenshtein_distance(a: str, b: str) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            insert_cost = curr[j - 1] + 1
            delete_cost = prev[j] + 1
            replace_cost = prev[j - 1] + (ca != cb)
            curr.append(min(insert_cost, delete_cost, replace_cost))
        prev = curr
    return prev[-1]


def build_row(case_id: str, method: str, reference_text: str, hypothesis_text: str, hypothesis_path: Path) -> dict[str, Any]:
    metrics = compute_cer(reference_text, hypothesis_text)
    return {
        "case_id": case_id,
        "method": method,
        "reference_type": "verified_reference",
        "hypothesis_path": hypothesis_path.relative_to(PROJECT_ROOT).as_posix(),
        "reference_length": metrics["reference_length"],
        "hypothesis_length": metrics["hypothesis_length"],
        "edit_distance": metrics["edit_distance"],
        "cer": metrics["cer"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate CER for one or more verified cases.")
    parser.add_argument("--case", required=True, help="Audio case id, e.g. NoOverlap, LightOverlap, or all")
    return parser.parse_args()


def read_existing_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def upsert_row(rows: list[dict[str, Any]], row: dict[str, Any]) -> list[dict[str, Any]]:
    key = (str(row["case_id"]), str(row["method"]))
    filtered = [
        existing
        for existing in rows
        if (str(existing.get("case_id")), str(existing.get("method"))) != key
    ]
    filtered.append(row)
    return sorted(filtered, key=lambda item: (str(item["case_id"]), str(item["method"])))


def rows_for_case(case_id: str) -> list[dict[str, Any]]:
    reference = load_reference(case_id)
    reference_text = reference.get("full_text", "")

    mixed_path = PROJECT_ROOT / "results" / "transcripts_raw" / f"{case_id}_mixed_whisper.json"
    separated_path = (
        PROJECT_ROOT / "results" / "transcripts_speaker" / f"{case_id}_separated_speaker_transcript.json"
    )
    cleaned_path = (
        PROJECT_ROOT
        / "results"
        / "transcripts_postprocessed"
        / f"{case_id}_separated_speaker_transcript_cleaned.json"
    )
    mixed = load_json(mixed_path)
    separated = load_json(separated_path)

    rows = [
        build_row(case_id, "mixed_whisper", reference_text, mixed.get("text", ""), mixed_path),
        build_row(
            case_id,
            "separated_whisper",
            reference_text,
            separated.get("full_text", ""),
            separated_path,
        ),
    ]
    if cleaned_path.exists():
        cleaned = load_json(cleaned_path)
        rows.append(
            build_row(
                case_id,
                "separated_whisper_cleaned",
                reference_text,
                cleaned.get("cleaned_full_text", ""),
                cleaned_path,
            )
        )
    else:
        print(
            f"skip missing cleaned transcript for case '{case_id}': "
            f"{cleaned_path.relative_to(PROJECT_ROOT)}"
        )
    return rows


def main() -> None:
    args = parse_args()
    _ = load_config()
    if args.case == "all":
        cases = list_verified_cases()
    else:
        cases = [args.case]

    rows = read_existing_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv")
    for case_id in cases:
        for row in rows_for_case(case_id):
            rows = upsert_row(rows, row)

    output_dir = PROJECT_ROOT / "results" / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "cer_results.csv"
    json_path = output_dir / "cer_results.json"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote CER CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote CER JSON: {json_path.relative_to(PROJECT_ROOT)}")
    for row in rows:
        print(f"{row['method']}: CER={row['cer']}")


if __name__ == "__main__":
    main()
