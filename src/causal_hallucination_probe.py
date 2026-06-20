"""Causal & internal-state hallucination probe (experimental/frontier).

Pre-registered research question (issue #855; full text in
``docs/frontier/causal_hallucination_probe.md``; literature grounding in
``docs/frontier/causal_hallucination_probe_litreview.md``):

  ``separation_tax`` closed the *acoustic* loop on the separation tax: the low-overlap
  penalty is a heavy hallucination tail driven by oracle-separated tracks with a long
  leading-silent region; a reference-free compression-ratio (CR) guard ranks the
  catastrophic tracks at AUC=1.0 and a guard-gated router closes ~76% of the offline
  oracle gap. That rests on two unexamined assumptions this probe attacks:

    1. The detector is an OUTPUT signal. CR is computed over the FULL decoded segment, so
       by the time it inflates past 2.4 Whisper has already EMITTED the repetition loop.
    2. The mechanism is a black box. We never looked inside Whisper.

  A 3-second smoke test (tone + silence) reproduces the loop (token 7322 x224) with
  compression_ratio=37, no_speech_prob=0.82 (encoder: "no speech"), avg_logprob=-0.065
  (decoder: highly confident). The loop is a CONFIDENT LOOP under an input the encoder
  flags as silent -- an encoder/decoder decoupling, not a confidence collapse.

RQs / hypotheses (CER is post-hoc evaluation only; never a routing input):
  RQ-M (mechanism)   H-M: catastrophic tracks (CER>1) show high no_speech_prob + high
                     avg_logprob + low token-id entropy vs non-catastrophic => confident
                     loop / decoupling. Kill: catastrophic tracks instead show low
                     avg_logprob (true uncertainty collapse).
  RQ-D (latency)     H-D: a token-repetition lock-in detector fires at a smaller emitted-
                     token fraction than the CR guard. Honest scope: detection AUC is NOT
                     expected to beat CR (already AUC=1.0 here) -- the contribution is
                     CAUSAL LATENCY. Kill: lock-in latency >= CR latency.
  RQ-C (deployable)  H-C: a causal router (prefix-only signals) loses a measurable share
                     of the offline routing gain. Kill: causal recovers >=80% of offline.
                     H-C': a causal-internal-abort router recovers more than causal-CR.
                     Kill: causal-internal <= causal-CR.

Useful even if it fails: a confident-loop negative is the first model-level mechanistic
characterization in this repo; a causal-deployability negative is a "the offline router
is streaming-safe" result; either way the detector latency ladder (lock-in << CR) is new.

Labels: experimental/frontier; references synthetic/silver (Whisper-small on clean
snippets). ASR = Whisper-tiny (only model cached offline). Stable tables untouched; all
outputs in results/frontier/causal_hallucination_probe/. CER/reference never a routing
input.

Literature note (see litreview doc): the confident-loop mechanism is now named in the
2025-26 literature (Aparin 2026; Waldendorf ACL 2026; Calm-Whisper; Viakhirev). The
genuinely novel slot here is (1) token-id repetition lock-in as an EARLY CAUSAL trip-wire
and (2) quantifying the offline-CR router's gain decay under causal prefix forcing, for
the separation-tax oracle-silence regime. We EXTEND the confident-attractor line; we do
not claim to discover it. Whisper-CD shows decode-time *intervention* survives causally,
so H-C is scoped to *output-metric gating*, not decode-time intervention.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "causal_hallucination_probe"
SNIPPETS_DIR = PROJECT_ROOT / "resources" / "snippets"
SR = 16000
CATASTROPHIC_CER = 1.0  # separation_tax convention: hypothesis longer than reference => tail
GUARD_THRESHOLD = 2.4  # Whisper's own default compression_ratio_threshold (principled, not CER-tuned)


# --------------------------------------------------------------------------------------
# Pure helpers (no Whisper / no audio -- unit tested directly)
# --------------------------------------------------------------------------------------
def compression_ratio(text: str) -> float:
    """Whisper-faithful compression ratio: len(raw utf-8) / len(gzip(raw)). 0 for empty."""
    if not text:
        return 0.0
    raw = text.encode("utf-8")
    comp = gzip.compress(raw, mtime=0)  # mtime=0 -> deterministic header
    if not comp:
        return 0.0
    return len(raw) / len(comp)


def prefix_compression_ratios(text: str, fracs: list[float]) -> list[float]:
    """CR over each character-prefix fraction of ``text`` (the causal CR trajectory)."""
    n = len(text)
    out: list[float] = []
    for f in fracs:
        k = int(round(n * float(f)))
        out.append(compression_ratio(text[:max(0, k)]))
    return out


def cr_causal_latency_fraction(
    text: str, threshold: float = GUARD_THRESHOLD, n_steps: int = 40
) -> float | None:
    """Smallest character-prefix fraction at which CR(prefix) > threshold (the causal
    detection latency of the EXISTING output signal). None if it never fires."""
    if not text:
        return None
    n = len(text)
    for i in range(1, n_steps + 1):
        f = i / n_steps
        k = max(1, int(round(n * f)))
        if compression_ratio(text[:k]) > threshold:
            return round(f, 6)
    return None


def repetition_lockin_index(tokens: list[int], min_run: int = 3, max_period: int = 12) -> int | None:
    """Index of the first token at which the decoder has locked into a repetition loop of
    ANY period p in [1, max_period] -- i.e. the suffix is ``min_run`` exact repetitions of
    some length-p unit. p=1 catches single-token loops (token 7322 x N); p=6 catches
    phrase loops ("你是不是在那里" x N). Returns the smallest such index (the moment the
    lock-in is detectable in the causal stream), else None. This is the causal trip-wire --
    see litreview, the novel signal. ``min_run`` defaults to 3 (need >=3 reps to call it)."""
    n = len(tokens)
    for j in range(n):
        for p in range(1, max_period + 1):
            need = min_run * p
            start = j + 1 - need
            if start < 0:
                continue
            unit = tokens[start:start + p]
            if all(tokens[start + k] == unit[k % p] for k in range(need)):
                return j
    return None


def lockin_latency_fraction(tokens: list[int], min_run: int = 3) -> float | None:
    """Lock-in index normalized to [0,1] of the emitted-token stream. None if no lock-in."""
    idx = repetition_lockin_index(tokens, min_run=min_run)
    n = len(tokens)
    if idx is None or n <= 1:
        return None
    return round(idx / (n - 1), 6)


def dominant_token_fraction(tokens: list[int]) -> float:
    """Max single-token-id count / total. 1.0 = a fully locked single-token loop."""
    if not tokens:
        return 0.0
    _, counts = np.unique(np.asarray(tokens), return_counts=True)
    return float(counts.max() / counts.sum())


def token_id_entropy(tokens: list[int]) -> float:
    """Shannon entropy (nats) over the token-id histogram. ~0 for a locked repeat."""
    if not tokens:
        return 0.0
    _, counts = np.unique(np.asarray(tokens), return_counts=True)
    p = counts / counts.sum()
    return float(-(p * np.log(p)).sum())


def confident_loop_anomaly(
    no_speech_prob: float, avg_logprob: float, tokens: list[int]
) -> dict[str, float]:
    """Mechanism vector for the encoder/decoder decoupling.

    ``decoder_confidence`` = exp(avg_logprob) in [0,1] (high = decoder confident).
    ``confident_silent_score`` = no_speech_prob * decoder_confidence (high iff the
    encoder flags silence WHILE the decoder is confident -- the confident-loop signature).
    """
    conf = float(np.exp(avg_logprob))  # avg_logprob is mean log-prob; exp -> [0,1] proxy
    dom = dominant_token_fraction(tokens)
    return {
        "no_speech_prob": float(no_speech_prob),
        "decoder_confidence": conf,
        "dominant_token_fraction": dom,
        "confident_silent_score": float(no_speech_prob) * conf,
    }


def _mean(xs: list[float]) -> float:
    xs = [x for x in xs if x == x]  # drop NaN
    return float(np.mean(xs)) if xs else float("nan")


def rank_auc(scores: list[float], labels: list[int]) -> float:
    """AUC via Mann-Whitney U. 0.5 if either class empty."""
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


def summarize_probe(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate per-arm rows into mechanism, latency, and AUC tables."""
    cat = [r for r in rows if r.get("catastrophic")]
    clean = [r for r in rows if not r.get("catastrophic")]

    def m(key: str, group: list[dict[str, Any]]) -> float:
        return round(_mean([float(r.get(key, float("nan"))) for r in group]), 6)

    mechanism = {
        "n_arms": len(rows),
        "n_catastrophic": len(cat),
        "n_clean": len(clean),
        "catastrophic_mean_no_speech_prob": m("no_speech_prob", cat),
        "clean_mean_no_speech_prob": m("no_speech_prob", clean),
        "catastrophic_mean_avg_logprob": m("avg_logprob", cat),
        "clean_mean_avg_logprob": m("avg_logprob", clean),
        "catastrophic_mean_token_entropy": m("token_entropy", cat),
        "clean_mean_token_entropy": m("token_entropy", clean),
        "catastrophic_mean_dominant_token_fraction": m("dominant_token_fraction", cat),
        "clean_mean_dominant_token_fraction": m("dominant_token_fraction", clean),
        "catastrophic_mean_confident_silent_score": m("confident_silent_score", cat),
        "clean_mean_confident_silent_score": m("confident_silent_score", clean),
    }

    cr_lats = [float(r["cr_lat_frac"]) for r in rows if r.get("cr_lat_frac") is not None]
    lock_lats = [float(r["lockin_lat_frac"]) for r in rows if r.get("lockin_lat_frac") is not None]
    cr_mean = float(np.mean(cr_lats)) if cr_lats else float("nan")
    lock_mean = float(np.mean(lock_lats)) if lock_lats else float("nan")
    latency = {
        "cr_mean_lat_frac_where_fires": round(cr_mean, 6) if cr_mean == cr_mean else None,
        "lockin_mean_lat_frac_where_fires": round(lock_mean, 6) if lock_mean == lock_mean else None,
        "n_cr_fired": len(cr_lats),
        "n_lockin_fired": len(lock_lats),
        "lockin_earlier_than_cr": bool(lock_mean == lock_mean and cr_mean == cr_mean and lock_mean < cr_mean),
    }

    labels = [1 if r.get("catastrophic") else 0 for r in rows]
    auc = {
        "n_pos": sum(labels),
        "n_neg": len(labels) - sum(labels),
        "auc_compression_ratio": round(rank_auc([float(r.get("compression_ratio", 0.0)) for r in rows], labels), 6),
        "auc_no_speech_prob": round(rank_auc([float(r.get("no_speech_prob", 0.0)) for r in rows], labels), 6),
        "auc_confident_silent_score": round(rank_auc([float(r.get("confident_silent_score", 0.0)) for r in rows], labels), 6),
        "auc_dominant_token_fraction": round(rank_auc([float(r.get("dominant_token_fraction", 0.0)) for r in rows], labels), 6),
    }
    return {"mechanism": mechanism, "latency": latency, "auc": auc}


