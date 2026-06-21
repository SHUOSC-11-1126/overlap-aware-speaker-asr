from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .generative_audiodepth_common import FIGURE_DIR, ROUTES, TEST_CSV, read_rows, safe_float, unique_samples, write_csv, write_markdown


OUT_CSV = Path("results/tables/generative_audiodepth_downstream_comparison.csv")
PER_SPLIT_CSV = Path("results/tables/generative_audiodepth_per_split.csv")
PER_FAMILY_CSV = Path("results/tables/generative_audiodepth_per_family.csv")
LEADERBOARD_PNG = FIGURE_DIR / "generative_audiodepth_downstream_leaderboard.png"
SUMMARY_MD = FIGURE_DIR / "generative_audiodepth_downstream_summary.md"


def cer(row: dict[str, str], route: str) -> float:
    return safe_float(row.get(f"{route}_cer"), 1.0)


def evaluate_route_policy(samples: list[dict[str, str]], name: str, routes: dict[str, str]) -> dict[str, object]:
    selected = [cer(row, routes.get(row["sample_id"], "mixed")) for row in samples]
    oracle = [min(cer(row, route) for route in ROUTES) for row in samples]
    correct = [routes.get(row["sample_id"], "mixed") == row.get("oracle_route") for row in samples]
    false_safe = [row for row in samples if safe_float(row.get("mixed_cer"), 0.0) >= 0.6 and routes.get(row["sample_id"], "mixed") == "mixed"]
    return {
        "model_name": name,
        "sample_count": len(samples),
        "selected_route_cer": round(sum(selected) / len(selected), 6) if selected else 0.0,
        "oracle_gap": round((sum(selected) - sum(oracle)) / len(selected), 6) if selected else 0.0,
        "route_accuracy": round(sum(correct) / len(correct), 6) if correct else 0.0,
        "false_safe_count": len(false_safe),
    }


def routes_for_policy(policy: dict[str, object], samples: list[dict[str, str]], route_maps: dict[str, dict[str, str]]) -> dict[str, str]:
    model_name = str(policy["model_name"])
    if model_name in route_maps:
        return route_maps[model_name]
    if model_name == "oracle":
        return {row["sample_id"]: row.get("oracle_route", "mixed") for row in samples}
    if model_name.startswith("fixed_"):
        route = model_name.replace("fixed_", "")
        return {row["sample_id"]: route for row in samples}
    return {row["sample_id"]: "mixed" for row in samples}


def main() -> None:
    samples = unique_samples(read_rows(TEST_CSV))
    predictions = read_rows(Path("results/tables/generative_route_regret_predictions.csv"))
    no_cost_routes = {row["sample_id"]: row["predicted_route"] for row in predictions if row["policy_name"] == "generative_regret_no_cost"}
    cost_routes = {row["sample_id"]: row["predicted_route"] for row in predictions if row["policy_name"] == "generative_regret_cost_aware"}
    route_maps = {
        "generative_regret_no_cost": no_cost_routes,
        "generative_regret_cost_aware": cost_routes,
    }
    policies = [
        evaluate_route_policy(samples, "fixed_mixed", {row["sample_id"]: "mixed" for row in samples}),
        evaluate_route_policy(samples, "fixed_separated", {row["sample_id"]: "separated" for row in samples}),
        evaluate_route_policy(samples, "fixed_cleaned", {row["sample_id"]: "cleaned" for row in samples}),
        evaluate_route_policy(samples, "generative_regret_no_cost", no_cost_routes),
        evaluate_route_policy(samples, "generative_regret_cost_aware", cost_routes),
        evaluate_route_policy(samples, "oracle", {row["sample_id"]: row.get("oracle_route", "mixed") for row in samples}),
    ]
    write_csv(OUT_CSV, policies)
    write_csv(PER_SPLIT_CSV, [{**row, "split": "test"} for row in policies])
    family_rows = []
    for family in sorted({row.get("target_family", "") for row in samples}):
        subset = [row for row in samples if row.get("target_family") == family]
        for policy in policies:
            if policy["model_name"] == "oracle":
                continue
            family_rows.append(
                {
                    **evaluate_route_policy(subset, str(policy["model_name"]), routes_for_policy(policy, subset, route_maps)),
                    "target_family": family,
                }
            )
    write_csv(PER_FAMILY_CSV, family_rows)
    width, height = 860, 360
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 18), "Generative AudioDepth downstream selected-route CER", fill=(0, 0, 0))
    max_cer = max(safe_float(row["selected_route_cer"]) for row in policies) or 1.0
    for idx, row in enumerate(policies):
        y = 60 + idx * 38
        value = safe_float(row["selected_route_cer"])
        draw.text((20, y), str(row["model_name"])[:34], fill=(0, 0, 0))
        draw.rectangle((300, y, 300 + int(450 * value / max_cer), y + 22), fill=(80, 130, 185))
        draw.text((770, y), f"{value:.3f}", fill=(0, 0, 0))
    LEADERBOARD_PNG.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(LEADERBOARD_PNG)
    lines = [
        "# Generative AudioDepth Downstream Summary",
        "",
        "First-pass downstream comparison on the source-disjoint test split.",
        "",
        "| model | selected CER | oracle gap | route accuracy | false-safe |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in policies:
        lines.append(f"| {row['model_name']} | {row['selected_route_cer']} | {row['oracle_gap']} | {row['route_accuracy']} | {row['false_safe_count']} |")
    write_markdown(SUMMARY_MD, lines)
    print(f"Wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
