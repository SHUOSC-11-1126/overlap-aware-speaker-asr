"""Separation-tax phase study (experimental/frontier).

Research question (pre-registered in this docstring):
  The stable baseline reports that speech separation HELPS Whisper at no/heavy/opposite
  overlap but HURTS at light/mid overlap, attributed to "insertion + repetition
  hallucination". That conclusion rests on 5 hand-labeled gold cases plus a noisy
  single-sample-per-ratio synthetic scatter. This module replaces that with a
  controlled, multi-seed, *oracle-separation* phase study and asks three questions:

  RQ1 (phase curve): As a continuous function of overlap ratio r in [0, 0.9], what is the
     separation gain  delta_CER(r) = CER_mixed(r) - CER_separated(r)  under ORACLE
     separation (the additive mixture's own source tracks = a perfect-separation upper
     bound)? Where is the crossover r* at which separation stops hurting and starts
     helping? We report mean AND median with bootstrap CIs.

  RQ2 (mechanism): Is the low-r "separation hurts" effect a *uniform* degradation, or a
     *heavy-tailed* hallucination phenomenon -- a minority of oracle tracks whose long
     silence tail (where the other talker used to be) triggers Whisper to hallucinate
     (CER >> 1)? We quantify the catastrophic-tail rate (CER > 1.0) per ratio and the
     insertion/repetition share of errors.

  RQ3 (decoder artifact -- the bold claim): The baseline pipeline forces Whisper
     temperature=0.0, which DISABLES Whisper's default temperature-fallback
     anti-hallucination mechanism. We A/B two decoder configs (greedy vs temperature
     fallback) and a silence-trim arm to test whether the low-overlap separation penalty
     is substantially a *decoder-default artifact* that standard decoding hygiene cures,
     rather than an intrinsic property of separation.

  RQ4 (reference-free triage): Can the catastrophic separated tracks be flagged using
     only reference-free Whisper signals (compression ratio, repetition, no-speech prob)
     -- never CER/reference -- so a router could avoid them? We report ranking AUC.

Hypotheses:
  H1: Under greedy decoding, mean delta_CER < 0 at small r (separation hurts on average)
      while median delta_CER >= 0 (it helps the typical clip) -- i.e. the mean is dragged
      by a tail.
  H2: The tail rate of catastrophic separated CER is highest at small r (longest silence
      tails) and the errors are insertion/repetition dominated.
  H3: Temperature fallback and/or silence trimming collapse the tail and push the
      crossover r* toward 0, partly overturning "separation hurts at low overlap".

What is useful even if a hypothesis fails:
  If H3 is false (fallback/trim do NOT fix it), that is itself a strong result: the
  separation tax is intrinsic to Whisper-on-isolated-tracks and robust to decoding, which
  *justifies* a when-to-separate router. Either outcome is a computed, falsifiable finding.

Labels: experimental/frontier; references are synthetic/silver (Whisper-small on clean
snippets). ASR = Whisper-tiny (only model cached offline). CER is post-hoc evaluation
only and is never used as a routing input. Stable result tables are not touched; all
outputs go to results/frontier/separation_tax/.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT
from .evaluate_cer import compute_cer, normalize_text, repetition_count_from_text
from .evaluate_error_types import levenshtein_alignment_counts
from .generate_synthetic_overlap import AudioClip, build_mixture, read_mono_audio

TARGET_SR = 16000


def _rel(path: Path) -> str:
    """Repo-relative display when possible, else the bare path (e.g. /tmp out-dirs)."""
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)

# Decoder configs under test. "greedy" matches the baseline pipeline (temperature=0.0 ->
# Whisper's temperature-fallback is disabled). "fallback" is Whisper's default
# anti-hallucination behavior (retry at higher temperature when a decode looks
# degenerate per compression_ratio_threshold / logprob_threshold).
WHISPER_CONFIGS: dict[str, dict[str, Any]] = {
    "greedy": {"temperature": 0.0, "condition_on_previous_text": False},
    "fallback": {
        "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
        "condition_on_previous_text": False,
    },
}

DEFAULT_RATIOS = [
    0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70, 0.80, 0.90,
]
QUICK_RATIOS = [0.0, 0.15, 0.35, 0.60, 0.90]

CATASTROPHIC_CER = 1.0  # hypothesis longer/wronger than reference => hallucination tail

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "separation_tax"
SNIPPET_TX_DIR = PROJECT_ROOT / "results" / "snippet_transcripts"
SNIPPETS_DIR = PROJECT_ROOT / "resources" / "snippets"


# --------------------------------------------------------------------------------------
# Pure helpers (no Whisper / no audio model required -- unit tested directly)
# --------------------------------------------------------------------------------------
def nonzero_speech_span(track: np.ndarray, rel_thresh: float = 1e-3) -> tuple[int, int]:
    """Return (start, end_exclusive) sample indices of the speech region, defined as the
    span between the first and last samples whose |amplitude| exceeds rel_thresh * peak.
    Returns (0, 0) for silent/empty input."""
    if track.size == 0:
        return (0, 0)
    peak = float(np.max(np.abs(track)))
    if peak <= 0.0:
        return (0, 0)
    mask = np.abs(track) > rel_thresh * peak
    idx = np.nonzero(mask)[0]
    if idx.size == 0:
        return (0, 0)
    return (int(idx[0]), int(idx[-1]) + 1)


def trim_silence(track: np.ndarray, rel_thresh: float = 1e-3, margin_samples: int = 1600) -> np.ndarray:
    """Crop leading/trailing silence, keeping a small margin (default 0.1 s @ 16 kHz).
    If the track is entirely silent, return it unchanged so the ASR still receives input."""
    start, end = nonzero_speech_span(track, rel_thresh)
    if end <= start:
        return track
    s = max(0, start - margin_samples)
    e = min(int(track.size), end + margin_samples)
    return track[s:e]


def estimate_crossover(ratios: list[float], mean_deltas: list[float]) -> float | None:
    """First ascending zero-crossing of delta_CER (= mixed - separated) vs ratio.

    delta < 0  => separation hurts; delta > 0 => separation helps. We return the
    interpolated ratio where the curve crosses from <=0 to >0. If the curve is already
    positive at the smallest ratio, return that ratio (separation helps everywhere). If it
    never becomes positive, return None.
    """
    pts = [(float(r), float(d)) for r, d in zip(ratios, mean_deltas) if d == d]  # drop NaN
    pts.sort(key=lambda p: p[0])
    if not pts:
        return None
    if pts[0][1] > 0:
        return pts[0][0]
    for (r0, d0), (r1, d1) in zip(pts, pts[1:]):
        if d0 <= 0 < d1:
            if d1 == d0:
                return r1
            return round(r0 + (r1 - r0) * (0.0 - d0) / (d1 - d0), 4)
    return None


def tail_rate(cers: list[float], threshold: float = CATASTROPHIC_CER) -> float:
    """Fraction of CER values strictly greater than `threshold` (catastrophic hallucination)."""
    vals = [c for c in cers if c == c]
    if not vals:
        return 0.0
    return sum(1 for c in vals if c > threshold) / len(vals)


def rank_auc(scores: list[float], labels: list[int]) -> float:
    """AUC via Mann-Whitney U: P(score(pos) > score(neg)) with 0.5 credit for ties.
    Returns 0.5 if either class is empty."""
    pos = [s for s, l in zip(scores, labels) if l == 1]
    neg = [s for s, l in zip(scores, labels) if l == 0]
    if not pos or not neg:
        return 0.5
    wins = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1.0
            elif p == n:
                wins += 0.5
    return wins / (len(pos) * len(neg))


def bootstrap_ci(values: list[float], n_boot: int = 1000, alpha: float = 0.05, seed: int = 0) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean of `values`."""
    arr = np.asarray([v for v in values if v == v], dtype=float)
    if arr.size == 0:
        return (float("nan"), float("nan"))
    if arr.size == 1:
        return (float(arr[0]), float(arr[0]))
    rng = np.random.default_rng(seed)
    means = rng.choice(arr, size=(n_boot, arr.size), replace=True).mean(axis=1)
    lo = float(np.percentile(means, 100 * alpha / 2))
    hi = float(np.percentile(means, 100 * (1 - alpha / 2)))
    return (lo, hi)


