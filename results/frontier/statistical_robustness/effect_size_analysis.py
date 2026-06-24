#!/usr/bin/env python3
"""Effect size and post-hoc power analysis for the 21 frontier findings (RQ11).

Builds on ``bh_correction.py`` (RQ3, issue #882). For each of the 21 numbered
findings this script computes:

* **Cohen's d** — standardized effect size (mean difference / pooled SD, or
  2r/sqrt(1-r^2) for correlations).
* **Hedges' g** — small-sample corrected d via the correction factor
  J = 1 - 3/(4*df - 1).
* **95% CI for d** — analytical approximation (Hedges & Olkin 1985 for t-tests;
  Fisher-z for correlations).
* **Post-hoc power** at two-sided alpha=0.05 given the observed d and n.
  For t-tests the noncentral t CDF is evaluated via Gauss-Laguerre quadrature
  over the chi-squared mixing distribution (accurate for small n where the
  normal approximation overestimates power); for correlations the Fisher-z
  normal approximation is used.
* **MDE** (minimum detectable effect) at 80% power in d units.
* **Classification**: practically significant (|d|>0.5 AND power>0.80),
  underpowered (|d|>0.5 AND power<0.80), or genuinely small (|d|<0.5).

This is a REANALYSIS ONLY: no new data is collected. Raw per-track CSV/JSON
artifacts under ``results/`` are re-read; the BH correction table from RQ3 is
reused for survival status.

Label: ``experimental/frontier``.

Dependencies: numpy + pandas (project env). scipy is NOT required — the
normal CDF uses ``math.erf``; the t-distribution quantiles reuse the
implementations in ``bh_correction.py``.
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from dataclasses import dataclass, field, asdict

import numpy as np

# Reuse the statistical core and data-extraction helpers from bh_correction.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bh_correction as bh  # noqa: E402

ROOT = bh.ROOT
RESULTS = bh.RESULTS
OUT_DIR = bh.OUT_DIR

# Convenience aliases for the statistical functions implemented in bh_correction
_read_csv = bh.read_csv
_to_float = bh._to_float
_sep_tax_rows = bh._sep_tax_rows
t_cdf = bh.t_cdf
t_sf = bh.t_sf
t_ppf = bh.t_ppf
norm_ppf = bh.norm_ppf
mean = bh.mean
sd = bh.sd


# --------------------------------------------------------------------------- #
# Normal CDF (uses math.erf, available in the Python standard library)
# --------------------------------------------------------------------------- #
def norm_cdf(x: float) -> float:
    """Standard-normal CDF via erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_sf(x: float) -> float:
    return 1.0 - norm_cdf(x)


# --------------------------------------------------------------------------- #
# Noncentral t CDF via Gauss-Laguerre quadrature
# --------------------------------------------------------------------------- #
# Pre-compute Gauss-Laguerre nodes/weights (100-point, sufficient for all df
# encountered here: 2 to 287).  These approximate  integral_0^inf f(u) e^{-u} du
# as  sum_i w_i f(u_i).
_GL_NODES, _GL_WEIGHTS = np.polynomial.laguerre.laggauss(100)


def nct_cdf(t: float, df: float, delta: float) -> float:
    """CDF of the noncentral t-distribution with df and noncentrality delta.

    Uses the representation T = (Z + delta) / sqrt(V/df) where Z ~ N(0,1) and
    V ~ chi2(df).  Conditioning on V:

        F(t; df, delta) = E_V[ Phi(t * sqrt(V/df) - delta) ]

    With the substitution u = V/2 (so u ~ Gamma(df/2, 1)):

        F = (1/Gamma(df/2)) * integral_0^inf Phi(t*sqrt(2u/df) - delta) u^{df/2-1} e^{-u} du

    evaluated by Gauss-Laguerre quadrature in log-space (to avoid overflow for
    large df).  Accurate even for df=2 (n=3) where the normal approximation
    badly overestimates power.
    """
    if df <= 0:
        return float("nan")
    half_df = df / 2.0
    log_gamma = math.lgamma(half_df)
    exponent = half_df - 1.0
    # Compute in log-space: term = w * Phi(arg) * u^exponent
    #   = exp(log(w) + exponent*log(u)) * Phi(arg)
    # The Gauss-Laguerre weight w already includes e^{-u}; we add log(w) + exponent*log(u).
    log_s = float("-inf")  # log of running sum (logsumexp)
    for u, w in zip(_GL_NODES, _GL_WEIGHTS):
        if u <= 0 or w <= 0:
            continue
        arg = t * math.sqrt(2.0 * u / df) - delta
        phi_val = norm_cdf(arg)
        if phi_val <= 0:
            continue
        log_term = math.log(w) + exponent * math.log(u) + math.log(phi_val)
        # logsumexp accumulation
        if log_s == float("-inf"):
            log_s = log_term
        else:
            if log_term > log_s:
                log_s = log_term + math.log1p(math.exp(log_s - log_term))
            else:
                log_s = log_s + math.log1p(math.exp(log_term - log_s))
    if log_s == float("-inf"):
        return 0.0
    val = math.exp(log_s - log_gamma)
    return min(max(val, 0.0), 1.0)