def deployability_regrets(rows: list[dict[str, Any]], abort_frac_cap: float) -> dict[str, Any]:
    """Causal-deployability simulation (RQ-C). Each row is one (pair,overlap,arm) condition with
    ``cer_mixed`` (the fallback), ``cer_sep`` (the separated-route CER), a ``catastrophic`` flag
    (full-segment CR guard would catch it offline), ``cr_lat_frac`` (prefix fraction at which the
    CR guard fires causally; None = never within the stream) and ``lockin_lat_frac`` (prefix
    fraction at which the token-id lock-in fires; None = never).

    Policies (references used ONLY to score regret, never to route):
      fixed_mixed / fixed_sep     : always use one arm.
      offline_guard               : sep unless catastrophic (full-seg CR catches it) -> mixed.
      causal_cr                   : sep unless CR fires within ``abort_frac_cap`` -> abort to mixed.
      causal_internal             : sep unless lock-in fires within ``abort_frac_cap`` -> abort.
    """
    def policy_cer(use_mixed_when: Any) -> list[float]:
        out = []
        for r in rows:
            cm, cs = float(r["cer_mixed"]), float(r["cer_sep"])
            out.append(cm if use_mixed_when(r) else cs)
        return out

    def mean(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 6) if xs else 0.0

    fixed_mixed = policy_cer(lambda r: True)
    fixed_sep = policy_cer(lambda r: False)
    offline_guard = policy_cer(lambda r: bool(r.get("catastrophic")))
    causal_cr = policy_cer(
        lambda r: r.get("cr_lat_frac") is not None and float(r["cr_lat_frac"]) <= abort_frac_cap
    )
    causal_internal = policy_cer(
        lambda r: r.get("lockin_lat_frac") is not None and float(r["lockin_lat_frac"]) <= abort_frac_cap
    )
    oracle = [min(float(r["cer_mixed"]), float(r["cer_sep"])) for r in rows]

    oracle_cer = mean(oracle)
    og_cer = mean(offline_guard)
    fm_cer = mean(fixed_mixed)
    fs_cer = mean(fixed_sep)
    ccr_cer = mean(causal_cr)
    cin_cer = mean(causal_internal)
    return {
        "n": len(rows),
        "abort_frac_cap": abort_frac_cap,
        "oracle_cer": oracle_cer,
        "offline_guard_cer": og_cer,
        "fixed_mixed_cer": fm_cer,
        "fixed_sep_cer": fs_cer,
        "causal_cr_cer": ccr_cer,
        "causal_internal_cer": cin_cer,
        "offline_guard_regret": round(og_cer - oracle_cer, 6),
        "fixed_mixed_regret": round(fm_cer - oracle_cer, 6),
        "fixed_sep_regret": round(fs_cer - oracle_cer, 6),
        "causal_cr_regret": round(ccr_cer - oracle_cer, 6),
        "causal_internal_regret": round(cin_cer - oracle_cer, 6),
    }


