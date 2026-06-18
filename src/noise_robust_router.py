"""Reference-free noise-robust router: mixed vs (separate + speaker-gate), keyed on decoder degeneracy.

Issue #814 (frontier capstone). From #13/#811: across noisy conditions the decision that matters is
separate-vs-mixed by overlap — mixed wins at low overlap, separation+speaker-gate wins at high overlap —
and a large per-utterance ORACLE gap remains that no fixed strategy can take. This builds the router
that tries to take it, keyed ONLY on Whisper decoder degeneracy signals of the candidate
separated+gated output (max_compression_ratio, repetition_count, mean logprob, no_speech_prob) — never CER.

Pre-registered hypotheses (CER post-hoc; signals a-priori):
  H1  the router beats BOTH fixed strategies (always-mixed, always-sep+gate) pooled across the grid.
  H2  it recovers a substantial fraction of the oracle gap with small, stable regret across overlap.
  H3  the degeneracy signal of the gated output tracks the separation tax: high compression-ratio /
      repetition ⇒ separation hallucinated ⇒ the gated arm is worse than mixed ⇒ route to mixed.
  Useful either way: if noise itself inflates compression-ratio so the signal no longer tracks CER,
  that bounds reference-free routing under noise (extends router_v2's validity envelope to the noisy
  regime) — a real negative result.

The routing/evaluation logic is pure and unit-tested offline; the grid collector uses Whisper-tiny +
Resemblyzer (reused from gate_selector/speaker_conditioned_gate). Labels: experimental/frontier;
references synthetic/silver; no gold tables touched. Outputs to results/frontier/noise_robust_router/.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "noise_robust_router"
CR_GUARD = 2.4          # compression-ratio hallucination guard (project-wide: #810/#813)
REP_GUARD = 5           # repetition-count guard
CATASTROPHIC_CER = 1.0
OVERLAPS = [0.0, 0.1, 0.3, 0.6, 0.8]
NOISE_TYPES = ["white", "pink", "babble"]
NOISE_SNR = [10.0, 5.0, 0.0]


# ======================================================================================
# Pure routing + evaluation logic (no Whisper) -- unit tested
# ======================================================================================
def gated_degeneracy(sig1: dict, sig2: dict) -> dict:
    """Aggregate the two separated+gated tracks' decoder signals into one routing signal."""
    return {
        "max_compression_ratio": max(float(sig1.get("max_compression_ratio", 0.0)),
                                     float(sig2.get("max_compression_ratio", 0.0))),
        "repetition_count": int(sig1.get("repetition_count", 0)) + int(sig2.get("repetition_count", 0)),
        "mean_logprob": float(np.mean([float(sig1.get("mean_avg_logprob", 0.0)),
                                       float(sig2.get("mean_avg_logprob", 0.0))])),
        "max_no_speech_prob": max(float(sig1.get("max_no_speech_prob", 0.0)),
                                  float(sig2.get("max_no_speech_prob", 0.0))),
    }


def route(degeneracy: dict, cr_guard: float = CR_GUARD, rep_guard: int = REP_GUARD) -> str:
    """Route a single utterance. If the gated candidate looks degenerate (hallucinated), prefer the
    raw mixture; otherwise take separation + speaker-gate. Reference-free."""
    cr = float(degeneracy.get("max_compression_ratio", 0.0))
    rep = int(degeneracy.get("repetition_count", 0))
    if cr > cr_guard or rep >= rep_guard:
        return "mixed"
    return "separate_gate"


def _pearson(x: list[float], y: list[float]) -> float:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if x.size < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _mean(xs: list[float]) -> float:
    xs = [v for v in xs if isinstance(v, (int, float)) and math.isfinite(v)]
    return round(float(np.mean(xs)), 6) if xs else float("nan")


def _router_cer(row: dict, cr_guard: float, rep_guard: int) -> float:
    choice = route(row, cr_guard, rep_guard)
    return float(row["cer_mixed"]) if choice == "mixed" else float(row["cer_speaker_gate"])