def nct_power_two_sided(d: float, n: int, n2: int, test_category: str,
                         alpha: float = 0.05) -> float:
    """Post-hoc power for a two-sided t-test using the noncentral t CDF.

    Noncentrality parameter:
        one-sample / paired:  delta = d * sqrt(n)
        two-sample:           delta = d * sqrt(n1*n2/(n1+n2))

    Power = P(T > t_crit) + P(T < -t_crit)  where T ~ nct(df, delta)
          = 1 - F(t_crit; df, delta) + F(-t_crit; df, delta)
    """
    if test_category in ("one-sample", "paired"):
        df = n - 1
        delta = d * math.sqrt(n)
    elif test_category == "two-sample":
        n1 = n
        df = n1 + n2 - 2
        delta = d * math.sqrt(n1 * n2 / (n1 + n2))
    else:
        return float("nan")
    if df < 1:
        return float("nan")
    t_crit = t_ppf(1.0 - alpha / 2.0, df)
    power = 1.0 - nct_cdf(t_crit, df, delta) + nct_cdf(-t_crit, df, delta)
    return min(max(power, 0.0), 1.0)


# --------------------------------------------------------------------------- #
# Finding raw-data records
# --------------------------------------------------------------------------- #
@dataclass
class FindingData:
    """Raw data extracted for one finding, sufficient for effect-size math."""
    finding_id: str
    short_name: str
    claim: str
    test_category: str  # "one-sample", "paired", "two-sample", "correlation", "insufficient"
    n: int
    n2: int = 0  # second group size for two-sample
    mean_diff: float = float("nan")  # mean of differences (paired/one-sample) or mean1-mean2 (two-sample)
    sd_diff: float = float("nan")  # SD of differences (paired/one-sample) or pooled SD (two-sample)
    r_value: float = float("nan")  # Pearson r for correlation findings
    direction: str = ""  # sign of the claimed effect: "positive" or "negative"
    bh_survives: bool = False
    in_bh_family: bool = True
    is_null: bool = False  # F15 null finding
    raw_p: float = float("nan")
    bh_adj_p: float = float("nan")
    note: str = ""
    data_source: str = ""


# --------------------------------------------------------------------------- #
# Per-finding raw-data extraction (mirrors bh_correction.finding_NN but returns
# the intermediate mean/SD needed for Cohen's d).
# --------------------------------------------------------------------------- #
def extract_01() -> FindingData:
    rows = [r for r in _sep_tax_rows() if _to_float(r["overlap_ratio"]) <= 0.15]
    delta = [_to_float(r["cer_mixed"]) - _to_float(r["cer_sep"]) for r in rows]
    md = mean(delta)
    sdd = sd(delta)
    return FindingData("F01", "separation_tax_low_overlap",
                       "Separation hurts ASR at low overlap (not universally beneficial)",
                       "one-sample", len(delta), mean_diff=md, sd_diff=sdd,
                       direction="negative",
                       data_source="separation_tax/phase_curve.csv")


def extract_02() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "tables", "cer_results.csv"))
    cases = {"NoOverlap", "HeavyOverlap", "OppositeOverlap"}
    mixed, sep = [], []
    for r in rows:
        if r["case_id"] in cases and r["method"] == "mixed_whisper":
            mixed.append(_to_float(r["cer"]))
        if r["case_id"] in cases and r["method"] == "separated_whisper":
            sep.append(_to_float(r["cer"]))
    d = [m - s for m, s in zip(mixed, sep)]
    return FindingData("F02", "gold_benefit_separation",
                       "NoOverlap/Heavy/Opposite benefit from separated ASR",
                       "paired", len(d), mean_diff=mean(d), sd_diff=sd(d),
                       direction="positive", note="n=3 gold cases; underpowered",
                       data_source="tables/cer_results.csv")


def extract_03() -> FindingData:
    rows = [r for r in _sep_tax_rows() if _to_float(r["overlap_ratio"]) <= 0.15]
    rep_mixed = [_to_float(r["rep_mixed"]) for r in rows]
    rep_sep = [max(_to_float(r["rep_sep1"]), _to_float(r["rep_sep2"])) for r in rows]
    d = [a - b for a, b in zip(rep_sep, rep_mixed)]
    return FindingData("F03", "repetition_hallucination_mechanism",
                       "Low-overlap separation tax driven by repetition/insertion hallucination",
                       "paired", len(d), mean_diff=mean(d), sd_diff=sd(d),
                       direction="positive",
                       data_source="separation_tax/phase_curve.csv")


def extract_05() -> FindingData:
    cer = _read_csv(os.path.join(RESULTS, "tables", "synthetic_cer_results.csv"))
    dec = _read_csv(os.path.join(RESULTS, "tables", "synthetic_routing_decisions.csv"))
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
    d = [a - b for a, b in zip(v1_cer, orc)]
    return FindingData("F05", "router_v1_fails_synthetic",
                       "Overlap-only router v1 fails on synthetic silver validation",
                       "paired", len(d), mean_diff=mean(d), sd_diff=sd(d),
                       direction="positive",
                       data_source="tables/synthetic_cer_results.csv + synthetic_routing_decisions.csv")


