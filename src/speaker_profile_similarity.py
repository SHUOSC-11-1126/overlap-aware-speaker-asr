from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .evaluate_cer import list_verified_cases, load_json, load_reference


CSV_COLUMNS = [
    "case_id",
    "best_profile_alignment",
    "direct_profile_score",
    "swapped_profile_score",
    "profile_confidence_gap",
    "hypothesis_source",
    "observation",
]

TRIAGE_COLUMNS = [
    "dominant_pattern",
    "case_count",
    "swapped_count",
    "direct_count",
    "average_confidence_gap",
    "cleaned_source_count",
    "next_action",
]

METHOD_HANDOFF_COLUMNS = [
    "dominant_pattern",
    "first_method_direction",
    "method_goal",
    "expected_evidence",
    "handoff_note",
]

METHOD_RECEIPT_COLUMNS = [
    "execution_status",
    "method_scope",
    "expected_inputs",
    "expected_outputs",
    "writeback_note",
]

CHECKLIST_COLUMNS = [
    "checklist_order",
    "dominant_pattern",
    "checklist_goal",
    "expected_evidence",
    "preflight_step",
    "next_gate",
]


def text_overlap_ratio(left: str, right: str) -> float:
    left_counter = Counter(str(left).strip())
    right_counter = Counter(str(right).strip())
    shared = sum(min(left_counter[ch], right_counter[ch]) for ch in left_counter)
    total = sum(left_counter.values())
    if total == 0:
        return 0.0
    return round(shared / total, 6)


def build_profile_text(rows: list[dict[str, Any]]) -> str:
    texts: list[str] = []
    for row in rows:
        text = str(row.get("text", "")).strip()
        if text:
            texts.append(text)
    return "".join(texts)


def build_similarity_rows(
    case_ids: list[str],
    profile_texts: dict[str, str],
    references: dict[str, dict[str, Any]],
    hypothesis_texts: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    con_profile = str(profile_texts.get("con", ""))
    pro_profile = str(profile_texts.get("pro", ""))
    for case_id in case_ids:
        reference = references.get(case_id, {})
        hypothesis = hypothesis_texts.get(case_id, {})
        speaker_1_text = str(hypothesis.get("speaker_1_text", reference.get("speaker_1_text", "")))
        speaker_2_text = str(hypothesis.get("speaker_2_text", reference.get("speaker_2_text", "")))
        direct_profile_score = round(
            (
                text_overlap_ratio(con_profile, speaker_1_text)
                + text_overlap_ratio(pro_profile, speaker_2_text)
            )
            / 2,
            6,
        )
        swapped_profile_score = round(
            (
                text_overlap_ratio(con_profile, speaker_2_text)
                + text_overlap_ratio(pro_profile, speaker_1_text)
            )
            / 2,
            6,
        )
        best_alignment = "direct" if direct_profile_score >= swapped_profile_score else "swapped"
        rows.append(
            {
                "case_id": case_id,
                "best_profile_alignment": best_alignment,
                "direct_profile_score": direct_profile_score,
                "swapped_profile_score": swapped_profile_score,
                "profile_confidence_gap": round(abs(direct_profile_score - swapped_profile_score), 6),
                "hypothesis_source": str(hypothesis.get("hypothesis_source", "reference_only")),
                "observation": "This is a lightweight risk signal, not speaker identification.",
            }
        )
    return rows


def build_speaker_profile_summary_lines(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "# Speaker Profile Risk Summary",
        "",
        "This generated note uses text-profile overlap only as a lightweight risk signal; it is not a voiceprint or speaker-ID claim.",
        "",
        "| case_id | best_profile_alignment | direct_profile_score | swapped_profile_score | profile_confidence_gap | hypothesis_source | observation |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['best_profile_alignment']} | {row['direct_profile_score']} | {row['swapped_profile_score']} | "
            f"{row['profile_confidence_gap']} | {row['hypothesis_source']} | {row['observation']} |"
        )
    return lines


def build_speaker_profile_triage_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    swapped_count = sum(1 for row in rows if str(row.get("best_profile_alignment", "")) == "swapped")
    direct_count = sum(1 for row in rows if str(row.get("best_profile_alignment", "")) == "direct")
    cleaned_source_count = sum(
        1 for row in rows if str(row.get("hypothesis_source", "")) == "separated_whisper_cleaned"
    )
    confidence_gaps = [float(row.get("profile_confidence_gap", 0.0) or 0.0) for row in rows]
    average_confidence_gap = round(sum(confidence_gaps) / len(confidence_gaps), 6) if confidence_gaps else 0.0
    dominant_pattern = "swapped_bias" if swapped_count > direct_count else "direct_bias_or_tie"
    next_action = (
        "Test a stronger profile method before claiming attribution value."
        if dominant_pattern == "swapped_bias"
        else "Check whether the simple profile signal adds stable value beyond the current per-case table."
    )
    return [
        {
            "dominant_pattern": dominant_pattern,
            "case_count": str(len(rows)),
            "swapped_count": str(swapped_count),
            "direct_count": str(direct_count),
            "average_confidence_gap": f"{average_confidence_gap:.6f}",
            "cleaned_source_count": str(cleaned_source_count),
            "next_action": next_action,
        }
    ]


def build_speaker_profile_triage_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Triage",
        "",
        "This generated card summarizes the current aggregate pattern in the lightweight profile signal. It does not claim voiceprint or speaker-ID success.",
        "",
        "| dominant_pattern | case_count | swapped_count | direct_count | average_confidence_gap | cleaned_source_count | next_action |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['dominant_pattern']} | {row['case_count']} | {row['swapped_count']} | {row['direct_count']} | {row['average_confidence_gap']} | {row['cleaned_source_count']} | {row['next_action']} |"
        )
    return lines