def insertion_share(reference: str, hypothesis: str) -> float:
    """Share of the edit distance attributable to insertions (proxy for over-generation /
    hallucination). Returns 0.0 when there are no errors."""
    subs, dels, ins, dist = levenshtein_alignment_counts(reference, hypothesis)
    if dist <= 0:
        return 0.0
    return ins / dist


def aggregate_phase(rows: list[dict[str, Any]], config: str) -> list[dict[str, Any]]:
    """Aggregate per-(pair,ratio) rows of one config into per-ratio statistics."""
    sub = [r for r in rows if r.get("config") == config]
    ratios = sorted({float(r["overlap_ratio"]) for r in sub})
    out: list[dict[str, Any]] = []
    for ratio in ratios:
        at = [r for r in sub if float(r["overlap_ratio"]) == ratio]
        deltas = [float(r["delta_cer"]) for r in at]
        cer_mixed = [float(r["cer_mixed"]) for r in at]
        cer_sep = [float(r["cer_sep"]) for r in at]
        lo, hi = bootstrap_ci(deltas)
        out.append(
            {
                "config": config,
                "overlap_ratio": ratio,
                "n": len(at),
                "mean_delta_cer": round(float(np.mean(deltas)), 6) if deltas else 0.0,
                "median_delta_cer": round(float(np.median(deltas)), 6) if deltas else 0.0,
                "ci_lo": round(lo, 6),
                "ci_hi": round(hi, 6),
                "mean_cer_mixed": round(float(np.mean(cer_mixed)), 6) if cer_mixed else 0.0,
                "mean_cer_sep": round(float(np.mean(cer_sep)), 6) if cer_sep else 0.0,
                "median_cer_sep": round(float(np.median(cer_sep)), 6) if cer_sep else 0.0,
                "tail_rate_sep": round(tail_rate(cer_sep), 6),
                "tail_rate_mixed": round(tail_rate(cer_mixed), 6),
                "sep_helps_frac": round(sum(1 for d in deltas if d > 0) / len(deltas), 6) if deltas else 0.0,
            }
        )
    return out


