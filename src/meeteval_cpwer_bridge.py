from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .evaluate_cer import levenshtein_distance, list_verified_cases, normalize_text
from .meeteval_dry_run import load_jsonl_segments, select_preferred_case


BRIDGE_COLUMNS = [
    "case_id",
    "hypothesis_source",
    "speaker_count",
    "direct_macro_cer",
    "swapped_macro_cer",
    "cpwer_bridge_lite",
    "best_mapping",
    "observation",
]

HANDOFF_COLUMNS = [
    "bridge_status",
    "case_id",
    "cpwer_bridge_lite",
    "best_mapping",
    "bridge_goal",
    "primary_limitation",
    "expected_evidence",
    "handoff_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "run_scope",
    "case_id",
    "cpwer_bridge_lite",
    "best_mapping",
    "expected_inputs",
    "writeback_note",
]

SUMMARY_COLUMNS = [
    "scope",
    "case_count",
    "average_cpwer_bridge_lite",
    "direct_mapping_count",
    "swapped_mapping_count",
    "observation",
]


def aggregate_speaker_text(segments: list[dict[str, Any]], speaker: str) -> str:
    texts: list[str] = []
    for segment in segments:
        if str(segment.get("speaker", "")).strip() == speaker:
            text = str(segment.get("text", "")).strip()
            if text:
                texts.append(text)
    return "".join(texts)


def compute_cer(reference_text: str, hypothesis_text: str) -> float:
    ref_norm = normalize_text(reference_text)
    hyp_norm = normalize_text(hypothesis_text)
    distance = levenshtein_distance(ref_norm, hyp_norm)
    reference_length = len(ref_norm)
    return round(distance / reference_length, 6) if reference_length else 0.0


def macro_cer_for_mapping(
    reference_segments: list[dict[str, Any]],
    hypothesis_segments: list[dict[str, Any]],
    speakers: list[str],
    mapping: dict[str, str],
) -> float:
    scores: list[float] = []
    for speaker in speakers:
        reference_text = aggregate_speaker_text(reference_segments, speaker)
        hypothesis_text = aggregate_speaker_text(hypothesis_segments, mapping[speaker])
        if reference_text:
            scores.append(compute_cer(reference_text, hypothesis_text))
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 6)


def build_cpwer_bridge_row(
    case_id: str,
    reference_segments: list[dict[str, Any]],
    hypothesis_segments: list[dict[str, Any]],
    hypothesis_source: str = "",
) -> dict[str, Any]:
    speakers = sorted(
        {
            str(segment.get("speaker", "")).strip()
            for segment in reference_segments + hypothesis_segments
            if str(segment.get("speaker", "")).strip()
        }
    )
    if len(speakers) != 2:
        return {
            "case_id": case_id,
            "hypothesis_source": hypothesis_source,
            "speaker_count": len(speakers),
            "direct_macro_cer": 0.0,
            "swapped_macro_cer": 0.0,
            "cpwer_bridge_lite": 0.0,
            "best_mapping": "unsupported",
            "observation": "cpWER bridge-lite currently supports exactly two speakers per case.",
        }

    speaker_a, speaker_b = speakers
    direct_mapping = {speaker_a: speaker_a, speaker_b: speaker_b}
    swapped_mapping = {speaker_a: speaker_b, speaker_b: speaker_a}
    direct_macro_cer = macro_cer_for_mapping(
        reference_segments,
        hypothesis_segments,
        speakers,
        direct_mapping,
    )
    swapped_macro_cer = macro_cer_for_mapping(
        reference_segments,
        hypothesis_segments,
        speakers,
        swapped_mapping,
    )
    if swapped_macro_cer < direct_macro_cer:
        best_mapping = "swapped"
        cpwer_bridge_lite = swapped_macro_cer
    else:
        best_mapping = "direct"
        cpwer_bridge_lite = direct_macro_cer

    return {
        "case_id": case_id,
        "hypothesis_source": hypothesis_source,
        "speaker_count": len(speakers),
        "direct_macro_cer": direct_macro_cer,
        "swapped_macro_cer": swapped_macro_cer,
        "cpwer_bridge_lite": cpwer_bridge_lite,
        "best_mapping": best_mapping,
        "observation": (
            "experimental/frontier cpWER bridge-lite from JSONL exports; "
            "this is not a full MeetEval cpWER claim."
        ),
    }


