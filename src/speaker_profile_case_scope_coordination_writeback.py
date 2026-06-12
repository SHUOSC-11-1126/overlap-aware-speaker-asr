from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


CARD_COLUMNS = [
    "section_id",
    "headline",
    "artifact_anchor",
    "coordination_note",
    "result_label",
]

FILL_COLUMNS = [
    "fill_status",
    "writeback_scope",
    "coordination_section_count",
    "completed_case_scope",
    "candidate_case_scope",
    "execution_receipt_status",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "coordination_scope",
    "wave7_closure_status",
    "nooverlap_diagnostic_status",
    "signals_agree",
    "expected_inputs",
    "writeback_note",
]


def load_json_dict(path_rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def assert_writeback_preconditions(
    wave7_receipt: dict[str, Any],
    embedding_fill: dict[str, Any],
) -> None:
    if str(wave7_receipt.get("execution_status", "")) != "wave7_exploration_baseline_closure_complete":
        raise RuntimeError("Wave7 closure must be complete before speaker profile case-scope coordination")
    if str(embedding_fill.get("execution_receipt_status", "")) != "embedding_diagnostic_complete":
        raise RuntimeError("NoOverlap embedding diagnostic must be complete before case-scope coordination")


def build_coordination_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "nooverlap_complete",
            "headline": "NoOverlap spectral embedding diagnostic complete",
            "artifact_anchor": "results/tables/speaker_profile_embedding_trial_execution_receipt_fill.json",
            "coordination_note": "Swapped-bias signal recorded; not speaker-ID or attribution.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "overlap_candidates",
            "headline": "LightOverlap and MidOverlap are next diagnostic-only candidates",
            "artifact_anchor": "results/figures/separation_phase_diagram.md",
            "coordination_note": "Separation hurts on these gold anchors; any extension stays diagnostic-only.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "attribution_boundary",
            "headline": "Attribution claims remain blocked by weak_support",
            "artifact_anchor": "results/figures/speaker_profile_go_no_go_summary.md",
            "coordination_note": "Do not upgrade embedding diagnostic into voiceprint identification.",
            "result_label": "experimental/frontier",
        },
        {
            "section_id": "wave7_link",
            "headline": "Wave7 exploration+baseline closure defers broader case rollout",
            "artifact_anchor": "results/figures/wave7_exploration_baseline_closure_card.md",
            "coordination_note": "Case-scope coordination only; gold baseline CER tables unchanged.",
            "result_label": "experimental/frontier",
        },
    ]


def build_fill_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "speaker_profile_case_scope_coordination_card",
        "coordination_section_count": str(len(rows)),
        "completed_case_scope": "NoOverlap",
        "candidate_case_scope": "LightOverlap,MidOverlap",
        "execution_receipt_status": "speaker_profile_case_scope_coordination_complete",
        "blocker": "attribution_claims_still_blocked",
        "fill_note": (
            "Documented speaker profile case-scope boundary after NoOverlap embedding diagnostic; "
            "overlap cases remain diagnostic candidates only."
        ),
    }


def build_receipt_row(
    wave7_receipt: dict[str, Any],
    embedding_fill: dict[str, Any],
) -> dict[str, str]:
    return {
        "execution_status": "speaker_profile_case_scope_coordination_complete",
        "coordination_scope": "wave7_speaker_profile_case_scope",
        "wave7_closure_status": str(wave7_receipt.get("execution_status", "")),
        "nooverlap_diagnostic_status": str(embedding_fill.get("execution_receipt_status", "")),
        "signals_agree": str(embedding_fill.get("signals_agree", "")),
        "expected_inputs": "NoOverlap embedding receipt fill and Wave7 exploration baseline closure.",
        "writeback_note": (
            "experimental/frontier case-scope coordination only; does not claim multi-case embedding execution."
        ),
    }


