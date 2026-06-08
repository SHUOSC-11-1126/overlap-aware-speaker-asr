from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


DIAGNOSTIC_COLUMNS = [
    "case_id",
    "hypothesis_source",
    "text_best_alignment",
    "audio_best_alignment",
    "text_confidence_gap",
    "audio_confidence_gap",
    "alignment_agreement",
    "audio_support_level",
    "combined_signal_status",
    "recommended_next_step",
    "result_label",
    "observation",
]

SUMMARY_COLUMNS = [
    "case_count",
    "agreement_count",
    "weak_support_count",
    "frontier_decision",
    "summary_note",
]


def load_rows(path_rel: str) -> list[dict[str, str]]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{key: str(value) for key, value in row.items()} for row in csv.DictReader(f)]


def classify_audio_support_level(audio_gap: float) -> str:
    return "weak_support" if audio_gap < 0.01 else "separable_support"


def build_multisignal_row(
    profile_row: dict[str, str],
    audio_row: dict[str, str],
) -> dict[str, str]:
    case_id = str(profile_row.get("case_id", audio_row.get("case_id", "")))
    hypothesis_source = str(profile_row.get("hypothesis_source", audio_row.get("hypothesis_source", "")))
    text_alignment = str(profile_row.get("best_profile_alignment", "missing"))
    audio_alignment = str(audio_row.get("best_audio_alignment", "missing"))
    text_gap = float(profile_row.get("profile_confidence_gap", "0.0") or 0.0)
    audio_gap = float(audio_row.get("audio_confidence_gap", "0.0") or 0.0)
    alignment_agreement = "agree" if text_alignment == audio_alignment and text_alignment != "missing" else "disagree"
    audio_support_level = classify_audio_support_level(audio_gap)

    if text_alignment == "swapped" and alignment_agreement == "agree" and audio_support_level == "weak_support":
        combined_signal_status = "text_swapped_audio_weak"
        recommended_next_step = (
            "Advance only to a narrow embedding baseline; attribution claims remain blocked."
        )
    elif alignment_agreement == "agree":
        combined_signal_status = "signals_aligned"
        recommended_next_step = "Signals align; a stronger embedding baseline is reasonable before any attribution claim."
    else:
        combined_signal_status = "signals_mixed"
        recommended_next_step = "Signals disagree; keep this as diagnostics only until a stronger baseline is run."

    return {
        "case_id": case_id,
        "hypothesis_source": hypothesis_source or "separated_whisper",
        "text_best_alignment": text_alignment,
        "audio_best_alignment": audio_alignment,
        "text_confidence_gap": f"{text_gap:.6f}",
        "audio_confidence_gap": f"{audio_gap:.6f}",
        "alignment_agreement": alignment_agreement,
        "audio_support_level": audio_support_level,
        "combined_signal_status": combined_signal_status,
        "recommended_next_step": recommended_next_step,
        "result_label": "experimental/frontier",
        "observation": "Multi-signal speaker-risk diagnostic only; this is not speaker identification.",
    }


def build_multisignal_summary_row(rows: list[dict[str, str]]) -> dict[str, str]:
    agreement_count = sum(1 for row in rows if str(row.get("alignment_agreement", "")) == "agree")
    weak_support_count = sum(1 for row in rows if str(row.get("audio_support_level", "")) == "weak_support")
    frontier_decision = (
        "advance_to_narrow_embedding_baseline"
        if rows and weak_support_count == len(rows)
        else "keep_diagnostic_only"
    )
    return {
        "case_count": str(len(rows)),
        "agreement_count": str(agreement_count),
        "weak_support_count": str(weak_support_count),
        "frontier_decision": frontier_decision,
        "summary_note": (
            "Text proxy keeps the swapped-bias direction, but the audio proxy remains weak; proceed only with narrow frontier execution."
            if frontier_decision == "advance_to_narrow_embedding_baseline"
            else "Multi-signal evidence is not yet strong enough to justify a stronger-method handoff."
        ),
    }


def build_diagnostic_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Multi-signal Diagnostic",
        "",
        "This generated note compares text-profile and audio-profile proxy signals. It remains experimental/frontier and does not claim speaker identification.",
        "",
        "| case_id | hypothesis_source | text_best_alignment | audio_best_alignment | text_confidence_gap | audio_confidence_gap | alignment_agreement | audio_support_level | combined_signal_status | recommended_next_step | result_label | observation |",
        "| --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['hypothesis_source']} | {row['text_best_alignment']} | "
            f"{row['audio_best_alignment']} | {row['text_confidence_gap']} | {row['audio_confidence_gap']} | "
            f"{row['alignment_agreement']} | {row['audio_support_level']} | {row['combined_signal_status']} | "
            f"{row['recommended_next_step']} | {row['result_label']} | {row['observation']} |"
        )
    return lines


def build_summary_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Multi-signal Summary",
        "",
        "This generated card summarizes whether text and audio proxy signals jointly justify a narrow stronger-method baseline.",
        "",
        "| case_count | agreement_count | weak_support_count | frontier_decision | summary_note |",
        "| ---: | ---: | ---: | --- | --- |",
        (
            f"| {row['case_count']} | {row['agreement_count']} | {row['weak_support_count']} | "
            f"{row['frontier_decision']} | {row['summary_note']} |"
        ),
    ]


def write_outputs(rows: list[dict[str, str]], summary_row: dict[str, str]) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_multisignal_diagnostic.csv"
    json_path = tables_dir / "speaker_profile_multisignal_diagnostic.json"
    md_path = figures_dir / "speaker_profile_multisignal_diagnostic.md"
    summary_csv_path = tables_dir / "speaker_profile_multisignal_summary.csv"
    summary_json_path = tables_dir / "speaker_profile_multisignal_summary.json"
    summary_md_path = figures_dir / "speaker_profile_multisignal_summary.md"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DIAGNOSTIC_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text("\n".join(build_diagnostic_lines(rows)) + "\n", encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(summary_row)
    summary_json_path.write_text(json.dumps(summary_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_md_path.write_text("\n".join(build_summary_lines(summary_row)) + "\n", encoding="utf-8")

    return csv_path, json_path, md_path, summary_csv_path, summary_json_path, summary_md_path


def main() -> None:
    profile_rows = load_rows("results/tables/speaker_profile_similarity.csv")
    audio_rows = load_rows("results/tables/speaker_profile_audio_proxy_trial.csv")
    audio_by_case = {str(row.get("case_id", "")): row for row in audio_rows}
    rows = [build_multisignal_row(profile_row, audio_by_case.get(str(profile_row.get("case_id", "")), {})) for profile_row in profile_rows]
    summary_row = build_multisignal_summary_row(rows)
    write_outputs(rows, summary_row)


if __name__ == "__main__":
    main()