def build_cpwer_bridge_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Bridge",
        "",
        "This generated note records a narrow cpWER bridge-lite pass on exported segments. "
        "It does not claim a full MeetEval or official cpWER benchmark evaluation.",
        "",
        "| case_id | hypothesis_source | speaker_count | direct_macro_cer | swapped_macro_cer | cpwer_bridge_lite | best_mapping | observation |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['hypothesis_source']} | {row['speaker_count']} | "
            f"{row['direct_macro_cer']} | {row['swapped_macro_cer']} | {row['cpwer_bridge_lite']} | "
            f"{row['best_mapping']} | {row['observation']} |"
        )
    return lines


def build_cpwer_bridge_summary_row(rows: list[dict[str, Any]], scope: str) -> dict[str, Any]:
    if not rows:
        return {
            "scope": scope,
            "case_count": 0,
            "average_cpwer_bridge_lite": 0.0,
            "direct_mapping_count": 0,
            "swapped_mapping_count": 0,
            "observation": "No cpWER bridge-lite rows were available for summary.",
        }

    direct_count = sum(1 for row in rows if str(row.get("best_mapping", "")) == "direct")
    swapped_count = sum(1 for row in rows if str(row.get("best_mapping", "")) == "swapped")
    average = round(
        sum(float(row.get("cpwer_bridge_lite", 0.0) or 0.0) for row in rows) / len(rows),
        6,
    )
    return {
        "scope": scope,
        "case_count": len(rows),
        "average_cpwer_bridge_lite": average,
        "direct_mapping_count": direct_count,
        "swapped_mapping_count": swapped_count,
        "observation": (
            "experimental/frontier all-case cpWER bridge-lite summary; "
            "this is not a full MeetEval cpWER benchmark claim."
        ),
    }


def build_cpwer_bridge_summary_lines(row: dict[str, Any]) -> list[str]:
    lines = [
        "# MeetEval cpWER Bridge Summary",
        "",
        "This generated note summarizes the cpWER bridge-lite pass across the selected gold scope. "
        "It does not claim a full MeetEval or official cpWER benchmark evaluation.",
        "",
        "| scope | case_count | average_cpwer_bridge_lite | direct_mapping_count | swapped_mapping_count | observation |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
        (
            f"| {row['scope']} | {row['case_count']} | {row['average_cpwer_bridge_lite']} | "
            f"{row['direct_mapping_count']} | {row['swapped_mapping_count']} | {row['observation']} |"
        ),
    ]
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MeetEval cpWER bridge-lite on exported segments.")
    parser.add_argument(
        "--case",
        default="preferred",
        help="Verified case id, 'all', or 'preferred' (default uses dry-run checklist priority).",
    )
    return parser.parse_args()


def load_hypothesis_source_map() -> dict[str, str]:
    summary_path = PROJECT_ROOT / "results" / "tables" / "meeteval_compatibility_summary.json"
    if not summary_path.exists():
        return {}
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    return {
        str(row.get("case_id", "")): str(row.get("hypothesis_source", ""))
        for row in payload
        if str(row.get("case_id", ""))
    }


def resolve_case_ids(case_arg: str) -> list[str]:
    if case_arg == "all":
        return list_verified_cases()
    if case_arg == "preferred":
        checklist_path = PROJECT_ROOT / "results" / "tables" / "meeteval_dry_run_checklist.csv"
        return [select_preferred_case(checklist_path)]
    return [case_arg]