# --------------------------------------------------------------------------------------
# Reference-free "trim-and-guard" router (operationalizes the findings; uses NO references)
# --------------------------------------------------------------------------------------
GUARD_THRESHOLD = 2.4  # Whisper's own default compression_ratio_threshold (degeneracy);
#                        principled, NOT tuned on CER -> no reference leakage into routing.


def router_choice(cr_sep1: float, cr_sep2: float, threshold: float = GUARD_THRESHOLD) -> bool:
    """Reference-free guard: True iff the separated tracks look NON-degenerate (both
    compression ratios at/below threshold). A True verdict means 'trust separation'."""
    return max(cr_sep1, cr_sep2) <= threshold


def summarize_router(rows: list[dict[str, Any]], threshold: float = GUARD_THRESHOLD) -> dict[str, Any]:
    """Compare routing policies against the oracle on greedy-decoded rows, reference-free.

    Policies (per condition):
      fixed_mixed       : always use the mixed transcript
      fixed_sep         : always use the separated transcript (no trim)  [baseline]
      always_trim       : always silence-trim the separated tracks
      guard_to_mixed    : trust trimmed-sep unless the guard flags degeneracy -> mixed
      guard_retry_trim  : use sep as-is unless the guard flags degeneracy -> trimmed-sep
    Oracle = best achievable per condition among {mixed, sep, sep_trim} (needs references;
    used only to measure regret, never to route).
    """
    greedy = [r for r in rows if r.get("config") == "greedy"]
    cm_l, cs_l, ct_l = [], [], []
    p_guard_mixed, p_guard_retry, oracle_l = [], [], []
    guard_fired = 0
    for r in greedy:
        cm, cs, ct = _to_float(r["cer_mixed"]), _to_float(r["cer_sep"]), _to_float(r["cer_sep_trim"])
        if cm != cm or cs != cs or ct != ct:  # skip rows missing any arm
            continue
        ok = router_choice(_to_float(r["cr_sep1"]), _to_float(r["cr_sep2"]), threshold)
        if not ok:
            guard_fired += 1
        cm_l.append(cm)
        cs_l.append(cs)
        ct_l.append(ct)
        p_guard_mixed.append(ct if ok else cm)
        p_guard_retry.append(cs if ok else ct)
        oracle_l.append(min(cm, cs, ct))
    n = len(cm_l)

    def mean(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 6) if xs else 0.0

    means = {
        "fixed_mixed": mean(cm_l),
        "fixed_sep": mean(cs_l),
        "always_trim": mean(ct_l),
        "guard_to_mixed": mean(p_guard_mixed),
        "guard_retry_trim": mean(p_guard_retry),
        "oracle": mean(oracle_l),
    }
    regret = {k: round(v - means["oracle"], 6) for k, v in means.items() if k != "oracle"}
    best_policy = min(regret, key=lambda k: regret[k]) if regret else None
    return {
        "n": n,
        "guard_threshold": threshold,
        "guard_fired_frac": round(guard_fired / n, 6) if n else 0.0,
        "mean_cer": means,
        "regret_vs_oracle": regret,
        "best_deployable_policy": best_policy,
    }


