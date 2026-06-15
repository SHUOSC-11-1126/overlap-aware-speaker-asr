from __future__ import annotations

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel, write_csv
from .audio_depth_systematic_common import STRESS_MANIFEST_CSV, rows_by_sample, safe_float
from .evaluate_audio_depth_real_asr_cer import load_reference
from .text_normalization import length_ratio, normalize_asr_text


OUT_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_reference_quality.csv"
OUT_MD = PROJECT_ROOT / "results" / "figures" / "audio_depth_real_asr_reference_quality.md"


def main() -> None:
    manifest = rows_by_sample(STRESS_MANIFEST_CSV)
    cer_rows = read_csv(PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_cer.csv")
    transcripts = read_csv(PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_transcripts.csv")
    by_route = {(row["sample_id"], row["route"]): row.get("text", "") for row in transcripts}
    out = []
    for row in cer_rows:
        sid = row["sample_id"]
        sample = manifest[sid]
        ref = load_reference(sample)
        ref_text = ref["reference_text"]
        norm_ref = normalize_asr_text(ref_text)
        notes = []
        if not norm_ref:
            notes.append("empty_reference")
        if len(norm_ref) < 12:
            notes.append("short_reference")
        if len(norm_ref) > 300:
            notes.append("long_reference")
        if ref.get("reference_type") == "silver_reference":
            notes.append("weak_silver_reference")
        for route in ["mixed", "separated", "cleaned"]:
            if safe_float(row.get(f"{route}_cer_real"), 0.0) > 0.65:
                notes.append(f"{route}_high_cer")
        out.append(
            {
                "sample_id": sid,
                "reference_type": ref.get("reference_type", ""),
                "reference_path": ref.get("reference_path", ""),
                "reference_norm_len": len(norm_ref),
                "mixed_len_ratio": length_ratio(ref_text, by_route.get((sid, "mixed"), "")),
                "separated_len_ratio": length_ratio(ref_text, by_route.get((sid, "separated"), "")),
                "cleaned_len_ratio": length_ratio(ref_text, by_route.get((sid, "cleaned"), "")),
                "mixed_cer_real": row.get("mixed_cer_real", ""),
                "separated_cer_real": row.get("separated_cer_real", ""),
                "cleaned_cer_real": row.get("cleaned_cer_real", ""),
                "quality_notes": ";".join(dict.fromkeys(notes)) or "none",
            }
        )
    write_csv(OUT_CSV, out)
    weak = sum(1 for row in out if "weak_silver_reference" in row["quality_notes"])
    high = sum(1 for row in out if "high_cer" in row["quality_notes"])
    lines = [
        "# AudioDepth Real-ASR Reference Quality",
        "",
        f"- Cases checked: `{len(out)}`",
        f"- Weak silver references: `{weak}`",
        f"- Cases with high route CER: `{high}`",
        "",
        "`real Whisper validation is limited by synthetic/silver reference quality` for this slice. The references are useful for stress auditing but are not gold human transcripts.",
    ]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote reference quality report to {rel(OUT_CSV)}")


if __name__ == "__main__":
    main()
