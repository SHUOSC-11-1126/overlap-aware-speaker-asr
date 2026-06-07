from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT
from .meeteval_cpwer_bridge import aggregate_speaker_text
from .meeteval_cpwer_execution_preflight_batch import GOLD_CASES
from .meeteval_dry_run import load_jsonl_segments
from .meeteval_tokenization import count_meeteval_tokens


DIAGNOSTIC_COLUMNS = [
    "case_id",
    "speaker_count",
    "raw_token_count_per_speaker",
    "character_token_count_per_speaker",
    "root_cause",
    "diagnostic_status",
    "diagnostic_note",
]


def load_official_execution_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_official_execution.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_diagnostic_row(case_id: str, official_row: dict[str, str] | None) -> dict[str, str]:
    reference_path = PROJECT_ROOT / "results" / "tables" / "meeteval_reference_segments.jsonl"
    reference_segments = load_jsonl_segments(reference_path, case_id)
    speakers = sorted(
        {
            str(segment.get("speaker", "")).strip()
            for segment in reference_segments
            if str(segment.get("speaker", "")).strip()
        }
    )
    raw_counts: list[int] = []
    char_counts: list[int] = []
    for speaker in speakers:
        text = aggregate_speaker_text(reference_segments, speaker)
        raw_counts.append(1 if text.strip() else 0)
        char_counts.append(count_meeteval_tokens(text))

    official_cpwer = str((official_row or {}).get("official_cpwer", ""))
    speaker_count = len(speakers)
    avg_raw = round(sum(raw_counts) / len(raw_counts), 2) if raw_counts else 0.0
    avg_char = round(sum(char_counts) / len(char_counts), 2) if char_counts else 0.0

    if official_cpwer and float(official_cpwer) > 1.0 and avg_raw <= 1.0:
        root_cause = "no_whitespace_word_tokenization"
        diagnostic_status = "root_cause_identified"
        diagnostic_note = (
            "MeetEval word-level cpWER treats each speaker aggregate as one token without whitespace; "
            "character-spaced tokenization is required for CJK alignment with bridge-lite."
        )
    elif not official_cpwer:
        diagnostic_status = "pending_official_execution"
        root_cause = "unknown"
        diagnostic_note = "Official cpWER not yet available for tokenization diagnostic."
    else:
        root_cause = "no_obvious_tokenization_mismatch"
        diagnostic_status = "diagnostic_complete"
        diagnostic_note = "No obvious whitespace tokenization mismatch detected."

    return {
        "case_id": case_id,
        "speaker_count": str(speaker_count),
        "raw_token_count_per_speaker": str(avg_raw),
        "character_token_count_per_speaker": str(avg_char),
        "root_cause": root_cause,
        "diagnostic_status": diagnostic_status,
        "diagnostic_note": diagnostic_note,
    }


def build_diagnostic_rows() -> list[dict[str, str]]:
    official_by_case = {str(row.get("case_id", "")): row for row in load_official_execution_rows()}
    return [build_diagnostic_row(case_id, official_by_case.get(case_id)) for case_id in GOLD_CASES]


def build_diagnostic_lines(rows: list[dict[str, str]]) -> list[str]:
    identified_count = sum(1 for row in rows if row.get("diagnostic_status") == "root_cause_identified")
    lines = [
        "# MeetEval cpWER Official Execution Tokenization Diagnostic",
        "",
        "This generated diagnostic identifies why official MeetEval cpWER may drift from bridge-lite on Chinese gold cases. "
        "It remains experimental/frontier and does not claim benchmark completion.",
        "",
        f"Summary: `{identified_count}/{len(rows)}` cases report `no_whitespace_word_tokenization` root cause.",
        "",
        "| case_id | speaker_count | raw_token_count_per_speaker | character_token_count_per_speaker | root_cause | diagnostic_status | diagnostic_note |",
        "| --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['speaker_count']} | {row['raw_token_count_per_speaker']} | "
            f"{row['character_token_count_per_speaker']} | {row['root_cause']} | {row['diagnostic_status']} | "
            f"{row['diagnostic_note']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_official_execution_tokenization_diagnostic.csv"
    json_path = tables_dir / "meeteval_cpwer_official_execution_tokenization_diagnostic.json"
    md_path = figures_dir / "meeteval_cpwer_official_execution_tokenization_diagnostic.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DIAGNOSTIC_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_diagnostic_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_diagnostic_rows()
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote MeetEval cpWER official execution tokenization diagnostic CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER official execution tokenization diagnostic JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER official execution tokenization diagnostic note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