def evaluate_router(out_dir: Path, threshold: float = GUARD_THRESHOLD) -> dict[str, Any]:
    rows = _read_curve(out_dir / "phase_curve.csv")
    result = summarize_router(rows, threshold)
    csv_path = out_dir / "router_eval.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(["policy", "mean_cer", "regret_vs_oracle", "reference_free"])
        for policy, cer in result["mean_cer"].items():
            ref_free = "no(oracle)" if policy == "oracle" else "yes"
            writer.writerow([policy, cer, result["regret_vs_oracle"].get(policy, 0.0), ref_free])
    print(f"[separation-tax] wrote {_rel(csv_path)} best={result['best_deployable_policy']}", flush=True)
    return result


# --------------------------------------------------------------------------------------
# Whisper-dependent driver
# --------------------------------------------------------------------------------------
@dataclass
class PairPlan:
    con_path: Path
    pro_path: Path
    con_text: str
    pro_text: str
    con_clip: AudioClip = field(repr=False, default=None)  # type: ignore[assignment]
    pro_clip: AudioClip = field(repr=False, default=None)  # type: ignore[assignment]


def load_snippet_reference(snippet_path: Path) -> str:
    """Silver reference text (Whisper-small on the clean snippet), from results/snippet_transcripts."""
    tx = SNIPPET_TX_DIR / f"{snippet_path.stem}_whisper.json"
    if not tx.exists():
        raise FileNotFoundError(f"Missing snippet transcript: {tx.relative_to(PROJECT_ROOT)}")
    payload = json.loads(tx.read_text(encoding="utf-8-sig"))
    return str(payload.get("text", "")).strip()


def select_pairs(num_pairs: int) -> list[PairPlan]:
    con_files = sorted(SNIPPETS_DIR.glob("con_*.wav"))
    pro_files = sorted(SNIPPETS_DIR.glob("pro_*.wav"))
    if not con_files or not pro_files:
        raise FileNotFoundError(f"No con_/pro_ snippets in {SNIPPETS_DIR.relative_to(PROJECT_ROOT)}")
    stride = 7  # coprime with typical pro counts -> spreads speaker pairings deterministically
    plans: list[PairPlan] = []
    for i in range(num_pairs):
        con_path = con_files[i % len(con_files)]
        pro_path = pro_files[(i * stride) % len(pro_files)]
        plans.append(
            PairPlan(
                con_path=con_path,
                pro_path=pro_path,
                con_text=load_snippet_reference(con_path),
                pro_text=load_snippet_reference(pro_path),
            )
        )
    return plans


def transcribe_with_signals(model: Any, audio: np.ndarray, config: str, language: str = "zh") -> dict[str, Any]:
    cfg = WHISPER_CONFIGS[config]
    audio = np.ascontiguousarray(np.asarray(audio, dtype=np.float32))
    result = model.transcribe(audio, language=language, verbose=False, fp16=False, **cfg)
    segs = result.get("segments", [])
    text = str(result.get("text", "")).strip()
    return {
        "text": text,
        "n_segments": len(segs),
        "mean_avg_logprob": float(np.mean([s.get("avg_logprob", 0.0) for s in segs])) if segs else 0.0,
        "max_compression_ratio": float(max((s.get("compression_ratio", 0.0) for s in segs), default=0.0)),
        "max_no_speech_prob": float(max((s.get("no_speech_prob", 0.0) for s in segs), default=0.0)),
        "max_temperature": float(max((s.get("temperature", 0.0) for s in segs), default=0.0)),
        "repetition_count": repetition_count_from_text(text),
    }