# --------------------------------------------------------------------------------------
# Whisper-dependent driver (reuses the separation_tax harness)
# --------------------------------------------------------------------------------------
def _arm_internals(segments: list[dict[str, Any]], full_text: str) -> dict[str, Any]:
    """Reduce a decoded arm's raw Whisper segments to the internal-state + causal-latency
    signals. ``segments`` carry per-segment tokens/avg_logprob/no_speech_prob/compression_ratio."""
    tokens_all: list[int] = []
    nsp_vals: list[float] = []
    logp_vals: list[float] = []
    cr_vals: list[float] = []
    for seg in segments or []:
        toks = seg.get("tokens") or []
        tokens_all.extend(int(t) for t in toks)
        if seg.get("no_speech_prob") is not None:
            nsp_vals.append(float(seg["no_speech_prob"]))
        if seg.get("avg_logprob") is not None:
            logp_vals.append(float(seg["avg_logprob"]))
        if seg.get("compression_ratio") is not None:
            cr_vals.append(float(seg["compression_ratio"]))
    mean_logp = float(np.mean(logp_vals)) if logp_vals else 0.0
    anom = confident_loop_anomaly(
        no_speech_prob=(max(nsp_vals) if nsp_vals else 0.0),
        avg_logprob=mean_logp,
        tokens=tokens_all,
    )
    return {
        "n_tokens": len(tokens_all),
        "no_speech_prob": anom["no_speech_prob"],
        "avg_logprob": round(mean_logp, 6),
        "decoder_confidence": round(anom["decoder_confidence"], 6),
        "dominant_token_fraction": anom["dominant_token_fraction"],
        "token_entropy": round(token_id_entropy(tokens_all), 6),
        "confident_silent_score": round(anom["confident_silent_score"], 6),
        "compression_ratio": round(max(cr_vals) if cr_vals else 0.0, 6),
        "cr_lat_frac": cr_causal_latency_fraction(full_text, threshold=GUARD_THRESHOLD),
        "lockin_lat_frac": lockin_latency_fraction(tokens_all, min_run=3),
    }


