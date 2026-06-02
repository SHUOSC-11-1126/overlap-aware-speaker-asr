from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .evaluate_cer import compute_cer, load_json, load_reference, normalize_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze CER errors for a single case and method.")
    parser.add_argument("--case", required=True, help="Audio case id, e.g. LightOverlap")
    parser.add_argument(
        "--method",
        required=True,
        choices=["mixed_whisper", "separated_whisper"],
        help="Transcript method to analyze",
    )
    return parser.parse_args()


def hypothesis_path_for(case_id: str, method: str) -> Path:
    if method == "mixed_whisper":
        return PROJECT_ROOT / "results" / "transcripts_raw" / f"{case_id}_mixed_whisper.json"
    return PROJECT_ROOT / "results" / "transcripts_speaker" / f"{case_id}_separated_speaker_transcript.json"


def extract_hypothesis_text(payload: dict[str, Any], method: str) -> str:
    return payload.get("text", "") if method == "mixed_whisper" else payload.get("full_text", "")


def find_repeated_phrases(text: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    normalized = normalize_text(text)

    # Rule 1: repeated short lines/clauses after splitting on speaker labels and newlines.
    lines = [line.strip() for line in re.split(r"(?:\n|\[SPEAKER_\d+\])+", text) if line.strip()]
    line_counts = Counter(lines)
    for phrase, count in line_counts.items():
        if count >= 2 and len(phrase) <= 40:
            candidates.append(
                {"type": "repeated_clause", "phrase": phrase, "count": count}
            )

    # Rule 2: repeated 4-12 character chunks in the normalized text.
    for size in range(4, 13):
        counts = Counter(
            normalized[i : i + size]
            for i in range(0, max(0, len(normalized) - size + 1))
        )
        for phrase, count in counts.items():
            if count >= 3:
                candidates.append(
                    {"type": "high_frequency_chunk", "phrase": phrase, "count": count}
                )

    deduped: list[dict[str, Any]] = []
    seen = set()
    for item in candidates:
        key = (item["type"], item["phrase"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def build_report(case_id: str, method: str) -> dict[str, Any]:
    reference = load_reference(case_id)
    hypothesis_path = hypothesis_path_for(case_id, method)
    hypothesis = load_json(hypothesis_path)
    hypothesis_text = extract_hypothesis_text(hypothesis, method)

    metrics = compute_cer(reference.get("full_text", ""), hypothesis_text)
    repeated = find_repeated_phrases(hypothesis_text)

    return {
        "case_id": case_id,
        "method": method,
        "hypothesis_path": hypothesis_path.relative_to(PROJECT_ROOT).as_posix(),
        "reference_length": metrics["reference_length"],
        "hypothesis_length": metrics["hypothesis_length"],
        "edit_distance": metrics["edit_distance"],
        "cer": metrics["cer"],
        "normalized_reference": metrics["normalized_reference"],
        "normalized_hypothesis": metrics["normalized_hypothesis"],
        "reference_preview": reference.get("full_text", "")[:500],
        "hypothesis_preview_start": hypothesis_text[:500],
        "hypothesis_preview_end": hypothesis_text[-500:] if len(hypothesis_text) > 500 else hypothesis_text,
        "suspected_repeated_phrases": repeated,
    }


def write_outputs(report: dict[str, Any]) -> tuple[Path, Path]:
    output_dir = PROJECT_ROOT / "results" / "error_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{report['case_id']}_{report['method']}_error_analysis"
    md_path = output_dir / f"{stem}.md"
    json_path = output_dir / f"{stem}.json"

    md_lines = [
        f"# CER Error Analysis: {report['case_id']} / {report['method']}",
        "",
        f"- reference_length: {report['reference_length']}",
        f"- hypothesis_length: {report['hypothesis_length']}",
        f"- edit_distance: {report['edit_distance']}",
        f"- cer: {report['cer']}",
        "",
        "## Suspected Repeated Phrases",
        json.dumps(report["suspected_repeated_phrases"], ensure_ascii=False, indent=2),
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8-sig")
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path, json_path


def main() -> None:
    args = parse_args()
    _ = load_config()
    if args.case != "LightOverlap":
        raise ValueError("This stage only supports case LightOverlap.")

    report = build_report(args.case, args.method)
    md_path, json_path = write_outputs(report)
    print(f"Wrote analysis: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote analysis: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Repeated phrases: {len(report['suspected_repeated_phrases'])}")


if __name__ == "__main__":
    main()