def run_sweep(num_pairs: int, ratios: list[float], out_dir: Path) -> Path:
    import whisper

    out_dir.mkdir(parents=True, exist_ok=True)
    curve_path = out_dir / "phase_curve.csv"

    plans = select_pairs(num_pairs)
    model = whisper.load_model("tiny")
    print(f"[separation-tax] model=tiny pairs={len(plans)} ratios={len(ratios)}", flush=True)

    fieldnames = [
        "pair_id", "con", "pro", "overlap_ratio", "config",
        "cer_mixed", "cer_sep", "cer_sep_trim", "delta_cer", "delta_cer_trim",
        "ins_share_mixed", "ins_share_sep",
        "sil_tail_sec_spk1", "sil_lead_sec_spk2",
        "rep_mixed", "rep_sep1", "rep_sep2",
        "cr_mixed", "cr_sep1", "cr_sep2",
        "nsp_sep1", "nsp_sep2", "temp_sep1_used",
        "cer_sep1", "cer_sep2", "cer_sep1_trim", "cer_sep2_trim",
    ]
    rows: list[dict[str, Any]] = []
    with curve_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for pi, plan in enumerate(plans):
            s1 = read_mono_audio(plan.con_path)
            s2 = read_mono_audio(plan.pro_path)
            ref_combined = plan.con_text + plan.pro_text
            for ratio in ratios:
                mixed, track1, track2, _scale = build_mixture(s1, s2, ratio)
                span1 = nonzero_speech_span(track1)
                span2 = nonzero_speech_span(track2)
                sil_tail_spk1 = max(0, track1.size - span1[1]) / TARGET_SR
                sil_lead_spk2 = max(0, span2[0]) / TARGET_SR
                t1_trim = trim_silence(track1)
                t2_trim = trim_silence(track2)
                for config in ("greedy", "fallback"):
                    mx = transcribe_with_signals(model, mixed, config)
                    o1 = transcribe_with_signals(model, track1, config)
                    o2 = transcribe_with_signals(model, track2, config)
                    sep_text = o1["text"] + o2["text"]
                    cer_mixed = compute_cer(ref_combined, mx["text"])["cer"]
                    cer_sep = compute_cer(ref_combined, sep_text)["cer"]
                    cer_sep1 = compute_cer(plan.con_text, o1["text"])["cer"]
                    cer_sep2 = compute_cer(plan.pro_text, o2["text"])["cer"]
                    # silence-trim arm only under greedy (isolate the silence mechanism)
                    if config == "greedy":
                        o1t = transcribe_with_signals(model, t1_trim, config)
                        o2t = transcribe_with_signals(model, t2_trim, config)
                        sep_trim_text = o1t["text"] + o2t["text"]
                        cer_sep_trim = compute_cer(ref_combined, sep_trim_text)["cer"]
                        cer_sep1_trim = compute_cer(plan.con_text, o1t["text"])["cer"]
                        cer_sep2_trim = compute_cer(plan.pro_text, o2t["text"])["cer"]
                    else:
                        cer_sep_trim = float("nan")
                        cer_sep1_trim = float("nan")
                        cer_sep2_trim = float("nan")
                    row = {
                        "pair_id": pi,
                        "con": plan.con_path.name,
                        "pro": plan.pro_path.name,
                        "overlap_ratio": ratio,
                        "config": config,
                        "cer_mixed": round(cer_mixed, 6),
                        "cer_sep": round(cer_sep, 6),
                        "cer_sep_trim": cer_sep_trim if cer_sep_trim != cer_sep_trim else round(cer_sep_trim, 6),
                        "delta_cer": round(cer_mixed - cer_sep, 6),
                        "delta_cer_trim": (cer_mixed - cer_sep_trim)
                        if cer_sep_trim != cer_sep_trim else round(cer_mixed - cer_sep_trim, 6),
                        "ins_share_mixed": round(insertion_share(ref_combined, mx["text"]), 6),
                        "ins_share_sep": round(insertion_share(ref_combined, sep_text), 6),
                        "sil_tail_sec_spk1": round(sil_tail_spk1, 4),
                        "sil_lead_sec_spk2": round(sil_lead_spk2, 4),
                        "rep_mixed": mx["repetition_count"],
                        "rep_sep1": o1["repetition_count"],
                        "rep_sep2": o2["repetition_count"],
                        "cr_mixed": round(mx["max_compression_ratio"], 4),
                        "cr_sep1": round(o1["max_compression_ratio"], 4),
                        "cr_sep2": round(o2["max_compression_ratio"], 4),
                        "nsp_sep1": round(o1["max_no_speech_prob"], 4),
                        "nsp_sep2": round(o2["max_no_speech_prob"], 4),
                        "temp_sep1_used": round(o1["max_temperature"], 3),
                        "cer_sep1": round(cer_sep1, 6),
                        "cer_sep2": round(cer_sep2, 6),
                        "cer_sep1_trim": cer_sep1_trim if cer_sep1_trim != cer_sep1_trim else round(cer_sep1_trim, 6),
                        "cer_sep2_trim": cer_sep2_trim if cer_sep2_trim != cer_sep2_trim else round(cer_sep2_trim, 6),
                    }
                    writer.writerow(row)
                    rows.append(row)
            fh.flush()
            print(f"[separation-tax] pair {pi + 1}/{len(plans)} done ({plan.con_path.name}+{plan.pro_path.name})", flush=True)
    print(f"[separation-tax] wrote {_rel(curve_path)} rows={len(rows)}", flush=True)
    return curve_path


