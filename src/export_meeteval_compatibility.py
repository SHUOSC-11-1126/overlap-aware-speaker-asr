from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .evaluate_cer import list_verified_cases, load_json, load_reference


SUMMARY_COLUMNS = [
    "case_id",
    "reference_segment_count",
    "hypothesis_segment_count",
    "speaker_count",
    "hypothesis_source",
    "reference_export",
    "hypothesis_export",
    "observation",
]

READINESS_COLUMNS = [
    "bridge_status",
    "case_count",
    "raw_source_count",
    "cleaned_fallback_count",
    "readiness_note",
    "next_action",
]

DRY_RUN_HANDOFF_COLUMNS = [
    "bridge_status",
    "source_mix",
    "recommended_slice",
    "dry_run_goal",
    "primary_blocker",
    "expected_evidence",
    "handoff_note",
]

DRY_RUN_RECEIPT_COLUMNS = [
    "execution_status",
    "run_scope",
    "expected_inputs",
    "expected_outputs",
    "writeback_note",
]

DRY_RUN_BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "bridge_status",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]

DRY_RUN_CHECKLIST_COLUMNS = [
    "case_id",
    "hypothesis_source",
    "dry_run_priority",
    "operator_step",
    "expected_evidence",
    "validation_note",
]

DRY_RUN_RECEIPT_CHECKLIST_COLUMNS = [
    "checklist_order",
    "dry_run_scope",
    "receipt_state",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "preflight_step",
    "next_gate",
]

DRY_RUN_RECEIPT_BOARD_COLUMNS = [
    "board_order",
    "dry_run_scope",
    "receipt_state",
    "prerequisite_artifact",
    "receipt_target",
    "board_note",
    "next_gate",
]

DRY_RUN_RECEIPT_MAP_COLUMNS = [
    "map_order",
    "dry_run_scope",
    "receipt_state",
    "prerequisite_artifact",
    "receipt_target",
    "map_note",
    "next_gate",
]


def load_reference_payload(case_id: str) -> dict[str, Any]:
    payload = load_reference(case_id)
    return {"segments": list(payload.get("segments", []))}


def load_hypothesis_payload(case_id: str) -> dict[str, Any]:
    raw_path = PROJECT_ROOT / "results" / "transcripts_speaker" / f"{case_id}_separated_speaker_transcript.json"
    if raw_path.exists():
        payload = load_json(raw_path)
        return {
            "segments": list(payload.get("segments", [])),
            "hypothesis_source": "separated_whisper",
        }

    cleaned_path = (
        PROJECT_ROOT / "results" / "transcripts_postprocessed" / f"{case_id}_separated_speaker_transcript_cleaned.json"
    )
    if cleaned_path.exists():
        payload = load_json(cleaned_path)
        return {
            "segments": list(payload.get("cleaned_segments", [])),
            "hypothesis_source": "separated_whisper_cleaned",
        }
    raise FileNotFoundError(
        f"Missing speaker transcript candidates: {raw_path.relative_to(PROJECT_ROOT)} and {cleaned_path.relative_to(PROJECT_ROOT)}"
    )