def build_speaker_profile_method_handoff_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return []

    triage = rows[0]
    dominant_pattern = str(triage.get("dominant_pattern", ""))
    first_method_direction = (
        "embedding_or_voiceprint_baseline"
        if dominant_pattern == "swapped_bias"
        else "stability_check_against_current_signal"
    )
    return [
        {
            "dominant_pattern": dominant_pattern,
            "first_method_direction": first_method_direction,
            "method_goal": "Test a stronger profile method before any attribution claim.",
            "expected_evidence": "results/tables/speaker_profile_method_receipt.json",
            "handoff_note": "Current signal is diagnostic only, not speaker-ID success.",
        }
    ]


def build_speaker_profile_method_handoff_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Method Handoff",
        "",
        "This generated packet translates the current profile triage result into a first stronger-method direction. It does not claim voiceprint or speaker-ID success.",
        "",
        "| dominant_pattern | first_method_direction | method_goal | expected_evidence | handoff_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['dominant_pattern']} | {row['first_method_direction']} | {row['method_goal']} | {row['expected_evidence']} | {row['handoff_note']} |"
        )
    return lines


def build_speaker_profile_method_receipt_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return []

    handoff = rows[0]
    method_scope = str(handoff.get("first_method_direction", ""))
    return [
        {
            "execution_status": "template_only",
            "method_scope": method_scope,
            "expected_inputs": "Speaker profile triage plus one stronger-method baseline stub.",
            "expected_outputs": "Diagnostic stronger-method comparison note and a narrow evidence writeback.",
            "writeback_note": "No stronger speaker-profile method has been executed yet; fill this receipt only after the first trial.",
        }
    ]