def evaluate_gold_real_separation(out_dir: Path) -> dict[str, Any]:
    """External-validity check: does the silence-trim cure transfer from oracle tracks to a
    REAL separator's output on the 5 verified gold cases? Uses the actual separated audio in
    resources/separated_audio and the verified gold references. ASR = Whisper-tiny (so these
    CERs are NOT comparable to the whisper-small gold table; only trim-vs-no-trim is compared
    here, and the gold tables are not touched)."""
    import whisper

    from .config import load_config
    from .evaluate_cer import load_reference, list_verified_cases

    cfg = load_config()
    sep_dir = PROJECT_ROOT / cfg["paths"]["separated_audio_dir"]
    cases_by_id = {c["id"]: c for c in cfg.get("audio_cases", [])}
    out_dir.mkdir(parents=True, exist_ok=True)
    model = whisper.load_model("tiny")

    rows: list[dict[str, Any]] = []
    for cid in list_verified_cases():
        case = cases_by_id.get(cid)
        if not case or "separated" not in case:
            continue
        ref = str(load_reference(cid).get("full_text", ""))
        p1 = sep_dir / case["separated"]["spk1"]
        p2 = sep_dir / case["separated"]["spk2"]
        if not p1.exists() or not p2.exists():
            continue
        a1 = read_mono_audio(p1).samples
        a2 = read_mono_audio(p2).samples
        o1 = transcribe_with_signals(model, a1, "greedy")
        o2 = transcribe_with_signals(model, a2, "greedy")
        cer_sep = compute_cer(ref, o1["text"] + o2["text"])["cer"]
        t1, t2 = trim_silence(a1), trim_silence(a2)
        o1t = transcribe_with_signals(model, t1, "greedy")
        o2t = transcribe_with_signals(model, t2, "greedy")
        cer_sep_trim = compute_cer(ref, o1t["text"] + o2t["text"])["cer"]
        sp1, sp2 = nonzero_speech_span(a1), nonzero_speech_span(a2)
        sil1 = 1.0 - (sp1[1] - sp1[0]) / max(1, a1.size)
        sil2 = 1.0 - (sp2[1] - sp2[0]) / max(1, a2.size)
        fire = not router_choice(o1["max_compression_ratio"], o2["max_compression_ratio"])
        gated = cer_sep_trim if fire else cer_sep  # trim ONLY when degeneracy guard fires
        rows.append(
            {
                "case_id": cid,
                "cer_sep": round(cer_sep, 6),
                "cer_sep_trim": round(cer_sep_trim, 6),
                "cer_guard_gated_trim": round(gated, 6),
                "delta_trim": round(cer_sep - cer_sep_trim, 6),
                "max_cr": round(max(o1["max_compression_ratio"], o2["max_compression_ratio"]), 4),
                "guard_would_fire": fire,
                "silence_frac_spk1": round(sil1, 4),
                "silence_frac_spk2": round(sil2, 4),
            }
        )

    csv_path = out_dir / "gold_real_separation.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "case_id", "cer_sep", "cer_sep_trim", "cer_guard_gated_trim", "delta_trim",
                "max_cr", "guard_would_fire", "silence_frac_spk1", "silence_frac_spk2",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    mean_sep = round(sum(r["cer_sep"] for r in rows) / len(rows), 6) if rows else 0.0
    mean_trim = round(sum(r["cer_sep_trim"] for r in rows) / len(rows), 6) if rows else 0.0
    mean_gated = round(sum(r["cer_guard_gated_trim"] for r in rows) / len(rows), 6) if rows else 0.0
    summary = {
        "n_cases": len(rows),
        "mean_cer_sep": mean_sep,
        "mean_cer_sep_trim": mean_trim,
        "mean_cer_guard_gated_trim": mean_gated,
        "mean_delta_trim": round(mean_sep - mean_trim, 6),
        "mean_delta_guard_gated": round(mean_sep - mean_gated, 6),
        "cases_trim_helped": sum(1 for r in rows if r["delta_trim"] > 0),
        "cases_guard_fired": sum(1 for r in rows if r["guard_would_fire"]),
        "mean_silence_frac": round(
            sum(r["silence_frac_spk1"] + r["silence_frac_spk2"] for r in rows) / (2 * len(rows)), 4
        ) if rows else 0.0,
    }
    (out_dir / "gold_real_separation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[separation-tax] wrote {_rel(csv_path)} mean_sep={mean_sep} mean_trim={mean_trim}", flush=True)
    return summary


