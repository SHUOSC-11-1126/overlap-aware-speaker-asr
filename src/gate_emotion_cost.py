"""Do the CER-tuned hallucination-cure gates damage emotion? (experimental/frontier)

The closing loop of the emotion frontier. Findings #11–#13 built gates (spectral-flatness, speaker-
conditioned) that cure separation-induced Whisper hallucination under noise — all tuned to lower CER.
But a gate cures CER by CROPPING audio, and #14 showed emotion lives in regions a CER-blind decision can
discard. So: do these CER-tuned cures have a hidden EMOTION cost?

For each separated track under babble (where the gates fire, #12), we measure both axes against the
clean source:
  - CER benefit  = CER(raw separated) - CER(gated)      (>0: the gate cures hallucination)
  - emotion cost = prosody_dist(gated) - prosody_dist(raw)   (>0: the gate moved prosody away from
                   the clean source, i.e. it damaged emotion; gain-invariant prosody, src/prosody.py)

Falsifiable: a gate with a positive mean CER benefit AND a positive mean emotion cost is objective-
blind — it trades emotion for text, extending the #14 "objective-dependent" thesis to the cures
themselves. If emotion cost ~0, the gates are emotion-safe (also useful to know).

Offline; reuses the #11/#12 gates + src/prosody.py. Whisper-tiny for CER. Labels: experimental/
frontier; references synthetic/silver. No gold tables touched. Outputs to
results/frontier/gate_emotion_cost/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "gate_emotion_cost"
OVERLAPS = [0.1, 0.3]
SNRS = [10.0, 5.0]
GATES = ["flatness", "speaker"]


# ======================================================================================
# Pure aggregation (no Whisper/librosa) -- unit tested
# ======================================================================================
def aggregate_gate_cost(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-gate mean CER benefit (cer_raw - cer_gated) and mean emotion cost (dist_gated - dist_raw),
    plus the per-row trade-off correlation. CER/distortions are post-hoc."""
    by_gate = []
    for gate in sorted({r["gate"] for r in rows}):
        at = [r for r in rows if r["gate"] == gate]
        benefits = [float(r["cer_raw"]) - float(r["cer_gated"]) for r in at]
        costs = [float(r["dist_gated"]) - float(r["dist_raw"]) for r in at]
        row: dict[str, Any] = {
            "gate": gate, "n": len(at),
            "mean_cer_benefit": round(float(np.mean(benefits)), 6),
            "mean_emotion_cost": round(float(np.mean(costs)), 6),
        }
        if len(at) > 1 and np.std(benefits) > 0 and np.std(costs) > 0:
            row["pearson_benefit_cost"] = round(float(np.corrcoef(benefits, costs)[0, 1]), 6)
        else:
            row["pearson_benefit_cost"] = float("nan")
        by_gate.append(row)
    return {"n": len(rows), "by_gate": by_gate}


