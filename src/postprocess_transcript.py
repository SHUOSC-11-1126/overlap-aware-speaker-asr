from __future__ import annotations

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config


WINDOW_SIZE = 2
SIMILARITY_THRESHOLD = 0.86
SHORT_TEXT_MAX_LEN = 16
MIN_REPEAT_LEN = 4


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing transcript: {path.relative_to(PROJECT_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_cases() -> list[dict[str, Any]]:
    config = load_config()
    return list(config.get("audio_cases", []))


def get_case_ids(case_arg: str) -> list[str]:
    if case_arg == "all":
        return [case["id"] for case in load_cases()]
    return [case_arg]


def normalized_text(text: str) -> str:
    text = text.replace("\n", "").replace("\r", "").replace(" ", "")
    text = re.sub(r"[^\w\u4e00-\u9fff]", "", text)
    return text


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalized_text(a), normalized_text(b)).ratio()


def should_remove_segment(
    segment: dict[str, Any],
    kept_segments: list[dict[str, Any]],
    recent_kept_by_speaker: dict[str, list[dict[str, Any]]],
) -> tuple[bool, str]:
    text = str(segment.get("text", "")).strip()
    speaker = str(segment.get("speaker", ""))
    if not text:
        return True, "empty_text"

    if kept_segments:
        prev = kept_segments[-1]
        prev_text = str(prev.get("text", "")).strip()
        if normalized_text(prev_text) == normalized_text(text):
            return True, "exact_duplicate_adjacent"

    if kept_segments:
        recent_pool = kept_segments[-WINDOW_SIZE:]
        for prev in recent_pool:
            if str(prev.get("speaker", "")) != speaker:
                continue
            prev_text = str(prev.get("text", "")).strip()
            norm = normalized_text(text)
            prev_norm = normalized_text(prev_text)
            if len(norm) < MIN_REPEAT_LEN:
                continue
            if norm == prev_norm:
                return True, "exact_duplicate_nearby_same_speaker"
            if len(norm) <= SHORT_TEXT_MAX_LEN and similarity(prev_text, text) >= SIMILARITY_THRESHOLD:
                return True, "near_duplicate_same_speaker"

    speaker_recent = recent_kept_by_speaker.get(speaker, [])
    for prev in speaker_recent[-WINDOW_SIZE:]:
        prev_text = str(prev.get("text", "")).strip()
        norm = normalized_text(text)
        prev_norm = normalized_text(prev_text)
        if len(norm) < MIN_REPEAT_LEN:
            continue
        if norm == prev_norm:
            return True, "repeated_same_speaker_window"
        if len(norm) <= SHORT_TEXT_MAX_LEN and similarity(prev_text, text) >= SIMILARITY_THRESHOLD:
            return True, "similar_repeated_short_phrase"

    return False, ""


def process_segments(segments: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cleaned_segments: list[dict[str, Any]] = []
    removed_segments: list[dict[str, Any]] = []
    recent_kept_by_speaker: dict[str, list[dict[str, Any]]] = {}

    for segment in segments:
        remove, reason = should_remove_segment(segment, cleaned_segments, recent_kept_by_speaker)
        if remove:
            removed_segments.append(
                {
                    "speaker": segment.get("speaker"),
                    "start": segment.get("start"),
                    "end": segment.get("end"),
                    "text": segment.get("text"),
                    "reason": reason,
                }
            )
            continue

        cleaned_segments.append(segment)
        speaker = str(segment.get("speaker", ""))
        recent_kept_by_speaker.setdefault(speaker, []).append(segment)

    return cleaned_segments, removed_segments


def build_full_text(segments: list[dict[str, Any]]) -> str:
    return "\n".join(f"[{seg.get('speaker', 'SPEAKER')}] {seg.get('text', '')}" for seg in segments)


def clean_case(case_id: str, overwrite: bool = False) -> Path:
    source_path = PROJECT_ROOT / "results" / "transcripts_speaker" / f"{case_id}_separated_speaker_transcript.json"
    output_path = (
        PROJECT_ROOT
        / "results"
        / "transcripts_postprocessed"
        / f"{case_id}_separated_speaker_transcript_cleaned.json"
    )

    if output_path.exists() and not overwrite:
        print(f"skip existing cleaned transcript: {output_path.relative_to(PROJECT_ROOT)}")
        return output_path

    source = load_json(source_path)
    cleaned_segments, removed_segments = process_segments(list(source.get("segments", [])))
    cleaned_full_text = build_full_text(cleaned_segments)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "case_id": case_id,
        "method": "duplicate_suppression",
        "source_path": source_path.relative_to(PROJECT_ROOT).as_posix(),
        "cleaned_segments": cleaned_segments,
        "cleaned_full_text": cleaned_full_text,
        "removed_segments": removed_segments,
        "removed_count": len(removed_segments),
    }
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote cleaned transcript: {output_path.relative_to(PROJECT_ROOT)}")
    print(f"removed_count={len(removed_segments)}")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post-process separated speaker transcripts.")
    parser.add_argument("--case", required=True, help="Case id or all")
    parser.add_argument("--method", required=True, help="Post-processing method")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.method != "duplicate_suppression":
        raise ValueError("Only duplicate_suppression is supported in this stage.")

    _ = load_config()
    for case_id in get_case_ids(args.case):
        clean_case(case_id, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
