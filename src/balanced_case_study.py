from __future__ import annotations

from .audio_depth_router_common import read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .balanced_v2_common import BALANCED_CASE_STUDIES, BALANCED_PREDICTIONS, BALANCED_REVIEW_CANDIDATES, FIGURE_DIR, V2_CER, V2_TX


def main() -> None:
    rows = read_csv(V2_CER)
    tx = {(row["sample_id"], row["route"]): row.get("text", "") for row in read_csv(V2_TX)}
    preds = {(row["sample_id"], row["model_name"]): row.get("predicted_route", "") for row in read_csv(BALANCED_PREDICTIONS)}
    review = {row["sample_id"] for row in read_csv(BALANCED_REVIEW_CANDIDATES)} if BALANCED_REVIEW_CANDIDATES.exists() else set()
    selected = []
    for route in ["mixed", "separated", "cleaned"]:
        selected.extend([row for row in sorted(rows, key=lambda r: safe_float(r["route_gap"]), reverse=True) if row["oracle_route"] == route][:3])
    selected.extend([row for row in rows if row["sample_id"] in review][:3])
    unique = []
    seen = set()
    for row in selected:
        if row["sample_id"] not in seen:
            seen.add(row["sample_id"])
            unique.append(row)
    out = []
    for row in unique[:12]:
        sid = row["sample_id"]
        out.append(
            {
                "sample_id": sid,
                "intended_family": row["intended_family"],
                "oracle_route": row["oracle_route"],
                "route_gap": row["route_gap"],
                "mixed_cer": row["mixed_cer"],
                "separated_cer": row["separated_cer"],
                "cleaned_cer": row["cleaned_cer"],
                "router_v2_prediction": preds.get((sid, "router_v2"), ""),
                "balanced_router_prediction": preds.get((sid, "audio_depth_balanced_route_winner_router"), ""),
                "review_candidate": "True" if sid in review else "False",
                "mixed_transcript": tx.get((sid, "mixed"), ""),
                "separated_transcript": tx.get((sid, "separated"), ""),
                "cleaned_transcript": tx.get((sid, "cleaned"), ""),
            }
        )
    write_csv(BALANCED_CASE_STUDIES, out)
    lines = ["# Balanced v2 Case Studies", ""]
    for row in out:
        lines.extend(
            [
                f"## {row['sample_id']}",
                "",
                f"- family: `{row['intended_family']}` oracle: `{row['oracle_route']}` gap: `{row['route_gap']}` review: `{row['review_candidate']}`",
                f"- CER mixed/separated/cleaned: `{row['mixed_cer']}` / `{row['separated_cer']}` / `{row['cleaned_cer']}`",
                f"- router_v2: `{row['router_v2_prediction']}` balanced: `{row['balanced_router_prediction']}`",
                "",
            ]
        )
    (FIGURE_DIR / "audio_depth_balanced_case_studies.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote balanced case studies to {rel(BALANCED_CASE_STUDIES)}")


if __name__ == "__main__":
    main()