def extract_06() -> FindingData:
    cer = _read_csv(os.path.join(RESULTS, "tables", "synthetic_cer_results.csv"))
    d1 = _read_csv(os.path.join(RESULTS, "tables", "synthetic_routing_decisions.csv"))
    d2 = _read_csv(os.path.join(RESULTS, "tables", "synthetic_routing_decisions_v2.csv"))
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
    d = [a - b for a, b in zip(v1c, v2c)]
    return FindingData("F06", "router_v2_improves_synthetic",
                       "Feature router v2 improves robustness over v1 on synthetic",
                       "paired", len(d), mean_diff=mean(d), sd_diff=sd(d),
                       direction="positive",
                       data_source="tables/synthetic_cer_results.csv + routing_decisions_v2.csv")


def extract_07() -> FindingData:
    cer = _read_csv(os.path.join(RESULTS, "tables", "cer_results.csv"))
    sel = _read_csv(os.path.join(RESULTS, "tables", "risk_aware_selection.csv"))
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
    d = [a - b for a, b in zip(ra, orc)]
    return FindingData("F07", "risk_aware_not_best_cer",
                       "Risk-aware selector is a deployability layer, not the best-CER result",
                       "paired", len(d), mean_diff=mean(d), sd_diff=sd(d),
                       direction="positive", note="n=5 gold; underpowered, mostly zero regrets",
                       data_source="tables/cer_results.csv + risk_aware_selection.csv")


def extract_10() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "frontier", "runtime_cascade", "cascade_curve.csv"))
    tiny = [_to_float(r["cer_tiny"]) for r in rows]
    base = [_to_float(r["cer_base"]) for r in rows]
    d = [a - b for a, b in zip(tiny, base)]
    return FindingData("F10", "compute_cascade_base_better",
                       "Base model eliminates the separation tax (base<tiny) in the compute cascade",
                       "paired", len(d), mean_diff=mean(d), sd_diff=sd(d),
                       direction="positive",
                       data_source="runtime_cascade/cascade_curve.csv")


def extract_11() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "frontier", "noise_robust_gate", "gate_curve.csv"))
    noisy = [r for r in rows if r.get("snr_db") not in (None, "", "None", "clean")]
    sep = [_to_float(r["cer_sep"]) for r in noisy]
    gate = [_to_float(r["cer_flatness_relenergy_gate"]) for r in noisy]
    d = [a - b for a, b in zip(sep, gate)]
    return FindingData("F11", "noise_robust_gate_cure",
                       "Flatness+rel-energy gate recovers the separation-hallucination cure under noise",
                       "paired", len(d), mean_diff=mean(d), sd_diff=sd(d),
                       direction="positive",
                       data_source="noise_robust_gate/gate_curve.csv")


def extract_12() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "frontier", "speaker_conditioned_gate", "speaker_gate_curve.csv"))
    sub = [r for r in rows if r.get("noise_type") == "babble" and _to_float(r["snr_db"]) in (5.0, 10.0)]
    sep = [_to_float(r["cer_sep"]) for r in sub]
    spk = [_to_float(r["cer_speaker_gate"]) for r in sub]
    d = [a - b for a, b in zip(sep, spk)]
    return FindingData("F12", "speaker_gate_moderate_babble",
                       "Speaker-conditioned gate beats raw separation at moderate babble (5-10 dB)",
                       "paired", len(d), mean_diff=mean(d), sd_diff=sd(d),
                       direction="positive",
                       data_source="speaker_conditioned_gate/speaker_gate_curve.csv")


def extract_13() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "frontier", "gate_selector", "selector_curve.csv"))
    sel = [_to_float(r["cer_selector"]) for r in rows]
    spk = [_to_float(r["cer_speaker_gate"]) for r in rows]
    d = [a - b for a, b in zip(sel, spk)]
    return FindingData("F13", "gate_selector_falsified",
                       "Reference-free gate selector does NOT beat always-speaker (H1 falsified)",
                       "paired", len(d), mean_diff=mean(d), sd_diff=sd(d),
                       direction="positive",
                       data_source="gate_selector/selector_curve.csv")


def extract_14() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "frontier", "emotion_separation_tax", "crosslink_curve_a015.csv"))
    sub = [r for r in rows if _to_float(r["overlap_ratio"]) in (0.1, 0.3)]
    eb = [_to_float(r["emotion_benefit"]) for r in sub]
    return FindingData("F14", "emotion_no_separation_tax",
                       "Separation helps (not hurts) emotion at low/mid overlap (no emotion tax)",
                       "one-sample", len(eb), mean_diff=mean(eb), sd_diff=sd(eb),
                       direction="positive",
                       data_source="emotion_separation_tax/crosslink_curve_a015.csv")


