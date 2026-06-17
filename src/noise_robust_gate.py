"""Noise-robust speech gate: a separation-hallucination cure that survives noise (frontier).

Pre-registered research question (extends Separation-Tax RQ3 and the noise-robustness map):
  Prior frontier work established a chain of findings:
    1. Speech separation HELPS Whisper at no/heavy/opposite overlap but HURTS at light/mid
       overlap, via a heavy-tailed hallucination phenomenon: a separated track left with a
       long low-information region (where the other talker used to be) drives Whisper into
       a catastrophic CER > 1 loop (separation_tax_phase.py).
    2. In CLEAN audio an energy-based leading/trailing silence trim cures that tail
       (hallucination_cure_eval.py: catastrophic-group CER 19.84 -> 0.54, tail_rate -> 0).
    3. But noise DEFEATS the cure (noise_robustness.py, #806): at every noisy SNR the
       trimmed and untrimmed separated CERs were identical (trim_gain_vs_sep == 0.0). The
       trim is energy-based; additive noise fills the "silent" region above the amplitude
       threshold, so `trim_silence` stops cropping and the hallucination tail returns.

  RQ (this module): The energy trim dies because amplitude is not noise-robust. Spectral
  FLATNESS is: broadband noise is spectrally flat (flatness -> high), voiced speech is
  peaky/harmonic (flatness -> low), and the contrast survives well into low SNR (a grounding
  probe measured speech-vs-residual ranking AUC 0.999 clean -> 0.765 at 0 dB). Can a
  flatness-gated trim re-fire under noise where the energy trim cannot, and recover (some of)
  the separation-hallucination cure that #806 showed noise destroys?

  H1: Under noise the energy trim fires on ~0% of tracks (keeps ~100% of samples) while the
      flatness gate keeps firing.
  H2: At moderate noise (5-20 dB) the flatness gate lowers mean separated CER and the
      catastrophic tail rate relative to both raw separation and energy-trim; the advantage
      narrows toward 0 dB as the flatness contrast collapses.
  Useful-either-way: if the flatness gate does NOT help at the lowest SNR, that bounds where
  any reference-free silence cure can work and argues for routing to the mixed input there.

Design (all reference-free; CER is post-hoc evaluation only, never a gate/routing input):
  Frame the track (25 ms / 10 ms), compute per-frame spectral flatness, find an ADAPTIVE
  threshold in the valley of the (speech-low, noise-high) flatness distribution, and crop to
  the contiguous low-flatness (speech-like) span -- a drop-in replacement for the energy-based
  `trim_silence`. A second variant additionally rescues frames whose energy exceeds the
  estimated noise floor (noise-floor-RELATIVE energy, unlike the absolute `trim_silence`).

Labels: experimental/frontier; references are synthetic/silver (Whisper-small on clean
snippets); ASR = Whisper-tiny (only model cached offline). Stable/gold tables are NOT touched;
all outputs go to results/frontier/noise_robust_gate/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT

SR = 16000
WIN = 400   # 25 ms @ 16 kHz
HOP = 160   # 10 ms @ 16 kHz
CATASTROPHIC_CER = 1.0
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "noise_robust_gate"


# ======================================================================================
# Pure primitives (no Whisper, no audio I/O) -- unit tested in tests/test_noise_robust_gate.py
# ======================================================================================
def frame_signal(x: np.ndarray, win: int = WIN, hop: int = HOP) -> np.ndarray:
    """Split a 1-D signal into overlapping frames -> (n_frames, win). Returns (0, win) if the
    signal is shorter than one frame."""
    x = np.asarray(x, dtype=np.float32)
    if x.size < win:
        return np.zeros((0, win), dtype=np.float32)
    n = 1 + (x.size - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    return x[idx]


def spectral_flatness(frames: np.ndarray, window: bool = True) -> np.ndarray:
    """Per-frame spectral flatness (Wiener entropy) = geometric_mean(PSD) / arithmetic_mean(PSD)
    in [0, 1]. ->0 for a peaky/harmonic spectrum (voiced speech), ->1 for a flat spectrum
    (broadband noise). An all-zero frame has no structure and returns ~1.0 (reads as non-speech,
    so true silence is cropped like noise)."""
    if frames.shape[0] == 0:
        return np.zeros((0,), dtype=np.float64)
    win = frames.shape[1]
    w = np.hanning(win).astype(np.float32) if window else np.ones(win, dtype=np.float32)
    psd = np.abs(np.fft.rfft(frames * w, axis=1)) ** 2 + 1e-10
    gm = np.exp(np.mean(np.log(psd), axis=1))
    am = np.mean(psd, axis=1)
    return np.clip(gm / am, 0.0, 1.0)


def track_flatness(x: np.ndarray, win: int = WIN, hop: int = HOP) -> np.ndarray:
    return spectral_flatness(frame_signal(x, win, hop))


def adaptive_flatness_threshold(
    flatness: np.ndarray,
    lo_pct: float = 20.0,
    hi_pct: float = 80.0,
    gate_frac: float = 0.5,
    min_gap: float = 0.15,
) -> float | None:
    """Place a threshold in the valley between the speech (low-flatness) and noise/silence
    (high-flatness) clusters. Returns None when the distribution is unimodal (gap < min_gap):
    that means there is no clear noise-only region to crop (all-speech or all-noise), so the
    caller should abstain and keep the track unchanged."""
    fl = np.asarray(flatness, dtype=np.float64)
    fl = fl[np.isfinite(fl)]
    if fl.size == 0:
        return None
    lo = float(np.percentile(fl, lo_pct))
    hi = float(np.percentile(fl, hi_pct))
    if (hi - lo) < min_gap:
        return None
    return lo + gate_frac * (hi - lo)


def flatness_speech_mask(flatness: np.ndarray, threshold: float) -> np.ndarray:
    """Speech-like frames have flatness at/below threshold."""
    return np.asarray(flatness, dtype=np.float64) <= threshold


def frame_energy(frames: np.ndarray) -> np.ndarray:
    if frames.shape[0] == 0:
        return np.zeros((0,), dtype=np.float64)
    return np.mean(np.asarray(frames, dtype=np.float64) ** 2, axis=1)


def relenergy_speech_mask(frames: np.ndarray, floor_pct: float = 20.0, factor: float = 3.0) -> np.ndarray:
    """Frames whose energy exceeds factor x the estimated noise floor (the low-percentile
    frame energy). Noise-floor-RELATIVE -- unlike absolute trim_silence it adapts to the noise
    level, so it keeps discriminating speech from residual as the floor rises with noise."""
    e = frame_energy(frames)
    if e.size == 0:
        return np.zeros((0,), dtype=bool)
    floor = float(np.percentile(e, floor_pct)) + 1e-12
    return e > factor * floor


def mask_to_span(mask: np.ndarray) -> tuple[int, int]:
    """(first True, last True + 1) -- the contiguous span to keep. (0, 0) if no True frame."""
    idx = np.nonzero(np.asarray(mask, dtype=bool))[0]
    if idx.size == 0:
        return (0, 0)
    return (int(idx[0]), int(idx[-1]) + 1)


def _span_frames_to_samples(
    span: tuple[int, int], hop: int, win: int, n_samples: int, margin: int
) -> tuple[int, int] | None:
    sf, ef = span
    if ef <= sf:
        return None
    start = max(0, sf * hop - margin)
    end = min(n_samples, (ef - 1) * hop + win + margin)
    if end <= start:
        return None
    return (start, end)


def _gate_trim(track: np.ndarray, mask_fn, win: int, hop: int, margin_samples: int) -> np.ndarray:
    """Shared crop machinery: build a speech mask via mask_fn(frames, flatness), keep the
    contiguous span + margin. Falls back to the unchanged track when there is nothing to crop."""
    x = np.asarray(track, dtype=np.float32)
    frames = frame_signal(x, win, hop)
    if frames.shape[0] == 0:
        return x
    flatness = spectral_flatness(frames)
    mask = mask_fn(frames, flatness)
    if mask is None:
        return x
    span = mask_to_span(mask)
    samples = _span_frames_to_samples(span, hop, win, x.size, margin_samples)
    if samples is None:
        return x
    s, e = samples
    if e - s >= x.size:
        return x
    return x[s:e]


def flatness_trim(
    track: np.ndarray,
    win: int = WIN,
    hop: int = HOP,
    margin_samples: int = 1600,
    **thr_kwargs: Any,
) -> np.ndarray:
    """Crop leading/trailing low-information (high-flatness) regions using an adaptive
    spectral-flatness threshold. Drop-in replacement for the energy-based `trim_silence`,
    but noise-robust."""
    def mask_fn(frames: np.ndarray, flatness: np.ndarray):
        thr = adaptive_flatness_threshold(flatness, **thr_kwargs)
        if thr is None:
            return None
        return flatness_speech_mask(flatness, thr)

    return _gate_trim(track, mask_fn, win, hop, margin_samples)


def flatness_relenergy_trim(
    track: np.ndarray,
    win: int = WIN,
    hop: int = HOP,
    margin_samples: int = 1600,
    floor_pct: float = 20.0,
    energy_factor: float = 3.0,
    **thr_kwargs: Any,
) -> np.ndarray:
    """Like `flatness_trim`, but a frame counts as speech if it is low-flatness OR its energy
    exceeds the estimated noise floor. The union widens the kept span (conservative: only crops
    frames that are confidently BOTH flat AND quiet)."""
    def mask_fn(frames: np.ndarray, flatness: np.ndarray):
        thr = adaptive_flatness_threshold(flatness, **thr_kwargs)
        flat_mask = flatness_speech_mask(flatness, thr) if thr is not None else np.zeros(flatness.shape[0], dtype=bool)
        energy_mask = relenergy_speech_mask(frames, floor_pct, energy_factor)
        return flat_mask | energy_mask

    return _gate_trim(track, mask_fn, win, hop, margin_samples)


# ======================================================================================
# Pure aggregation (unit tested)
# ======================================================================================
ARMS = ["mixed", "sep", "energy_trim", "flatness_gate", "flatness_relenergy_gate"]


def _tail_rate(cers: list[float], threshold: float = CATASTROPHIC_CER) -> float:
    vals = [c for c in cers if c == c]
    return sum(1 for c in vals if c > threshold) / len(vals) if vals else 0.0


def aggregate_by_snr(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-SNR mean CER + catastrophic tail rate for each arm, plus the headline deltas:
    flatness_gate gain vs raw separation and vs the (noise-defeated) energy trim, and the
    fraction of tracks each gate actually cropped."""
    def snr_key(r: dict[str, Any]) -> float:
        v = r.get("snr_db")
        return -1.0 if v in ("", "None", None, "clean") else float(v)

    out: list[dict[str, Any]] = []
    for snr in sorted({snr_key(r) for r in rows}):
        at = [r for r in rows if snr_key(r) == snr]
        cer = {arm: [float(r[f"cer_{arm}"]) for r in at if r.get(f"cer_{arm}", "") not in ("", None)] for arm in ARMS}
        row: dict[str, Any] = {"snr_db": "clean" if snr == -1.0 else snr, "n": len(at)}
        for arm in ARMS:
            row[f"mean_cer_{arm}"] = round(float(np.mean(cer[arm])), 6) if cer[arm] else 0.0
            row[f"tail_{arm}"] = round(_tail_rate(cer[arm]), 6)
        row["flatness_gain_vs_sep"] = round(row["mean_cer_sep"] - row["mean_cer_flatness_gate"], 6)
        row["flatness_gain_vs_energytrim"] = round(row["mean_cer_energy_trim"] - row["mean_cer_flatness_gate"], 6)
        row["energytrim_gain_vs_sep"] = round(row["mean_cer_sep"] - row["mean_cer_energy_trim"], 6)
        for gate in ("energy_trim", "flatness_gate", "flatness_relenergy_gate"):
            fired = [float(r[f"fired_{gate}"]) for r in at if r.get(f"fired_{gate}", "") not in ("", None)]
            row[f"fire_rate_{gate}"] = round(float(np.mean(fired)), 6) if fired else 0.0
        out.append(row)
    return out


