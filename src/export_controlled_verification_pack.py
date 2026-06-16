from __future__ import annotations

import argparse

from .audio_depth_router_common import rel, write_csv, read_csv
from .controlled_benchmark_common import FIGURE_DIR, INVENTORY_CSV, VERIFICATION_PACK_CSV


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export controlled benchmark manual verification pack.")
    parser.add_argument("--limit", type=int, default=60)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    inventory = read_csv(INVENTORY_CSV)
    rows = []
    for row in inventory[: args.limit]:
        rows.append(
            {
                "utterance_id": row["utterance_id"],
                "speaker_id": row["speaker_id"],
                "wav_path": row["wav_path"],
                "candidate_transcript": row["transcript_candidate"],
                "verified_transcript": "",
                "verification_notes": "",
                "verification_status": row["verification_status"],
            }
        )
    write_csv(VERIFICATION_PACK_CSV, rows)
    md = FIGURE_DIR / "controlled_verification_pack.md"
    lines = [
        "# Controlled Verification Pack",
        "",
        "Fill `verified_transcript` to upgrade future controlled samples from `silver_plus_unverified` to `verified_micro_gold`.",
        "",
        f"- Rows exported: `{len(rows)}`",
        f"- CSV: `{rel(VERIFICATION_PACK_CSV)}`",
    ]
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote verification pack to {rel(VERIFICATION_PACK_CSV)}")


if __name__ == "__main__":
    main()