def extract_15() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "frontier", "arousal_asr_probe", "arousal_probe_curve.csv"))
    ar = [_to_float(r["arousal"]) for r in rows]
    cer = [_to_float(r["cer"]) for r in rows]
    x = np.asarray(ar, dtype=float)
    y = np.asarray(cer, dtype=float)
    rx, ry = x - x.mean(), y - y.mean()
    denom = math.sqrt(float((rx * rx).sum()) * float((ry * ry).sum()))
    r = float((rx * ry).sum() / denom) if denom != 0 else float("nan")
    return FindingData("F15", "arousal_null_predictor",
                       "Arousal does NOT predict ASR difficulty (null result)",
                       "correlation", len(ar), r_value=r, direction="null",
                       in_bh_family=False, is_null=True,
                       note="NULL finding: consistent with H0 (p>0.05); excluded from BH rejection family",
                       data_source="arousal_asr_probe/arousal_probe_curve.csv")


def extract_16() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "frontier", "lexical_emotion_tax", "lexical_tax_curve.csv"))
    sub = [r for r in rows if _to_float(r["overlap_ratio"]) in (0.1, 0.3)]
    cb = [_to_float(r["cer_benefit"]) for r in sub]
    return FindingData("F16", "lexical_tax_cer_reproduction",
                       "CER separation tax reproduced at low/mid overlap (lexical-emotion study)",
                       "one-sample", len(cb), mean_diff=mean(cb), sd_diff=sd(cb),
                       direction="negative",
                       data_source="lexical_emotion_tax/lexical_tax_curve.csv")


def extract_17() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "frontier", "llm_asr_critic", "critic_curve.csv"))
    before = [_to_float(r["cer_before"]) for r in rows]
    after = [_to_float(r["cer_after"]) for r in rows]
    d = [a - b for a, b in zip(after, before)]
    return FindingData("F17", "llm_repair_net_harm",
                       "Local-LLM GER repair net-harms CER (over-correction)",
                       "paired", len(d), mean_diff=mean(d), sd_diff=sd(d),
                       direction="positive",
                       data_source="llm_asr_critic/critic_curve.csv")


def extract_18() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "frontier", "objective_aware_routing", "routing_curve.csv"))
    coupled, decoupled = [], []
    for r in rows:
        emo_mixed = _to_float(r["emo_mixed"])
        emo_sep = _to_float(r["emo_sep"])
        route = r.get("text_route", "")
        c = emo_mixed if route == "mixed" else emo_sep
        coupled.append(c)
        decoupled.append(emo_sep)
    d = [a - b for a, b in zip(coupled, decoupled)]
    return FindingData("F18", "objective_aware_decoupling",
                       "Objective-aware decoupled routing cuts emotion distortion vs coupled switch",
                       "paired", len(d), mean_diff=mean(d), sd_diff=sd(d),
                       direction="positive",
                       data_source="objective_aware_routing/routing_curve.csv")


def extract_19() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "frontier", "emotion_fidelity_meter", "fidelity_curve.csv"))
    meter = [_to_float(r["meter"]) for r in rows]
    alpha = [_to_float(r["alpha"]) for r in rows]
    x = np.asarray(meter, dtype=float)
    y = np.asarray(alpha, dtype=float)
    rx, ry = x - x.mean(), y - y.mean()
    denom = math.sqrt(float((rx * rx).sum()) * float((ry * ry).sum()))
    r = float((rx * ry).sum() / denom) if denom != 0 else float("nan")
    return FindingData("F19", "emotion_fidelity_meter_corr",
                       "Reference-free emotion-fidelity meter falls as separation degrades (r<0 with alpha)",
                       "correlation", len(meter), r_value=r, direction="negative",
                       data_source="emotion_fidelity_meter/fidelity_curve.csv")


def extract_20() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "frontier", "gate_emotion_cost", "gate_emotion_curve.csv"))
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
    d = [a - b for a, b in zip(flat, spk)]
    return FindingData("F20", "gate_emotion_cost_speaker_least",
                       "Speaker gate damages emotion less than flatness gate (least emotion-damaging cure)",
                       "paired", len(d), mean_diff=mean(d), sd_diff=sd(d),
                       direction="positive",
                       data_source="gate_emotion_cost/gate_emotion_curve.csv")


def extract_21() -> FindingData:
    rows = _read_csv(os.path.join(RESULTS, "frontier", "causal_hallucination_probe", "probe_rows.csv"))
    cat = [_to_float(r["avg_logprob"]) for r in rows if r.get("catastrophic") == "True"]
    clean = [_to_float(r["avg_logprob"]) for r in rows if r.get("catastrophic") == "False"]
    m1, m2 = mean(cat), mean(clean)
    v1, v2 = float(np.var(cat, ddof=1)), float(np.var(clean, ddof=1))
    n1, n2 = len(cat), len(clean)
    sp = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    return FindingData("F21", "causal_confident_attractor",
                       "Catastrophic separation-tax routes decode with higher decoder confidence (confident attractor)",
                       "two-sample", n1, n2=n2, mean_diff=m1 - m2, sd_diff=sp,
                       direction="positive",
                       data_source="causal_hallucination_probe/probe_rows.csv")