# Whisper's default compression_ratio_threshold (a degeneracy signal), reused as the
# reference-free guard. Mirrors separation_tax_phase.GUARD_THRESHOLD -- chosen a priori,
# NOT tuned on CER, so no reference leakage enters the routing decision.
GUARD_THRESHOLD = 2.4


def selective_gate_policy(
    rows: list[dict[str, Any]],
    threshold: float = GUARD_THRESHOLD,
    gate_arm: str = "flatness_relenergy_gate",
) -> dict[str, Any]:
    """Reference-free SELECTIVE gating. The noise-robust gate helps the catastrophic minority
    but slightly over-crops the healthy majority, so apply it only when the raw separated
    tracks look degenerate: max(compression_ratio) > threshold. Compares always_sep /
    always_gate / guard_gated / oracle(min). Routing uses ONLY the reference-free CR signal;
    CER scores the outcome and is never a routing input."""
    sep, gate, guard, oracle = [], [], [], []
    fired = 0
    for r in rows:
        if r.get("cr_sep1") in (None, "") or r.get(f"cer_{gate_arm}") in (None, ""):
            continue
        cs, cg = float(r["cer_sep"]), float(r[f"cer_{gate_arm}"])
        cr = max(float(r["cr_sep1"]), float(r["cr_sep2"]))
        use_gate = cr > threshold
        fired += int(use_gate)
        sep.append(cs)
        gate.append(cg)
        guard.append(cg if use_gate else cs)
        oracle.append(min(cs, cg))
    n = len(sep)

    def m(x: list[float]) -> float:
        return round(sum(x) / len(x), 6) if x else 0.0

    def tail(x: list[float]) -> float:
        return round(sum(1 for c in x if c > CATASTROPHIC_CER) / len(x), 6) if x else 0.0

    means = {"always_sep": m(sep), "always_gate": m(gate), "guard_gated": m(guard), "oracle": m(oracle)}
    return {
        "n": n,
        "threshold": threshold,
        "gate_arm": gate_arm,
        "guard_fired_frac": round(fired / n, 6) if n else 0.0,
        "mean_cer": means,
        "tail_rate": {"always_sep": tail(sep), "always_gate": tail(gate),
                      "guard_gated": tail(guard), "oracle": tail(oracle)},
        "regret_vs_oracle": {k: round(v - means["oracle"], 6) for k, v in means.items() if k != "oracle"},
    }