def build_cpwer_bridge_handoff_rows(
    bridge_rows: list[dict[str, Any]],
    summary_row: dict[str, Any],
) -> list[dict[str, str]]:
    if not bridge_rows:
        return []

    scope = str(summary_row.get("scope", "single_verified_case"))
    case_id = "ALL" if scope == "all_gold_cases" else str(bridge_rows[0].get("case_id", ""))
    cpwer_value = (
        str(summary_row.get("average_cpwer_bridge_lite", ""))
        if scope == "all_gold_cases"
        else str(bridge_rows[0].get("cpwer_bridge_lite", ""))
    )
    mapping_note = (
        f"direct={summary_row.get('direct_mapping_count', 0)}, swapped={summary_row.get('swapped_mapping_count', 0)}"
        if scope == "all_gold_cases"
        else str(bridge_rows[0].get("best_mapping", ""))
    )
    handoff_note = (
        "MeetEval cpWER bridge-lite has been computed across all gold cases; it is not a finished benchmark claim."
        if scope == "all_gold_cases"
        else "MeetEval cpWER bridge-lite has been computed for one case; it is not a finished benchmark claim."
    )
    return [
        {
            "bridge_status": "cpwer_bridge_complete",
            "case_id": case_id,
            "cpwer_bridge_lite": cpwer_value,
            "best_mapping": mapping_note,
            "bridge_goal": "Use the bridge-lite result as a narrow compatibility signal before any broader MeetEval integration.",
            "primary_limitation": "This uses speaker-aggregated macro CER rather than a full MeetEval cpWER implementation.",
            "expected_evidence": "results/tables/meeteval_cpwer_bridge_receipt.json",
            "handoff_note": handoff_note,
        }
    ]


def build_cpwer_bridge_handoff_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Bridge Handoff",
        "",
        "This generated handoff packet turns the cpWER bridge-lite result into the next narrow frontier step.",
        "",
        "| bridge_status | case_id | cpwer_bridge_lite | best_mapping | bridge_goal | primary_limitation | expected_evidence | handoff_note |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['bridge_status']} | {row['case_id']} | {row['cpwer_bridge_lite']} | {row['best_mapping']} | "
            f"{row['bridge_goal']} | {row['primary_limitation']} | {row['expected_evidence']} | {row['handoff_note']} |"
        )
    return lines


def build_cpwer_bridge_receipt_rows(handoff_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not handoff_rows:
        return []

    handoff = handoff_rows[0]
    return [
        {
            "execution_status": "bridge_complete",
            "run_scope": "single_verified_case",
            "case_id": str(handoff.get("case_id", "")),
            "cpwer_bridge_lite": str(handoff.get("cpwer_bridge_lite", "")),
            "best_mapping": str(handoff.get("best_mapping", "")),
            "expected_inputs": "results/tables/meeteval_reference_segments.jsonl; results/tables/meeteval_hypothesis_segments.jsonl",
            "writeback_note": "cpWER bridge-lite complete for one case; full MeetEval evaluation remains pending.",
        }
    ]


def build_cpwer_bridge_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Bridge Receipt",
        "",
        "This receipt records the first cpWER bridge-lite writeback. It does not claim a finished MeetEval benchmark evaluation.",
        "",
        "| execution_status | run_scope | case_id | cpwer_bridge_lite | best_mapping | expected_inputs | writeback_note |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['run_scope']} | {row['case_id']} | {row['cpwer_bridge_lite']} | "
            f"{row['best_mapping']} | {row['expected_inputs']} | {row['writeback_note']} |"
        )
    return lines


def run_cpwer_bridge(case_id: str, hypothesis_source_map: dict[str, str] | None = None) -> dict[str, Any]:
    reference_path = PROJECT_ROOT / "results" / "tables" / "meeteval_reference_segments.jsonl"
    hypothesis_path = PROJECT_ROOT / "results" / "tables" / "meeteval_hypothesis_segments.jsonl"
    reference_segments = load_jsonl_segments(reference_path, case_id)
    hypothesis_segments = load_jsonl_segments(hypothesis_path, case_id)

    source_map = hypothesis_source_map or {}
    hypothesis_source = str(source_map.get(case_id, ""))
    if not hypothesis_source:
        diagnostic_path = PROJECT_ROOT / "results" / "tables" / "meeteval_dry_run_diagnostic.json"
        if diagnostic_path.exists():
            diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
            if str(diagnostic.get("case_id", "")) == case_id:
                hypothesis_source = str(diagnostic.get("hypothesis_source", ""))

    return build_cpwer_bridge_row(case_id, reference_segments, hypothesis_segments, hypothesis_source)


