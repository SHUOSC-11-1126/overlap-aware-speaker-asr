from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .external_validation_license_confirmation import CONFIRMED_LICENSE_STATUS


CHECK_COLUMNS = [
    "dataset_name",
    "slice_id",
    "label",
    "license_status",
    "license_confirmed",
    "mapping_schema_valid",
    "audio_staged",
    "reference_staged",
    "validation_status",
    "result_label",
    "observation",
]

SUMMARY_COLUMNS = [
    "metric",
    "value",
    "label",
]


def load_slice_mapping() -> dict[str, Any]:
    mapping_path = PROJECT_ROOT / "results" / "tables" / "external_validation_slice_mapping.json"
    if not mapping_path.exists():
        return {}
    payload = json.loads(mapping_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def schema_is_valid(mapping: dict[str, Any]) -> bool:
    schema = mapping.get("speaker_schema", {})
    if not isinstance(schema, dict):
        return False
    required = {"speaker_field", "start_field", "end_field", "text_field"}
    return required.issubset(schema.keys())


def build_check_row(mapping: dict[str, Any]) -> dict[str, str]:
    license_status = str(mapping.get("license_status", "pending_confirmation"))
    license_confirmed = license_status == CONFIRMED_LICENSE_STATUS
    audio_path = PROJECT_ROOT / str(mapping.get("audio_path", ""))
    reference_path = PROJECT_ROOT / str(mapping.get("reference_path", ""))
    audio_staged = audio_path.exists()
    reference_staged = reference_path.exists()
    schema_valid = schema_is_valid(mapping)

    if not license_confirmed:
        validation_status = "blocked_license_pending"
        observation = "Mini sanity check blocked until license confirmation is recorded."
    elif not schema_valid:
        validation_status = "mapping_schema_invalid"
        observation = "Mapping speaker schema is incomplete."
    elif audio_staged and reference_staged:
        validation_status = "ready_for_narrow_audio_eval"
        observation = "License confirmed and both audio/reference paths exist; narrow eval may proceed."
    else:
        validation_status = "metadata_only_pass"
        observation = (
            "License confirmed and mapping schema valid; audio not staged yet — metadata-only sanity check pass."
        )

    return {
        "dataset_name": str(mapping.get("dataset_name", "")),
        "slice_id": str(mapping.get("slice_id", "")),
        "label": str(mapping.get("label", "external/sanity-check")),
        "license_status": license_status,
        "license_confirmed": str(license_confirmed),
        "mapping_schema_valid": str(schema_valid),
        "audio_staged": str(audio_staged),
        "reference_staged": str(reference_staged),
        "validation_status": validation_status,
        "result_label": "external/sanity-check",
        "observation": observation,
    }


def build_summary_rows(check_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"metric": "validation_status", "value": check_row["validation_status"], "label": "external/sanity-check"},
        {"metric": "license_confirmed", "value": check_row["license_confirmed"], "label": "external/sanity-check"},
        {"metric": "audio_staged", "value": check_row["audio_staged"], "label": "external/sanity-check"},
    ]


def build_summary_lines(check_row: dict[str, str], summary_rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation Mini Sanity Check (external/sanity-check)",
        "",
        "Label: `external/sanity-check` — narrow preflight check for the first AISHELL-4 slice. "
        "Does not claim gold benchmark results.",
        "",
        "| metric | value | label |",
        "| --- | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(f"| {row['metric']} | {row['value']} | {row['label']} |")
    lines.extend(
        [
            "",
            f"- Observation: {check_row['observation']}",
        ]
    )
    return lines


def build_check_report() -> tuple[dict[str, str], list[dict[str, str]]]:
    mapping = load_slice_mapping()
    check_row = build_check_row(mapping)
    return check_row, build_summary_rows(check_row)


def write_outputs(
    check_row: dict[str, str],
    summary_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "external_validation_mini_sanity_check.csv"
    json_path = table_dir / "external_validation_mini_sanity_check.json"
    summary_csv_path = table_dir / "external_validation_mini_sanity_check_summary.csv"
    summary_json_path = table_dir / "external_validation_mini_sanity_check_summary.json"
    md_path = figure_dir / "external_validation_mini_sanity_check.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CHECK_COLUMNS)
        writer.writeheader()
        writer.writerow(check_row)
    json_path.write_text(json.dumps(check_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)
    summary_json_path.write_text(json.dumps(summary_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text("\n".join(build_summary_lines(check_row, summary_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, summary_csv_path, summary_json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run metadata-only mini sanity check for external validation slice.")
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    _ = load_config()
    check_row, summary_rows = build_check_report()
    paths = write_outputs(check_row, summary_rows)
    for path in paths:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")
    print(f"Validation status: {check_row['validation_status']}")


if __name__ == "__main__":
    main()
