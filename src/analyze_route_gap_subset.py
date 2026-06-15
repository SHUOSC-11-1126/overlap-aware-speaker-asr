from __future__ import annotations

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float


OUT_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_route_gap_subset.csv"
OUT_MD = PROJECT_ROOT / "results" / "figures" / "audio_depth_real_asr_route_gap_subset.md"


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def route_gap(row: dict[str, str]) -> float:
    vals = sorted([safe_float(row[f"{r}_cer_real"], 999.0) for r in ["mixed", "separated", "cleaned"]])
    return round(vals[1] - vals[0], 6)


def main() -> None:
    rows = read_csv(PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_cer.csv")
    out = []
    for threshold in [0.01, 0.03, 0.05, 0.10]:
        subset = [row for row in rows if route_gap(row) >= threshold]
        out.append(
            {
                "route_gap_threshold": threshold,
                "sample_count": len(subset),
                "fixed_mixed_cer": mean([safe_float(r["mixed_cer_real"]) for r in subset]),
                "fixed_separated_cer": mean([safe_float(r["separated_cer_real"]) for r in subset]),
                "fixed_cleaned_cer": mean([safe_float(r["cleaned_cer_real"]) for r in subset]),
                "router_v2_cer": mean([safe_float(r["router_v2_cer_real"]) for r in subset]),
                "hybrid_cer": mean([safe_float(r["systematic_router_cer_real"]) for r in subset]),
                "oracle_cer": mean([safe_float(r["oracle_cer_real"]) for r in subset]),
            }
        )
    write_csv(OUT_CSV, out)
    lines = ["# Real-ASR Route-Gap Subset", ""]
    for row in out:
        lines.append(f"- gap >= `{row['route_gap_threshold']}`: n=`{row['sample_count']}`, hybrid=`{row['hybrid_cer']}`, router_v2=`{row['router_v2_cer']}`, oracle=`{row['oracle_cer']}`")
    lines.append("")
    lines.append("If route-gap subsets are small, a router cannot show large aggregate gains on the current sampled slice.")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote route-gap subset report to {rel(OUT_CSV)}")


if __name__ == "__main__":
    main()