def evaluate(rows: list[dict], cr_guard: float = CR_GUARD, rep_guard: int = REP_GUARD) -> dict:
    """Pooled + per-overlap CER for {always-mixed, always-sep+gate, router, oracle}, regret, oracle-gap
    recovery, and the H1/H2/H3 verdicts. NaN-safe on empty input."""
    def block(rs: list[dict]) -> dict:
        mixed = [float(r["cer_mixed"]) for r in rs]
        gate = [float(r["cer_speaker_gate"]) for r in rs]
        router = [_router_cer(r, cr_guard, rep_guard) for r in rs]
        oracle = [min(float(r["cer_mixed"]), float(r["cer_speaker_gate"])) for r in rs]
        m_mixed, m_gate, m_router, m_oracle = _mean(mixed), _mean(gate), _mean(router), _mean(oracle)
        best_fixed = min([v for v in (m_mixed, m_gate) if math.isfinite(v)], default=float("nan"))
        gap = (best_fixed - m_oracle) if (math.isfinite(best_fixed) and math.isfinite(m_oracle)) else float("nan")
        recovered = round((best_fixed - m_router) / gap, 6) if (math.isfinite(gap) and gap > 1e-9) else float("nan")
        return {
            "n": len(rs),
            "mean_cer_mixed": m_mixed, "mean_cer_speaker_gate": m_gate,
            "mean_cer_router": m_router, "mean_cer_oracle": m_oracle,
            "regret_vs_oracle": round(m_router - m_oracle, 6) if (math.isfinite(m_router) and math.isfinite(m_oracle)) else float("nan"),
            "oracle_gap_recovered": recovered,
            "pearson_cr_vs_gate_minus_mixed": round(_pearson(
                [float(r.get("max_compression_ratio", 0.0)) for r in rs],
                [float(r["cer_speaker_gate"]) - float(r["cer_mixed"]) for r in rs]), 6),
            "router_route_dist": {
                "mixed": sum(1 for r in rs if route(r, cr_guard, rep_guard) == "mixed"),
                "separate_gate": sum(1 for r in rs if route(r, cr_guard, rep_guard) == "separate_gate"),
            },
        }

    pooled = block(rows)
    by_overlap = []
    for ov in sorted({float(r["overlap_ratio"]) for r in rows}):
        b = block([r for r in rows if float(r["overlap_ratio"]) == ov])
        b["overlap_ratio"] = ov
        by_overlap.append(b)

    p = pooled
    h1 = bool(math.isfinite(p["mean_cer_router"]) and math.isfinite(p["mean_cer_mixed"])
              and math.isfinite(p["mean_cer_speaker_gate"])
              and p["mean_cer_router"] < p["mean_cer_mixed"] and p["mean_cer_router"] < p["mean_cer_speaker_gate"])
    h3 = bool(math.isfinite(p["pearson_cr_vs_gate_minus_mixed"]) and p["pearson_cr_vs_gate_minus_mixed"] > 0.1)
    return {
        "pooled": pooled, "by_overlap": by_overlap,
        "cr_guard": cr_guard, "rep_guard": rep_guard,
        "H1_router_beats_both_fixed": h1,
        "H3_degeneracy_tracks_tax": h3,
    }