def extract_insufficient(fid, name, claim, source, note) -> FindingData:
    return FindingData(fid, name, claim, "insufficient", 0, note=note,
                       in_bh_family=False, data_source=source)


def collect_finding_data():
    return [
        extract_01(),
        extract_02(),
        extract_03(),
        extract_insufficient("F04", "speaker_swap_not_dominant",
                             "Speaker swap is not the dominant error source in the 5 gold cases",
                             "tables/speaker_cer_results.csv",
                             "Descriptive error-composition claim; no per-error-count hypothesis test possible"),
        extract_05(),
        extract_06(),
        extract_07(),
        extract_insufficient("F08", "synthetic_silver_label",
                             "Synthetic benchmarks are silver robustness validation, not gold evaluation",
                             "docs/project_state.md",
                             "Labeling/methodology claim; not an inferential hypothesis"),
        extract_insufficient("F09", "llm_rag_optional",
                             "LLM/RAG is optional future extension, not core quantitative contribution",
                             "docs/project_state.md",
                             "Methodology statement; no quantitative hypothesis to test"),
        extract_10(),
        extract_11(),
        extract_12(),
        extract_13(),
        extract_14(),
        extract_15(),
        extract_16(),
        extract_17(),
        extract_18(),
        extract_19(),
        extract_20(),
        extract_21(),
    ]


# --------------------------------------------------------------------------- #
# Load BH survival status from the existing correction table
# --------------------------------------------------------------------------- #
def load_bh_status():
    """Return {finding_id: (raw_p, bh_adj_p, survives, in_bh_family)}."""
    path = os.path.join(OUT_DIR, "correction_table.csv")
    status = {}
    for r in _read_csv(path):
        fid = r["finding_id"]
        raw_p = _to_float(r["raw_p"])
        adj_p = _to_float(r["bh_corrected_p"])
        survives = r["survives_q005"].strip().lower() == "true"
        in_family = r["test_type"] != "insufficient data" and fid != "F15"
        status[fid] = (raw_p, adj_p, survives, in_family)
    return status


# --------------------------------------------------------------------------- #
# Effect-size computation
# --------------------------------------------------------------------------- #
def cohen_d(fd: FindingData) -> float:
    """Cohen's d for the finding.

    one-sample / paired: d = mean_diff / sd_diff
    two-sample:           d = (mean1 - mean2) / pooled_sd   (mean_diff already = m1-m2)
    correlation:          d = 2r / sqrt(1 - r^2)
    """
    if fd.test_category in ("one-sample", "paired"):
        if not (fd.sd_diff == fd.sd_diff) or fd.sd_diff == 0:
            return float("nan")
        return fd.mean_diff / fd.sd_diff
    if fd.test_category == "two-sample":
        if not (fd.sd_diff == fd.sd_diff) or fd.sd_diff == 0:
            return float("nan")
        return fd.mean_diff / fd.sd_diff
    if fd.test_category == "correlation":
        r = fd.r_value
        if not (r == r) or abs(r) >= 1.0:
            return float("nan")
        return 2.0 * r / math.sqrt(1.0 - r * r)
    return float("nan")


def hedges_correction_factor(fd: FindingData) -> float:
    """J = 1 - 3/(4*df - 1) where df depends on the test.

    one-sample / paired: df = n - 1
    two-sample:          df = n + n2 - 2
    correlation:         df = n - 2
    """
    if fd.test_category in ("one-sample", "paired"):
        df = fd.n - 1
    elif fd.test_category == "two-sample":
        df = fd.n + fd.n2 - 2
    elif fd.test_category == "correlation":
        df = fd.n - 2
    else:
        return float("nan")
    if df < 1:
        return float("nan")
    return 1.0 - 3.0 / (4.0 * df - 1.0)


def hedges_g(fd: FindingData, d: float) -> float:
    if not (d == d):
        return float("nan")
    j = hedges_correction_factor(fd)
    if not (j == j):
        return float("nan")
    return d * j


def d_ci(fd: FindingData, d: float, conf: float = 0.95):
    """95% CI for Cohen's d.

    t-tests: analytical SE (Hedges & Olkin 1985, eq. 8.17/8.25).
    correlation: Fisher-z transform.
    Returns (low, high).
    """
    if not (d == d):
        return float("nan"), float("nan")
    alpha_ci = 1.0 - conf
    if fd.test_category in ("one-sample", "paired"):
        n = fd.n
        se = math.sqrt(1.0 / n + d * d / (2.0 * n))
        tcrit = t_ppf(1.0 - alpha_ci / 2.0, n - 1)
        return d - tcrit * se, d + tcrit * se
    if fd.test_category == "two-sample":
        n1, n2 = fd.n, fd.n2
        se = math.sqrt((n1 + n2) / (n1 * n2) + d * d / (2.0 * (n1 + n2 - 2)))
        tcrit = t_ppf(1.0 - alpha_ci / 2.0, n1 + n2 - 2)
        return d - tcrit * se, d + tcrit * se
    if fd.test_category == "correlation":
        r = fd.r_value
        if not (r == r) or abs(r) >= 1.0:
            return float("nan"), float("nan")
        z = math.atanh(r)
        se_z = 1.0 / math.sqrt(fd.n - 3)
        zcrit = norm_ppf(1.0 - alpha_ci / 2.0)
        r_lo = math.tanh(z - zcrit * se_z)
        r_hi = math.tanh(z + zcrit * se_z)
        # convert r bounds to d bounds
        d_lo = 2.0 * r_lo / math.sqrt(1.0 - r_lo * r_lo) if abs(r_lo) < 1.0 else float("nan")
        d_hi = 2.0 * r_hi / math.sqrt(1.0 - r_hi * r_hi) if abs(r_hi) < 1.0 else float("nan")
        return min(d_lo, d_hi), max(d_lo, d_hi)
    return float("nan"), float("nan")


