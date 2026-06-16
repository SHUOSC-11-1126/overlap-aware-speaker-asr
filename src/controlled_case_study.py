from __future__ import annotations

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .controlled_benchmark_common import CER_CSV, FIGURE_DIR, MANIFEST_CSV, ROUTER_PREDICTIONS_CSV, TRANSCRIPTS_CSV


CSV = PROJECT_ROOT / "results" / "tables" / "controlled_case_studies.csv"
MD = PROJECT_ROOT / "results" / "figures" / "controlled_case_studies.md"


def main() -> None:
    cer_rows = read_csv(CER_CSV)
    manifest = {row["sample_id"]: row for row in read_csv(MANIFEST_CSV)}
    tx = {(row["sample_id"], row["route"]): row.get("text", "") for row in read_csv(TRANSCRIPTS_CSV)}
    preds = {(row["sample_id"], row["model_name"]): row.get("predicted_route", "") for row in read_csv(ROUTER_PREDICTIONS_CSV)}
    selected = []
    selected.extend(sorted(cer_rows, key=lambda row: safe_float(row["route_gap"]), reverse=True)[:4])
    selected.extend([row for row in cer_rows if row["oracle_route"] == "mixed"][:2])
    selected.extend([row for row in cer_rows if row["oracle_route"] == "separated"][:2])
    selected.extend([row for row in cer_rows if row["oracle_route"] == "cleaned"][:2])
    unique = []
    seen = set()
    for row in selected:
        if row["sample_id"] not in seen:
            seen.add(row["sample_id"])
            unique.append(row)
    out = []
    for row in unique[:12]:
        sid = row["sample_id"]
        man = manifest[sid]
        out.append(
            {
                "sample_id": sid,
                "style": man["style"],
                "overlap_ratio": man["overlap_ratio"],
                "reference": man["reference_text"],
                "mixed_transcript": tx.get((sid, "mixed"), ""),
                "separated_transcript": tx.get((sid, "separated"), ""),
                "cleaned_transcript": tx.get((sid, "cleaned"), ""),
                "mixed_cer": row["mixed_cer"],
                "separated_cer": row["separated_cer"],
                "cleaned_cer": row["cleaned_cer"],
                "oracle_route": row["oracle_route"],
                "router_v2_prediction": preds.get((sid, "router_v2"), ""),
                "hybrid_prediction": preds.get((sid, "stage23_systematic_heuristic"), ""),
                "explanation": f"route_gap={row['route_gap']}; separation_gain={row['separation_gain']}",
            }
        )
    write_csv(CSV, out)
    lines = ["# Controlled Case Studies", ""]
    for row in out:
        lines.extend(
            [
                f"## {row['sample_id']}",
                "",
                f"- style: `{row['style']}` overlap: `{row['overlap_ratio']}` oracle: `{row['oracle_route']}`",
                f"- CER mixed/separated/cleaned: `{row['mixed_cer']}` / `{row['separated_cer']}` / `{row['cleaned_cer']}`",
                f"- router_v2: `{row['router_v2_prediction']}` hybrid: `{row['hybrid_prediction']}`",
                "",
            ]
        )
    MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote controlled case studies to {rel(CSV)}")


if __name__ == "__main__":
    main()