# ======================================================================================
# Grid collector (Whisper-tiny + Resemblyzer; reuses the gate_selector pipeline) -- lazy
# ======================================================================================
def collect_grid(num_pairs: int, overlaps: list[float], noise_types: list[str], snrs: list[float]) -> list[dict]:
    import whisper

    from .evaluate_cer import compute_cer
    from .gate_selector import residual_window_signal  # reuse, harmless
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .noise_robust_gate import add_noise_field, make_noise
    from .separation_tax_phase import SNIPPETS_DIR, select_pairs, transcribe_with_signals
    from .speaker_conditioned_gate import resemblyzer_embedder, speaker_gate_trim

    plans = select_pairs(num_pairs)
    all_snips = {p.name: read_mono_audio(p).samples for p in sorted(SNIPPETS_DIR.glob("*.wav"))}
    model = whisper.load_model("tiny")
    embed = resemblyzer_embedder()
    print(f"[nrr] pairs={len(plans)} overlaps={overlaps} noise={noise_types} snr={snrs}", flush=True)

    rows: list[dict] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        ref = plan.con_text + plan.pro_text
        babble_src = [v for k, v in all_snips.items() if k not in (plan.con_path.name, plan.pro_path.name)]
        for overlap in overlaps:
            mixed, t1, t2, _ = build_mixture(s1, s2, overlap)
            for kind in noise_types:
                for snr in snrs:
                    sd = pi * 137 + int(round(overlap * 100)) + int(snr) * 7 + noise_types.index(kind) * 31
                    mx = add_noise_field(mixed, snr, make_noise(kind, mixed.size, sd, babble_src))
                    n1 = add_noise_field(t1, snr, make_noise(kind, t1.size, sd + 1, babble_src))
                    n2 = add_noise_field(t2, snr, make_noise(kind, t2.size, sd + 2, babble_src))
                    g1, g2 = speaker_gate_trim(n1, embed, min_gap=0.10), speaker_gate_trim(n2, embed, min_gap=0.10)
                    sig_mx = transcribe_with_signals(model, mx, "greedy")
                    sig_g1 = transcribe_with_signals(model, g1, "greedy")
                    sig_g2 = transcribe_with_signals(model, g2, "greedy")
                    deg = gated_degeneracy(sig_g1, sig_g2)
                    rows.append({
                        "pair_id": pi, "overlap_ratio": overlap, "noise_type": kind, "snr_db": snr,
                        "cer_mixed": round(compute_cer(ref, sig_mx["text"])["cer"], 6),
                        "cer_speaker_gate": round(compute_cer(ref, sig_g1["text"] + sig_g2["text"])["cer"], 6),
                        "max_compression_ratio": round(deg["max_compression_ratio"], 4),
                        "repetition_count": deg["repetition_count"],
                        "mean_logprob": round(deg["mean_logprob"], 4),
                        "max_no_speech_prob": round(deg["max_no_speech_prob"], 4),
                    })
        print(f"[nrr] pair {pi + 1}/{len(plans)} done", flush=True)
    return rows


