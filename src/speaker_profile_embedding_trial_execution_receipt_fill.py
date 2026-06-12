from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .speaker_profile_spectral_embedding_baseline import build_nooverlap_baseline_row


FILL_COLUMNS = [
    "fill_status",
    "case_id",
    "method_direction",
    "execution_receipt_status",
    "spectral_best_alignment",
    "text_best_alignment",
    "signals_agree",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "run_scope",
    "case_id",
    "method_direction",
    "preflight_pass",
    "swapped_bias_detected",
    "text_best_alignment",
    "spectral_best_alignment",
    "signals_agree",
    "spectral_confidence_gap",
    "expected_inputs",
    "expected_outputs",
    "writeback_note",
]


def load_json_dict(path_rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_readiness() -> dict[str, Any]:
    return load_json_dict("results/tables/speaker_profile_embedding_trial_execution_receipt_readiness.json")


def assert_readiness(readiness: dict[str, Any]) -> None:
    if str(readiness.get("readiness_status", "")) != "receipt_ready_to_fill":
        raise RuntimeError(
            f"Receipt readiness must be receipt_ready_to_fill; got {readiness.get('readiness_status', 'missing')!r}"
        )
    if str(readiness.get("preflight_pass", "")).lower() != "true":
        raise RuntimeError("Embedding trial preflight must pass before filling receipt")


def build_filled_receipt_row(
    readiness: dict[str, Any],
    baseline_row: dict[str, str],
) -> dict[str, str]:
    case_id = str(readiness.get("case_id", baseline_row.get("case_id", "NoOverlap")))
    return {
        "execution_status": "embedding_diagnostic_complete",
        "run_scope": "single_case_embedding_execution",
        "case_id": case_id,
        "method_direction": "embedding_or_voiceprint_baseline",
        "preflight_pass": str(readiness.get("preflight_pass", "True")),
        "swapped_bias_detected": str(readiness.get("swapped_bias_detected", "True")),
        "text_best_alignment": str(baseline_row.get("text_best_alignment", "")),
        "spectral_best_alignment": str(baseline_row.get("spectral_best_alignment", "")),
        "signals_agree": str(baseline_row.get("signals_agree", "")),
        "spectral_confidence_gap": str(baseline_row.get("spectral_confidence_gap", "")),
        "expected_inputs": "con/pro snippet audio for one verified gold case plus spectral profile tooling.",
        "expected_outputs": "Embedding-similarity diagnostic note comparing direct vs swapped assignment.",
        "writeback_note": (
            "Narrow spectral embedding diagnostic executed on NoOverlap; experimental/frontier risk signal only — "
            "not voiceprint identification or speaker-attribution claim."
        ),
    }


def build_fill_row(readiness: dict[str, Any], baseline_row: dict[str, str]) -> dict[str, str]:
    return {
        "fill_status": "receipt_filled",
        "case_id": str(readiness.get("case_id", baseline_row.get("case_id", "NoOverlap"))),
        "method_direction": "embedding_or_voiceprint_baseline",
        "execution_receipt_status": "embedding_diagnostic_complete",
        "spectral_best_alignment": str(baseline_row.get("spectral_best_alignment", "")),
        "text_best_alignment": str(baseline_row.get("text_best_alignment", "")),
        "signals_agree": str(baseline_row.get("signals_agree", "")),
        "blocker": "none_documented",
        "fill_note": (
            "Execution receipt filled after spectral embedding baseline run on the verified NoOverlap case."
        ),
    }


def build_fill_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Execution Receipt Fill",
        "",
        "experimental/frontier writeback — diagnostic only, not speaker-ID.",
        "",
        "| fill_status | case_id | execution_receipt_status | spectral_alignment | text_alignment | signals_agree | blocker |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['fill_status']} | {row['case_id']} | {row['execution_receipt_status']} | "
            f"{row['spectral_best_alignment']} | {row['text_best_alignment']} | {row['signals_agree']} | {row['blocker']} |"
        ),
    ]
    return lines


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Execution Receipt",
        "",
        "| execution_status | case_id | spectral_alignment | text_alignment | signals_agree | writeback_note |",
        "| --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['case_id']} | {row['spectral_best_alignment']} | "
            f"{row['text_best_alignment']} | {row['signals_agree']} | {row['writeback_note']} |"
        ),
    ]
    return lines


def write_outputs(fill_row: dict[str, str], receipt_row: dict[str, str]) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    fill_csv = tables_dir / "speaker_profile_embedding_trial_execution_receipt_fill.csv"
    fill_json = tables_dir / "speaker_profile_embedding_trial_execution_receipt_fill.json"
    fill_md = figures_dir / "speaker_profile_embedding_trial_execution_receipt_fill.md"
    receipt_json = tables_dir / "speaker_profile_embedding_trial_execution_receipt.json"
    receipt_md = figures_dir / "speaker_profile_embedding_trial_execution_receipt.md"

    with fill_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FILL_COLUMNS)
        writer.writeheader()
        writer.writerow(fill_row)
    fill_json.write_text(json.dumps(fill_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fill_md.write_text("\n".join(build_fill_lines(fill_row)) + "\n", encoding="utf-8")
    receipt_json.write_text(json.dumps([receipt_row], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt_md.write_text("\n".join(build_receipt_lines(receipt_row)) + "\n", encoding="utf-8")
    return fill_csv, fill_json, fill_md, receipt_json, receipt_md


def fill_execution_receipt(force: bool = False) -> dict[str, str]:
    readiness = load_readiness()
    assert_readiness(readiness)

    receipt_path = PROJECT_ROOT / "results/tables/speaker_profile_embedding_trial_execution_receipt.json"
    if receipt_path.exists() and not force:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        if isinstance(payload, list) and payload:
            status = str(payload[0].get("execution_status", ""))
            if status == "embedding_diagnostic_complete":
                return {"fill_status": "already_filled", "execution_receipt_status": status}

    config = load_config()
    baseline_row = build_nooverlap_baseline_row(config)
    receipt_row = build_filled_receipt_row(readiness, baseline_row)
    fill_row = build_fill_row(readiness, baseline_row)
    write_outputs(fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "signals_agree": fill_row["signals_agree"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fill speaker profile embedding trial execution receipt after spectral baseline run."
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled receipt.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = fill_execution_receipt(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
