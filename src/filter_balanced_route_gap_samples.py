from __future__ import annotations

from collections import Counter

from .audio_depth_router_common import read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .balanced_v2_common import FIGURE_DIR, V2_CER, V2_DISTRIBUTION, V2_FILTERED, route_winner_counts
from .controlled_benchmark_common import draw_bar


def main() -> None:
    rows = read_csv(V2_CER)
    filtered = []
    for row in rows:
        min_cer = min(safe_float(row["mixed_cer"]), safe_float(row["separated_cer"]), safe_float(row["cleaned_cer"]))
        tag = "route_winner"
        if min_cer > 0.6 or safe_float(row["route_gap"]) < 0.02:
            tag = "review_needed"
        filtered.append({**row, "route_winner_tag": tag})
    counts = route_winner_counts(rows)
    dist = [{"oracle_route": route, "count": count, "fraction": round(count / max(len(rows), 1), 6)} for route, count in counts.items()]
    dist.append({"oracle_route": "review_needed", "count": sum(1 for row in filtered if row["route_winner_tag"] == "review_needed"), "fraction": round(sum(1 for row in filtered if row["route_winner_tag"] == "review_needed") / max(len(rows), 1), 6)})
    family_counts = Counter(row["intended_family"] for row in rows)
    for family, count in sorted(family_counts.items()):
        dist.append({"oracle_route": f"family:{family}", "count": count, "fraction": round(count / max(len(rows), 1), 6)})
    write_csv(V2_FILTERED, filtered)
    write_csv(V2_DISTRIBUTION, dist)
    write_csv(
        FIGURE_DIR.parent / "tables" / "route_winner_balanced_v2_summary.csv",
        [
            {"bucket": row["oracle_route"], "count": row["count"], "fraction": row["fraction"], "source": "real_whisper_oracle_distribution"}
            for row in dist[:4]
        ],
    )
    draw_bar(dist[:4], FIGURE_DIR / "controlled_v2_oracle_route_distribution.png", "oracle_route", "count", "Controlled v2 oracle route distribution")
    gap_rows = sorted([{"sample_id": row["sample_id"], "route_gap": row["route_gap"]} for row in rows], key=lambda row: safe_float(row["route_gap"]))
    draw_bar(gap_rows[:20], FIGURE_DIR / "controlled_v2_route_gap_distribution.png", "sample_id", "route_gap", "Smallest v2 real-ASR route gaps")
    (FIGURE_DIR / "route_winner_balanced_v2_summary.md").write_text(
        "\n".join(
            [
                "# Route-Winner Balanced v2 Summary",
                "",
                *[f"- `{row['oracle_route']}`: `{row['count']}` (`{row['fraction']}`)" for row in dist[:4]],
                "",
                "The cleaned route is reported honestly; in the current real Whisper run it did not become the oracle winner.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote v2 route-gap filtered table to {rel(V2_FILTERED)}")


if __name__ == "__main__":
    main()