def build_speaker_profile_checklist_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not rows:
        return []

    handoff = rows[0]
    dominant_pattern = str(handoff.get("dominant_pattern", ""))
    first_method_direction = str(handoff.get("first_method_direction", ""))
    checklist_goal = str(handoff.get("method_goal", "Test a stronger profile method before any attribution claim."))
    preflight_step = (
        "Confirm swapped-bias diagnostics before staging the stronger-profile baseline stub."
        if dominant_pattern == "swapped_bias"
        else "Confirm the current profile signal before comparing against a stronger baseline stub."
    )
    next_gate = (
        "Verify one stronger profile method before any speaker-attribution claim."
        if first_method_direction == "embedding_or_voiceprint_baseline"
        else "Keep the profile signal diagnostic and compare it against the current baseline stub."
    )
    return [
        {
            "checklist_order": "1",
            "dominant_pattern": dominant_pattern,
            "checklist_goal": checklist_goal,
            "expected_evidence": "results/tables/speaker_profile_method_receipt.json",
            "preflight_step": preflight_step,
            "next_gate": next_gate,
        }
    ]


def build_speaker_profile_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Checklist",
        "",
        "This generated checklist orders the speaker-profile frontier before any stronger attribution method is claimed to work. It does not claim voiceprint success.",
        "",
        "| checklist_order | dominant_pattern | checklist_goal | expected_evidence | preflight_step | next_gate |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['dominant_pattern']} | {row['checklist_goal']} | {row['expected_evidence']} | {row['preflight_step']} | {row['next_gate']} |"
        )
    return lines


def build_speaker_profile_method_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Method Receipt",
        "",
        "This generated receipt is a template-only writeback target for the first stronger speaker-profile method trial. It does not claim speaker-ID success.",
        "",
        "| execution_status | method_scope | expected_inputs | expected_outputs | writeback_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['method_scope']} | {row['expected_inputs']} | {row['expected_outputs']} | {row['writeback_note']} |"
        )
    return lines