def _read_curve(curve_path: Path) -> list[dict[str, Any]]:
    with curve_path.open("r", newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _to_float(value: Any) -> float:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return f


def analyze(out_dir: Path) -> dict[str, Any]:
    curve_path = out_dir / "phase_curve.csv"
    raw = _read_curve(curve_path)
    # coerce numeric
    rows = []
    for r in raw:
        rows.append(
            {
                **r,
                "overlap_ratio": _to_float(r["overlap_ratio"]),
                "cer_mixed": _to_float(r["cer_mixed"]),
                "cer_sep": _to_float(r["cer_sep"]),
                "delta_cer": _to_float(r["delta_cer"]),
            }
        )
    summary: dict[str, Any] = {"configs": {}}
    agg_rows: list[dict[str, Any]] = []
    for config in ("greedy", "fallback"):
        agg = aggregate_phase(rows, config)
        agg_rows.extend(agg)
        ratios = [a["overlap_ratio"] for a in agg]
        mean_deltas = [a["mean_delta_cer"] for a in agg]
        median_deltas = [a["median_delta_cer"] for a in agg]
        summary["configs"][config] = {
            "crossover_mean": estimate_crossover(ratios, mean_deltas),
            "crossover_median": estimate_crossover(ratios, median_deltas),
            "overall_mean_delta": round(float(np.mean([a["mean_delta_cer"] for a in agg])), 6),
            "overall_tail_rate_sep": round(float(np.mean([a["tail_rate_sep"] for a in agg])), 6),
        }
    # aggregate table
    agg_path = out_dir / "phase_aggregate.csv"
    with agg_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "config", "overlap_ratio", "n", "mean_delta_cer", "median_delta_cer",
                "ci_lo", "ci_hi", "mean_cer_mixed", "mean_cer_sep", "median_cer_sep",
                "tail_rate_sep", "tail_rate_mixed", "sep_helps_frac",
            ],
        )
        writer.writeheader()
        writer.writerows(agg_rows)

    # RQ4: reference-free detector for catastrophic separated tracks (greedy only)
    greedy = [r for r in raw if r.get("config") == "greedy"]
    scores_cr: list[float] = []
    scores_rep: list[float] = []
    labels: list[int] = []
    for r in greedy:
        for s, rep, cer in (
            (r["cr_sep1"], r["rep_sep1"], r["cer_sep1"]),
            (r["cr_sep2"], r["rep_sep2"], r["cer_sep2"]),
        ):
            cer_f = _to_float(cer)
            if cer_f != cer_f:
                continue
            scores_cr.append(_to_float(s))
            scores_rep.append(_to_float(rep))
            labels.append(1 if cer_f > CATASTROPHIC_CER else 0)
    summary["detector"] = {
        "n_tracks": len(labels),
        "n_catastrophic": int(sum(labels)),
        "auc_compression_ratio": round(rank_auc(scores_cr, labels), 4),
        "auc_repetition": round(rank_auc(scores_rep, labels), 4),
    }
    # trim cure effect (greedy): mean sep CER vs mean sep_trim CER on shared rows
    sep_cers = [_to_float(r["cer_sep"]) for r in greedy]
    trim_cers = [_to_float(r["cer_sep_trim"]) for r in greedy]
    paired = [(a, b) for a, b in zip(sep_cers, trim_cers) if a == a and b == b]
    if paired:
        summary["trim_cure"] = {
            "mean_cer_sep_greedy": round(float(np.mean([a for a, _ in paired])), 6),
            "mean_cer_sep_greedy_trim": round(float(np.mean([b for _, b in paired])), 6),
            "tail_rate_sep_greedy": round(tail_rate([a for a, _ in paired]), 6),
            "tail_rate_sep_greedy_trim": round(tail_rate([b for _, b in paired]), 6),
        }
    summary["router"] = evaluate_router(out_dir)
    summary_path = out_dir / "analysis_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[separation-tax] wrote {_rel(agg_path)} and {_rel(summary_path)}", flush=True)
    try:
        render_figure(out_dir)
    except Exception as exc:  # figure is a presentation nicety; never fail analysis on it
        print(f"[separation-tax] figure skipped: {exc}", flush=True)
    return summary