def post_hoc_power(fd: FindingData, d: float, alpha: float = 0.05) -> float:
    """Post-hoc power for a two-sided test at the given alpha.

    For t-tests (one-sample, paired, two-sample) the noncentral t CDF is
    evaluated via Gauss-Laguerre quadrature (see ``nct_cdf``), which is
    accurate for small n where the normal approximation overestimates power.

    For correlations the Fisher-z normal approximation is used (standard and
    accurate for n >= 20).

    Noncentrality parameter:
        one-sample / paired:  delta = d * sqrt(n)
        two-sample:           delta = d * sqrt(n1*n2/(n1+n2))
        correlation:          delta = atanh(r) * sqrt(n-3)
    """
    if not (d == d):
        return float("nan")
    if fd.test_category in ("one-sample", "paired", "two-sample"):
        return nct_power_two_sided(d, fd.n, fd.n2, fd.test_category, alpha)
    if fd.test_category == "correlation":
        z_crit = norm_ppf(1.0 - alpha / 2.0)
        r = fd.r_value
        if not (r == r) or abs(r) >= 1.0:
            return float("nan")
        z_r = math.atanh(r)
        delta = z_r * math.sqrt(fd.n - 3)
        power = norm_cdf(delta - z_crit) + norm_cdf(-delta - z_crit)
        return min(max(power, 0.0), 1.0)
    return float("nan")


def mde_d(fd: FindingData, alpha: float = 0.05, power: float = 0.80) -> float:
    """Minimum detectable effect in d units at the given power.

    Inverts the two-sided t-test using the t-distribution (consistent with
    bh_correction.mde_paired / mde_two_sample / mde_correlation, but expressed
    in standardized d units rather than raw units).
    """
    if fd.test_category in ("one-sample", "paired"):
        n = fd.n
        if n < 2:
            return float("nan")
        df = n - 1
        t_crit = t_ppf(1.0 - alpha / 2.0, df)
        t_pow = t_ppf(power, df)
        return (t_crit + t_pow) / math.sqrt(n)
    if fd.test_category == "two-sample":
        n1, n2 = fd.n, fd.n2
        if n1 + n2 < 3:
            return float("nan")
        df = n1 + n2 - 2
        t_crit = t_ppf(1.0 - alpha / 2.0, df)
        t_pow = t_ppf(power, df)
        return (t_crit + t_pow) * math.sqrt(1.0 / n1 + 1.0 / n2)
    if fd.test_category == "correlation":
        n = fd.n
        if n < 4:
            return float("nan")
        z_crit = norm_ppf(1.0 - alpha / 2.0)
        z_pow = norm_ppf(power)
        mde_r = math.tanh((z_crit + z_pow) / math.sqrt(n - 3))
        if abs(mde_r) >= 1.0:
            return float("nan")
        return 2.0 * mde_r / math.sqrt(1.0 - mde_r * mde_r)
    return float("nan")


def classify(fd: FindingData, d: float, power: float) -> str:
    """Classify the finding.

    - practically_significant: |d| > 0.5 AND power > 0.80
    - underpowered:            |d| > 0.5 AND power < 0.80
    - genuinely_small:         |d| <= 0.5
    - insufficient_data:       no test possible
    - null_finding:            F15 (reported separately)
    """
    if fd.test_category == "insufficient":
        return "insufficient_data"
    if fd.is_null:
        # F15: classify by effect size for completeness, but tag as null
        if not (d == d):
            return "null_finding"
        return "null_finding" if abs(d) <= 0.5 else "null_finding_large_effect"
    if not (d == d) or not (power == power):
        return "indeterminate"
    if abs(d) <= 0.5:
        return "genuinely_small"
    if power > 0.80:
        return "practically_significant"
    return "underpowered"