def build_meeteval_compatibility_rows(
    case_ids: list[str],
    reference_payloads: dict[str, dict[str, Any]],
    hypothesis_payloads: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case_id in case_ids:
        reference_segments = list(reference_payloads.get(case_id, {}).get("segments", []))
        hypothesis_segments = list(hypothesis_payloads.get(case_id, {}).get("segments", []))
        speakers = {
            str(segment.get("speaker", "")).strip()
            for segment in reference_segments + hypothesis_segments
            if str(segment.get("speaker", "")).strip()
        }
        rows.append(
            {
                "case_id": case_id,
                "reference_segment_count": len(reference_segments),
                "hypothesis_segment_count": len(hypothesis_segments),
                "speaker_count": len(speakers),
                "hypothesis_source": str(hypothesis_payloads.get(case_id, {}).get("hypothesis_source", "")),
                "reference_export": "results/tables/meeteval_reference_segments.jsonl",
                "hypothesis_export": "results/tables/meeteval_hypothesis_segments.jsonl",
                "observation": "compatibility bridge only; this export does not claim cpWER evaluation yet.",
            }
        )
    return rows


def build_meeteval_segment_lines(case_id: str, source: str, segments: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for segment in segments:
        payload = {
            "session_id": case_id,
            "speaker": str(segment.get("speaker", "")),
            "start_time": float(segment.get("start", 0.0) or 0.0),
            "end_time": float(segment.get("end", 0.0) or 0.0),
            "text": str(segment.get("text", "")),
            "source": source,
        }
        lines.append(json.dumps(payload, ensure_ascii=False))
    return lines


def build_meeteval_compatibility_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# MeetEval Compatibility Note",
        "",
        "This generated note documents a segment-level compatibility bridge only; it does not claim a finished MeetEval or cpWER evaluation.",
        "",
        "| case_id | reference_segment_count | hypothesis_segment_count | speaker_count | hypothesis_source | reference_export | hypothesis_export | observation |",
        "| --- | ---: | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['reference_segment_count']} | {row['hypothesis_segment_count']} | {row['speaker_count']} | {row['hypothesis_source']} | "
            f"{row['reference_export']} | {row['hypothesis_export']} | {row['observation']} |"
        )
    return lines


def build_meeteval_readiness_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    raw_source_count = sum(1 for row in rows if str(row.get("hypothesis_source", "")) == "separated_whisper")
    cleaned_fallback_count = sum(
        1 for row in rows if str(row.get("hypothesis_source", "")) == "separated_whisper_cleaned"
    )
    bridge_status = "ready_for_dry_run" if rows else "missing_export"
    readiness_note = (
        "The bridge is export-complete, but cleaned fallback is still common, so any next MeetEval step should stay narrow and diagnostic."
        if cleaned_fallback_count
        else "The bridge is export-complete with raw separated sources only, so a narrow diagnostic dry run is the next reasonable step."
    )
    next_action = "Use one narrow dry run before claiming any cpWER-style evaluation."
    return [
        {
            "bridge_status": bridge_status,
            "case_count": str(len(rows)),
            "raw_source_count": str(raw_source_count),
            "cleaned_fallback_count": str(cleaned_fallback_count),
            "readiness_note": readiness_note,
            "next_action": next_action,
        }
    ]


def build_meeteval_readiness_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval Readiness",
        "",
        "This generated card summarizes whether the current compatibility bridge is ready for a narrow diagnostic follow-up. It does not claim that MeetEval or cpWER has already been run.",
        "",
        "| bridge_status | case_count | raw_source_count | cleaned_fallback_count | readiness_note | next_action |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['bridge_status']} | {row['case_count']} | {row['raw_source_count']} | {row['cleaned_fallback_count']} | {row['readiness_note']} | {row['next_action']} |"
        )
    return lines


def build_meeteval_dry_run_handoff_rows(readiness_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not readiness_rows:
        return []

    readiness = readiness_rows[0]
    cleaned_fallback_count = int(str(readiness.get("cleaned_fallback_count", "0")) or "0")
    raw_source_count = int(str(readiness.get("raw_source_count", "0")) or "0")
    if cleaned_fallback_count > raw_source_count:
        source_mix = "cleaned_fallback_dominant"
        primary_blocker = "Cleaned fallback still dominates the current hypothesis mix, so the first dry run should stay diagnostic."
    elif raw_source_count:
        source_mix = "raw_source_available"
        primary_blocker = "Raw separated sources are available, but the bridge still needs a tightly scoped first dry run."
    else:
        source_mix = "source_mix_unknown"
        primary_blocker = "The current source mix is unclear, so the next dry run should start by validating one exported case."

    return [
        {
            "bridge_status": str(readiness.get("bridge_status", "")),
            "source_mix": source_mix,
            "recommended_slice": "single_verified_case",
            "dry_run_goal": "Run one narrow diagnostic pass to validate the export path before any broader MeetEval or cpWER claim.",
            "primary_blocker": primary_blocker,
            "expected_evidence": "results/tables/meeteval_dry_run_receipt.json",
            "handoff_note": "MeetEval / cpWER has not been run yet; this card only frames the first dry run.",
        }
    ]


def build_meeteval_dry_run_handoff_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval Dry Run Handoff",
        "",
        "This generated handoff packet translates readiness into a single narrow next step. It does not claim that MeetEval or cpWER has been run.",
        "",
        "| bridge_status | source_mix | recommended_slice | dry_run_goal | primary_blocker | expected_evidence | handoff_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['bridge_status']} | {row['source_mix']} | {row['recommended_slice']} | {row['dry_run_goal']} | {row['primary_blocker']} | {row['expected_evidence']} | {row['handoff_note']} |"
        )
    return lines