def load_snippet_rows(prefix: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((PROJECT_ROOT / "results" / "snippet_transcripts").glob(f"{prefix}_*_whisper.json")):
        payload = load_json(path)
        rows.append({"text": str(payload.get("text", ""))})
    return rows


def load_hypothesis_text(case_id: str) -> dict[str, Any]:
    raw_path = PROJECT_ROOT / "results" / "transcripts_speaker" / f"{case_id}_separated_speaker_transcript.json"
    if raw_path.exists():
        payload = load_json(raw_path)
        segments = list(payload.get("segments", []))
        return {
            "speaker_1_text": "".join(str(seg.get("text", "")).strip() for seg in segments if str(seg.get("speaker", "")).upper() == "SPEAKER_1"),
            "speaker_2_text": "".join(str(seg.get("text", "")).strip() for seg in segments if str(seg.get("speaker", "")).upper() == "SPEAKER_2"),
            "hypothesis_source": "separated_whisper",
        }
    cleaned_path = PROJECT_ROOT / "results" / "transcripts_postprocessed" / f"{case_id}_separated_speaker_transcript_cleaned.json"
    if cleaned_path.exists():
        payload = load_json(cleaned_path)
        segments = list(payload.get("cleaned_segments", []))
        return {
            "speaker_1_text": "".join(str(seg.get("text", "")).strip() for seg in segments if str(seg.get("speaker", "")).upper() == "SPEAKER_1"),
            "speaker_2_text": "".join(str(seg.get("text", "")).strip() for seg in segments if str(seg.get("speaker", "")).upper() == "SPEAKER_2"),
            "hypothesis_source": "separated_whisper_cleaned",
        }
    return {
        "speaker_1_text": "",
        "speaker_2_text": "",
        "hypothesis_source": "missing_hypothesis",
    }


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    csv_path = tables_dir / "speaker_profile_similarity.csv"
    json_path = tables_dir / "speaker_profile_similarity.json"
    md_path = figures_dir / "speaker_profile_risk_summary.md"
    triage_rows = build_speaker_profile_triage_rows(rows)
    triage_csv_path = tables_dir / "speaker_profile_triage.csv"
    triage_json_path = tables_dir / "speaker_profile_triage.json"
    triage_md_path = figures_dir / "speaker_profile_triage.md"
    method_handoff_rows = build_speaker_profile_method_handoff_rows(triage_rows)
    method_handoff_csv_path = tables_dir / "speaker_profile_method_handoff.csv"
    method_handoff_json_path = tables_dir / "speaker_profile_method_handoff.json"
    method_handoff_md_path = figures_dir / "speaker_profile_method_handoff.md"
    method_receipt_rows = build_speaker_profile_method_receipt_rows(method_handoff_rows)
    method_receipt_json_path = tables_dir / "speaker_profile_method_receipt.json"
    method_receipt_md_path = figures_dir / "speaker_profile_method_receipt.md"
    checklist_rows = build_speaker_profile_checklist_rows(method_handoff_rows)
    checklist_csv_path = tables_dir / "speaker_profile_checklist.csv"
    checklist_json_path = tables_dir / "speaker_profile_checklist.json"
    checklist_md_path = figures_dir / "speaker_profile_checklist.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_speaker_profile_summary_lines(rows)) + "\n", encoding="utf-8")
    with triage_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=TRIAGE_COLUMNS)
        writer.writeheader()
        writer.writerows(triage_rows)
    triage_json_path.write_text(json.dumps(triage_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    triage_md_path.write_text("\n".join(build_speaker_profile_triage_lines(triage_rows)) + "\n", encoding="utf-8")
    with method_handoff_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=METHOD_HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerows(method_handoff_rows)
    method_handoff_json_path.write_text(json.dumps(method_handoff_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    method_handoff_md_path.write_text(
        "\n".join(build_speaker_profile_method_handoff_lines(method_handoff_rows)) + "\n",
        encoding="utf-8",
    )
    method_receipt_json_path.write_text(json.dumps(method_receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    method_receipt_md_path.write_text(
        "\n".join(build_speaker_profile_method_receipt_lines(method_receipt_rows)) + "\n",
        encoding="utf-8",
    )
    with checklist_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(checklist_rows)
    checklist_json_path.write_text(json.dumps(checklist_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    checklist_md_path.write_text(
        "\n".join(build_speaker_profile_checklist_lines(checklist_rows)) + "\n",
        encoding="utf-8",
    )
    return (
        csv_path,
        json_path,
        md_path,
        triage_csv_path,
        triage_json_path,
        triage_md_path,
        method_handoff_csv_path,
        method_handoff_json_path,
        method_handoff_md_path,
        method_receipt_json_path,
        method_receipt_md_path,
        checklist_csv_path,
        checklist_json_path,
        checklist_md_path,
    )


def main() -> None:
    case_ids = list_verified_cases()
    profile_texts = {
        "con": build_profile_text(load_snippet_rows("con")),
        "pro": build_profile_text(load_snippet_rows("pro")),
    }
    references = {case_id: load_reference(case_id) for case_id in case_ids}
    hypothesis_texts = {case_id: load_hypothesis_text(case_id) for case_id in case_ids}
    rows = build_similarity_rows(case_ids, profile_texts, references, hypothesis_texts)
    (
        csv_path,
        json_path,
        md_path,
        triage_csv_path,
        triage_json_path,
        triage_md_path,
        method_handoff_csv_path,
        method_handoff_json_path,
        method_handoff_md_path,
        method_receipt_json_path,
        method_receipt_md_path,
        checklist_csv_path,
        checklist_json_path,
        checklist_md_path,
    ) = write_outputs(rows)
    print(f"Wrote speaker profile similarity: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile summary: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile triage CSV: {triage_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile triage JSON: {triage_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile triage note: {triage_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile method handoff CSV: {method_handoff_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile method handoff JSON: {method_handoff_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile method handoff note: {method_handoff_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile method receipt JSON: {method_receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile method receipt note: {method_receipt_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile checklist CSV: {checklist_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile checklist JSON: {checklist_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile checklist note: {checklist_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
