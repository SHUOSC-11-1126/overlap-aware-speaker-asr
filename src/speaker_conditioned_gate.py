"""Speaker-conditioned gate: cure babble-induced separation hallucination (experimental/frontier).

The noise-robust-gate study (`noise_robust_gate.py`, FINDINGS) established that a spectral-flatness
gate recovers the separation-hallucination cure under broadband noise but FAILS under babble: the
residual is speech-like, so flatness carries no signal (measured target-vs-residual AUC 0.56, and a
cheap mel-centroid embedding only 0.52 ~ chance). The synthesis was that babble needs SPEAKER
IDENTITY, not spectral statistics.

This module acts on that. Using a real pretrained speaker embedding (Resemblyzer GE2E, 256-d, whose
weights ship inside the pip wheel so it runs fully offline), a grounding probe measured
target-vs-babble window separability at AUC 0.95 (vs flatness 0.56) — so a speaker-conditioned gate
can crop babble residual where the flatness gate cannot.

Method (still reference-free w.r.t. transcripts/CER; uses only the audio):
  Slide ~1.6 s windows; embed each; estimate the track's dominant-speaker reference embedding from
  the highest-energy windows (the target's own clear speech); keep the contiguous span of windows
  whose cosine similarity to that reference is high (target speech) and crop the low-similarity ends
  (babble residual). The speaker embedder is dependency-injected, so the gate logic is unit-tested
  without resemblyzer, and resemblyzer is imported lazily only in the driver/factory.

Labels: experimental/frontier; references synthetic/silver; ASR Whisper-tiny; speaker embedder is a
documented stronger model (Resemblyzer GE2E, offline). CER post-hoc only. No gold tables touched;
outputs to results/frontier/speaker_conditioned_gate/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .config import PROJECT_ROOT
from .noise_robust_gate import adaptive_flatness_threshold, mask_to_span

WIN = 25600   # 1.6 s @ 16 kHz (>= one GE2E partial frame)
HOP = 8000    # 0.5 s
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "speaker_conditioned_gate"

EmbedFn = Callable[[np.ndarray], np.ndarray]


# ======================================================================================
# Pure logic (no resemblyzer, no Whisper) -- unit tested with an injected fake embedder
# ======================================================================================
def frame_windows(n: int, win: int = WIN, hop: int = HOP) -> list[tuple[int, int]]:
    if n < win:
        return []
    return [(i * hop, i * hop + win) for i in range(1 + (n - win) // hop)]


def window_energies(x: np.ndarray, windows: list[tuple[int, int]]) -> np.ndarray:
    x = np.asarray(x, dtype=np.float32)
    return np.array([float(np.mean(x[s:e] ** 2)) for s, e in windows], dtype=np.float64)


def reference_embedding(embeddings: np.ndarray, energies: np.ndarray, top_frac: float = 0.4) -> np.ndarray:
    """Reference (dominant-speaker) embedding = mean of the embeddings of the top-energy windows
    (the target's own clear speech). Reference-free: uses only window energy, no transcript."""
    embeddings = np.asarray(embeddings, dtype=np.float64)
    energies = np.asarray(energies, dtype=np.float64)
    if embeddings.shape[0] == 0:
        return np.zeros((embeddings.shape[1] if embeddings.ndim == 2 else 0,))
    k = max(1, int(round(top_frac * embeddings.shape[0])))
    top = np.argsort(energies)[-k:]
    return embeddings[top].mean(axis=0)


def cosine_sims(embeddings: np.ndarray, ref: np.ndarray) -> np.ndarray:
    embeddings = np.asarray(embeddings, dtype=np.float64)
    ref = np.asarray(ref, dtype=np.float64)
    if embeddings.shape[0] == 0:
        return np.zeros((0,))
    en = np.linalg.norm(embeddings, axis=1) + 1e-12
    rn = float(np.linalg.norm(ref)) + 1e-12
    return (embeddings @ ref) / (en * rn)


def keep_span_from_sims(sims: np.ndarray, threshold: float) -> tuple[int, int]:
    """Contiguous span of windows whose similarity-to-target is at/above threshold (= speech)."""
    return mask_to_span(np.asarray(sims, dtype=np.float64) >= threshold)


def speaker_gate_trim(
    wav: np.ndarray,
    embed_window: EmbedFn,
    win: int = WIN,
    hop: int = HOP,
    margin_samples: int = 4000,
    top_frac: float = 0.4,
    **thr_kwargs: Any,
) -> np.ndarray:
    """Crop leading/trailing windows that don't match the track's dominant speaker. Falls back to
    the unchanged wav when there is no clear speaker split (all-target, or too short)."""
    x = np.asarray(wav, dtype=np.float32)
    windows = frame_windows(x.size, win, hop)
    if len(windows) < 2:
        return x
    embs = np.array([np.asarray(embed_window(x[s:e]), dtype=np.float64) for s, e in windows])
    sims = cosine_sims(embs, reference_embedding(embs, window_energies(x, windows), top_frac))
    thr = adaptive_flatness_threshold(sims, **thr_kwargs)  # valley between target & residual sims
    if thr is None:
        return x
    span = keep_span_from_sims(sims, thr)
    if span[1] <= span[0]:
        return x
    s = max(0, windows[span[0]][0] - margin_samples)
    e = min(x.size, windows[span[1] - 1][1] + margin_samples)
    if e - s >= x.size:
        return x
    return x[s:e]


# ======================================================================================
# Resemblyzer GE2E embedder (lazy; offline -- weights ship in the wheel)
# ======================================================================================
def resemblyzer_embedder() -> EmbedFn:
    from resemblyzer import VoiceEncoder
    from resemblyzer.audio import normalize_volume

    encoder = VoiceEncoder(verbose=False)

    def embed(w: np.ndarray) -> np.ndarray:
        w = normalize_volume(np.asarray(w, dtype=np.float32), -30, increase_only=False)
        return encoder.embed_utterance(w)

    return embed


# ======================================================================================
# Driver: does the speaker gate cure babble where the flatness gate fails?
# ======================================================================================
ARMS = ["mixed", "sep", "flatness_gate", "speaker_gate"]
NOISE_SNR: list[float] = [10.0, 5.0, 0.0]
OVERLAPS = [0.1, 0.3]


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    keys = sorted({(r["noise_type"], float(r["snr_db"])) for r in rows})
    for ntype, snr in keys:
        at = [r for r in rows if r["noise_type"] == ntype and float(r["snr_db"]) == snr]
        row: dict[str, Any] = {"noise_type": ntype, "snr_db": snr, "n": len(at)}
        for arm in ARMS:
            cers = [float(r[f"cer_{arm}"]) for r in at]
            row[f"mean_cer_{arm}"] = round(float(np.mean(cers)), 6)
            row[f"tail_{arm}"] = round(float(np.mean([c > 1.0 for c in cers])), 6)
        row["speaker_gain_vs_sep"] = round(row["mean_cer_sep"] - row["mean_cer_speaker_gate"], 6)
        row["speaker_gain_vs_flatness"] = round(row["mean_cer_flatness_gate"] - row["mean_cer_speaker_gate"], 6)
        out.append(row)
    return out


def run_babble_cure(out_dir: Path, num_pairs: int, noise_types: list[str]) -> dict[str, Any]:
    import whisper

    from .evaluate_cer import compute_cer
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .noise_robust_gate import add_noise_field, flatness_relenergy_trim, make_noise
    from .separation_tax_phase import SNIPPETS_DIR, select_pairs, transcribe_with_signals

    out_dir.mkdir(parents=True, exist_ok=True)
    plans = select_pairs(num_pairs)
    all_snips = {p.name: read_mono_audio(p).samples for p in sorted(SNIPPETS_DIR.glob("*.wav"))}
    model = whisper.load_model("tiny")
    embed = resemblyzer_embedder()
    print(f"[spk-gate] pairs={len(plans)} types={noise_types} snr={NOISE_SNR}", flush=True)

    def tx(a: np.ndarray) -> str:
        return transcribe_with_signals(model, a, "greedy")["text"]

    rows: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        ref = plan.con_text + plan.pro_text
        babble_src = [v for k, v in all_snips.items() if k not in (plan.con_path.name, plan.pro_path.name)]
        for overlap in OVERLAPS:
            mixed, t1, t2, _ = build_mixture(s1, s2, overlap)
            for kind in noise_types:
                for snr in NOISE_SNR:
                    sd = pi * 137 + int(round(overlap * 100)) + int(snr) * 7 + noise_types.index(kind) * 31
                    mx = add_noise_field(mixed, snr, make_noise(kind, mixed.size, sd, babble_src))
                    n1 = add_noise_field(t1, snr, make_noise(kind, t1.size, sd + 1, babble_src))
                    n2 = add_noise_field(t2, snr, make_noise(kind, t2.size, sd + 2, babble_src))
                    f1, f2 = flatness_relenergy_trim(n1), flatness_relenergy_trim(n2)
                    g1, g2 = speaker_gate_trim(n1, embed, min_gap=0.10), speaker_gate_trim(n2, embed, min_gap=0.10)
                    cer = {
                        "mixed": compute_cer(ref, tx(mx))["cer"],
                        "sep": compute_cer(ref, tx(n1) + tx(n2))["cer"],
                        "flatness_gate": compute_cer(ref, tx(f1) + tx(f2))["cer"],
                        "speaker_gate": compute_cer(ref, tx(g1) + tx(g2))["cer"],
                    }
                    rows.append({
                        "pair_id": pi, "overlap_ratio": overlap, "noise_type": kind, "snr_db": snr,
                        **{f"cer_{a}": round(cer[a], 6) for a in ARMS},
                    })
        print(f"[spk-gate] pair {pi + 1}/{len(plans)} done", flush=True)

    curve = out_dir / "speaker_gate_curve.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    summary = aggregate(rows)
    (out_dir / "speaker_gate_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[spk-gate] wrote {curve} + speaker_gate_summary.json (rows={len(rows)})", flush=True)
    return {"summary": summary, "n_rows": len(rows)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Speaker-conditioned gate babble-cure experiment (frontier).")
    p.add_argument("--pairs", type=int, default=8)
    p.add_argument("--types", type=str, default="babble,white", help="comma-separated noise types")
    p.add_argument("--figure", action="store_true", help="Render the figure from an existing summary and exit.")
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def render_figure(out_dir: Path) -> Path | None:
    """Reproducible figure from speaker_gate_summary.json: per-noise-type CER bars (sep vs
    flatness vs speaker gate) across SNR. Presentation nicety; reads the committed summary."""
    summary_path = out_dir / "speaker_gate_summary.json"
    if not summary_path.exists():
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    types = sorted({r["noise_type"] for r in summary})
    fig, axes = plt.subplots(1, len(types), figsize=(5 * len(types), 4.2), sharey=True)
    if len(types) == 1:
        axes = [axes]
    colors = {"sep": "#999999", "flatness_gate": "#e45756", "speaker_gate": "#4c78a8"}
    for ax, ntype in zip(axes, types):
        rows = sorted([r for r in summary if r["noise_type"] == ntype], key=lambda r: r["snr_db"])
        snrs = [r["snr_db"] for r in rows]
        x = np.arange(len(snrs))
        w = 0.27
        for i, (arm, lab) in enumerate([("sep", "raw sep"), ("flatness_gate", "flatness"), ("speaker_gate", "speaker")]):
            ax.bar(x + (i - 1) * w, [r[f"mean_cer_{arm}"] for r in rows], w, color=colors[arm], label=lab)
        ax.axhline(1.0, color="black", lw=0.8, ls=":")
        ax.set_title(f"{ntype} noise")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{s:g} dB" for s in snrs])
        ax.set_xlabel("input SNR")
        ax.grid(alpha=0.3, axis="y")
    axes[0].set_ylabel("mean separated CER (lower better)")
    axes[0].legend(fontsize=9)
    fig.suptitle("Speaker-conditioned gate cures moderate babble where flatness fails (Whisper-tiny, zh)")
    fig.tight_layout()
    fig_path = out_dir / "speaker_gate.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[spk-gate] wrote {fig_path}", flush=True)
    return fig_path


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    if args.figure:
        render_figure(out_dir)
        return
    run_babble_cure(out_dir, args.pairs, [t.strip() for t in args.types.split(",") if t.strip()])
    render_figure(out_dir)


if __name__ == "__main__":
    main()
