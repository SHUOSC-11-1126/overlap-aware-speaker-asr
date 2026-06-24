#!/usr/bin/env python3
"""Statistical robustness audit of the 21 frontier findings (Issue #882, RQ3).

Applies Benjamini-Hochberg (BH) multiple-comparison correction at q=0.05 and
post-hoc power analysis (minimum detectable effect at 80% power) across the 21
numbered findings documented in ``docs/project_state.md``.

This is a REANALYSIS ONLY: no new data is collected. p-values are computed from
the existing raw CSV/JSON artifacts under ``results/`` (stable tables + frontier
dirs). Where a finding's data is insufficient for an inferential test it is
recorded as "insufficient data" and excluded from the BH family.

Label: ``experimental/frontier``.

Dependencies: numpy + pandas (both available in the project env). scipy is NOT
required -- the Student-t CDF/inverse and BH procedure are implemented here from
first principles (regularized incomplete beta via continued fractions, Numerical
Recipes), so the script runs under the bare project python.
"""

from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import dataclass, field, asdict

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
RESULTS = os.path.join(ROOT, "results")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------- #
# Statistical core (pure python + numpy; no scipy)
# --------------------------------------------------------------------------- #
def _betacf(a: float, b: float, x: float) -> float:
    MAXIT, EPS, FPMIN = 300, 3e-14, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    bt = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_cdf(t: float, df: float) -> float:
    """CDF of Student's t distribution."""
    if df <= 0:
        return float("nan")
    x = df / (df + t * t)
    half = 0.5 * betai(df / 2.0, 0.5, x)
    return 1.0 - half if t > 0 else half


def t_sf(t: float, df: float) -> float:
    return 1.0 - t_cdf(t, df)


def t_ppf(p: float, df: float) -> float:
    """Inverse CDF of Student's t via bisection (robust, no scipy)."""
    if p <= 0.0:
        return -float("inf")
    if p >= 1.0:
        return float("inf")
    lo, hi = -500.0, 500.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-10:
            break
    return 0.5 * (lo + hi)


def norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF (Acklam's rational approximation)."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow = 0.02425
    phigh = 1.0 - plow
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    if p <= phigh:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
               (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
           ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)


def mean(xs):
    return float(np.mean(xs)) if len(xs) else float("nan")


def sd(xs, ddof=1):
    return float(np.std(xs, ddof=ddof)) if len(xs) > ddof else float("nan")


def one_sample_t(xs, mu0=0.0):
    """One-sample t-test of H0: mean==mu0. Returns (t, df, two_sided_p)."""
    xs = np.asarray(xs, dtype=float)
    n = len(xs)
    if n < 2:
        return float("nan"), n - 1, float("nan")
    m = float(np.mean(xs))
    s = float(np.std(xs, ddof=1))
    if s == 0.0:
        # No variation: degenerate. p = 0 if m != mu0 else 1.
        return (0.0 if m == mu0 else float("inf")), n - 1, (1.0 if m == mu0 else 0.0)
    t = (m - mu0) / (s / math.sqrt(n))
    df = n - 1
    p = 2.0 * t_sf(abs(t), df)
    return t, df, min(max(p, 0.0), 1.0)


def paired_t(x, y):
    """Paired t-test on differences x-y. Returns (t, df, two_sided_p, mean_diff, sd_diff)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    d = x - y
    t, df, p = one_sample_t(d, 0.0)
    return t, df, p, mean(d), sd(d)


def two_sample_t(x, y):
    """Welch's two-sample t-test. Returns (t, df, two_sided_p, mean_diff, pooled_sd)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n1, n2 = len(x), len(y)
    if n1 < 2 or n2 < 2:
        return float("nan"), float("nan"), float("nan"), float("nan"), float("nan")
    m1, m2 = float(np.mean(x)), float(np.mean(y))
    v1, v2 = float(np.var(x, ddof=1)), float(np.var(y, ddof=1))
    se = math.sqrt(v1 / n1 + v2 / n2)
    if se == 0.0:
        return (0.0 if m1 == m2 else float("inf")), float("nan"), (1.0 if m1 == m2 else 0.0), m1 - m2, 0.0
    t = (m1 - m2) / se
    df = (v1 / n1 + v2 / n2) ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
    p = 2.0 * t_sf(abs(t), df)
    sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    return t, df, min(max(p, 0.0), 1.0), m1 - m2, sp


def pearson_test(x, y):
    """Pearson correlation test. Returns (r, t, df, two_sided_p)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), n - 2, float("nan")
    rx, ry = x - x.mean(), y - y.mean()
    denom = math.sqrt(float((rx * rx).sum()) * float((ry * ry).sum()))
    if denom == 0.0:
        return float("nan"), float("nan"), n - 2, float("nan")
    r = float((rx * ry).sum() / denom)
    t = r * math.sqrt((n - 2) / max(1e-300, 1.0 - r * r))
    p = 2.0 * t_sf(abs(t), n - 2)
    return r, t, n - 2, min(max(p, 0.0), 1.0)


def bh_correct(pvals, q=0.05):
    """Benjamini-Hochberg FDR correction.

    Returns (adjusted_p, reject) arrays. adjusted_p is the BH-adjusted p-value
    (monotonized step-up). reject[i] is True if the finding survives at level q.
    """
    pvals = list(pvals)
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = float("inf")
    for rank in range(m, 0, -1):  # from largest p (rank m) down to 1
        idx = order[rank - 1]
        val = pvals[idx] * m / rank
        running = min(running, val)
        adj[idx] = min(running, 1.0)
    reject = [a <= q for a in adj]
    return adj, reject


def mde_paired(n, sd_diff, alpha=0.05, power=0.80):
    """Min detectable mean difference (paired/one-sample) at given power."""
    if n < 2 or not (sd_diff == sd_diff) or sd_diff <= 0:
        return float("nan")
    df = n - 1
    t_crit = t_ppf(1.0 - alpha / 2.0, df)
    t_pow = t_ppf(power, df)
    return (t_crit + t_pow) * sd_diff / math.sqrt(n)


def mde_two_sample(n1, n2, pooled_sd, alpha=0.05, power=0.80):
    if n1 + n2 < 3 or not (pooled_sd == pooled_sd) or pooled_sd <= 0:
        return float("nan")
    df = n1 + n2 - 2
    t_crit = t_ppf(1.0 - alpha / 2.0, df)
    t_pow = t_ppf(power, df)
    return (t_crit + t_pow) * pooled_sd * math.sqrt(1.0 / n1 + 1.0 / n2)


def mde_correlation(n, alpha=0.05, power=0.80):
    """Min detectable |r| at given power (Fisher z approximation)."""
    if n < 4:
        return float("nan")
    z = (norm_ppf(1.0 - alpha / 2.0) + norm_ppf(power)) / math.sqrt(n - 3)
    return math.tanh(z)


# --------------------------------------------------------------------------- #
# CSV helpers
# --------------------------------------------------------------------------- #
def read_csv(path):
    # utf-8-sig strips a leading BOM if present (some result CSVs have one).
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def fnum(x):
    if x is None:
        return ""
    if isinstance(x, float):
        if math.isnan(x):
            return "nan"
        if math.isinf(x):
            return "inf" if x > 0 else "-inf"
        return f"{x:.6g}"
    return str(x)


# --------------------------------------------------------------------------- #
# Finding records
# --------------------------------------------------------------------------- #
@dataclass
class Finding:
    finding_id: str
    short_name: str
    claim: str
    test_type: str
    direction: str  # "claim supported by small p" description
    n: int
    raw_p: float
    effect: str  # human-readable effect estimate
    mde: float
    mde_units: str
    data_source: str
    note: str = ""
    in_bh_family: bool = True
    # filled later
    bh_adj_p: float = field(default=float("nan"))
    survives: bool = False


def _to_float(v):
    try:
        if v is None or v == "" or v is None:
            return float("nan")
        return float(v)
    except (ValueError, TypeError):
        return float("nan")


# --------------------------------------------------------------------------- #
# Per-finding analyses
# --------------------------------------------------------------------------- #
def _sep_tax_rows():
    rows = read_csv(os.path.join(RESULTS, "frontier", "separation_tax", "phase_curve.csv"))
    return [r for r in rows if r.get("config") == "greedy"]


def finding_01():
    # Separation hurts ASR at low overlap ("not universally beneficial").
    rows = [r for r in _sep_tax_rows() if _to_float(r["overlap_ratio"]) <= 0.15]
    delta = [_to_float(r["cer_mixed"]) - _to_float(r["cer_sep"]) for r in rows]
    t, df, p2 = one_sample_t(delta, 0.0)
    # claim: mean delta < 0  -> one-sided
    p = p2 / 2.0 if t < 0 else 1.0 - p2 / 2.0
    md = mean(delta)
    sdd = sd(delta)
    return Finding("F01", "separation_tax_low_overlap",
                   "Separation hurts ASR at low overlap (not universally beneficial)",
                   "one-sample t (mean delta_cer<0)", "small p => sep hurts",
                   len(delta), p, f"mean dCER={md:.3f} (mixed-sep)",
                   mde_paired(len(delta), sdd), "dCER", "separation_tax/phase_curve.csv")


def finding_02():
    # Gold: NoOverlap/Heavy/Opposite benefit from separation (sep<mixed).
    rows = read_csv(os.path.join(RESULTS, "tables", "cer_results.csv"))
    cases = {"NoOverlap", "HeavyOverlap", "OppositeOverlap"}
    mixed, sep = [], []
    for r in rows:
        if r["case_id"] in cases and r["method"] == "mixed_whisper":
            mixed.append(_to_float(r["cer"]))
        if r["case_id"] in cases and r["method"] == "separated_whisper":
            sep.append(_to_float(r["cer"]))
    t, df, p2, md, sdd = paired_t(mixed, sep)
    # claim: mixed - sep > 0 (sep better) -> one-sided
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F02", "gold_benefit_separation",
                   "NoOverlap/Heavy/Opposite benefit from separated ASR",
                   "paired t (mixed-sep>0)", "small p => sep better",
                   len(mixed), p, f"mean dCER={md:.3f}",
                   mde_paired(len(mixed), sdd), "dCER", "tables/cer_results.csv",
                   note="n=3 gold cases; underpowered")


def finding_03():
    # Mechanism: separated low-overlap tracks have higher repetition than mixed.
    rows = [r for r in _sep_tax_rows() if _to_float(r["overlap_ratio"]) <= 0.15]
    rep_mixed = [_to_float(r["rep_mixed"]) for r in rows]
    rep_sep = [max(_to_float(r["rep_sep1"]), _to_float(r["rep_sep2"])) for r in rows]
    t, df, p2, md, sdd = paired_t(rep_sep, rep_mixed)
    # claim: rep_sep > rep_mixed -> one-sided
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F03", "repetition_hallucination_mechanism",
                   "Low-overlap separation tax driven by repetition/insertion hallucination",
                   "paired t (rep_sep-rep_mixed>0)", "small p => sep repeats more",
                   len(rep_sep), p, f"mean dRep={md:.2f}",
                   mde_paired(len(rep_sep), sdd), "rep-count", "separation_tax/phase_curve.csv")


def finding_05():
    # Router v1 fails on synthetic: v1 CER > oracle CER (per-sample).
    cer = read_csv(os.path.join(RESULTS, "tables", "synthetic_cer_results.csv"))
    dec = read_csv(os.path.join(RESULTS, "tables", "synthetic_routing_decisions.csv"))
    # per-sample method CER
    by_sample = {}
    for r in cer:
        by_sample.setdefault(r["sample_id"], {})[r["method"]] = _to_float(r["cer"])
    v1_sel = {r["sample_id"]: r["selected_method"] for r in dec}
    v1_cer, orc = [], []
    for sid, methods in by_sample.items():
        if sid not in v1_sel:
            continue
        sel = v1_sel[sid]
        if sel not in methods:
            continue
        v1_cer.append(methods[sel])
        orc.append(min(methods.values()))
    t, df, p2, md, sdd = paired_t(v1_cer, orc)
    # claim: v1 > oracle (fails) -> one-sided
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F05", "router_v1_fails_synthetic",
                   "Overlap-only router v1 fails on synthetic silver validation",
                   "paired t (v1-oracle>0)", "small p => v1 worse than oracle",
                   len(v1_cer), p, f"mean regret={md:.3f}",
                   mde_paired(len(v1_cer), sdd), "dCER",
                   "tables/synthetic_cer_results.csv + synthetic_routing_decisions.csv")


def finding_06():
    # Router v2 improves on synthetic: v1 CER > v2 CER (per-sample).
    cer = read_csv(os.path.join(RESULTS, "tables", "synthetic_cer_results.csv"))
    d1 = read_csv(os.path.join(RESULTS, "tables", "synthetic_routing_decisions.csv"))
    d2 = read_csv(os.path.join(RESULTS, "tables", "synthetic_routing_decisions_v2.csv"))
    by_sample = {}
    for r in cer:
        by_sample.setdefault(r["sample_id"], {})[r["method"]] = _to_float(r["cer"])
    v1_sel = {r["sample_id"]: r["selected_method"] for r in d1}
    v2_sel = {r["sample_id"]: r["selected_method"] for r in d2}
    v1c, v2c = [], []
    for sid, methods in by_sample.items():
        if sid in v1_sel and sid in v2_sel and v1_sel[sid] in methods and v2_sel[sid] in methods:
            v1c.append(methods[v1_sel[sid]])
            v2c.append(methods[v2_sel[sid]])
    t, df, p2, md, sdd = paired_t(v1c, v2c)
    # claim: v1 > v2 (v2 better) -> one-sided
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F06", "router_v2_improves_synthetic",
                   "Feature router v2 improves robustness over v1 on synthetic",
                   "paired t (v1-v2>0)", "small p => v2 better",
                   len(v1c), p, f"mean dCER={md:.3f}",
                   mde_paired(len(v1c), sdd), "dCER",
                   "tables/synthetic_cer_results.csv + routing_decisions_v2.csv")


def finding_07():
    # Risk-aware selector is NOT the best CER (regret>0 vs oracle) on gold.
    cer = read_csv(os.path.join(RESULTS, "tables", "cer_results.csv"))
    sel = read_csv(os.path.join(RESULTS, "tables", "risk_aware_selection.csv"))
    by_case = {}
    for r in cer:
        by_case.setdefault(r["case_id"], {})[r["method"]] = _to_float(r["cer"])
    ra_sel = {r["case_id"]: r["final_selected_method"] for r in sel}
    ra, orc = [], []
    for cid, methods in by_case.items():
        if cid not in ra_sel or ra_sel[cid] not in methods:
            continue
        ra.append(methods[ra_sel[cid]])
        orc.append(min(methods.values()))
    t, df, p2, md, sdd = paired_t(ra, orc)
    # claim: risk_aware > oracle (not best) -> one-sided
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F07", "risk_aware_not_best_cer",
                   "Risk-aware selector is a deployability layer, not the best-CER result",
                   "paired t (risk_aware-oracle>0)", "small p => not best CER",
                   len(ra), p, f"mean regret={md:.3f}",
                   mde_paired(len(ra), sdd), "dCER",
                   "tables/cer_results.csv + risk_aware_selection.csv",
                   note="n=5 gold; underpowered, mostly zero regrets")


def finding_10():
    # Compute-aware cascade: base model eliminates separation tax (base<tiny).
    rows = read_csv(os.path.join(RESULTS, "frontier", "runtime_cascade", "cascade_curve.csv"))
    tiny = [_to_float(r["cer_tiny"]) for r in rows]
    base = [_to_float(r["cer_base"]) for r in rows]
    t, df, p2, md, sdd = paired_t(tiny, base)
    # claim: tiny > base (base better) -> one-sided
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F10", "compute_cascade_base_better",
                   "Base model eliminates the separation tax (base<tiny) in the compute cascade",
                   "paired t (tiny-base>0)", "small p => base better",
                   len(tiny), p, f"mean dCER={md:.3f}",
                   mde_paired(len(tiny), sdd), "dCER", "runtime_cascade/cascade_curve.csv")


def finding_11():
    # Noise-robust gate recovers cure under noise (gate < raw sep, noisy rows).
    rows = read_csv(os.path.join(RESULTS, "frontier", "noise_robust_gate", "gate_curve.csv"))
    noisy = [r for r in rows if r.get("snr_db") not in (None, "", "None", "clean")]
    sep = [_to_float(r["cer_sep"]) for r in noisy]
    gate = [_to_float(r["cer_flatness_relenergy_gate"]) for r in noisy]
    t, df, p2, md, sdd = paired_t(sep, gate)
    # claim: sep > gate (gate better) -> one-sided
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F11", "noise_robust_gate_cure",
                   "Flatness+rel-energy gate recovers the separation-hallucination cure under noise",
                   "paired t (sep-gate>0)", "small p => gate better",
                   len(sep), p, f"mean dCER={md:.3f}",
                   mde_paired(len(sep), sdd), "dCER", "noise_robust_gate/gate_curve.csv")


def finding_12():
    # Speaker gate beats raw sep at moderate babble (5-10 dB).
    rows = read_csv(os.path.join(RESULTS, "frontier", "speaker_conditioned_gate", "speaker_gate_curve.csv"))
    sub = [r for r in rows if r.get("noise_type") == "babble" and _to_float(r["snr_db"]) in (5.0, 10.0)]
    sep = [_to_float(r["cer_sep"]) for r in sub]
    spk = [_to_float(r["cer_speaker_gate"]) for r in sub]
    t, df, p2, md, sdd = paired_t(sep, spk)
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F12", "speaker_gate_moderate_babble",
                   "Speaker-conditioned gate beats raw separation at moderate babble (5-10 dB)",
                   "paired t (sep-speaker>0)", "small p => speaker gate better",
                   len(sep), p, f"mean dCER={md:.3f}",
                   mde_paired(len(sep), sdd), "dCER", "speaker_conditioned_gate/speaker_gate_curve.csv")


def finding_13():
    # Falsification: selector does NOT beat always-speaker (selector > speaker).
    rows = read_csv(os.path.join(RESULTS, "frontier", "gate_selector", "selector_curve.csv"))
    sel = [_to_float(r["cer_selector"]) for r in rows]
    spk = [_to_float(r["cer_speaker_gate"]) for r in rows]
    t, df, p2, md, sdd = paired_t(sel, spk)
    # claim: selector > speaker (selector loses) -> one-sided
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F13", "gate_selector_falsified",
                   "Reference-free gate selector does NOT beat always-speaker (H1 falsified)",
                   "paired t (selector-speaker>0)", "small p => selector loses",
                   len(sel), p, f"mean dCER={md:.3f}",
                   mde_paired(len(sel), sdd), "dCER", "gate_selector/selector_curve.csv")


def finding_14():
    # Emotion has no separation tax: emotion_benefit > 0 at low/mid overlap.
    rows = read_csv(os.path.join(RESULTS, "frontier", "emotion_separation_tax", "crosslink_curve_a015.csv"))
    sub = [r for r in rows if _to_float(r["overlap_ratio"]) in (0.1, 0.3)]
    eb = [_to_float(r["emotion_benefit"]) for r in sub]
    t, df, p2 = one_sample_t(eb, 0.0)
    # claim: emotion_benefit > 0 -> one-sided
    p = p2 / 2.0 if t > 0 else 1.0 - p2 / 2.0
    sdd = sd(eb)
    return Finding("F14", "emotion_no_separation_tax",
                   "Separation helps (not hurts) emotion at low/mid overlap (no emotion tax)",
                   "one-sample t (emotion_benefit>0)", "small p => emotion benefits",
                   len(eb), p, f"mean emo_benefit={mean(eb):.3f}",
                   mde_paired(len(eb), sdd), "emo-benefit", "emotion_separation_tax/crosslink_curve_a015.csv")


def finding_15():
    # NULL: arousal does NOT predict CER. Two-sided correlation test.
    rows = read_csv(os.path.join(RESULTS, "frontier", "arousal_asr_probe", "arousal_probe_curve.csv"))
    ar = [_to_float(r["arousal"]) for r in rows]
    cer = [_to_float(r["cer"]) for r in rows]
    r, t, df, p = pearson_test(ar, cer)
    return Finding("F15", "arousal_null_predictor",
                   "Arousal does NOT predict ASR difficulty (null result)",
                   "Pearson r two-sided (H0: r=0)", "null: large p => consistent with null",
                   len(ar), p, f"r={r:.3f}",
                   mde_correlation(len(ar)), "|r|",
                   "arousal_asr_probe/arousal_probe_curve.csv",
                   note="NULL finding: 'supported' = not refuted (p>0.05); excluded from BH rejection family",
                   in_bh_family=False)


def finding_16():
    # CER separation tax reproduced at low/mid overlap (cer_benefit<0).
    rows = read_csv(os.path.join(RESULTS, "frontier", "lexical_emotion_tax", "lexical_tax_curve.csv"))
    sub = [r for r in rows if _to_float(r["overlap_ratio"]) in (0.1, 0.3)]
    cb = [_to_float(r["cer_benefit"]) for r in sub]
    t, df, p2 = one_sample_t(cb, 0.0)
    # claim: cer_benefit < 0 -> one-sided
    p = p2 / 2.0 if t < 0 else 1.0 - p2 / 2.0
    sdd = sd(cb)
    return Finding("F16", "lexical_tax_cer_reproduction",
                   "CER separation tax reproduced at low/mid overlap (lexical-emotion study)",
                   "one-sample t (cer_benefit<0)", "small p => sep hurts CER",
                   len(cb), p, f"mean cer_benefit={mean(cb):.3f}",
                   mde_paired(len(cb), sdd), "cer-benefit", "lexical_emotion_tax/lexical_tax_curve.csv")


def finding_17():
    # LLM repair net-harms: cer_after > cer_before.
    rows = read_csv(os.path.join(RESULTS, "frontier", "llm_asr_critic", "critic_curve.csv"))
    before = [_to_float(r["cer_before"]) for r in rows]
    after = [_to_float(r["cer_after"]) for r in rows]
    t, df, p2, md, sdd = paired_t(after, before)
    # claim: after > before (net harm) -> one-sided
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F17", "llm_repair_net_harm",
                   "Local-LLM GER repair net-harms CER (over-correction)",
                   "paired t (after-before>0)", "small p => repair harms",
                   len(before), p, f"mean dCER={md:.3f}",
                   mde_paired(len(before), sdd), "dCER", "llm_asr_critic/critic_curve.csv")


def finding_18():
    # Decoupled cuts emotion distortion vs coupled.
    rows = read_csv(os.path.join(RESULTS, "frontier", "objective_aware_routing", "routing_curve.csv"))
    coupled, decoupled = [], []
    for r in rows:
        emo_mixed = _to_float(r["emo_mixed"])
        emo_sep = _to_float(r["emo_sep"])
        route = r.get("text_route", "")
        c = emo_mixed if route == "mixed" else emo_sep
        coupled.append(c)
        decoupled.append(emo_sep)  # decoupled always reads emotion from separated track
    t, df, p2, md, sdd = paired_t(coupled, decoupled)
    # claim: coupled > decoupled (decoupled better) -> one-sided
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F18", "objective_aware_decoupling",
                   "Objective-aware decoupled routing cuts emotion distortion vs coupled switch",
                   "paired t (coupled-decoupled>0)", "small p => decoupled better",
                   len(coupled), p, f"mean dEmo={md:.3f}",
                   mde_paired(len(coupled), sdd), "emo-distortion",
                   "objective_aware_routing/routing_curve.csv")


def finding_19():
    # Emotion fidelity meter correlates with leakage alpha (r<0).
    rows = read_csv(os.path.join(RESULTS, "frontier", "emotion_fidelity_meter", "fidelity_curve.csv"))
    meter = [_to_float(r["meter"]) for r in rows]
    alpha = [_to_float(r["alpha"]) for r in rows]
    r, t, df, p2 = pearson_test(meter, alpha)
    # claim: r < 0 -> one-sided
    p = p2 / 2.0 if t < 0 else 1.0 - p2 / 2.0
    return Finding("F19", "emotion_fidelity_meter_corr",
                   "Reference-free emotion-fidelity meter falls as separation degrades (r<0 with alpha)",
                   "Pearson r one-sided (r<0)", "small p => negative correlation",
                   len(meter), p, f"r={r:.3f}",
                   mde_correlation(len(meter)), "|r|", "emotion_fidelity_meter/fidelity_curve.csv")


def finding_20():
    # Speaker gate damages emotion LESS than flatness gate (paired by track).
    rows = read_csv(os.path.join(RESULTS, "frontier", "gate_emotion_cost", "gate_emotion_curve.csv"))
    by_key = {}
    for r in rows:
        key = (r["pair_id"], r["overlap_ratio"], r["snr_db"])
        cost = _to_float(r["dist_gated"]) - _to_float(r["dist_raw"])
        by_key.setdefault(key, {})[r["gate"]] = cost
    flat, spk = [], []
    for key, costs in by_key.items():
        if "flatness" in costs and "speaker" in costs:
            flat.append(costs["flatness"])
            spk.append(costs["speaker"])
    t, df, p2, md, sdd = paired_t(flat, spk)
    # claim: flatness cost > speaker cost (speaker damages less) -> one-sided
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F20", "gate_emotion_cost_speaker_least",
                   "Speaker gate damages emotion less than flatness gate (least emotion-damaging cure)",
                   "paired t (flatness_cost-speaker_cost>0)", "small p => speaker less damaging",
                   len(flat), p, f"mean dCost={md:.3f}",
                   mde_paired(len(flat), sdd), "emo-cost", "gate_emotion_cost/gate_emotion_curve.csv")


def finding_21():
    # Catastrophic routes decoded with HIGHER confidence (avg_logprob closer to 0).
    rows = read_csv(os.path.join(RESULTS, "frontier", "causal_hallucination_probe", "probe_rows.csv"))
    cat = [_to_float(r["avg_logprob"]) for r in rows if r.get("catastrophic") == "True"]
    clean = [_to_float(r["avg_logprob"]) for r in rows if r.get("catastrophic") == "False"]
    t, df, p2, md, sp = two_sample_t(cat, clean)
    # claim: cat > clean (higher confidence) -> one-sided
    p = p2 / 2.0 if md > 0 else 1.0 - p2 / 2.0
    return Finding("F21", "causal_confident_attractor",
                   "Catastrophic separation-tax routes decode with higher decoder confidence (confident attractor)",
                   "Welch two-sample t (cat>clean)", "small p => cat more confident",
                   len(cat) + len(clean), p, f"mean dLogprob={md:.3f} (n_cat={len(cat)},n_clean={len(clean)})",
                   mde_two_sample(len(cat), len(clean), sp), "avg_logprob",
                   "causal_hallucination_probe/probe_rows.csv")


def insufficient(finding_id, name, claim, source, note):
    return Finding(finding_id, name, claim, "insufficient data", "n/a",
                   0, float("nan"), "n/a", float("nan"), "n/a", source,
                   note=note, in_bh_family=False)


def collect_findings():
    return [
        finding_01(),
        finding_02(),
        finding_03(),
        insufficient("F04", "speaker_swap_not_dominant",
                     "Speaker swap is not the dominant error source in the 5 gold cases",
                     "tables/speaker_cer_results.csv",
                     "Descriptive error-composition claim; no per-error-count hypothesis test possible (n=5 cases, aggregate counts)"),
        finding_05(),
        finding_06(),
        finding_07(),
        insufficient("F08", "synthetic_silver_label",
                     "Synthetic benchmarks are silver robustness validation, not gold evaluation",
                     "docs/project_state.md",
                     "Labeling/methodology claim; not an inferential hypothesis"),
        insufficient("F09", "llm_rag_optional",
                     "LLM/RAG is optional future extension, not core quantitative contribution",
                     "docs/project_state.md",
                     "Methodology statement; no quantitative hypothesis to test"),
        finding_10(),
        finding_11(),
        finding_12(),
        finding_13(),
        finding_14(),
        finding_15(),
        finding_16(),
        finding_17(),
        finding_18(),
        finding_19(),
        finding_20(),
        finding_21(),
    ]


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    findings = collect_findings()

    # BH family = directional findings with computable p (in_bh_family True).
    bh_idx = [i for i, f in enumerate(findings) if f.in_bh_family and not math.isnan(f.raw_p)]
    pvals = [findings[i].raw_p for i in bh_idx]
    adj, reject = bh_correct(pvals, q=0.05)
    for k, i in enumerate(bh_idx):
        findings[i].bh_adj_p = adj[k]
        findings[i].survives = bool(reject[k])

    # F15 (null): survives interpretation = consistent with null (p>0.05)
    for f in findings:
        if f.finding_id == "F15":
            f.survives = (not math.isnan(f.raw_p)) and (f.raw_p > 0.05)
            f.bh_adj_p = f.raw_p  # not in BH family; report raw

    # ---- write CSV ----
    csv_path = os.path.join(OUT_DIR, "correction_table.csv")
    cols = ["finding_id", "short_name", "claim", "test_type", "n", "raw_p",
            "bh_corrected_p", "survives_q005", "MDE_80pct_power", "mde_units",
            "effect", "data_source", "note"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for fd in findings:
            w.writerow([
                fd.finding_id, fd.short_name, fd.claim, fd.test_type, fd.n,
                fnum(fd.raw_p), fnum(fd.bh_adj_p), str(fd.survives),
                fnum(fd.mde), fd.mde_units, fd.effect, fd.data_source, fd.note,
            ])

    # ---- write JSON ----
    json_path = os.path.join(OUT_DIR, "correction_table.json")
    bh_family = [findings[i] for i in bh_idx]
    n_survive_bh = sum(1 for f in bh_family if f.survives)
    n_survive_total = sum(1 for f in findings if f.survives)
    n_insufficient = sum(1 for f in findings if f.test_type == "insufficient data")
    h3_supported = n_survive_total >= 15
    payload = {
        "label": "experimental/frontier",
        "method": {
            "correction": "Benjamini-Hochberg FDR, q=0.05",
            "tests": "one-sided in the direction of each finding's claim (two-sided for the F15 null correlation)",
            "power": "post-hoc minimum detectable effect (MDE) at 80% power, two-sided alpha=0.05",
            "note": "scipy unavailable in env; Student-t CDF/inverse implemented via regularized incomplete beta (continued fractions). Reanalysis only; no new data.",
        },
        "n_findings_total": len(findings),
        "n_in_bh_family": len(bh_family),
        "n_insufficient_data": n_insufficient,
        "n_survive_bh": n_survive_bh,
        "n_survive_total_including_null": n_survive_total,
        "H3": {
            "statement": "Under BH at q=0.05, >=15 of 21 frontier findings' core directional claims remain statistically supported.",
            "supported": h3_supported,
            "survivors": n_survive_total,
            "threshold": 15,
        },
        "findings": [asdict(f) for f in findings],
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # ---- print table ----
    print(f"{'F':>4} {'name':28} {'n':>5} {'raw_p':>10} {'bh_p':>10} {'surv':>5} {'MDE80':>10}  claim")
    print("-" * 120)
    for fd in findings:
        print(f"{fd.finding_id:>4} {fd.short_name[:28]:28} {fd.n:>5} {fnum(fd.raw_p):>10} "
              f"{fnum(fd.bh_adj_p):>10} {str(fd.survives):>5} {fnum(fd.mde):>10}  {fd.claim[:48]}")
    print("-" * 120)
    print(f"BH family size: {len(bh_family)} | survive BH: {n_survive_bh} | "
          f"insufficient: {n_insufficient} | total survive (incl. null F15): {n_survive_total}")
    print(f"H3 (>=15 survive): {'SUPPORTED' if h3_supported else 'NOT SUPPORTED'}")
    print(f"\nWrote: {csv_path}")
    print(f"Wrote: {json_path}")


if __name__ == "__main__":
    main()