# ======================================================================================
# Whisper-dependent driver
# ======================================================================================
def run(out_dir: Path, num_pairs: int, overlaps: list[float], snr_levels: list[float | None]) -> dict[str, Any]:
    import whisper

    from .evaluate_cer import compute_cer
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .noise_robustness import add_noise, _seed
    from .separation_tax_phase import select_pairs, transcribe_with_signals, trim_silence

    out_dir.mkdir(parents=True, exist_ok=True)
    plans = select_pairs(num_pairs)
    model = whisper.load_model("tiny")
    print(f"[gate] pairs={len(plans)} overlaps={len(overlaps)} snr={len(snr_levels)} arms={len(ARMS)}", flush=True)

    def tx(audio: np.ndarray) -> str:
        return transcribe_with_signals(model, audio, "greedy")["text"]

    rows: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        ref = plan.con_text + plan.pro_text
        for overlap in overlaps:
            mixed, t1, t2, _ = build_mixture(s1, s2, overlap)
            for snr in snr_levels:
                mx = add_noise(mixed, snr, _seed(pi, overlap, snr, 0))
                n1 = add_noise(t1, snr, _seed(pi, overlap, snr, 1))
                n2 = add_noise(t2, snr, _seed(pi, overlap, snr, 2))
                gates = {
                    "energy_trim": trim_silence,
                    "flatness_gate": flatness_trim,
                    "flatness_relenergy_gate": flatness_relenergy_trim,
                }
                # raw separated -- capture the reference-free degeneracy guard signal too
                o1 = transcribe_with_signals(model, n1, "greedy")
                o2 = transcribe_with_signals(model, n2, "greedy")
                cer = {
                    "mixed": compute_cer(ref, tx(mx))["cer"],
                    "sep": compute_cer(ref, o1["text"] + o2["text"])["cer"],
                }
                fired: dict[str, int] = {}
                for name, fn in gates.items():
                    g1, g2 = fn(n1), fn(n2)
                    fired[name] = int(g1.size < n1.size or g2.size < n2.size)
                    cer[name] = compute_cer(ref, tx(g1) + tx(g2))["cer"]
                row = {
                    "pair_id": pi, "overlap_ratio": overlap,
                    "snr_db": "None" if snr is None else snr,
                    "cr_sep1": round(o1["max_compression_ratio"], 4),
                    "cr_sep2": round(o2["max_compression_ratio"], 4),
                    **{f"cer_{a}": round(cer[a], 6) for a in ARMS},
                    **{f"fired_{g}": fired[g] for g in gates},
                }
                rows.append(row)
        print(f"[gate] pair {pi + 1}/{len(plans)} done", flush=True)

    curve = out_dir / "gate_curve.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    grid = aggregate_by_snr(rows)
    (out_dir / "gate_summary.json").write_text(json.dumps(grid, ensure_ascii=False, indent=2), encoding="utf-8")
    noisy = [r for r in rows if r["snr_db"] not in ("None", "clean")]
    selective = selective_gate_policy(noisy)
    (out_dir / "selective_policy.json").write_text(json.dumps(selective, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[gate] wrote {curve} + gate_summary.json (rows={len(rows)})", flush=True)
    print(f"[gate] selective guard-gated mean_cer={selective['mean_cer']} fired={selective['guard_fired_frac']}", flush=True)
    try:
        render_figure(out_dir, grid)
    except Exception as exc:  # figure is a presentation nicety; never fail the run on it
        print(f"[gate] figure skipped: {exc}", flush=True)
    return {"grid": grid, "n_rows": len(rows)}


def render_figure(out_dir: Path, grid: list[dict[str, Any]]) -> Path | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    order = sorted(grid, key=lambda g: (g["snr_db"] == "clean", g["snr_db"] if g["snr_db"] != "clean" else 1e9))
    labels = [str(g["snr_db"]) for g in order]
    x = np.arange(len(order))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 8), sharex=True)
    styles = {
        "sep": ("#999999", "raw separation"),
        "energy_trim": ("#e45756", "energy trim (#806 cure)"),
        "flatness_gate": ("#4c78a8", "flatness gate (this work)"),
        "flatness_relenergy_gate": ("#54a24b", "flatness + rel-energy"),
    }
    for arm, (c, lab) in styles.items():
        ax1.plot(x, [g[f"mean_cer_{arm}"] for g in order], "-o", color=c, label=lab)
        ax2.plot(x, [g[f"tail_{arm}"] for g in order], "-s", color=c, label=lab)
    ax1.set_ylabel("mean separated CER (lower better)")
    ax1.set_title("Noise-robust gate vs the noise-defeated energy trim (Whisper-tiny, zh)")
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)
    ax2.set_ylabel("catastrophic tail rate\nP(CER > 1.0)")
    ax2.set_xlabel("input SNR (dB)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig_path = out_dir / "noise_robust_gate.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[gate] wrote {fig_path}", flush=True)
    return fig_path


DEFAULT_OVERLAPS = [0.0, 0.1, 0.3, 0.6]
DEFAULT_SNR: list[float | None] = [None, 20.0, 10.0, 5.0, 0.0]


def run_gold_noisy(out_dir: Path, snr_levels: list[float | None]) -> dict[str, Any]:
    """External-validity transfer check: do the gates that help on synthetic oracle mixtures
    still help on a REAL separator's output once noise is added? Uses the actual separated
    audio in resources/separated_audio and the 5 verified gold references, noise-injected at
    each SNR. ASR = Whisper-tiny, so these CERs are NOT comparable to the whisper-small gold
    table; only the relative arms (sep / energy_trim / flatness gates) are compared, and the
    gold tables are not touched. Emits the same row schema as run() so aggregate_by_snr applies."""
    import whisper

    from .config import load_config
    from .evaluate_cer import compute_cer, list_verified_cases, load_reference
    from .generate_synthetic_overlap import read_mono_audio
    from .noise_robustness import add_noise, _seed
    from .separation_tax_phase import transcribe_with_signals, trim_silence

    cfg = load_config()
    mixed_dir = PROJECT_ROOT / cfg["paths"]["mixed_audio_dir"]
    sep_dir = PROJECT_ROOT / cfg["paths"]["separated_audio_dir"]
    cases_by_id = {c["id"]: c for c in cfg.get("audio_cases", [])}
    out_dir.mkdir(parents=True, exist_ok=True)
    model = whisper.load_model("tiny")

    def tx(audio: np.ndarray) -> str:
        return transcribe_with_signals(model, audio, "greedy")["text"]

    gates = {"energy_trim": trim_silence, "flatness_gate": flatness_trim,
             "flatness_relenergy_gate": flatness_relenergy_trim}
    rows: list[dict[str, Any]] = []
    for ci, cid in enumerate(list_verified_cases()):
        case = cases_by_id.get(cid)
        if not case or "separated" not in case:
            continue
        ref = str(load_reference(cid).get("full_text", ""))
        mx_path = mixed_dir / case["mixed"]
        p1, p2 = sep_dir / case["separated"]["spk1"], sep_dir / case["separated"]["spk2"]
        if not (mx_path.exists() and p1.exists() and p2.exists()):
            continue
        mxa = read_mono_audio(mx_path).samples
        a1, a2 = read_mono_audio(p1).samples, read_mono_audio(p2).samples
        for snr in snr_levels:
            mx = add_noise(mxa, snr, _seed(ci, 0.0, snr, 0))
            n1 = add_noise(a1, snr, _seed(ci, 0.0, snr, 1))
            n2 = add_noise(a2, snr, _seed(ci, 0.0, snr, 2))
            o1 = transcribe_with_signals(model, n1, "greedy")
            o2 = transcribe_with_signals(model, n2, "greedy")
            cer = {"mixed": compute_cer(ref, tx(mx))["cer"], "sep": compute_cer(ref, o1["text"] + o2["text"])["cer"]}
            fired: dict[str, int] = {}
            for name, fn in gates.items():
                g1, g2 = fn(n1), fn(n2)
                fired[name] = int(g1.size < n1.size or g2.size < n2.size)
                cer[name] = compute_cer(ref, tx(g1) + tx(g2))["cer"]
            rows.append({
                "case_id": cid, "overlap_ratio": case.get("overlap_level", ""),
                "snr_db": "None" if snr is None else snr,
                "cr_sep1": round(o1["max_compression_ratio"], 4),
                "cr_sep2": round(o2["max_compression_ratio"], 4),
                **{f"cer_{a}": round(cer[a], 6) for a in ARMS},
                **{f"fired_{g}": fired[g] for g in gates},
            })
        print(f"[gate-gold] {cid} done", flush=True)

    curve = out_dir / "gold_noisy_curve.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    grid = aggregate_by_snr(rows)
    (out_dir / "gold_noisy_summary.json").write_text(json.dumps(grid, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[gate-gold] wrote {curve} + gold_noisy_summary.json (rows={len(rows)})", flush=True)
    return {"grid": grid, "n_rows": len(rows)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Noise-robust spectral-flatness gate experiment (frontier).")
    p.add_argument("--pairs", type=int, default=8)
    p.add_argument("--quick", action="store_true", help="Tiny smoke grid (2 pairs, coarse).")
    p.add_argument("--gold-noisy", action="store_true", help="Real-separator transfer check on the 5 gold cases (noise-injected) and exit.")
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    if args.gold_noisy:
        run_gold_noisy(out_dir, DEFAULT_SNR)
    elif args.quick:
        run(out_dir, num_pairs=2, overlaps=[0.0, 0.3], snr_levels=[None, 5.0])
    else:
        run(out_dir, args.pairs, DEFAULT_OVERLAPS, DEFAULT_SNR)


if __name__ == "__main__":
    main()
