from __future__ import annotations

from .audio_depth_router_common import read_csv, rel, write_csv
from .audio_depth_systematic_common import CASE_STUDIES_CSV, PREDICTIONS_CSV, SYSTEMATIC_FIGURE_PREFIX, safe_float


def main() -> None:
    rows = read_csv(PREDICTIONS_CSV)
    by_sample = {}
    for row in rows:
        by_sample.setdefault(row["sample_id"], {})[row["model_name"]] = row
    cases = []
    for sample_id, group in by_sample.items():
        hybrid = group.get("hybrid_mlp_v2") or group.get("calibrated_confidence_router")
        router = group.get("old_router_v2")
        oracle = group.get("oracle_best")
        if not hybrid or not router or not oracle:
            continue
        h_ok = hybrid["predicted_route_label"] == hybrid["true_route_label"]
        r_ok = router["predicted_route_label"] == router["true_route_label"]
        tag = "both_correct" if h_ok and r_ok else "hybrid_correct_router_v2_wrong" if h_ok else "router_v2_correct_hybrid_wrong" if r_ok else "both_wrong"
        if safe_float(hybrid.get("confidence"), 1.0) < 0.65:
            tag = "low_confidence"
        cases.append(
            {
                "sample_id": sample_id,
                "case_type": tag,
                "audio_tier": hybrid.get("overlap_tier", ""),
                "overlap_ratio": hybrid.get("overlap_ratio", ""),
                "router_v2_route": router["predicted_route_label"],
                "hybrid_route": hybrid["predicted_route_label"],
                "oracle_route": oracle["predicted_route_label"],
                "hybrid_confidence": hybrid.get("confidence", ""),
                "hybrid_cer": hybrid.get("predicted_cer", ""),
                "router_v2_cer": router.get("predicted_cer", ""),
                "explanation": hybrid.get("explanation", ""),
            }
        )
    selected = []
    seen = set()
    for desired in ["hybrid_correct_router_v2_wrong", "router_v2_correct_hybrid_wrong", "both_correct", "both_wrong", "low_confidence"]:
        for row in cases:
            if row["case_type"] == desired and row["sample_id"] not in seen:
                selected.append(row)
                seen.add(row["sample_id"])
                if len([item for item in selected if item["case_type"] == desired]) >= 2:
                    break
    selected = selected[:12]
    write_csv(CASE_STUDIES_CSV, selected)
    lines = ["# AudioDepth Systematic Case Studies", ""]
    for row in selected:
        lines.extend(
            [
                f"## {row['sample_id']} ({row['case_type']})",
                f"- tier: `{row['audio_tier']}`, overlap_ratio: `{row['overlap_ratio']}`",
                f"- router_v2 route/CER: `{row['router_v2_route']}` / `{row['router_v2_cer']}`",
                f"- hybrid route/CER/confidence: `{row['hybrid_route']}` / `{row['hybrid_cer']}` / `{row['hybrid_confidence']}`",
                f"- oracle route: `{row['oracle_route']}`",
                f"- explanation: {row['explanation']}",
                "",
            ]
        )
    (SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_case_studies.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote case studies to {rel(CASE_STUDIES_CSV)}")


if __name__ == "__main__":
    main()
