from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .evaluate_cer import normalize_text


CSV_COLUMNS = [
    "sample_id",
    "tier",
    "method",
    "cer",
    "reference_length",
    "hypothesis_length",
    "length_ratio",
    "source_snippet_filenames",
    "mixed_audio_path",
    "spk1_audio_path",
    "spk2_audio_path",
    "hypothesis_preview",
    "reference_preview",
    "suspected_issue",
]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing table: {path.relative_to(PROJECT_ROOT)}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f) if isinstance(row, dict)]


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path.relative_to(PROJECT_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def safe_preview(text: str, limit: int = 180) -> str:
    return " ".join(text.split())[:limit]


def get_reference_text(payload: dict[str, Any]) -> str:
    text = str(payload.get("full_text", "")).strip()
    if text:
        return text
    return str(payload.get("text", "")).strip()


def get_hypothesis_text(payload: dict[str, Any]) -> str:
    for key in ("full_text", "cleaned_full_text", "text"):
        text = str(payload.get(key, "")).strip()
        if text:
            return text
    segments = payload.get("segments", [])
    if isinstance(segments, list):
        texts = [str(seg.get("text", "")).strip() for seg in segments if str(seg.get("text", "")).strip()]
        return "\n".join(texts)
    return ""


def issue_for_row(
    row: dict[str, Any],
    reference_text: str,
    hypothesis_text: str,
    reference_path: Path,
    hypothesis_path: Path,
) -> str | None:
    reference_length = int(float(str(row.get("reference_length", 0)).strip() or 0))
    hypothesis_length = int(float(str(row.get("hypothesis_length", 0)).strip() or 0))
    cer = float(str(row.get("cer", 0)).strip() or 0.0)
    if not reference_path.exists() or not hypothesis_path.exists():
        return "missing_file"
    if not reference_text:
        return "empty_reference"
    if reference_length == 0:
        return "empty_reference"

    length_ratio = hypothesis_length / reference_length if reference_length else 0.0
    if length_ratio > 1.5:
        if cer > 0.8:
            return "high_length_ratio; possible repetition hallucination or reference mismatch"
        return "high_length_ratio; possible repetition hallucination or reference mismatch"
    if cer > 0.8 and length_ratio <= 1.5:
        return "high_cer_low_length_ratio; possible substitution-heavy ASR error"
    return None


def audit_rows() -> list[dict[str, Any]]:
    manifest_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_manifest.csv")
    cer_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_cer_results.csv")
    cer_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in cer_rows:
        sample_id = str(row.get("sample_id", "")).strip()
        method = str(row.get("method", "")).strip()
        if sample_id and method:
            cer_lookup[(sample_id, method)] = row

    manifest_lookup = {str(row.get("sample_id", "")).strip(): row for row in manifest_rows if str(row.get("sample_id", "")).strip()}
    rows: list[dict[str, Any]] = []

    for (sample_id, method), row in cer_lookup.items():
        if method not in {"mixed_whisper", "separated_whisper", "separated_whisper_cleaned"}:
            continue
        manifest = manifest_lookup.get(sample_id)
        if not manifest:
            continue
        tier = str(manifest.get("tier", ""))
        reference_path = PROJECT_ROOT / str(row.get("reference_path", ""))
        hypothesis_path = PROJECT_ROOT / str(row.get("hypothesis_path", ""))

        reference_payload = read_json(reference_path) if reference_path.exists() else {}
        hypothesis_payload = read_json(hypothesis_path) if hypothesis_path.exists() else {}
        reference_text = get_reference_text(reference_payload)
        hypothesis_text = get_hypothesis_text(hypothesis_payload)
        issue = issue_for_row(row, reference_text, hypothesis_text, reference_path, hypothesis_path)
        if not issue:
            continue

        reference_length = int(float(str(row.get("reference_length", 0)).strip() or 0))
        hypothesis_length = int(float(str(row.get("hypothesis_length", 0)).strip() or 0))
        length_ratio = round(hypothesis_length / reference_length, 6) if reference_length else 0.0

        rows.append(
            {
                "sample_id": sample_id,
                "tier": tier,
                "method": method,
                "cer": float(str(row.get("cer", 0)).strip() or 0.0),
                "reference_length": reference_length,
                "hypothesis_length": hypothesis_length,
                "length_ratio": length_ratio,
                "source_snippet_filenames": f"{manifest.get('con_source', '')}, {manifest.get('pro_source', '')}",
                "mixed_audio_path": str(manifest.get("mixed_path", "")),
                "spk1_audio_path": str(manifest.get("spk1_path", "")),
                "spk2_audio_path": str(manifest.get("spk2_path", "")),
                "hypothesis_preview": safe_preview(hypothesis_text),
                "reference_preview": safe_preview(reference_text),
                "suspected_issue": issue,
            }
        )
    return rows


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    fig_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "synthetic_audit_report.csv"
    json_path = table_dir / "synthetic_audit_report.json"
    md_path = fig_dir / "synthetic_audit_report.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Synthetic Benchmark Sanity Audit",
        "",
        "This audit checks whether the synthetic silver benchmark contains reference construction issues, missing files, or true ASR hallucination patterns.",
        "",
        "| sample_id | tier | method | cer | reference_length | hypothesis_length | length_ratio | suspected_issue |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['sample_id']} | {row['tier']} | {row['method']} | {row['cer']} | {row['reference_length']} | "
            f"{row['hypothesis_length']} | {row['length_ratio']} | {row['suspected_issue']} |"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    _ = load_config()
    rows = audit_rows()
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote synthetic audit CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote synthetic audit JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote synthetic audit MD: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Audit rows: {len(rows)}")


if __name__ == "__main__":
    main()