def run_cpwer_bridges(case_ids: list[str]) -> list[dict[str, Any]]:
    source_map = load_hypothesis_source_map()
    return [run_cpwer_bridge(case_id, source_map) for case_id in case_ids]


def write_outputs(
    bridge_rows: list[dict[str, Any]],
    summary_row: dict[str, Any],
    handoff_rows: list[dict[str, str]],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    bridge_csv_path = tables_dir / "meeteval_cpwer_bridge.csv"
    bridge_json_path = tables_dir / "meeteval_cpwer_bridge.json"
    bridge_md_path = figures_dir / "meeteval_cpwer_bridge.md"
    summary_csv_path = tables_dir / "meeteval_cpwer_bridge_summary.csv"
    summary_json_path = tables_dir / "meeteval_cpwer_bridge_summary.json"
    summary_md_path = figures_dir / "meeteval_cpwer_bridge_summary.md"
    handoff_csv_path = tables_dir / "meeteval_cpwer_bridge_handoff.csv"
    handoff_json_path = tables_dir / "meeteval_cpwer_bridge_handoff.json"
    handoff_md_path = figures_dir / "meeteval_cpwer_bridge_handoff.md"
    receipt_json_path = tables_dir / "meeteval_cpwer_bridge_receipt.json"
    receipt_md_path = figures_dir / "meeteval_cpwer_bridge_receipt.md"

    with bridge_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_COLUMNS)
        writer.writeheader()
        writer.writerows(bridge_rows)
    bridge_json_path.write_text(json.dumps(bridge_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    bridge_md_path.write_text("\n".join(build_cpwer_bridge_lines(bridge_rows)) + "\n", encoding="utf-8")
    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(summary_row)
    summary_json_path.write_text(json.dumps(summary_row, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_md_path.write_text("\n".join(build_cpwer_bridge_summary_lines(summary_row)) + "\n", encoding="utf-8")
    with handoff_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerows(handoff_rows)
    handoff_json_path.write_text(json.dumps(handoff_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    handoff_md_path.write_text("\n".join(build_cpwer_bridge_handoff_lines(handoff_rows)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_cpwer_bridge_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return (
        bridge_csv_path,
        bridge_json_path,
        bridge_md_path,
        summary_csv_path,
        summary_json_path,
        summary_md_path,
        handoff_csv_path,
        handoff_json_path,
        handoff_md_path,
        receipt_json_path,
        receipt_md_path,
    )


def main() -> None:
    args = parse_args()
    case_ids = resolve_case_ids(args.case)
    scope = "all_gold_cases" if args.case == "all" else "single_verified_case"
    bridge_rows = run_cpwer_bridges(case_ids)
    summary_row = build_cpwer_bridge_summary_row(bridge_rows, scope)
    handoff_rows = build_cpwer_bridge_handoff_rows(bridge_rows, summary_row)
    receipt_rows = build_cpwer_bridge_receipt_rows(handoff_rows)
    (
        bridge_csv_path,
        bridge_json_path,
        bridge_md_path,
        summary_csv_path,
        summary_json_path,
        summary_md_path,
        handoff_csv_path,
        handoff_json_path,
        handoff_md_path,
        receipt_json_path,
        receipt_md_path,
    ) = write_outputs(bridge_rows, summary_row, handoff_rows, receipt_rows)
    print(f"Wrote MeetEval cpWER bridge CSV: {bridge_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER bridge JSON: {bridge_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER bridge note: {bridge_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER bridge summary CSV: {summary_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER bridge summary JSON: {summary_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER bridge summary note: {summary_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER bridge handoff CSV: {handoff_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER bridge handoff JSON: {handoff_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER bridge handoff note: {handoff_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER bridge receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER bridge receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")
    print(
        f"cpWER bridge-lite summary: scope={summary_row['scope']}, "
        f"average={summary_row['average_cpwer_bridge_lite']}, cases={summary_row['case_count']}"
    )


if __name__ == "__main__":
    main()