def _decode(model: Any, wav: np.ndarray) -> tuple[str, list[dict[str, Any]]]:
    """Greedy Whisper-tiny decode -> (text, raw segments with internals)."""
    result = model.transcribe(
        np.ascontiguousarray(np.asarray(wav, dtype=np.float32)),
        language="zh", verbose=False, fp16=False,
        temperature=0.0, condition_on_previous_text=False,
    )
    segs = result.get("segments", []) or []
    return str(result.get("text", "")).strip(), segs


def _agg_sep(sep1_int: dict[str, Any], sep2_int: dict[str, Any]) -> dict[str, Any]:
    """Aggregate the separated-route internal signals across the two speaker tracks. For the
    causal-latency signals we take the EARLIEST fire across arms (min over non-None); for the
    mechanism signals we take the most loop-like extreme (max confidence/nsp/dominant, min entropy)."""
    def earliest(k: str) -> Any:
        vals = [v for v in (sep1_int.get(k), sep2_int.get(k)) if v is not None]
        return min(vals) if vals else None

    return {
        "no_speech_prob": round(max(sep1_int["no_speech_prob"], sep2_int["no_speech_prob"]), 6),
        "avg_logprob": round(max(sep1_int["avg_logprob"], sep2_int["avg_logprob"]), 6),
        "decoder_confidence": round(max(sep1_int["decoder_confidence"], sep2_int["decoder_confidence"]), 6),
        "token_entropy": round(min(sep1_int["token_entropy"], sep2_int["token_entropy"]), 6),
        "dominant_token_fraction": round(max(sep1_int["dominant_token_fraction"], sep2_int["dominant_token_fraction"]), 6),
        "confident_silent_score": round(max(sep1_int["confident_silent_score"], sep2_int["confident_silent_score"]), 6),
        "compression_ratio": round(max(sep1_int["compression_ratio"], sep2_int["compression_ratio"]), 6),
        "cr_lat_frac": earliest("cr_lat_frac"),
        "lockin_lat_frac": earliest("lockin_lat_frac"),
    }