# --------------------------------------------------------------------------- #
# Output helpers
# --------------------------------------------------------------------------- #
def fnum(x):
    return bh.fnum(x)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    findings = collect_finding_data()
    bh_status = load_bh_status()

    # Attach BH survival status
    for fd in findings:
        if fd.finding_id in bh_status:
            raw_p, adj_p, survives, in_family = bh_status[fd.finding_id]
            fd.raw_p = raw_p
            fd.bh_adj_p = adj_p
            fd.bh_survives = survives
            fd.in_bh_family = in_family

    # Compute effect sizes for each finding
    results = []
    for fd in findings:
        d = cohen_d(fd)
        g = hedges_g(fd, d)
        ci_lo, ci_hi = d_ci(fd, d)
        power = post_hoc_power(fd, d, alpha=0.05)
        mde = mde_d(fd, alpha=0.05, power=0.80)
        cls = classify(fd, d, power)
        results.append({
            "finding_id": fd.finding_id,
            "short_name": fd.short_name,
            "claim": fd.claim,
            "test_category": fd.test_category,
            "n": fd.n,
            "n2": fd.n2,
            "mean_diff": fd.mean_diff,
            "sd_diff": fd.sd_diff,
            "r_value": fd.r_value,
            "cohen_d": d,
            "hedges_g": g,
            "d_ci_low": ci_lo,
            "d_ci_high": ci_hi,
            "post_hoc_power_alpha05": power,
            "mde_d_80pct_power": mde,
            "classification": cls,
            "bh_survives": fd.bh_survives,
            "in_bh_family": fd.in_bh_family,
            "is_null": fd.is_null,
            "raw_p": fd.raw_p,
            "bh_adj_p": fd.bh_adj_p,
            "data_source": fd.data_source,
            "note": fd.note,
        })

    # ---- write CSV ----
    csv_path = os.path.join(OUT_DIR, "effect_size_table.csv")
    cols = [
        "finding_id", "short_name", "claim", "test_category", "n", "n2",
        "mean_diff", "sd_diff", "r_value",
        "cohen_d", "hedges_g", "d_ci_low", "d_ci_high",
        "post_hoc_power_alpha05", "mde_d_80pct_power",
        "classification", "bh_survives", "in_bh_family", "is_null",
        "raw_p", "bh_adj_p", "data_source", "note",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in results:
            w.writerow([fnum(r[c]) if isinstance(r[c], float) else r[c] for c in cols])

    # ---- summary stats ----
    # BH family directional findings (exclude insufficient + F15 null)
    directional = [r for r in results if r["in_bh_family"]]
    survivors = [r for r in directional if r["bh_survives"]]
    non_survivors = [r for r in directional if not r["bh_survives"]]

    n_practically_sig = sum(1 for r in results if r["classification"] == "practically_significant")
    n_underpowered = sum(1 for r in results if r["classification"] == "underpowered")
    n_genuinely_small = sum(1 for r in results if r["classification"] == "genuinely_small")
    n_insufficient = sum(1 for r in results if r["classification"] == "insufficient_data")
    n_null = sum(1 for r in results if r["classification"].startswith("null_finding"))

    # RQ1: Are all 6 BH-surviving findings practically significant (|d| > 0.5)?
    survivors_with_d = [r for r in survivors if r["cohen_d"] == r["cohen_d"]]
    survivors_practically_sig = [r for r in survivors if r["classification"] == "practically_significant"]
    survivors_underpowered = [r for r in survivors if r["classification"] == "underpowered"]
    survivors_small = [r for r in survivors if r["classification"] == "genuinely_small"]
    rq1_all_practically_sig = len(survivors_small) == 0 and len(survivors_underpowered) == 0

    # RQ2: Are >50% of the 11 non-surviving findings underpowered (|d|>0.5 but power<0.80)?
    non_surv_underpowered = [r for r in non_survivors if r["classification"] == "underpowered"]
    non_surv_small = [r for r in non_survivors if r["classification"] == "genuinely_small"]
    non_surv_practically_sig = [r for r in non_survivors if r["classification"] == "practically_significant"]
    rq2_majority_underpowered = len(non_surv_underpowered) > len(non_survivors) / 2.0

    # RQ3: Do the 9 underpowered findings from the RQ3 FINDINGS.md match?
    # The RQ3 FINDINGS.md lists: F02, F03, F05, F06, F07, F11, F12, F16, F17, F20
    # (10 listed, but the text says "9"; F13 is excluded as a well-powered falsification).
    # We compare the RQ3 underpowered set against our |d|>0.5 & power<0.80 set.
    rq3_underpowered_ids = {"F02", "F03", "F05", "F06", "F07", "F11", "F12", "F16", "F17", "F20"}
    our_underpowered_ids = {r["finding_id"] for r in results if r["classification"] == "underpowered"}
    rq3_match = rq3_underpowered_ids == our_underpowered_ids
    rq3_intersection = rq3_underpowered_ids & our_underpowered_ids
    rq3_only_rq3 = rq3_underpowered_ids - our_underpowered_ids
    rq3_only_ours = our_underpowered_ids - rq3_underpowered_ids

    # ---- write JSON ----
    json_path = os.path.join(OUT_DIR, "effect_size_results.json")
    payload = {
        "label": "experimental/frontier",
        "method": {
            "effect_size": "Cohen's d (mean_diff / pooled SD for t-tests; 2r/sqrt(1-r^2) for correlations)",
            "hedges_g": "d * J, J = 1 - 3/(4*df - 1) (small-sample correction)",
            "ci": "95% CI: analytical SE (Hedges & Olkin 1985) for t-tests; Fisher-z for correlations",
            "power": "Post-hoc power at two-sided alpha=0.05. t-tests: noncentral t CDF via Gauss-Laguerre quadrature (accurate for small n). Correlations: Fisher-z normal approximation.",
            "mde": "Minimum detectable effect at 80% power in d units (t-distribution inversion)",
            "classification": {
                "practically_significant": "|d| > 0.5 AND power > 0.80",
                "underpowered": "|d| > 0.5 AND power < 0.80",
                "genuinely_small": "|d| <= 0.5",
            },
            "note": "scipy unavailable; normal CDF via math.erf, t-quantiles via bh_correction.py. Reanalysis only; no new data.",
        },
        "n_findings_total": len(results),
        "n_directional_in_bh_family": len(directional),
        "n_bh_survivors": len(survivors),
        "n_non_survivors": len(non_survivors),
        "classification_breakdown": {
            "practically_significant": n_practically_sig,
            "underpowered": n_underpowered,
            "genuinely_small": n_genuinely_small,
            "insufficient_data": n_insufficient,
            "null_finding": n_null,
        },
        "research_questions": {
            "RQ1": {
                "question": "Are all 6 BH-surviving findings practically significant (|d| > 0.5)?",
                "verdict": "SUPPORTED" if rq1_all_practically_sig else "NOT FULLY SUPPORTED",
                "n_survivors": len(survivors),
                "n_practically_significant": len(survivors_practically_sig),
                "n_underpowered": len(survivors_underpowered),
                "n_genuinely_small": len(survivors_small),
                "survivor_ids": [r["finding_id"] for r in survivors],
                "practically_significant_ids": [r["finding_id"] for r in survivors_practically_sig],
                "underpowered_survivor_ids": [r["finding_id"] for r in survivors_underpowered],
                "small_survivor_ids": [r["finding_id"] for r in survivors_small],
            },
            "RQ2": {
                "question": "Are >50% of the 11 non-surviving findings underpowered (|d|>0.5 but power<0.80)?",
                "verdict": "SUPPORTED" if rq2_majority_underpowered else "NOT SUPPORTED",
                "n_non_survivors": len(non_survivors),
                "n_underpowered": len(non_surv_underpowered),
                "n_genuinely_small": len(non_surv_small),
                "n_practically_significant": len(non_surv_practically_sig),
                "majority_threshold": len(non_survivors) / 2.0,
                "underpowered_ids": [r["finding_id"] for r in non_surv_underpowered],
                "genuinely_small_ids": [r["finding_id"] for r in non_surv_small],
            },
            "RQ3": {
                "question": "Do the 9 underpowered findings from RQ3 (FINDINGS.md) match the underpowered group from this power analysis?",
                "rq3_underpowered_ids": sorted(rq3_underpowered_ids),
                "our_underpowered_ids": sorted(our_underpowered_ids),
                "match": rq3_match,
                "intersection": sorted(rq3_intersection),
                "only_in_rq3": sorted(rq3_only_rq3),
                "only_in_rq11": sorted(rq3_only_ours),
                "note": "RQ3 used |observed effect| < MDE (raw units); RQ11 uses |d|>0.5 & power<0.80 (standardized). Differences arise from the standardization and the power vs MDE criterion.",
            },
        },
        "findings": results,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, default=lambda o: None if (isinstance(o, float) and math.isnan(o)) else o)

    # ---- print table ----
    print(f"{'F':>4} {'name':30} {'cat':12} {'n':>5} {'d':>8} {'g':>8} {'CI_lo':>8} {'CI_hi':>8} {'power':>8} {'MDE_d':>8}  classification")
    print("-" * 140)
    for r in results:
        print(f"{r['finding_id']:>4} {r['short_name'][:30]:30} {r['test_category']:12} {r['n']:>5} "
              f"{fnum(r['cohen_d']):>8} {fnum(r['hedges_g']):>8} {fnum(r['d_ci_low']):>8} {fnum(r['d_ci_high']):>8} "
              f"{fnum(r['post_hoc_power_alpha05']):>8} {fnum(r['mde_d_80pct_power']):>8}  {r['classification']}")
    print("-" * 140)
    print(f"Practically significant: {n_practically_sig} | Underpowered: {n_underpowered} | "
          f"Genuinely small: {n_genuinely_small} | Insufficient: {n_insufficient} | Null: {n_null}")
    print(f"\nRQ1 (all 6 survivors practically significant?): {'YES' if rq1_all_practically_sig else 'NO'}")
    print(f"RQ2 (>50% of 11 non-survivors underpowered?): {'YES' if rq2_majority_underpowered else 'NO'} "
          f"({len(non_surv_underpowered)}/{len(non_survivors)})")
    print(f"RQ3 (underpowered set matches RQ3?): {'YES' if rq3_match else 'NO'}")
    if not rq3_match:
        print(f"  RQ3 only:  {sorted(rq3_only_rq3)}")
        print(f"  RQ11 only: {sorted(rq3_only_ours)}")
    print(f"\nWrote: {csv_path}")
    print(f"Wrote: {json_path}")


if __name__ == "__main__":
    main()
