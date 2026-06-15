from __future__ import annotations

from pathlib import Path

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel, write_csv
from .audio_depth_systematic_common import STRESS_MANIFEST_CSV, rows_by_sample, safe_float
from .evaluate_audio_depth_real_asr_cer import load_reference


OUT_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_audit_cases.csv"
OUT_MD = PROJECT_ROOT / "results" / "figures" / "audio_depth_real_asr_audit_pack.md"


def by_sample_route(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(row["sample_id"], row["route"]): row for row in rows}


def main() -> None:
    manifest = rows_by_sample(STRESS_MANIFEST_CSV)
    cer_rows = read_csv(PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_cer.csv")
    tx = by_sample_route(read_csv(PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_transcripts.csv"))
    out = []
    for row in cer_rows:
        sid = row["sample_id"]
        sample = manifest.get(sid, {})
        ref = load_reference(sample) if sample else {"reference_text": "", "reference_type": "missing"}
        cers = [safe_float(row.get(f"{route}_cer_real"), 999.0) for route in ["mixed", "separated", "cleaned"]]
        cers_sorted = sorted(cers)
        gap = round(cers_sorted[1] - cers_sorted[0], 6) if len(cers_sorted) >= 2 else 0.0
        notes = []
        if gap < 0.01:
            notes.append("route_gap_tiny")
        if min(cers) > 0.65:
            notes.append("all_routes_high_cer")
        if ref.get("reference_type") != "silver_reference":
            notes.append("reference_not_silver")
        out.append(
            {
                "sample_id": sid,
                "overlap_ratio": sample.get("overlap_ratio", ""),
                "tier": sample.get("interruption_style", ""),
                "audio_path": sample.get("mixed_path", ""),
                "reference_text": ref.get("reference_text", ""),
                "mixed_transcript": tx.get((sid, "mixed"), {}).get("text", ""),
                "separated_transcript": tx.get((sid, "separated"), {}).get("text", ""),
                "cleaned_transcript": tx.get((sid, "cleaned"), {}).get("text", ""),
                "mixed_cer_real": row.get("mixed_cer_real", ""),
                "separated_cer_real": row.get("separated_cer_real", ""),
                "cleaned_cer_real": row.get("cleaned_cer_real", ""),
                "oracle_route_real": row.get("oracle_route_real", ""),
                "router_v2_route": row.get("router_v2_route", ""),
                "hybrid_route": row.get("best_systematic_router_route", ""),
                "oracle_had_meaningful_route_gap": gap >= 0.03,
                "route_gap": gap,
                "error_notes": ";".join(notes) or "none",
            }
        )
    write_csv(OUT_CSV, out)
    tiny = sum(1 for row in out if safe_float(row["route_gap"]) < 0.01)
    high = sum(1 for row in out if "all_routes_high_cer" in row["error_notes"])
    lines = [
        "# AudioDepth Real-ASR Audit Pack",
        "",
        f"- Cases audited: `{len(out)}`",
        f"- Tiny route gap cases `<0.01`: `{tiny}`",
        f"- All-route high CER cases `>0.65`: `{high}`",
        "",
        "Interpretation: if oracle route gaps are small, routing has little room to win. If all routes have high CER, the bottleneck is ASR/reference/audio quality rather than router choice.",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote audit pack to {rel(OUT_CSV)} and {rel(OUT_MD)}")


if __name__ == "__main__":
    main()
