from __future__ import annotations

import argparse

from .audio_depth_router_common import PROJECT_ROOT, draw_bar_chart, read_csv, rel, write_csv, write_json

ABLATION_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_router_ablation.csv"
ABLATION_JSON = PROJECT_ROOT / "results" / "tables" / "audio_depth_router_ablation.json"
ABLATION_PNG = PROJECT_ROOT / "results" / "figures" / "audio_depth_router_ablation.png"
ABLATION_MD = PROJECT_ROOT / "results" / "figures" / "audio_depth_router_ablation.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize AudioDepth-Router ablation results.")
    return parser.parse_args()


def rows_from_performance() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted((PROJECT_ROOT / "results" / "tables").glob("audio_depth_router_performance_*.csv")):
        if path.name == "audio_depth_router_performance.csv":
            continue
        rows.extend(read_csv(path))
    if rows:
        return rows
    path = PROJECT_ROOT / "results" / "tables" / "audio_depth_router_performance.csv"
    return read_csv(path) if path.exists() else []


def main() -> None:
    _ = parse_args()
    rows = rows_from_performance()
    if not rows:
        return
    ablation = []
    seen: set[str] = set()
    for row in rows:
        strategy = row.get("strategy", "")
        if not strategy.startswith("audio_depth") and strategy in seen:
            continue
        seen.add(strategy)
        ablation.append(
            {
                "strategy": strategy,
                "representation": "audio_depth" if strategy.startswith("audio_depth") else "baseline",
                "routing_average_cer": row.get("routing_average_cer", ""),
                "classification_accuracy": row.get("classification_accuracy", ""),
                "label": row.get("label", "synthetic/silver"),
                "interpretation": "learned depth-augmented route"
                if strategy.startswith("audio_depth")
                else "fixed or oracle comparison",
            }
        )
    write_csv(ABLATION_CSV, ablation)
    write_json(ABLATION_JSON, ablation)
    draw_bar_chart(ablation, ABLATION_PNG, "strategy", "routing_average_cer", "AudioDepth-Router ablation")
    best = min(ablation, key=lambda row: float(row["routing_average_cer"]))
    audio_depth_rows = [row for row in ablation if row["strategy"].startswith("audio_depth")]
    ABLATION_MD.write_text(
        "\n".join(
            [
                "# AudioDepth-Router Ablation",
                "",
                "This ablation compares fixed routes, oracle best, and the current AudioDepth learned router output on the same synthetic split test scope.",
                "",
                f"Best row: `{best['strategy']}` with routing CER `{best['routing_average_cer']}`.",
                "",
                "AudioDepth rows:",
                *[
                    f"- `{row['strategy']}`: routing CER `{row['routing_average_cer']}`, accuracy `{row['classification_accuracy']}`"
                    for row in audio_depth_rows
                ],
                "",
                "Conclusion: this first pass is an `experimental/frontier` evidence stack. It should not be promoted into the stable baseline unless it beats router_v2 on matched rows with a larger controlled run.",
                "",
                f"Figure: `{rel(ABLATION_PNG)}`",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {rel(ABLATION_CSV)} and {rel(ABLATION_MD)}")


if __name__ == "__main__":
    main()