def build_meeteval_dry_run_receipt_rows(handoff_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not handoff_rows:
        return []

    handoff = handoff_rows[0]
    return [
        {
            "execution_status": "template_only",
            "run_scope": str(handoff.get("recommended_slice", "")),
            "expected_inputs": "results/tables/meeteval_reference_segments.jsonl; results/tables/meeteval_hypothesis_segments.jsonl",
            "expected_outputs": "Diagnostic export-path confirmation and a narrow run note.",
            "writeback_note": "MeetEval / cpWER has not been executed yet; fill this receipt only after the first dry run.",
        }
    ]


def build_meeteval_dry_run_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval Dry Run Receipt",
        "",
        "This generated receipt is a template-only writeback target for the first narrow dry run. It does not claim that MeetEval or cpWER has been executed.",
        "",
        "| execution_status | run_scope | expected_inputs | expected_outputs | writeback_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['run_scope']} | {row['expected_inputs']} | {row['expected_outputs']} | {row['writeback_note']} |"
        )
    return lines


def build_meeteval_dry_run_bridge_checklist_rows(
    handoff_rows: list[dict[str, str]],
    receipt_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not handoff_rows or not receipt_rows:
        return []

    handoff = handoff_rows[0]
    receipt = receipt_rows[0]
    bridge_status = str(handoff.get("bridge_status", ""))
    run_scope = str(receipt.get("run_scope", ""))
    return [
        {
            "checklist_order": "1",
            "bridge_status": bridge_status,
            "prerequisite_artifact": "results/figures/meeteval_dry_run_handoff.md",
            "receipt_target": "results/figures/meeteval_dry_run_receipt.md",
            "checklist_goal": f"Verify the first MeetEval dry run bridge for {bridge_status} before any writeback is advanced.",
            "bridge_note": f"Open the handoff packet first, then write back through the receipt target for {run_scope}.",
            "next_gate": "Confirm this bridge before opening the receipt target.",
        }
    ]


def build_meeteval_dry_run_bridge_checklist_lines(
    rows: list[dict[str, str]],
) -> list[str]:
    lines = [
        "# MeetEval Dry Run Bridge Checklist",
        "",
        "This generated checklist turns the dry-run handoff into a row-by-row bridge verification path. It remains coordination-only and does not claim that MeetEval or cpWER has already been executed.",
        "",
        "| checklist_order | bridge_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['bridge_status']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def build_meeteval_dry_run_checklist_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    checklist_rows: list[dict[str, str]] = []
    for row in rows:
        hypothesis_source = str(row.get("hypothesis_source", ""))
        if hypothesis_source == "separated_whisper":
            dry_run_priority = "preferred"
            validation_note = "Raw separated source is available, so this is the cleanest first dry-run candidate."
        elif hypothesis_source == "separated_whisper_cleaned":
            dry_run_priority = "secondary"
            validation_note = "Cleaned fallback is available, but it should stay behind raw separated source cases in the dry-run queue."
        else:
            dry_run_priority = "unknown"
            validation_note = "Source mix is unclear, so the case should only be used after the export path is checked."

        checklist_rows.append(
            {
                "case_id": str(row.get("case_id", "")),
                "hypothesis_source": hypothesis_source,
                "dry_run_priority": dry_run_priority,
                "operator_step": "Validate one exported case end-to-end before any cpWER-style claim.",
                "expected_evidence": "results/tables/meeteval_dry_run_receipt.json",
                "validation_note": validation_note,
            }
        )
    return checklist_rows


def build_meeteval_dry_run_receipt_checklist_rows(receipt_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not receipt_rows:
        return []

    receipt = receipt_rows[0]
    dry_run_scope = str(receipt.get("run_scope", "single_verified_case"))
    receipt_state = str(receipt.get("execution_status", "template_only"))
    return [
        {
            "checklist_order": "1",
            "dry_run_scope": dry_run_scope,
            "receipt_state": receipt_state,
            "prerequisite_artifact": "results/figures/meeteval_dry_run_checklist.md",
            "receipt_target": "results/figures/meeteval_dry_run_receipt.md",
            "checklist_goal": f"Verify the dry-run receipt path for {dry_run_scope} before any cpWER claim is advanced.",
            "preflight_step": "Open the dry-run checklist and confirm the preferred case export before filling the receipt.",
            "next_gate": "Fill the receipt before promoting any MeetEval evaluation claim.",
        }
    ]


def build_meeteval_dry_run_receipt_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval Dry Run Receipt Checklist",
        "",
        "This generated checklist turns the dry-run receipt into an ordered verification path. It remains coordination-only and does not claim a finished MeetEval or cpWER evaluation.",
        "",
        "| checklist_order | dry_run_scope | receipt_state | prerequisite_artifact | receipt_target | checklist_goal | preflight_step | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['dry_run_scope']} | {row['receipt_state']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | {row['preflight_step']} | {row['next_gate']} |"
        )
    return lines


def build_meeteval_dry_run_receipt_board_rows(
    receipt_rows: list[dict[str, str]],
    receipt_checklist_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not receipt_rows:
        return []

    receipt = receipt_rows[0]
    checklist = receipt_checklist_rows[0] if receipt_checklist_rows else {}
    dry_run_scope = str(receipt.get("run_scope", "single_verified_case"))
    return [
        {
            "board_order": "1",
            "dry_run_scope": dry_run_scope,
            "receipt_state": str(receipt.get("execution_status", "template_only")),
            "prerequisite_artifact": str(
                checklist.get("prerequisite_artifact", "results/figures/meeteval_dry_run_checklist.md")
            ),
            "receipt_target": str(checklist.get("receipt_target", "results/figures/meeteval_dry_run_receipt.md")),
            "board_note": f"Keep the dry-run receipt path visible for {dry_run_scope} while cpWER evaluation remains pending.",
            "next_gate": "Open the receipt checklist before advancing any MeetEval evaluation claim.",
        }
    ]


def build_meeteval_dry_run_receipt_board_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval Dry Run Receipt Board",
        "",
        "This generated board condenses the dry-run receipt path into a single coordination snapshot. It does not claim a finished MeetEval or cpWER evaluation.",
        "",
        "| board_order | dry_run_scope | receipt_state | prerequisite_artifact | receipt_target | board_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['board_order']} | {row['dry_run_scope']} | {row['receipt_state']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['board_note']} | {row['next_gate']} |"
        )
    return lines


def build_meeteval_dry_run_receipt_map_rows(
    receipt_rows: list[dict[str, str]],
    receipt_checklist_rows: list[dict[str, str]],
    receipt_board_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not receipt_rows:
        return []

    receipt = receipt_rows[0]
    checklist = receipt_checklist_rows[0] if receipt_checklist_rows else {}
    board = receipt_board_rows[0] if receipt_board_rows else {}
    dry_run_scope = str(receipt.get("run_scope", "single_verified_case"))
    return [
        {
            "map_order": "1",
            "dry_run_scope": dry_run_scope,
            "receipt_state": str(receipt.get("execution_status", "template_only")),
            "prerequisite_artifact": str(
                board.get("prerequisite_artifact", checklist.get("prerequisite_artifact", "results/figures/meeteval_dry_run_checklist.md"))
            ),
            "receipt_target": str(
                board.get("receipt_target", checklist.get("receipt_target", "results/figures/meeteval_dry_run_receipt.md"))
            ),
            "map_note": f"Keep the dry-run receipt path visible across the receipt, checklist, and board views for {dry_run_scope}.",
            "next_gate": "Open the receipt board and checklist before advancing any MeetEval evaluation claim.",
        }
    ]


def build_meeteval_dry_run_receipt_map_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval Dry Run Receipt Map",
        "",
        "This generated map condenses the dry-run receipt path into a single coordination view across the receipt, checklist, and board layers. It does not claim a finished MeetEval or cpWER evaluation.",
        "",
        "| map_order | dry_run_scope | receipt_state | prerequisite_artifact | receipt_target | map_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['map_order']} | {row['dry_run_scope']} | {row['receipt_state']} | {row['prerequisite_artifact']} | {row['receipt_target']} | {row['map_note']} | {row['next_gate']} |"
        )
    return lines


def build_meeteval_dry_run_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval Dry Run Checklist",
        "",
        "This generated checklist orders the verified cases for a single diagnostic dry run. It does not claim that MeetEval or cpWER has been run.",
        "",
        "| case_id | hypothesis_source | dry_run_priority | operator_step | expected_evidence | validation_note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['hypothesis_source']} | {row['dry_run_priority']} | {row['operator_step']} | {row['expected_evidence']} | {row['validation_note']} |"
        )
    return lines


def write_outputs(
    rows: list[dict[str, Any]],
    reference_lines: list[str],
    hypothesis_lines: list[str],
) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_compatibility_summary.csv"
    json_path = tables_dir / "meeteval_compatibility_summary.json"
    reference_path = tables_dir / "meeteval_reference_segments.jsonl"
    hypothesis_path = tables_dir / "meeteval_hypothesis_segments.jsonl"
    note_path = figures_dir / "meeteval_compatibility_note.md"
    readiness_rows = build_meeteval_readiness_rows(rows)
    readiness_csv_path = tables_dir / "meeteval_readiness.csv"
    readiness_json_path = tables_dir / "meeteval_readiness.json"
    readiness_note_path = figures_dir / "meeteval_readiness.md"
    dry_run_handoff_rows = build_meeteval_dry_run_handoff_rows(readiness_rows)
    dry_run_handoff_csv_path = tables_dir / "meeteval_dry_run_handoff.csv"
    dry_run_handoff_json_path = tables_dir / "meeteval_dry_run_handoff.json"
    dry_run_handoff_note_path = figures_dir / "meeteval_dry_run_handoff.md"
    dry_run_receipt_rows = build_meeteval_dry_run_receipt_rows(dry_run_handoff_rows)
    dry_run_receipt_json_path = tables_dir / "meeteval_dry_run_receipt.json"
    dry_run_receipt_note_path = figures_dir / "meeteval_dry_run_receipt.md"
    dry_run_bridge_checklist_rows = build_meeteval_dry_run_bridge_checklist_rows(
        dry_run_handoff_rows,
        dry_run_receipt_rows,
    )
    dry_run_bridge_checklist_csv_path = tables_dir / "meeteval_dry_run_bridge_checklist.csv"
    dry_run_bridge_checklist_json_path = tables_dir / "meeteval_dry_run_bridge_checklist.json"
    dry_run_bridge_checklist_note_path = figures_dir / "meeteval_dry_run_bridge_checklist.md"
    dry_run_checklist_rows = build_meeteval_dry_run_checklist_rows(rows)
    dry_run_checklist_csv_path = tables_dir / "meeteval_dry_run_checklist.csv"
    dry_run_checklist_json_path = tables_dir / "meeteval_dry_run_checklist.json"
    dry_run_checklist_note_path = figures_dir / "meeteval_dry_run_checklist.md"
    dry_run_receipt_checklist_rows = build_meeteval_dry_run_receipt_checklist_rows(dry_run_receipt_rows)
    dry_run_receipt_checklist_csv_path = tables_dir / "meeteval_dry_run_receipt_checklist.csv"
    dry_run_receipt_checklist_json_path = tables_dir / "meeteval_dry_run_receipt_checklist.json"
    dry_run_receipt_checklist_note_path = figures_dir / "meeteval_dry_run_receipt_checklist.md"
    dry_run_receipt_board_rows = build_meeteval_dry_run_receipt_board_rows(
        dry_run_receipt_rows,
        dry_run_receipt_checklist_rows,
    )
    dry_run_receipt_board_csv_path = tables_dir / "meeteval_dry_run_receipt_board.csv"
    dry_run_receipt_board_json_path = tables_dir / "meeteval_dry_run_receipt_board.json"
    dry_run_receipt_board_note_path = figures_dir / "meeteval_dry_run_receipt_board.md"
    dry_run_receipt_map_rows = build_meeteval_dry_run_receipt_map_rows(
        dry_run_receipt_rows,
        dry_run_receipt_checklist_rows,
        dry_run_receipt_board_rows,
    )
    dry_run_receipt_map_csv_path = tables_dir / "meeteval_dry_run_receipt_map.csv"
    dry_run_receipt_map_json_path = tables_dir / "meeteval_dry_run_receipt_map.json"
    dry_run_receipt_map_note_path = figures_dir / "meeteval_dry_run_receipt_map.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    reference_path.write_text("\n".join(reference_lines) + ("\n" if reference_lines else ""), encoding="utf-8")
    hypothesis_path.write_text("\n".join(hypothesis_lines) + ("\n" if hypothesis_lines else ""), encoding="utf-8")
    note_path.write_text("\n".join(build_meeteval_compatibility_lines(rows)) + "\n", encoding="utf-8")
    with readiness_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=READINESS_COLUMNS)
        writer.writeheader()
        writer.writerows(readiness_rows)
    readiness_json_path.write_text(json.dumps(readiness_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    readiness_note_path.write_text("\n".join(build_meeteval_readiness_lines(readiness_rows)) + "\n", encoding="utf-8")
    with dry_run_handoff_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DRY_RUN_HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerows(dry_run_handoff_rows)
    dry_run_handoff_json_path.write_text(json.dumps(dry_run_handoff_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    dry_run_handoff_note_path.write_text(
        "\n".join(build_meeteval_dry_run_handoff_lines(dry_run_handoff_rows)) + "\n",
        encoding="utf-8",
    )
    dry_run_receipt_json_path.write_text(json.dumps(dry_run_receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    dry_run_receipt_note_path.write_text(
        "\n".join(build_meeteval_dry_run_receipt_lines(dry_run_receipt_rows)) + "\n",
        encoding="utf-8",
    )
    with dry_run_bridge_checklist_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DRY_RUN_BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(dry_run_bridge_checklist_rows)
    dry_run_bridge_checklist_json_path.write_text(
        json.dumps(dry_run_bridge_checklist_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    dry_run_bridge_checklist_note_path.write_text(
        "\n".join(build_meeteval_dry_run_bridge_checklist_lines(dry_run_bridge_checklist_rows)) + "\n",
        encoding="utf-8",
    )
    with dry_run_checklist_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DRY_RUN_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(dry_run_checklist_rows)
    dry_run_checklist_json_path.write_text(json.dumps(dry_run_checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    dry_run_checklist_note_path.write_text(
        "\n".join(build_meeteval_dry_run_checklist_lines(dry_run_checklist_rows)) + "\n",
        encoding="utf-8",
    )
    with dry_run_receipt_checklist_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DRY_RUN_RECEIPT_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(dry_run_receipt_checklist_rows)
    dry_run_receipt_checklist_json_path.write_text(
        json.dumps(dry_run_receipt_checklist_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    dry_run_receipt_checklist_note_path.write_text(
        "\n".join(build_meeteval_dry_run_receipt_checklist_lines(dry_run_receipt_checklist_rows)) + "\n",
        encoding="utf-8",
    )
    with dry_run_receipt_board_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DRY_RUN_RECEIPT_BOARD_COLUMNS)
        writer.writeheader()
        writer.writerows(dry_run_receipt_board_rows)
    dry_run_receipt_board_json_path.write_text(
        json.dumps(dry_run_receipt_board_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    dry_run_receipt_board_note_path.write_text(
        "\n".join(build_meeteval_dry_run_receipt_board_lines(dry_run_receipt_board_rows)) + "\n",
        encoding="utf-8",
    )
    with dry_run_receipt_map_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DRY_RUN_RECEIPT_MAP_COLUMNS)
        writer.writeheader()
        writer.writerows(dry_run_receipt_map_rows)
    dry_run_receipt_map_json_path.write_text(
        json.dumps(dry_run_receipt_map_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    dry_run_receipt_map_note_path.write_text(
        "\n".join(build_meeteval_dry_run_receipt_map_lines(dry_run_receipt_map_rows)) + "\n",
        encoding="utf-8",
    )
    return (
        csv_path,
        json_path,
        reference_path,
        hypothesis_path,
        note_path,
        readiness_csv_path,
        readiness_json_path,
        readiness_note_path,
        dry_run_handoff_csv_path,
        dry_run_handoff_json_path,
        dry_run_handoff_note_path,
        dry_run_receipt_json_path,
        dry_run_receipt_note_path,
        dry_run_bridge_checklist_csv_path,
        dry_run_bridge_checklist_json_path,
        dry_run_bridge_checklist_note_path,
        dry_run_checklist_csv_path,
        dry_run_checklist_json_path,
        dry_run_checklist_note_path,
        dry_run_receipt_checklist_csv_path,
        dry_run_receipt_checklist_json_path,
        dry_run_receipt_checklist_note_path,
        dry_run_receipt_board_csv_path,
        dry_run_receipt_board_json_path,
        dry_run_receipt_board_note_path,
        dry_run_receipt_map_csv_path,
        dry_run_receipt_map_json_path,
        dry_run_receipt_map_note_path,
    )


def main() -> None:
    case_ids = list_verified_cases()
    reference_payloads = {case_id: load_reference_payload(case_id) for case_id in case_ids}
    hypothesis_payloads = {case_id: load_hypothesis_payload(case_id) for case_id in case_ids}
    rows = build_meeteval_compatibility_rows(case_ids, reference_payloads, hypothesis_payloads)
    reference_lines: list[str] = []
    hypothesis_lines: list[str] = []
    for case_id in case_ids:
        reference_lines.extend(
            build_meeteval_segment_lines(case_id, "reference", list(reference_payloads[case_id].get("segments", [])))
        )
        hypothesis_lines.extend(
            build_meeteval_segment_lines(case_id, "hypothesis", list(hypothesis_payloads[case_id].get("segments", [])))
        )
    (
        csv_path,
        json_path,
        reference_path,
        hypothesis_path,
        note_path,
        readiness_csv_path,
        readiness_json_path,
        readiness_note_path,
        dry_run_handoff_csv_path,
        dry_run_handoff_json_path,
        dry_run_handoff_note_path,
        dry_run_receipt_json_path,
        dry_run_receipt_note_path,
        dry_run_bridge_checklist_csv_path,
        dry_run_bridge_checklist_json_path,
        dry_run_bridge_checklist_note_path,
        dry_run_checklist_csv_path,
        dry_run_checklist_json_path,
        dry_run_checklist_note_path,
        dry_run_receipt_checklist_csv_path,
        dry_run_receipt_checklist_json_path,
        dry_run_receipt_checklist_note_path,
        dry_run_receipt_board_csv_path,
        dry_run_receipt_board_json_path,
        dry_run_receipt_board_note_path,
        dry_run_receipt_map_csv_path,
        dry_run_receipt_map_json_path,
        dry_run_receipt_map_note_path,
    ) = write_outputs(rows, reference_lines, hypothesis_lines)
    print(f"Wrote MeetEval summary: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval reference export: {reference_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval hypothesis export: {hypothesis_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval note: {note_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval readiness CSV: {readiness_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval readiness JSON: {readiness_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval readiness note: {readiness_note_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run handoff CSV: {dry_run_handoff_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run handoff JSON: {dry_run_handoff_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run handoff note: {dry_run_handoff_note_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run receipt JSON: {dry_run_receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run receipt note: {dry_run_receipt_note_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run bridge checklist CSV: {dry_run_bridge_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run bridge checklist JSON: {dry_run_bridge_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run bridge checklist note: {dry_run_bridge_checklist_note_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run checklist CSV: {dry_run_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run checklist JSON: {dry_run_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run checklist note: {dry_run_checklist_note_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run receipt checklist CSV: {dry_run_receipt_checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run receipt checklist JSON: {dry_run_receipt_checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run receipt checklist note: {dry_run_receipt_checklist_note_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run receipt board CSV: {dry_run_receipt_board_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run receipt board JSON: {dry_run_receipt_board_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run receipt board note: {dry_run_receipt_board_note_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run receipt map CSV: {dry_run_receipt_map_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run receipt map JSON: {dry_run_receipt_map_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval dry run receipt map note: {dry_run_receipt_map_note_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