# ======================================================================================
# Whisper + librosa + resemblyzer driver
# ======================================================================================
def run_gate_emotion_cost(out_dir: Path, num_pairs: int, overlaps: list[float], snrs: list[float]) -> dict[str, Any]:
    import whisper

    from .emotion_separation_tax import active_region
    from .evaluate_cer import compute_cer
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .noise_robust_gate import add_noise_field, flatness_relenergy_trim, make_noise
    from .prosody import prosodic_features, prosody_distance
    from .separation_tax_phase import SNIPPETS_DIR, select_pairs, transcribe_with_signals
    from .speaker_conditioned_gate import resemblyzer_embedder, speaker_gate_trim

    out_dir.mkdir(parents=True, exist_ok=True)
    plans = select_pairs(num_pairs)
    all_snips = {p.name: read_mono_audio(p).samples for p in sorted(SNIPPETS_DIR.glob("*.wav"))}
    model = whisper.load_model("tiny")
    embed = resemblyzer_embedder()
    print(f"[gate-emo] pairs={len(plans)} overlaps={overlaps} snrs={snrs} (babble)", flush=True)

    def tx(a: np.ndarray) -> str:
        return transcribe_with_signals(model, np.asarray(a, dtype=np.float32), "greedy")["text"]

    def dist_to_clean(track: np.ndarray, region: tuple[int, int], ref_feat: dict[str, float]) -> float:
        s, e = region
        seg = track[s:e] if e > s and e <= track.size else track
        return prosody_distance(ref_feat, prosodic_features(seg))["emotional_distortion"]

    rows: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        babble_src = [v for k, v in all_snips.items() if k not in (plan.con_path.name, plan.pro_path.name)]
        for overlap in overlaps:
            _, t1, t2, _ = build_mixture(s1, s2, overlap)
            for (tk, ref_text) in ((t1, plan.con_text), (t2, plan.pro_text)):
                region = active_region(tk)
                ref_feat = prosodic_features(tk[region[0]:region[1]])
                for snr in snrs:
                    sd = pi * 131 + int(round(overlap * 100)) + int(snr) * 7
                    nz = add_noise_field(tk, snr, make_noise("babble", tk.size, sd, babble_src))
                    cer_raw = compute_cer(ref_text, tx(nz))["cer"]
                    dist_raw = dist_to_clean(nz, region, ref_feat)
                    gated = {"flatness": flatness_relenergy_trim(nz),
                             "speaker": speaker_gate_trim(nz, embed, min_gap=0.10)}
                    for gate, g in gated.items():
                        # gated track may be shorter; emotion distortion on the gated track as-is
                        cer_g = compute_cer(ref_text, tx(g))["cer"]
                        dist_g = prosody_distance(ref_feat, prosodic_features(g))["emotional_distortion"]
                        rows.append({
                            "pair_id": pi, "overlap_ratio": overlap, "snr_db": snr, "gate": gate,
                            "cer_raw": round(cer_raw, 6), "cer_gated": round(cer_g, 6),
                            "dist_raw": round(float(dist_raw), 6), "dist_gated": round(float(dist_g), 6),
                            "fired": int(g.size < nz.size),
                        })
        print(f"[gate-emo] pair {pi + 1}/{len(plans)} done", flush=True)

    curve = out_dir / "gate_emotion_curve.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summary = aggregate_gate_cost(rows)
    (out_dir / "gate_emotion_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    for g in summary["by_gate"]:
        print(f"[gate-emo] {g['gate']}: CER benefit={g['mean_cer_benefit']} emotion cost={g['mean_emotion_cost']} "
              f"(corr={g['pearson_benefit_cost']})", flush=True)
    try:
        render_figure(out_dir, summary)
    except Exception as exc:
        print(f"[gate-emo] figure skipped: {exc}", flush=True)
    print(f"[gate-emo] wrote {curve} + gate_emotion_summary.json (rows={len(rows)})", flush=True)
    return {"summary": summary, "n_rows": len(rows)}


def render_figure(out_dir: Path, summary: dict[str, Any]) -> Path | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by = summary["by_gate"]
    gates = [g["gate"] for g in by]
    x = np.arange(len(gates))
    fig, ax = plt.subplots(figsize=(7, 4.6))
    w = 0.35
    ax.bar(x - w / 2, [g["mean_cer_benefit"] for g in by], w, color="#4c78a8", label="CER benefit (cure)")
    ax.bar(x + w / 2, [g["mean_emotion_cost"] for g in by], w, color="#e45756", label="emotion cost (damage)")
    ax.axhline(0.0, color="black", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(gates)
    ax.set_ylabel("Δ vs raw separated")
    ax.set_title("Do CER-tuned gate cures damage emotion? (babble, Whisper-tiny, zh)")
    ax.legend(fontsize=9); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig_path = out_dir / "gate_emotion_cost.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[gate-emo] wrote {fig_path}", flush=True)
    return fig_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Emotion cost of CER-tuned hallucination-cure gates (frontier).")
    p.add_argument("--pairs", type=int, default=8)
    p.add_argument("--overlaps", type=str, default="0.1,0.3")
    p.add_argument("--snrs", type=str, default="10,5")
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    run_gate_emotion_cost(Path(args.out_dir), args.pairs,
                          [float(o) for o in args.overlaps.split(",") if o.strip()],
                          [float(s) for s in args.snrs.split(",") if s.strip()])


if __name__ == "__main__":
    main()