def discover_cases(
    model: Any, ratios: list[float], con_files: list[Path], pro_files: list[Path],
    pair_limit: int | None = None,
) -> list[dict[str, Any]]:
    """Phase 1 -- exhaustive discovery. For every (con, pro) x ratio, decode ONLY the sep2
    (leading-silence / pro) track and flag catastrophic. This finds the natural catastrophic
    case set without cherry-picking. Returns one row per (con,pro,ratio)."""
    from .evaluate_cer import compute_cer
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .separation_tax_phase import load_snippet_reference

    pairs = [(c, p) for c in con_files for p in pro_files]
    if pair_limit:
        pairs = pairs[:pair_limit]
    print(f"[causal-probe] discovery: {len(pairs)} pairs x {len(ratios)} ratios (sep2 only)", flush=True)
    out: list[dict[str, Any]] = []
    for ci, (con_path, pro_path) in enumerate(pairs):
        s1 = read_mono_audio(con_path)
        s2 = read_mono_audio(pro_path)
        pro_ref = load_snippet_reference(pro_path)
        for ratio in ratios:
            _, _, track2, _ = build_mixture(s1, s2, float(ratio))
            text, segs = _decode(model, np.asarray(track2, dtype=np.float32))
            cer = compute_cer(pro_ref, text)["cer"]
            cat = bool(cer > CATASTROPHIC_CER)
            out.append({
                "con": con_path.stem, "pro": pro_path.stem, "overlap_ratio": float(ratio),
                "sep2_cer": round(cer, 6), "catastrophic": cat,
            })
            if cat:
                print(f"  [DISCOVER-CAT] {con_path.stem}/{pro_path.stem} r={ratio} sep2 CER={cer:.2f}", flush=True)
        if (ci + 1) % 30 == 0:
            print(f"  ...discovery {ci + 1}/{len(pairs)} pairs done", flush=True)
    return out