def build_card_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Case-Scope Coordination Card (experimental/frontier)",
        "",
        "Diagnostic case-scope boundary — not multi-case embedding execution.",
        "",
        "| section_id | headline | artifact_anchor | result_label |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['section_id']} | {row['headline']} | {row['artifact_anchor']} | {row['result_label']} |"
        )
    lines.append("")
    for row in rows:
        lines.append(f"- **{row['section_id']}**: {row['coordination_note']}")
    return lines


def build_fill_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Case-Scope Coordination Writeback",
        "",
        "| fill_status | completed_case_scope | candidate_case_scope | execution_receipt_status | blocker |",
        "| --- | --- | --- | --- | --- |",
        (
            f"| {row['fill_status']} | {row['completed_case_scope']} | {row['candidate_case_scope']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Case-Scope Coordination Receipt",
        "",
        "| execution_status | nooverlap_diagnostic_status | signals_agree | blocker |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['nooverlap_diagnostic_status']} | "
            f"{row['signals_agree']} | attribution_claims_still_blocked |"
        ),
    ]


def write_outputs(
    card_rows: list[dict[str, str]],
    fill_row: dict[str, str],
    receipt_row: dict[str, str],
) -> Path:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    card_csv = tables_dir / "speaker_profile_case_scope_coordination_card.csv"
    card_json = tables_dir / "speaker_profile_case_scope_coordination_card.json"
    card_md = figures_dir / "speaker_profile_case_scope_coordination_card.md"
    fill_csv = tables_dir / "speaker_profile_case_scope_coordination_writeback.csv"
    fill_json = tables_dir / "speaker_profile_case_scope_coordination_writeback.json"
    fill_md = figures_dir / "speaker_profile_case_scope_coordination_writeback.md"
    receipt_json = tables_dir / "speaker_profile_case_scope_coordination_receipt.json"
    receipt_md = figures_dir / "speaker_profile_case_scope_coordination_receipt.md"

    with card_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CARD_COLUMNS)
        writer.writeheader()
        writer.writerows(card_rows)
    card_json.write_text(json.dumps(card_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    card_md.write_text("\n".join(build_card_lines(card_rows)) + "\n", encoding="utf-8")

    with fill_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FILL_COLUMNS)
        writer.writeheader()
        writer.writerow(fill_row)
    fill_json.write_text(json.dumps(fill_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fill_md.write_text("\n".join(build_fill_lines(fill_row)) + "\n", encoding="utf-8")
    receipt_json.write_text(json.dumps(receipt_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt_md.write_text("\n".join(build_receipt_lines(receipt_row)) + "\n", encoding="utf-8")
    return fill_json


def run_coordination_writeback(force: bool = False) -> dict[str, str]:
    wave7_receipt = load_json_dict("results/tables/wave7_exploration_baseline_closure_receipt.json")
    embedding_fill = load_json_dict("results/tables/speaker_profile_embedding_trial_execution_receipt_fill.json")
    assert_writeback_preconditions(wave7_receipt, embedding_fill)

    receipt_path = PROJECT_ROOT / "results/tables/speaker_profile_case_scope_coordination_receipt.json"
    if receipt_path.exists() and not force:
        existing = load_json_dict("results/tables/speaker_profile_case_scope_coordination_receipt.json")
        if str(existing.get("execution_status", "")) == "speaker_profile_case_scope_coordination_complete":
            return {
                "fill_status": "already_filled",
                "execution_receipt_status": "speaker_profile_case_scope_coordination_complete",
                "blocker": "attribution_claims_still_blocked",
            }

    card_rows = build_coordination_rows()
    fill_row = build_fill_row(card_rows)
    receipt_row = build_receipt_row(wave7_receipt, embedding_fill)
    write_outputs(card_rows, fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "completed_case_scope": fill_row["completed_case_scope"],
        "candidate_case_scope": fill_row["candidate_case_scope"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write speaker profile case-scope coordination after Wave7 closure.")
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled coordination receipt.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_coordination_writeback(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