def render_figure(out_dir: Path) -> Path | None:
    """The money figure: separation gain delta_CER vs overlap ratio (greedy vs fallback)
    with bootstrap CI bands, plus the catastrophic-tail-rate panel that explains the gap."""
    agg_path = out_dir / "phase_aggregate.csv"
    if not agg_path.exists():
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with agg_path.open("r", newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    def series(cfg: str, key: str) -> list[float]:
        return [float(r[key]) for r in rows if r["config"] == cfg]

    colors = {"greedy": "#e45756", "fallback": "#4c78a8"}
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 8), sharex=True)

    for cfg in ("greedy", "fallback"):
        x = series(cfg, "overlap_ratio")
        mean = series(cfg, "mean_delta_cer")
        med = series(cfg, "median_delta_cer")
        lo = series(cfg, "ci_lo")
        hi = series(cfg, "ci_hi")
        ax1.plot(x, mean, "-o", color=colors[cfg], label=f"{cfg} mean ΔCER")
        ax1.plot(x, med, "--", color=colors[cfg], alpha=0.7, label=f"{cfg} median ΔCER")
        ax1.fill_between(x, lo, hi, color=colors[cfg], alpha=0.15)
        ax2.plot(x, series(cfg, "tail_rate_sep"), "-s", color=colors[cfg], label=f"{cfg} sep tail rate")

    ax1.axhline(0.0, color="black", lw=1)
    ax1.set_ylabel("ΔCER = CER(mixed) − CER(separated)\n>0: separation helps")
    ax1.set_title("Separation Tax: oracle-separation gain vs overlap ratio (Whisper-tiny, zh)")
    ax1.legend(fontsize=8, ncol=2)
    ax1.grid(alpha=0.3)

    ax2.set_ylabel("catastrophic tail rate\nP(CER_sep > 1.0)")
    ax2.set_xlabel("overlap ratio")
    ax2.set_title("Heavy-tailed hallucination on separated tracks (mechanism)")
    ax2.legend(fontsize=8)
    ax2.grid(alpha=0.3)

    fig.tight_layout()
    fig_path = out_dir / "separation_tax.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[separation-tax] wrote {_rel(fig_path)}", flush=True)
    return fig_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Separation-tax phase study (experimental/frontier).")
    parser.add_argument("--pairs", type=int, default=20, help="Number of speaker pairs to sweep.")
    parser.add_argument("--quick", action="store_true", help="Use a coarse 5-point ratio grid (smoke).")
    parser.add_argument("--analyze-only", action="store_true", help="Skip the ASR sweep; re-analyze existing phase_curve.csv.")
    parser.add_argument("--gold-real", action="store_true", help="Run the real-separator generalization check on the 5 gold cases and exit.")
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    if args.gold_real:
        evaluate_gold_real_separation(out_dir)
        return
    ratios = QUICK_RATIOS if args.quick else DEFAULT_RATIOS
    if not args.analyze_only:
        run_sweep(args.pairs, ratios, out_dir)
    analyze(out_dir)


if __name__ == "__main__":
    main()
