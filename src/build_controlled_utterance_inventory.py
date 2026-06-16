from __future__ import annotations

from pathlib import Path

from .audio_depth_router_common import PROJECT_ROOT, rel, write_csv
from .controlled_benchmark_common import FIGURE_DIR, INVENTORY_CSV, load_json, wav_duration


def main() -> None:
    rows = []
    for wav_path in sorted((PROJECT_ROOT / "resources" / "snippets").glob("*.wav")):
        utterance_id = wav_path.stem
        speaker_id = utterance_id.split("_", 1)[0]
        transcript_path = PROJECT_ROOT / "results" / "snippet_transcripts" / f"{utterance_id}_whisper.json"
        candidate = ""
        source = "missing"
        if transcript_path.exists():
            payload = load_json(transcript_path)
            candidate = payload.get("text", "").strip()
            source = rel(transcript_path)
        rows.append(
            {
                "utterance_id": utterance_id,
                "speaker_id": speaker_id,
                "wav_path": rel(wav_path),
                "duration": wav_duration(wav_path),
                "transcript_candidate": candidate,
                "transcript_source": source,
                "verification_status": "candidate_whisper_small" if candidate else "missing_transcript",
                "usable_for_benchmark": str(bool(candidate and len(candidate) >= 2)),
            }
        )
    write_csv(INVENTORY_CSV, rows)
    needs = [row for row in rows if row["verification_status"] != "verified"]
    md = FIGURE_DIR / "controlled_utterance_inventory_needs_verification.md"
    lines = [
        "# Controlled Utterance Inventory Needs Verification",
        "",
        f"- Inventory count: `{len(rows)}`",
        f"- Manually verified count: `0`",
        f"- Candidate transcript count: `{sum(1 for row in rows if row['transcript_candidate'])}`",
        "",
        "| utterance_id | speaker | wav | candidate |",
        "| --- | --- | --- | --- |",
    ]
    for row in needs:
        lines.append(f"| {row['utterance_id']} | {row['speaker_id']} | {row['wav_path']} | {row['transcript_candidate']} |")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} utterances to {rel(INVENTORY_CSV)}")


if __name__ == "__main__":
    main()