def run(num_pairs: int = 6, overlaps: list[float] | None = None, noise_types: list[str] | None = None,
        snrs: list[float] | None = None, out_dir: Path | str = OUT_DIR, rows: list[dict] | None = None) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = rows if rows is not None else collect_grid(
        num_pairs, overlaps or OVERLAPS, noise_types or NOISE_TYPES, snrs or NOISE_SNR)
    if not rows:
        raise RuntimeError("no rows collected")

    result = evaluate(rows)
    _write_csv(rows, out_dir / "router_curve.csv")
    (out_dir / "summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_findings(result, out_dir / "FINDINGS.md")
    _plot(result, out_dir / "noise_robust_router.png")
    p = result["pooled"]
    print(f"[nrr] router={p['mean_cer_router']} mixed={p['mean_cer_mixed']} gate={p['mean_cer_speaker_gate']} "
          f"oracle={p['mean_cer_oracle']} H1={result['H1_router_beats_both_fixed']} "
          f"H3={result['H3_degeneracy_tracks_tax']} (rows={len(rows)})", flush=True)
    return out_dir


def _write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _fmt(x: Any) -> str:
    if isinstance(x, float):
        return "nan" if math.isnan(x) else f"{x:.4f}"
    return str(x)


def _write_findings(s: dict, path: Path) -> None:
    p = s["pooled"]
    lines = [
        "# Reference-Free Noise-Robust Router — Findings",
        "",
        "**Label:** `experimental/frontier`. ASR Whisper-`tiny`; Resemblyzer speaker gate; references "
        "synthetic/silver; routing signals reference-free (decoder degeneracy of the gated output); CER "
        "post-hoc only; no gold tables touched. Issue #814.",
        "",
        f"Router: take separation+speaker-gate unless the gated output is degenerate "
        f"(max_compression_ratio > {s['cr_guard']} or repetition ≥ {s['rep_guard']}), else fall back to mixed.",
        "",
        "## Pooled CER (lower is better)",
        "",
        f"- always-mixed: {_fmt(p['mean_cer_mixed'])}",
        f"- always-(sep+speaker-gate): {_fmt(p['mean_cer_speaker_gate'])}",
        f"- **router (this work): {_fmt(p['mean_cer_router'])}**",
        f"- per-utterance oracle: {_fmt(p['mean_cer_oracle'])}",
        f"- regret vs oracle: {_fmt(p['regret_vs_oracle'])}; oracle-gap recovered: {_fmt(p['oracle_gap_recovered'])}",
        f"- route distribution: {p['router_route_dist']}",
        "",
        "## Hypotheses",
        "",
        f"- **H1 — router beats both fixed strategies:** router {_fmt(p['mean_cer_router'])} vs "
        f"always-mixed {_fmt(p['mean_cer_mixed'])} / always-gate {_fmt(p['mean_cer_speaker_gate'])}. "
        f"Verdict: **{'SUPPORTED' if s['H1_router_beats_both_fixed'] else 'NOT supported'}**.",
        f"- **H3 — degeneracy tracks the separation tax:** Pearson(compression_ratio, gate−mixed CER) = "
        f"{_fmt(p['pearson_cr_vs_gate_minus_mixed'])}. Verdict: "
        f"**{'SUPPORTED' if s['H3_degeneracy_tracks_tax'] else 'NOT supported'}** "
        "(positive ⇒ high CR predicts the gated arm is worse ⇒ correctly route to mixed).",
        "",
        "## CER by overlap (mixed / gate / router / oracle)",
        "",
        "| overlap | n | mixed | sep+gate | router | oracle |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for b in s["by_overlap"]:
        lines.append(f"| {b['overlap_ratio']} | {b['n']} | {_fmt(b['mean_cer_mixed'])} | "
                     f"{_fmt(b['mean_cer_speaker_gate'])} | {_fmt(b['mean_cer_router'])} | {_fmt(b['mean_cer_oracle'])} |")
    lines += [
        "",
        "## Honest limitations",
        "",
        "Small grid; Whisper-`tiny`; synthetic oracle separation + synthetic white/pink/babble (real "
        "babble differs); Resemblyzer speaker gate. The routing signal is the gated output's decoder "
        "degeneracy; if additive noise itself inflates compression-ratio, the signal stops tracking the "
        "separation tax (the H3 bound). `experimental/frontier`, not a gold result.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plot(s: dict, path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    by = s["by_overlap"]
    if not by:
        return
    ov = [b["overlap_ratio"] for b in by]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for key, lab, style in [("mean_cer_mixed", "always-mixed", "o--"), ("mean_cer_speaker_gate", "always-sep+gate", "s--"),
                            ("mean_cer_router", "router", "D-"), ("mean_cer_oracle", "oracle", "^:")]:
        ax.plot(ov, [b[key] for b in by], style, label=lab)
    ax.set_xlabel("overlap ratio"); ax.set_ylabel("mean CER")
    ax.set_title("Noise-robust router: mixed vs sep+speaker-gate by overlap (#814)")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Reference-free noise-robust router (issue #814)")
    p.add_argument("--pairs", type=int, default=6)
    p.add_argument("--overlaps", type=str, default="0.0,0.1,0.3,0.6,0.8")
    p.add_argument("--noise", type=str, default="white,pink,babble")
    p.add_argument("--snr", type=str, default="10,5,0")
    p.add_argument("--output-dir", type=str, default=str(OUT_DIR))
    return p.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    run(num_pairs=args.pairs,
        overlaps=[float(o) for o in args.overlaps.split(",") if o.strip()],
        noise_types=[n for n in args.noise.split(",") if n.strip()],
        snrs=[float(x) for x in args.snr.split(",") if x.strip()],
        out_dir=args.output_dir)
    print("[nrr] done")


if __name__ == "__main__":
    main()
