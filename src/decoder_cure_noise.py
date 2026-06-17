"""Is the noise-robust separation-hallucination cure in the DECODER, not the audio? (frontier)

Pre-registered research question (issue #809; reverses the assumption of the noise saga
#796 -> #804 -> #806 -> #808):

  The whole separation-hallucination thread assumes the cure must DETECT and crop the
  low-information residual *in the audio*. That detection is exactly what keeps dying as the
  noise gets harder: energy trim (#806) -> spectral flatness (broadband only) -> speaker
  embedding (moderate babble only). But hallucination_cure_eval.py (#804) already showed the
  catastrophe is a GREEDY-DECODING artifact: beam search and Whisper's NATIVE
  `hallucination_silence_threshold` kill the catastrophic tail in CLEAN audio with zero
  cropping -- and those decoder-domain cures were never tested under noise.

  RQ: do decoder-domain cures survive noise -- including the real-meeting babble case -- where
  input-domain silence-detection dies?

  H1 (silence-detectors die together): Whisper's native `hallucination_silence_threshold` IS a
     silence detector, so under noise its fire-rate collapses to ~0 and its CER == greedy -- the
     SAME death as the energy trim (#806), now shown for Whisper's own built-in feature.
  H2 (path-diversity survives): beam search does not detect silence; it keeps firing under noise
     and lowers the catastrophic tail rate vs greedy at every noise type/SNR, including babble --
     but as a PARTIAL cure (does not drive CER<1 at the lowest SNR).
  H3 (honest cost): quantify beam's tax on the non-catastrophic majority and its ~3x compute, and
     test whether the residual 0 dB tail is a fundamental floor (no recoverable target) rather
     than a cure failure.

Design (reference-free; CER is post-hoc evaluation only, never a gate/routing input):
  Add the missing NOISE dimension to the #804 decoder-cure head-to-head. Reuse the established
  harness -- select_pairs/build_mixture (oracle separation), make_noise/add_noise_field
  (white/pink/babble), and transcribe_cure (greedy/beam5/native halluc_silence) -- plus the
  input gates (energy_trim, flatness_relenergy) as the dead/partial baselines. Per track-condition
  record CER for every arm AND whether the arm's text changed vs greedy (the FIRE-RATE diagnostic
  that is the core H1 evidence).

Labels: experimental/frontier; references synthetic/silver; ASR Whisper-tiny. No gold tables
touched; all outputs in results/frontier/decoder_cure_noise/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "decoder_cure_noise"
CATASTROPHIC_CER = 1.0

# greedy baseline + two input-domain cures + two decoder-domain cures.
ARMS = ["greedy", "energy_trim", "flatness_gate", "beam5", "halluc_silence"]
INPUT_CURES = ["energy_trim", "flatness_gate"]      # transform the audio, then greedy-decode
DECODER_CURES = ["beam5", "halluc_silence"]          # keep the audio, change the decoder

# Map each arm to a (cure-name-in-hallucination_cure_eval.CURES | None, applies-input-gate) recipe.
# greedy/energy_trim/beam5/halluc_silence reuse the #804 CURES dict verbatim (DRY); flatness_gate
# is the one input gate the #804 study did not include, applied here as flatness_relenergy_trim
# + greedy decode.
_CURE_KEY = {
    "greedy": "greedy_baseline",
    "energy_trim": "silence_trim",
    "beam5": "beam5",
    "halluc_silence": "halluc_silence",
}


# ======================================================================================
# Pure aggregation (no Whisper, no audio I/O) -- unit tested in tests/test_decoder_cure_noise.py
# ======================================================================================
def _mean(xs: list[float]) -> float:
    return round(float(np.mean(xs)), 6) if xs else 0.0


def _tail_rate(xs: list[float], threshold: float = CATASTROPHIC_CER) -> float:
    vals = [x for x in xs if x == x]
    return round(sum(1 for x in vals if x > threshold) / len(vals), 6) if vals else 0.0


def _snr_key(r: dict[str, Any]) -> Any:
    v = r.get("snr_db")
    if v in ("", "None", None, "clean"):
        return "clean"
    return float(v)


def fire_rate(rows: list[dict[str, Any]], cure: str) -> float:
    """Fraction of rows where the cure changed Whisper's output vs greedy (`changed_{cure}`==1).
    The H1 diagnostic: a silence detector's fire-rate collapses under noise; beam search's does
    not. Returns 0.0 on empty input or when the flag is absent."""
    flags = [float(r[f"changed_{cure}"]) for r in rows if r.get(f"changed_{cure}", "") not in ("", None)]
    return round(float(np.mean(flags)), 6) if flags else 0.0


def _conditions(rows: list[dict[str, Any]]) -> list[tuple[str, Any]]:
    keys = {(str(r.get("noise_type", "")), _snr_key(r)) for r in rows}
    # sort: clean last, then by descending SNR; group by noise type
    return sorted(keys, key=lambda k: (k[0], k[1] == "clean", -(k[1] if k[1] != "clean" else -1e9)))


def aggregate_by_condition(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per (noise_type, snr): mean CER + catastrophic tail rate for each arm, plus the headline
    decoder-cure gains vs greedy (positive = the cure lowers mean CER)."""
    out: list[dict[str, Any]] = []
    for ntype, snr in _conditions(rows):
        at = [r for r in rows if str(r.get("noise_type", "")) == ntype and _snr_key(r) == snr]
        row: dict[str, Any] = {"noise_type": ntype, "snr_db": snr, "n": len(at)}
        for arm in ARMS:
            cers = [float(r[f"cer_{arm}"]) for r in at if r.get(f"cer_{arm}", "") not in ("", None)]
            row[f"mean_cer_{arm}"] = _mean(cers)
            row[f"tail_{arm}"] = _tail_rate(cers)
        row["beam_gain_vs_greedy"] = round(row["mean_cer_greedy"] - row["mean_cer_beam5"], 6)
        row["halluc_gain_vs_greedy"] = round(row["mean_cer_greedy"] - row["mean_cer_halluc_silence"], 6)
        for cure in INPUT_CURES + DECODER_CURES:
            row[f"fire_rate_{cure}"] = fire_rate(at, cure)
        out.append(row)
    return out


