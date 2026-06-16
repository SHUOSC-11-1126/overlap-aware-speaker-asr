from __future__ import annotations

from .audio_depth_router_common import read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .balanced_v2_common import BALANCED_REVIEW_CANDIDATES, FIGURE_DIR, V2_CER, V2_TX, duplicate_density


def main() -> None:
    rows = read_csv(V2_CER)
    tx = {(row["sample_id"], row["route"]): row.get("text", "") for row in read_csv(V2_TX)}
    out = []
    for row in rows:
        texts = [tx.get((row["sample_id"], route), "") for route in ["mixed", "separated", "cleaned"]]
        dup = max([duplicate_density(text) for text in texts] + [0.0])
        reasons = []
        if min(safe_float(row["mixed_cer"]), safe_float(row["separated_cer"]), safe_float(row["cleaned_cer"])) > 0.6:
            reasons.append("all_routes_high_cer")
        if safe_float(row["route_gap"]) < 0.02:
            reasons.append("low_route_gap")
        if dup > 0.45:
            reasons.append("duplicate_density_high")
        if max(len(text) for text in texts) > max(1, min(len(text) for text in texts)) * 2.8:
            reasons.append("length_inflation")
        if reasons:
            out.append({**row, "review_reasons": "|".join(reasons), "max_duplicate_density": dup})
    write_csv(BALANCED_REVIEW_CANDIDATES, out)
    md = ["# AudioDepth Balanced Review Candidates", "", f"- candidates: `{len(out)}`", "- Criteria: high min-CER, low route gap, duplicate density, or route length inflation.", ""]
    for row in out[:20]:
        md.append(f"- `{row['sample_id']}` oracle `{row['oracle_route']}` gap `{row['route_gap']}` reasons `{row['review_reasons']}`")
    (FIGURE_DIR / "audio_depth_balanced_review_candidates.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Wrote review candidates to {rel(BALANCED_REVIEW_CANDIDATES)}")


if __name__ == "__main__":
    main()
