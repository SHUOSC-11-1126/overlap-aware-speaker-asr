from __future__ import annotations

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel, write_csv
from .evaluate_audio_depth_real_asr_cer import load_reference
from .audio_depth_systematic_common import STRESS_MANIFEST_CSV, rows_by_sample, safe_float
from .text_normalization import cer


OUT_CER = PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_cer_normalized.csv"
OUT_COMP = PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_router_comparison_normalized.csv"
OUT_MD = PROJECT_ROOT / "results" / "figures" / "audio_depth_real_asr_normalized_summary.md"


def mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def main() -> None:
    manifest = rows_by_sample(STRESS_MANIFEST_CSV)
    original = read_csv(PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_cer.csv")
    transcripts = read_csv(PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_transcripts.csv")
    text = {(row["sample_id"], row["route"]): row.get("text", "") for row in transcripts}
    rows = []
    for row in original:
        sid = row["sample_id"]
        ref = load_reference(manifest[sid])["reference_text"]
        cers = {route: cer(ref, text.get((sid, route), "")) for route in ["mixed", "separated", "cleaned"]}
        oracle = min(cers, key=cers.get)
        sys_route = row["best_systematic_router_route"]
        v2_route = row["router_v2_route"]
        rows.append(
            {
                **row,
                "mixed_cer_normalized": cers["mixed"],
                "separated_cer_normalized": cers["separated"],
                "cleaned_cer_normalized": cers["cleaned"],
                "oracle_route_normalized": oracle,
                "router_v2_cer_normalized": cers.get(v2_route, 999.0),
                "systematic_router_cer_normalized": cers.get(sys_route, 999.0),
                "oracle_cer_normalized": cers[oracle],
            }
        )
    comp = [
        {"method": "fixed_mixed_normalized", "average_cer": mean([safe_float(r["mixed_cer_normalized"]) for r in rows]), "sample_count": len(rows)},
        {"method": "fixed_separated_normalized", "average_cer": mean([safe_float(r["separated_cer_normalized"]) for r in rows]), "sample_count": len(rows)},
        {"method": "fixed_cleaned_normalized", "average_cer": mean([safe_float(r["cleaned_cer_normalized"]) for r in rows]), "sample_count": len(rows)},
        {"method": "router_v2_normalized", "average_cer": mean([safe_float(r["router_v2_cer_normalized"]) for r in rows]), "sample_count": len(rows)},
        {"method": "hybrid_late_fusion_v2_normalized", "average_cer": mean([safe_float(r["systematic_router_cer_normalized"]) for r in rows]), "sample_count": len(rows)},
        {"method": "oracle_normalized", "average_cer": mean([safe_float(r["oracle_cer_normalized"]) for r in rows]), "sample_count": len(rows)},
    ]
    comp = sorted(comp, key=lambda r: safe_float(r["average_cer"]))
    write_csv(OUT_CER, rows)
    write_csv(OUT_COMP, comp)
    old = mean([safe_float(r["systematic_router_cer_real"]) for r in original])
    new = next(r for r in comp if r["method"] == "hybrid_late_fusion_v2_normalized")["average_cer"]
    OUT_MD.write_text(
        f"# Normalized Real-ASR Summary\n\n- Original hybrid CER: `{old}`\n- Normalized hybrid CER: `{new}`\n- Delta: `{round(safe_float(new) - old, 6)}`\n\nThe same conservative normalization is now explicit in `src/text_normalization.py`.\n",
        encoding="utf-8",
    )
    print(f"Wrote normalized comparison to {rel(OUT_COMP)}")


if __name__ == "__main__":
    main()
