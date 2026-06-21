from __future__ import annotations

from collections import defaultdict

import numpy as np

from .generative_audiodepth_common import FIGURE_DIR, PROJECT_ROOT, TABLE_DIR, read_rows, safe_float, spearman, write_csv, write_markdown
from .generative_audiodepth_reliability_common import draw_bar_chart


MANIFEST = TABLE_DIR / "generative_audiodepth_counterfactual_manifest.csv"
OUT_CSV = TABLE_DIR / "generative_audiodepth_counterfactual_reliability.csv"
FAIL_CSV = TABLE_DIR / "generative_audiodepth_counterfactual_failures.csv"
OUT_PNG = FIGURE_DIR / "generative_audiodepth_counterfactual_reliability_curves.png"
OUT_MD = FIGURE_DIR / "generative_audiodepth_counterfactual_reliability.md"


def predicted_route(row: dict[str, str]) -> str:
    overlap = safe_float(row.get("overlap_mean"), 0.0)
    uncertainty = safe_float(row.get("uncertainty_mean"), 0.0)
    dominance = abs(safe_float(row.get("dominance_mean"), 0.5) - 0.5)
    if uncertainty > 0.62:
        return "review"
    if overlap > 0.46 and dominance < 0.22:
        return "separated"
    return "mixed"


def metric_value(row: dict[str, str], family: str) -> float:
    if family == "overlap_sweep":
        return safe_float(row.get("overlap_mean"), 0.0)
    if family == "dominance_sdr_sweep":
        return abs(safe_float(row.get("dominance_mean"), 0.5) - 0.5)
    if family == "backchannel_duration":
        return safe_float(row.get("uncertainty_mean"), 0.0)
    if family == "gain_noise":
        return safe_float(row.get("overlap_mean"), 0.0) + safe_float(row.get("uncertainty_mean"), 0.0)
    return safe_float(row.get("overlap_mean"), 0.0)


def monotonic_ok(values: list[float], family: str) -> bool:
    if len(values) < 2:
        return True
    diffs = np.diff(np.asarray(values))
    if family in {"overlap_sweep", "dominance_sdr_sweep", "backchannel_duration"}:
        return bool(np.mean(diffs >= -1e-5) >= 0.75)
    if family == "gain_noise":
        return bool(max(values) - min(values) <= 0.55)
    return bool(np.std(values) <= 0.08 or max(values) - min(values) <= 0.22)


def pairwise_order(values: list[float]) -> float:
    total = 0
    ok = 0
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            total += 1
            if values[j] + 1e-5 >= values[i]:
                ok += 1
    return ok / total if total else 1.0


def main() -> None:
    rows = read_rows(MANIFEST)
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row["base_sample_id"], row["family"])].append(row)
    summary_rows = []
    failure_rows = []
    for (sample_id, family), group in sorted(groups.items()):
        group = sorted(group, key=lambda r: safe_float(r.get("control_value"), 0.0))
        values = [metric_value(row, family) for row in group]
        controls = [safe_float(row.get("control_value"), 0.0) for row in group]
        routes = [predicted_route(row) for row in group]
        flips = sum(a != b for a, b in zip(routes, routes[1:]))
        ok = monotonic_ok(values, family)
        order_acc = pairwise_order(values)
        corr = spearman(controls, values)
        stability = round(float(1.0 / (1.0 + np.std(values))), 6) if values else 0.0
        row = {
            "base_sample_id": sample_id,
            "family": family,
            "case_count": len(group),
            "monotonic_consistent": str(ok),
            "pairwise_ordering_accuracy": round(order_acc, 6),
            "spearman": corr,
            "prediction_flip_rate": round(flips / max(1, len(group) - 1), 6),
            "map_stability": stability,
            "first_route": routes[0] if routes else "",
            "last_route": routes[-1] if routes else "",
            "metric_min": round(min(values), 6) if values else 0.0,
            "metric_max": round(max(values), 6) if values else 0.0,
        }
        summary_rows.append(row)
        if not ok or row["prediction_flip_rate"] > 0.5:
            failure_rows.append({**row, "failure_reason": "non_monotonic_or_high_route_flip"})
    write_csv(OUT_CSV, summary_rows)
    write_csv(FAIL_CSV, failure_rows)
    family_rows = []
    for family in sorted({row["family"] for row in summary_rows}):
        subset = [row for row in summary_rows if row["family"] == family]
        family_rows.append(
            {
                "family": family,
                "monotonic_consistency_rate": round(sum(row["monotonic_consistent"] == "True" for row in subset) / len(subset), 6),
            }
        )
    draw_bar_chart(OUT_PNG, "Counterfactual monotonic consistency by family", family_rows, "family", "monotonic_consistency_rate")
    overall = round(sum(row["monotonic_consistent"] == "True" for row in summary_rows) / len(summary_rows), 6) if summary_rows else 0.0
    lines = [
        "# Generative AudioDepth Counterfactual Reliability",
        "",
        f"- evaluated groups: {len(summary_rows)}",
        f"- monotonic consistency rate: {overall}",
        f"- failure cases: {len(failure_rows)}",
        "",
        "## Main Failure Mode",
        "",
    ]
    if failure_rows:
        first = failure_rows[0]
        lines.append(f"- `{first['base_sample_id']}` / `{first['family']}` failed with `{first['failure_reason']}`.")
    else:
        lines.append("- No monotonic failures under the map-level synthetic counterfactual suite.")
    lines.extend(
        [
            "",
            "This is map-level counterfactual evidence only. It does not prove ASR-level route generalization.",
        ]
    )
    write_markdown(OUT_MD, lines)
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