def run_probe(
    out_dir: Path, discover_ratios: list[float], analyze_ratios: list[float],
    n_controls: int = 20, pair_limit: int | None = None,
) -> dict[str, Any]:
    """Two-phase case-control probe.

    Phase 1 (discover): exhaustively decode sep2 over all con x pro at ``discover_ratios`` to
    find the natural catastrophic case set (no cherry-picking).
    Phase 2 (analyze): for every discovered catastrophic (con,pro,ratio) case PLUS a matched
    clean control sample, decode all 3 arms (mixed, sep1, sep2) and reduce to per-condition
    separated-route internal signals + cer_mixed/cer_sep for the deployability simulation.
    """
    import whisper

    from .evaluate_cer import compute_cer
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .separation_tax_phase import load_snippet_reference

    out_dir.mkdir(parents=True, exist_ok=True)
    con_files = sorted(SNIPPETS_DIR.glob("con_*.wav"))
    pro_files = sorted(SNIPPETS_DIR.glob("pro_*.wav"))
    model = whisper.load_model("tiny")

    # ---- Phase 1: discovery ----
    discovered = discover_cases(model, discover_ratios, con_files, pro_files, pair_limit=pair_limit)
    (out_dir / "discovery.csv").write_text(
        "".join("con,pro,overlap_ratio,sep2_cer,catastrophic\n")
        + "".join(f'{d["con"]},{d["pro"]},{d["overlap_ratio"]},{d["sep2_cer"]},{int(d["catastrophic"])}\n' for d in discovered),
        encoding="utf-8",
    )
    case_keys = [(d["con"], d["pro"], d["overlap_ratio"]) for d in discovered if d["catastrophic"]]
    clean_pool = [(d["con"], d["pro"], d["overlap_ratio"]) for d in discovered if not d["catastrophic"]]
    # deterministic control sample (stride, no randomness -- Date/random unavailable in some contexts)
    controls = clean_pool[:: max(1, len(clean_pool) // n_controls)][:n_controls] if clean_pool else []
    print(f"[causal-probe] discovery: {len(case_keys)} catastrophic cases, "
          f"{len(controls)} clean controls selected", flush=True)

    # ---- Phase 2: analyze cases + controls over analyze_ratios ----
    # Build the set of (con,pro,ratio) conditions to fully decode: cases at their discovering
    # ratio, plus cases AND controls at the broader analyze_ratios for the deployability curve.
    conds: set[tuple[str, str, float]] = set()
    for con, pro, r in case_keys:
        conds.add((con, pro, float(r)))
        for ar in analyze_ratios:
            conds.add((con, pro, float(ar)))
    for con, pro, r in controls:
        conds.add((con, pro, float(r)))
    print(f"[causal-probe] analysis: {len(conds)} conditions x 3 arms", flush=True)

    clip_cache: dict[str, Any] = {}

    def clip(stem: str):
        if stem not in clip_cache:
            clip_cache[stem] = read_mono_audio(SNIPPETS_DIR / f"{stem}.wav")
        return clip_cache[stem]

    rows: list[dict[str, Any]] = []
    for con, pro, ratio in sorted(conds):
        mixed, t1, t2, _ = build_mixture(clip(con), clip(pro), float(ratio))
        con_ref = load_snippet_reference(SNIPPETS_DIR / f"{con}.wav")
        pro_ref = load_snippet_reference(SNIPPETS_DIR / f"{pro}.wav")
        both_ref = con_ref + pro_ref
        m_text, m_segs = _decode(model, np.asarray(mixed, dtype=np.float32))
        s1_text, s1_segs = _decode(model, np.asarray(t1, dtype=np.float32))
        s2_text, s2_segs = _decode(model, np.asarray(t2, dtype=np.float32))
        m_int = _arm_internals(m_segs, m_text)
        s1_int = _arm_internals(s1_segs, s1_text)
        s2_int = _arm_internals(s2_segs, s2_text)
        cer_mixed = compute_cer(both_ref, m_text)["cer"]
        cer_sep = compute_cer(both_ref, s1_text + s2_text)["cer"]
        agg = _agg_sep(s1_int, s2_int)
        row = {
            "con": con, "pro": pro, "overlap_ratio": round(float(ratio), 4),
            "cer_mixed": round(cer_mixed, 6), "cer_sep": round(cer_sep, 6),
            "catastrophic": bool(cer_sep > CATASTROPHIC_CER),
            **agg,
        }
        rows.append(row)
        if row["catastrophic"]:
            print(
                f"  [CASE] {con}/{pro} r={ratio} CER_sep={cer_sep:.2f} CER_mixed={cer_mixed:.2f} "
                f"nsp={agg['no_speech_prob']:.2f} logp={agg['avg_logprob']:.3f} cr={agg['compression_ratio']:.1f} "
                f"dom={agg['dominant_token_fraction']:.2f} ent={agg['token_entropy']:.2f} "
                f"cr_lat={agg['cr_lat_frac']} lock_lat={agg['lockin_lat_frac']}",
                flush=True,
            )

    rows_path = out_dir / "probe_rows.csv"
    _write_rows(rows_path, rows)
    summary = summarize_probe(rows)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # deployability over a few causal abort caps
    dep = {f"cap_{cap}": deployability_regrets(rows, abort_frac_cap=cap) for cap in (0.05, 0.15, 0.30, 1.0)}
    (out_dir / "deployability.json").write_text(json.dumps(dep, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[causal-probe] wrote probe_rows.csv ({len(rows)} conditions), summary.json, deployability.json", flush=True)
    lat = summary["latency"]
    if lat.get("lockin_earlier_than_cr"):
        print(f"[causal-probe] H-D SUPPORTED: lock-in ({lat['lockin_mean_lat_frac_where_fires']}) "
              f"< CR ({lat['cr_mean_lat_frac_where_fires']})", flush=True)
    mech = summary["mechanism"]
    if mech["n_catastrophic"] and mech["n_clean"]:
        conf_loop = (mech["catastrophic_mean_avg_logprob"] > mech["clean_mean_avg_logprob"]
                     and mech["catastrophic_mean_token_entropy"] < mech["clean_mean_token_entropy"])
        print(f"[causal-probe] H-M {'SUPPORTED' if conf_loop else 'NOT supported'}: "
              f"cat_logp={mech['catastrophic_mean_avg_logprob']} clean_logp={mech['clean_mean_avg_logprob']} "
              f"cat_ent={mech['catastrophic_mean_token_entropy']} clean_ent={mech['clean_mean_token_entropy']}", flush=True)
    return {"summary": summary, "deployability": dep, "n_conditions": len(rows)}


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    keys = [
        "con", "pro", "overlap_ratio", "cer_mixed", "cer_sep", "catastrophic",
        "no_speech_prob", "avg_logprob", "decoder_confidence", "token_entropy",
        "dominant_token_fraction", "confident_silent_score", "compression_ratio",
        "cr_lat_frac", "lockin_lat_frac",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(keys)
        for r in rows:
            w.writerow([r.get(k, "") for k in keys])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Causal & internal-state hallucination probe (frontier).")
    p.add_argument("--discover-ratios", type=str, default="0.1",
                   help="comma-separated overlap ratios for exhaustive sep2 discovery (default 0.1)")
    p.add_argument("--analyze-ratios", type=str, default="0.1,0.3,0.5",
                   help="comma-separated overlap ratios for the full 3-arm analysis curve (default 0.1,0.3,0.5)")
    p.add_argument("--controls", type=int, default=20, help="matched clean control conditions (default 20)")
    p.add_argument("--smoke", action="store_true", help="tiny smoke (discovery on a 6-pair subset)")
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    discover = [float(x) for x in args.discover_ratios.split(",") if x.strip()]
    analyze = [float(x) for x in args.analyze_ratios.split(",") if x.strip()]
    pair_limit = 6 if args.smoke else None
    run_probe(out_dir, discover, analyze, n_controls=args.controls, pair_limit=pair_limit)


if __name__ == "__main__":
    main()