def firerate_by_condition(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per (noise_type, snr): n + fire-rate of every cure. The mechanism table for H1."""
    out: list[dict[str, Any]] = []
    for ntype, snr in _conditions(rows):
        at = [r for r in rows if str(r.get("noise_type", "")) == ntype and _snr_key(r) == snr]
        row: dict[str, Any] = {"noise_type": ntype, "snr_db": snr, "n": len(at)}
        for cure in INPUT_CURES + DECODER_CURES:
            row[f"fire_rate_{cure}"] = fire_rate(at, cure)
        out.append(row)
    return out


def tail_conditional(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Split tracks by greedy CER>1 (catastrophic) vs normal; per arm report the mean CER on each
    subset and the normal-majority delta vs greedy (>0 means the cure TAXES healthy clips). Answers
    H2 (does the cure fix the tail?) and H3 (does it hurt the majority?)."""
    cat = [r for r in rows if float(r.get("cer_greedy", 0.0)) > CATASTROPHIC_CER]
    norm = [r for r in rows if 0.0 <= float(r.get("cer_greedy", 0.0)) <= CATASTROPHIC_CER]
    base_norm = _mean([float(r["cer_greedy"]) for r in norm])
    arms_out: list[dict[str, Any]] = []
    for arm in ARMS:
        cat_cers = [float(r[f"cer_{arm}"]) for r in cat if r.get(f"cer_{arm}", "") not in ("", None)]
        norm_cers = [float(r[f"cer_{arm}"]) for r in norm if r.get(f"cer_{arm}", "") not in ("", None)]
        norm_mean = _mean(norm_cers)
        arms_out.append({
            "arm": arm,
            "mean_cer_catastrophic": _mean(cat_cers),
            "tail_rate_catastrophic": _tail_rate(cat_cers),
            "mean_cer_normal": norm_mean,
            "normal_delta_vs_greedy": round(norm_mean - base_norm, 6),
        })
    return {"n_catastrophic": len(cat), "n_normal": len(norm), "arms": arms_out}


def audio_agnostic_regret(rows: list[dict[str, Any]], oracle_arms: tuple[str, ...] = ("greedy", "beam5", "flatness_gate")) -> dict[str, Any]:
    """Beam search is the only AUDIO-AGNOSTIC cure (no residual detection, no noise-type
    assumption, no speaker model). Compare always-greedy / always-beam / always-flatness against a
    per-track oracle (min over `oracle_arms`). Routing here is the fixed policy itself; CER scores
    the outcome and is never a routing input. Pooled over all rows."""
    greedy, beam, flat, oracle = [], [], [], []
    for r in rows:
        try:
            cg = float(r["cer_greedy"]); cb = float(r["cer_beam5"]); cf = float(r["cer_flatness_gate"])
        except (KeyError, ValueError, TypeError):
            continue
        greedy.append(cg); beam.append(cb); flat.append(cf)
        oracle.append(min(float(r[f"cer_{a}"]) for a in oracle_arms))
    means = {
        "always_greedy": _mean(greedy), "always_beam": _mean(beam),
        "always_flatness": _mean(flat), "oracle": _mean(oracle),
    }
    tails = {
        "always_greedy": _tail_rate(greedy), "always_beam": _tail_rate(beam),
        "always_flatness": _tail_rate(flat), "oracle": _tail_rate(oracle),
    }
    return {
        "n": len(greedy),
        "oracle_arms": list(oracle_arms),
        "mean_cer": means,
        "tail_rate": tails,
        "regret_vs_oracle": {k: round(v - means["oracle"], 6) for k, v in means.items() if k != "oracle"},
    }


# ======================================================================================
# Whisper-dependent driver
# ======================================================================================
DEFAULT_OVERLAPS = [0.0, 0.1, 0.3]
DEFAULT_NOISE_TYPES = ["white", "pink", "babble"]
DEFAULT_SNR: list[float] = [10.0, 5.0, 0.0]


def _arm_text(model: Any, audio: np.ndarray, arm: str) -> str:
    """Produce the transcript for one arm. Decoder cures + energy_trim reuse the #804 CURES recipes
    verbatim; flatness_gate is flatness_relenergy_trim + greedy decode."""
    from .hallucination_cure_eval import transcribe_cure
    from .noise_robust_gate import flatness_relenergy_trim
    from .separation_tax_phase import transcribe_with_signals

    if arm == "flatness_gate":
        return transcribe_with_signals(model, flatness_relenergy_trim(audio), "greedy")["text"]
    return transcribe_cure(model, audio, _CURE_KEY[arm])["text"]


def _eval_track(model: Any, track: np.ndarray, ref: str, meta: dict[str, Any]) -> dict[str, Any]:
    from .evaluate_cer import compute_cer

    texts = {arm: _arm_text(model, track, arm) for arm in ARMS}
    greedy_text = texts["greedy"]
    row: dict[str, Any] = dict(meta)
    for arm in ARMS:
        row[f"cer_{arm}"] = round(compute_cer(ref, texts[arm])["cer"], 6)
    for cure in INPUT_CURES + DECODER_CURES:
        row[f"changed_{cure}"] = int(texts[cure] != greedy_text)
    return row


def run(out_dir: Path, num_pairs: int, overlaps: list[float], noise_types: list[str],
        snr_levels: list[float], include_clean: bool = True) -> dict[str, Any]:
    import whisper

    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .noise_robust_gate import add_noise_field, make_noise
    from .separation_tax_phase import SNIPPETS_DIR, select_pairs

    out_dir.mkdir(parents=True, exist_ok=True)
    plans = select_pairs(num_pairs)
    all_snips = {p.name: read_mono_audio(p).samples for p in sorted(SNIPPETS_DIR.glob("*.wav"))}
    model = whisper.load_model("tiny")
    print(f"[decoder-cure] pairs={len(plans)} overlaps={overlaps} types={noise_types} "
          f"snr={snr_levels} arms={len(ARMS)} clean={include_clean}", flush=True)

    rows: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        # babble sources exclude this pair's own snippets (no target leakage into the babble)
        babble_src = [v for k, v in all_snips.items() if k not in (plan.con_path.name, plan.pro_path.name)]
        for overlap in overlaps:
            _, t1, t2, _ = build_mixture(s1, s2, overlap)
            tracks = [("spk1", t1, plan.con_text), ("spk2", t2, plan.pro_text)]
            # clean anchor: computed once per (pair, overlap, track), noise_type="clean"
            if include_clean:
                for name, tr, ref in tracks:
                    rows.append(_eval_track(model, tr, ref, {
                        "pair_id": pi, "overlap_ratio": overlap, "noise_type": "clean",
                        "snr_db": "clean", "track": name}))
            for kind in noise_types:
                for snr in snr_levels:
                    for ti, (name, tr, ref) in enumerate(tracks):
                        sd = pi * 911 + int(round(overlap * 100)) + int(snr) * 7 + noise_types.index(kind) * 53 + ti
                        noisy = add_noise_field(tr, snr, make_noise(kind, tr.size, sd, babble_src))
                        rows.append(_eval_track(model, noisy, ref, {
                            "pair_id": pi, "overlap_ratio": overlap, "noise_type": kind,
                            "snr_db": snr, "track": name}))
        print(f"[decoder-cure] pair {pi + 1}/{len(plans)} done", flush=True)

    _write_outputs(out_dir, rows)
    return {"n_rows": len(rows)}


def _write_outputs(out_dir: Path, rows: list[dict[str, Any]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    curve = out_dir / "cure_noise_curve.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    noisy = [r for r in rows if str(r.get("noise_type")) != "clean"]
    dichotomy = aggregate_by_condition(rows)
    (out_dir / "dichotomy_summary.json").write_text(
        json.dumps(dichotomy, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "firerate_summary.json").write_text(
        json.dumps(firerate_by_condition(rows), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "tail_conditional.json").write_text(
        json.dumps({"all": tail_conditional(rows), "babble": tail_conditional(
            [r for r in rows if r.get("noise_type") == "babble"])}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (out_dir / "regret_summary.json").write_text(
        json.dumps({"all_noisy": audio_agnostic_regret(noisy),
                    "babble": audio_agnostic_regret([r for r in noisy if r.get("noise_type") == "babble"])},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[decoder-cure] wrote {curve} + 4 summaries (rows={len(rows)})", flush=True)
    try:
        render_figure(out_dir, dichotomy)
    except Exception as exc:  # figure is a presentation nicety; never fail the run on it
        print(f"[decoder-cure] figure skipped: {exc}", flush=True)


def render_figure(out_dir: Path, dichotomy: list[dict[str, Any]]) -> Path | None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    types = [t for t in DEFAULT_NOISE_TYPES if any(r["noise_type"] == t for r in dichotomy)]
    if not types:
        return None
    fig, axes = plt.subplots(1, len(types), figsize=(5 * len(types), 4.4), sharey=True)
    if len(types) == 1:
        axes = [axes]
    styles = [("greedy", "#999999", "raw sep (greedy)"), ("energy_trim", "#b279a2", "energy trim (#806 dead)"),
              ("flatness_gate", "#e45756", "flatness gate"), ("beam5", "#4c78a8", "beam5 (decoder)"),
              ("halluc_silence", "#f58518", "native halluc-silence (decoder)")]
    for ax, ntype in zip(axes, types):
        rws = sorted([r for r in dichotomy if r["noise_type"] == ntype],
                     key=lambda r: -(r["snr_db"] if r["snr_db"] != "clean" else -1e9))
        labels = [str(r["snr_db"]) for r in rws]
        x = np.arange(len(rws))
        for arm, c, lab in styles:
            ax.plot(x, [r[f"mean_cer_{arm}"] for r in rws], "-o", color=c, label=lab)
        ax.axhline(1.0, color="black", lw=0.8, ls=":")
        ax.set_title(f"{ntype} noise")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{l} dB" if l != "clean" else l for l in labels])
        ax.set_xlabel("input SNR")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("mean separated CER (lower better)")
    axes[0].legend(fontsize=7)
    fig.suptitle("Decoder cures vs input gates under noise: does the cure survive babble? (Whisper-tiny, zh)")
    fig.tight_layout()
    fig_path = out_dir / "decoder_cure_noise.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[decoder-cure] wrote {fig_path}", flush=True)
    return fig_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Decoder-vs-input cures under noise (frontier).")
    p.add_argument("--pairs", type=int, default=8)
    p.add_argument("--quick", action="store_true", help="Tiny smoke grid (2 pairs, babble+white, 5 dB).")
    p.add_argument("--no-clean", action="store_true", help="Skip the clean anchor pass.")
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    if args.quick:
        run(out_dir, num_pairs=2, overlaps=[0.0, 0.1], noise_types=["babble", "white"],
            snr_levels=[5.0], include_clean=not args.no_clean)
    else:
        run(out_dir, args.pairs, DEFAULT_OVERLAPS, DEFAULT_NOISE_TYPES, DEFAULT_SNR,
            include_clean=not args.no_clean)


if __name__ == "__main__":
    main()
