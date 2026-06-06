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


def write_outputs(rows: list[dict[str, Any]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    csv_path = tables_dir / "speaker_profile_similarity.csv"
    json_path = tables_dir / "speaker_profile_similarity.json"
    md_path = figures_dir / "speaker_profile_risk_summary.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_speaker_profile_summary_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    case_ids = list_verified_cases()
    profile_texts = {
        "con": build_profile_text(load_snippet_rows("con")),
        "pro": build_profile_text(load_snippet_rows("pro")),
    }
    references = {case_id: load_reference(case_id) for case_id in case_ids}
    hypothesis_texts = {case_id: load_hypothesis_text(case_id) for case_id in case_ids}
    rows = build_similarity_rows(case_ids, profile_texts, references, hypothesis_texts)
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote speaker profile similarity: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile summary: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
