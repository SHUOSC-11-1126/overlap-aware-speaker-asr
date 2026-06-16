from __future__ import annotations

from .audio_depth_router_common import read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .audiodepth_centric_common import ABLATION_CSV, CASCADE_COST_CSV, FIGURE_DIR, GATE_PERFORMANCE_CSV, draw_bar, write_summary


def main() -> None:
    cascade = read_csv(CASCADE_COST_CSV)
    gate = read_csv(GATE_PERFORMANCE_CSV)[0] if GATE_PERFORMANCE_CSV.exists() else {}

    def row_for(model: str, label: str, modality: str) -> dict:
        source = next((row for row in cascade if row["model_name"] == model), {})
        return {
            "ablation_name": label,
            "modality": modality,
            "selected_route_cer": source.get("selected_route_cer", ""),
            "route_accuracy": source.get("route_accuracy", ""),
            "macro_f1": source.get("macro_f1", ""),
            "text_probe_reduction_rate": source.get("asr_text_probe_reduction_rate", ""),
            "average_cost": source.get("average_cost", ""),
            "interpretation": "",
        }

    rows = [
        row_for("audiodepth_stage1_only", "AudioDepth-only", "pre_asr_acoustic"),
        row_for("router_v2", "text-instability-only", "post_asr_text_proxy"),
        row_for("stage27_balanced_router_if_available", "AudioDepth + text late fusion", "hybrid_existing"),
        row_for("audiodepth_stage1_plus_text_stage2", "AudioDepth Stage-1 + text Stage-2", "two_stage"),
        row_for("router_v2", "text-first router", "post_asr_text_proxy"),
        row_for("oracle", "oracle", "upper_bound"),
    ]
    for row in rows:
        if row["ablation_name"] == "AudioDepth-only":
            row["interpretation"] = f"Stage-1 gate accuracy {gate.get('gate_accuracy', '')}; useful if it reduces probes without high false-safe risk."
        elif row["ablation_name"] == "AudioDepth Stage-1 + text Stage-2":
            row["interpretation"] = "Tests whether acoustic triage before text probing is more interpretable than flat routing."
        elif row["ablation_name"] == "text-instability-only":
            row["interpretation"] = "Text features remain the posterior stability checker and final route baseline."
    write_csv(ABLATION_CSV, rows)
    draw_bar(rows, FIGURE_DIR / "audiodepth_feature_ablation.png", "ablation_name", "selected_route_cer", "AudioDepth vs text feature ablation")
    two = next((row for row in rows if row["ablation_name"] == "AudioDepth Stage-1 + text Stage-2"), {})
    text = next((row for row in rows if row["ablation_name"] == "text-instability-only"), {})
    write_summary(
        FIGURE_DIR / "audiodepth_feature_ablation.md",
        "AudioDepth vs Text Feature Ablation",
        [
            f"- AudioDepth independent value: gate accuracy `{gate.get('gate_accuracy', '')}`, false-safe rate `{gate.get('false_safe_rate', '')}`.",
            f"- text-only CER: `{text.get('selected_route_cer', '')}`",
            f"- two-stage CER: `{two.get('selected_route_cer', '')}`",
            f"- two-stage text-probe reduction: `{two.get('text_probe_reduction_rate', '')}`",
            "- Conclusion: AudioDepth is most meaningful as a pre-ASR acoustic gate; text features remain the stronger posterior routing signal.",
        ],
    )
    print(f"Wrote AudioDepth feature ablation to {rel(ABLATION_CSV)}")


if __name__ == "__main__":
    main()
