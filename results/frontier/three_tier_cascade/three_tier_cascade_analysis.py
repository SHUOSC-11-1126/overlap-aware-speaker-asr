"""RQ43: 3-tier cascade (tiny -> KL gate -> base) Pareto analysis.

SIMULATION ONLY — no Whisper / no ASR model is run. This script combines two
existing datasets to ask whether a lightweight n-gram KL divergence gate
between whisper-tiny and whisper-base traces a useful compute/cpWER Pareto
frontier (filling Direction 2: compute-aware cascaded recognition with a
3-tier cascade).

Label: experimental/frontier. Closes #955.

Source data
-----------
1. ``results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json``
   (label ``external/sanity-check``, PR #890). 77 AISHELL-4 windows transcribed
   with **whisper-tiny** (``asr_model`` field). The ``separated_text_per_speaker``
   and ``mixed_text`` fields ARE whisper-tiny transcripts, and
   ``always_separated_cpwer`` / ``always_mixed_cpwer`` ARE whisper-tiny cpWER.
   This is the cascade corpus: real tiny transcripts (for the KL gate) + real
   tiny cpWER (for the tiny-route quality).
2. ``results/frontier/model_scale/scale_curve.csv`` (label
   ``experimental/frontier``, Issue #859). 5 speaker pairs x 5 overlap ratios
   with matched whisper-tiny and whisper-base CER. The per-ratio base/tiny CER
   ratio is the cost model that estimates whisper-base cpWER for each AISHELL-4
   window (tiny-base was NOT run on AISHELL-4, so base cpWER is estimated by
   scaling the real tiny cpWER by the model_scale improvement ratio).

Background
----------
The compute-aware cascade analysis (``results/frontier/runtime_cascade/``,
Issue #863) showed a binary cliff: a CR-based gate on whisper-tiny's separated
output either escalates ~everything or ~nothing, with no smooth Pareto
frontier. whisper-tiny separated CER is 0.467 (constant across overlap);
whisper-base separated CER is 0.200 (base eliminates the separation tax) at
1.93x compute. There is no middle tier. This study tests whether an n-gram KL
divergence detector on the tiny transcript (high KL => anomalous / hallucinated
transcript => escalate to base) fills that middle tier.

The referenced RQ34 n-gram KL implementation (``src/llm_semantic_critic.py`` /
``results/frontier/llm_semantic_critic/``) is NOT present in the repository at
the time of this study. The KL computation here is implemented from first
principles. The standard symmetric formulation (both P and Q add-1 smoothed
over the union vocabulary) was tried first and rejected: with V_union = 4116
bigrams and N_p ~ 50 tokens per window, the smoothing damps KL to ~0.09 nats
(max), making the task-specified threshold of 3.30 nats unreachable (cascade
escalates 0% of windows => degenerate Pareto with only the always-tiny /
always-base endpoints, replicating runtime_cascade's binary cliff). The
asymmetric formulation actually used here keeps P empirical and only smooths Q
(add-1 over Q's own support) so P's concentration is preserved; this yields KL
in the [0, ~8.5] nats range with mean ~3.4 nats, making threshold 3.30 a
meaningful operating point (escalates ~74% of windows). A full threshold sweep
[0.0 .. 6.0] traces the Pareto frontier.

Method
------
1. Load AISHELL-4 windows (tiny transcripts + tiny cpWER + overlap_ratio).
2. Load model_scale per-ratio mean CER; compute base/tiny CER ratio per bucket.
3. Estimate base cpWER per window: base_cpwer = tiny_cpwer * (base_cer/tiny_cer)
   at the window's nearest overlap-ratio bucket. (Separated ratio is constant
   0.200/0.467 = 0.4283 across overlap; mixed ratio varies by overlap.)
4. Compute n-gram KL divergence on each window's tiny transcript (separated:
   per-speaker texts concatenated; mixed: the mixed_text) against a corpus-
   pooled background bigram distribution. Asymmetric Laplace: P empirical, Q
   add-1 smoothed over Q's own support; KL in nats (see ``kl_divergence``
   docstring for the formulation choice rationale).
5. 3-tier cascade: tiny on all windows -> KL gate -> escalate to base if
   KL > threshold (3.30). Cascade cpWER = mean(tiny_cpwer if not escalated
   else base_cpwer). Cascade compute = 1.0*(1-f) + 1.93*f where f is the
   escalation fraction (KL gate cost is negligible, folded into the 1.0x).
6. Compare to: always-tiny (1.0x), always-base (1.93x), oracle cascade
   (worst-tiny-cpWER-first ordering = best possible Pareto curve), random
   cascade (seeded, = convex-hull baseline), RQ16 corrected router
   (cpWER 1.04329, reference; different axis: mixed-vs-separated routing).
7. Threshold sweep [0.0 .. 6.0] traces the KL cascade Pareto curve.
8. Pareto classification: a policy is dominated if another has cpWER <= AND
   compute <= with at least one strictly lower.
9. Repeat at char-level (Levenshtein CER per window from ref vs hyp text,
   RQ30/RQ31 tokenisation) and for the mixed-route condition.

Hypotheses
----------
- H43a: 3-tier cascade cpWER < always-tiny cpWER at equal-or-lower compute.
  Success: cascade cpWER < tiny cpWER.
- H43b: 3-tier cascade compute < always-base compute. Success: cascade compute
  < 1.93x.
- H43c: 3-tier cascade is Pareto-optimal (no single-tier policy dominates it).
  Success: no policy has both lower cpWER AND lower compute.

This script is pure reanalysis (numpy + stdlib only; scipy / sklearn / Whisper
are NOT required).
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
AISHELL4_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
MODEL_SCALE_CSV = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "model_scale"
    / "scale_curve.csv"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "three_tier_cascade"
OUT_CSV = OUT_DIR / "three_tier_cascade_results.csv"
OUT_JSON = OUT_DIR / "three_tier_cascade_results.json"
PARETO_CSV = OUT_DIR / "pareto_frontier.csv"

# ------------------------------------------------------------------- constants
KL_THRESHOLD = 3.30                # task-specified primary operating point (nats)
NGRAM_N = 2                        # character bigrams
COMPUTE_TINY = 1.0                 # whisper-tiny relative compute
COMPUTE_BASE = 1.93                # whisper-base relative compute (runtime_cascade FINDINGS)
COMPUTE_KL_GATE = 0.0              # n-gram KL on a short transcript is negligible vs ASR
N_BOOT = 10000
SEED = 42
EPS = 1e-12
RQ16_CORRECTED_ROUTER_CPWER = 1.04329   # RQ16, PR #912 (mixed-vs-separated axis)

THRESHOLD_SWEEP = [
    0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.30, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0,
]


# ------------------------------------------------------------- n-gram extraction
def char_ngrams(text: str, n: int) -> set[str]:
    """Set of character n-grams (whitespace stripped before windowing).

    If the stripped text is shorter than n, the whole stripped string is
    returned as the only element (so very short transcripts still yield a
    distribution). Empty stripped text returns the empty set.
    """
    s = "".join(text.split())
    if not s:
        return set()
    if len(s) < n:
        return {s}
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def ngram_distribution(text: str, n: int) -> dict[str, int]:
    """Frequency map of character n-grams (whitespace stripped)."""
    s = "".join(text.split())
    if not s:
        return {}
    dist: dict[str, int] = {}
    if len(s) < n:
        dist[s] = 1
        return dist
    for i in range(len(s) - n + 1):
        g = s[i:i + n]
        dist[g] = dist.get(g, 0) + 1
    return dist


def build_background_distribution(texts: list[str], n: int) -> dict[str, int]:
    """Corpus-pooled n-gram frequency map (each text whitespace-stripped)."""
    bg: dict[str, int] = {}
    for text in texts:
        dist = ngram_distribution(text, n)
        for g, c in dist.items():
            bg[g] = bg.get(g, 0) + c
    return bg


# ----------------------------------------------------------------- KL divergence
def kl_divergence(p_dist: dict[str, int], q_dist: dict[str, int]) -> float:
    """KL(P || Q) in nats. Asymmetric Laplace smoothing: P empirical (no
    smoothing); Q add-1 smoothed over its OWN support; sum over P's support.

    Formulation:
        p(x) = count_p(x) / N_p                              (empirical)
        q(x) = (count_q(x) + 1) / (N_q + V_q)               (add-1 over Q)
        KL = sum_{x in supp(P)} p(x) * ln(p(x) / q(x))

    where N_p = sum(count_p), N_q = sum(count_q), V_q = |supp(Q)|.

    Why asymmetric (P empirical, Q smoothed): the original both-smoothed-over-
    union-vocab formulation damps KL to ~0.09 nats on this corpus because
    V_union (4116 bigrams) >> N_p (~50 tokens per window), which waters P down
    toward a near-uniform distribution and makes the task-specified threshold
    of 3.30 nats unreachable (cascade escalates 0% of windows => degenerate
    Pareto with only the always-tiny / always-base endpoints). The asymmetric
    formulation preserves P's empirical concentration and only smooths Q to
    keep q(x) > 0 for bigrams that are absent from the corpus background. This
    yields KL values in the [0, ~8.5] nats range with mean ~3.4 nats, so
    threshold 3.30 is a meaningful operating point (escalates ~74% of windows).

    Edge cases:
    - P empty (N_p = 0): KL = 0 by convention (sum over empty support).
    - Q empty (V_q = 0, N_q = 0): KL = 0 (no background; nothing to compare
      against; treated as degenerate).
    - P == Q (non-empty): KL is small but > 0 because Q is smoothed while P is
      empirical (q(x) = (c+1)/(N+V) < c/N = p(x) for high-count tokens). This
      bias is O(V/N) and shrinks as the corpus grows.

    Returns 0.0 for empty P / empty Q. Always non-negative when both are
    non-empty (asymmetric KL with smoothed Q).
    """
    N_p = sum(p_dist.values())
    if N_p == 0:
        return 0.0
    vocab_q = set(q_dist)
    V_q = len(vocab_q)
    N_q = sum(q_dist.values())
    denom_q = N_q + V_q
    if denom_q == 0:
        return 0.0
    kl = 0.0
    for x, c in p_dist.items():
        p_x = c / N_p
        q_x = (q_dist.get(x, 0) + 1) / denom_q
        kl += p_x * math.log(p_x / q_x)
    return kl


# --------------------------------------------------------- base-cpWER estimation
def estimate_base_cpwer(tiny_cpwer: float, ratio: float) -> float:
    """Estimate whisper-base cpWER by scaling tiny cpWER by the base/tiny CER ratio.

    ratio = base_cer / tiny_cer (from model_scale). ratio < 1 means base is
    better; ratio > 1 means base is worse at that bucket.
    """
    return tiny_cpwer * ratio


def nearest_ratio(per_ratio: list[dict[str, Any]], overlap_ratio: float) -> dict[str, Any]:
    """Return the model_scale per-ratio row whose overlap_ratio is nearest."""
    return min(per_ratio, key=lambda r: abs(float(r["overlap_ratio"]) - overlap_ratio))


# ------------------------------------------------------------- cascade aggregate
def cascade_aggregate(
    tiny_cpwers: list[float],
    base_cpwers: list[float],
    mask: list[bool],
    compute_tiny: float,
    compute_base: float,
) -> tuple[float, float, float]:
    """Aggregate cascade cpWER, compute, and escalation fraction.

    cpwer = mean(tiny_cpwer[i] if not mask[i] else base_cpwer[i]).
    compute = compute_tiny*(1-f) + compute_base*f, f = mean(mask).
    """
    n = len(tiny_cpwers)
    assert len(base_cpwers) == n and len(mask) == n
    cpwer_vals = [
        base_cpwers[i] if mask[i] else tiny_cpwers[i] for i in range(n)
    ]
    cpwer = sum(cpwer_vals) / n if n else 0.0
    frac = sum(1 for m in mask if m) / n if n else 0.0
    compute = compute_tiny * (1.0 - frac) + compute_base * frac
    return cpwer, compute, frac


def escalation_mask(kl_scores: list[float], threshold: float) -> list[bool]:
    """Boolean escalation mask: escalate if KL > threshold (strict)."""
    return [s > threshold for s in kl_scores]


# --------------------------------------------------------------- Pareto classify
def classify_pareto(policies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mark each policy as 'frontier' or 'dominated'.

    A policy is dominated if another policy has cpWER <= AND compute <=, with
    at least one strictly lower. The first dominator (in iteration order) is
    recorded in 'dominated_by'. Policies with non-finite compute are excluded
    from both dominating and being dominated (they are reference-only).
    """
    finite = [
        p for p in policies
        if math.isfinite(float(p.get("cpwer", float("inf"))))
        and math.isfinite(float(p.get("compute", float("inf"))))
    ]
    out: list[dict[str, Any]] = []
    for p in policies:
        p_c = float(p.get("cpwer", float("inf")))
        p_co = float(p.get("compute", float("inf")))
        dominated_by = ""
        if math.isfinite(p_c) and math.isfinite(p_co):
            for o in finite:
                if o is p:
                    continue
                o_c = float(o["cpwer"])
                o_co = float(o["compute"])
                if o_c <= p_c + EPS and o_co <= p_co + EPS and (
                    o_c < p_c - EPS or o_co < p_co - EPS
                ):
                    dominated_by = str(o.get("name", ""))
                    break
        enriched = dict(p)
        enriched["pareto_status"] = "dominated" if dominated_by else "frontier"
        enriched["dominated_by"] = dominated_by
        out.append(enriched)
    return out


# ------------------------------------------------------- oracle / random ordering
def oracle_escalation_order(tiny_cpwers: list[float], base_cpwers: list[float]) -> list[int]:
    """Indices ordered worst-first by tiny-base improvement (tiny - base).

    Highest improvement first = escalate the windows where base helps most.
    Ties broken by ascending original index (stable, deterministic).
    """
    improvements = [
        (tiny_cpwers[i] - base_cpwers[i], i) for i in range(len(tiny_cpwers))
    ]
    improvements.sort(key=lambda t: (-t[0], t[1]))
    return [i for _, i in improvements]


def random_escalation_order(n: int, seed: int = SEED) -> list[int]:
    """Deterministic random permutation of [0, n) (seeded)."""
    rng = np.random.default_rng(seed)
    return [int(i) for i in rng.permutation(n)]


# ----------------------------------------------------------------- Levenshtein
def levenshtein(a: str, b: str) -> int:
    """Standard O(n*m) edit distance (stdlib only). Whitespace stripped first."""
    s1 = "".join(a.split())
    s2 = "".join(b.split())
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)
    n1, n2 = len(s1), len(s2)
    prev = list(range(n2 + 1))
    cur = [0] * (n2 + 1)
    for i in range(1, n1 + 1):
        cur[0] = i
        for j in range(1, n2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev, cur = cur, prev
    return prev[n2]


def char_cer(reference: str, hypothesis: str) -> float:
    """Length-normalised character Levenshtein CER (RQ30/RQ31 char-level)."""
    s1 = "".join(reference.split())
    s2 = "".join(hypothesis.split())
    m = max(len(s1), len(s2))
    if m <= 0:
        return 0.0
    return levenshtein(s1, s2) / m


# --------------------------------------------------------- model_scale per-ratio
def load_model_scale_per_ratio() -> dict[str, list[dict[str, Any]]]:
    """Load model_scale CSV (utf-8-sig for BOM) and compute per-ratio mean CER.

    Returns a dict with keys "separated" and "mixed", each a list of per-ratio
    rows: {overlap_ratio, cer_tiny, cer_base, ratio}. Separated CER is constant
    across overlap within each pair (so the per-ratio mean is the across-pair
    mean at that ratio); mixed CER varies by overlap.
    """
    by_ratio: dict[float, list[dict[str, Any]]] = {}
    with MODEL_SCALE_CSV.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            ratio = float(r["overlap_ratio"])
            by_ratio.setdefault(ratio, []).append(r)

    def per_ratio_rows(tiny_key: str, base_key: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for ratio in sorted(by_ratio):
            rs = by_ratio[ratio]
            cer_tiny = float(np.mean([float(r[tiny_key]) for r in rs]))
            cer_base = float(np.mean([float(r[base_key]) for r in rs]))
            rows.append({
                "overlap_ratio": ratio,
                "cer_tiny": cer_tiny,
                "cer_base": cer_base,
                "ratio": cer_base / cer_tiny if cer_tiny > EPS else float("inf"),
            })
        return rows

    return {
        "separated": per_ratio_rows("cer_sep_tiny", "cer_sep_base"),
        "mixed": per_ratio_rows("cer_mixed_tiny", "cer_mixed_base"),
    }


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- load AISHELL-4 (whisper-tiny transcripts + cpWER)
    aishell = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
    windows = aishell["windows"]
    n = len(windows)

    def concat_speakers(d: dict[str, Any]) -> str:
        return "".join(
            str(t).strip() for t in d.values() if t is not None and str(t).strip()
        )

    rows: list[dict[str, Any]] = []
    for w in windows:
        sep_text = concat_speakers(w.get("separated_text_per_speaker", {}))
        mix_text = str(w.get("mixed_text", "") or "")
        ref_text = concat_speakers(w.get("ref_text_per_speaker", {}))
        rows.append({
            "window_id": w["window_id"],
            "overlap_ratio": float(w["overlap_ratio"]),
            "overlap_label": w.get("overlap_label", ""),
            "tiny_sep_cpwer": float(w["always_separated_cpwer"]),
            "tiny_mix_cpwer": float(w["always_mixed_cpwer"]),
            "oracle_best_cpwer": float(w.get("oracle_best_cpwer", w["always_mixed_cpwer"])),
            "tiny_sep_text": sep_text,
            "tiny_mix_text": mix_text,
            "ref_text": ref_text,
            "tiny_sep_char_cer": char_cer(ref_text, sep_text),
            "tiny_mix_char_cer": char_cer(ref_text, mix_text),
            "num_speakers": w.get("num_speakers", 0),
        })

    # --- load model_scale per-ratio CER (base/tiny cost model)
    per_ratio = load_model_scale_per_ratio()
    sep_ratio_table = per_ratio["separated"]
    mix_ratio_table = per_ratio["mixed"]
    # separated ratio is constant across overlap (both CERs constant per pair)
    sep_ratio_const = float(np.mean([r["ratio"] for r in sep_ratio_table]))

    # --- estimate base cpWER / char-CER per window via model_scale ratio
    for r in rows:
        r["base_sep_cpwer"] = estimate_base_cpwer(r["tiny_sep_cpwer"], sep_ratio_const)
        r["base_sep_char_cer"] = estimate_base_cpwer(r["tiny_sep_char_cer"], sep_ratio_const)
        mix_row = nearest_ratio(mix_ratio_table, r["overlap_ratio"])
        r["base_mix_cpwer"] = estimate_base_cpwer(r["tiny_mix_cpwer"], mix_row["ratio"])
        r["base_mix_char_cer"] = estimate_base_cpwer(r["tiny_mix_char_cer"], mix_row["ratio"])
        r["mix_ratio_bucket"] = mix_row["overlap_ratio"]

    # --- KL divergence on tiny transcripts (separated + mixed backgrounds)
    sep_texts = [r["tiny_sep_text"] for r in rows]
    mix_texts = [r["tiny_mix_text"] for r in rows]
    sep_bg = build_background_distribution(sep_texts, NGRAM_N)
    mix_bg = build_background_distribution(mix_texts, NGRAM_N)
    for r in rows:
        r["kl_sep"] = kl_divergence(
            ngram_distribution(r["tiny_sep_text"], NGRAM_N), sep_bg)
        r["kl_mix"] = kl_divergence(
            ngram_distribution(r["tiny_mix_text"], NGRAM_N), mix_bg)

    # --- aggregate baseline means
    mean_tiny_sep_cpwer = float(np.mean([r["tiny_sep_cpwer"] for r in rows]))
    mean_base_sep_cpwer = float(np.mean([r["base_sep_cpwer"] for r in rows]))
    mean_tiny_mix_cpwer = float(np.mean([r["tiny_mix_cpwer"] for r in rows]))
    mean_base_mix_cpwer = float(np.mean([r["base_mix_cpwer"] for r in rows]))
    mean_tiny_sep_char = float(np.mean([r["tiny_sep_char_cer"] for r in rows]))
    mean_base_sep_char = float(np.mean([r["base_sep_char_cer"] for r in rows]))

    # --- build policies for the PRIMARY condition (separated, utterance-level cpWER)
    tiny_sep = [r["tiny_sep_cpwer"] for r in rows]
    base_sep = [r["base_sep_cpwer"] for r in rows]
    kl_sep = [r["kl_sep"] for r in rows]

    cascade_mask = escalation_mask(kl_sep, KL_THRESHOLD)
    cas_cpwer, cas_compute, cas_frac = cascade_aggregate(
        tiny_sep, base_sep, cascade_mask, COMPUTE_TINY, COMPUTE_BASE)

    # oracle + random at the cascade's escalation fraction (compute-matched)
    oracle_order = oracle_escalation_order(tiny_sep, base_sep)
    random_order = random_escalation_order(n, SEED)
    n_escalate = int(round(cas_frac * n))
    oracle_mask = [False] * n
    random_mask = [False] * n
    for i in oracle_order[:n_escalate]:
        oracle_mask[i] = True
    for i in random_order[:n_escalate]:
        random_mask[i] = True
    orc_cpwer, orc_compute, orc_frac = cascade_aggregate(
        tiny_sep, base_sep, oracle_mask, COMPUTE_TINY, COMPUTE_BASE)
    rnd_cpwer, rnd_compute, rnd_frac = cascade_aggregate(
        tiny_sep, base_sep, random_mask, COMPUTE_TINY, COMPUTE_BASE)

    policies: list[dict[str, Any]] = [
        {"name": "always_tiny_separated", "cpwer": mean_tiny_sep_cpwer,
         "compute": COMPUTE_TINY, "condition": "separated", "granularity": "utterance",
         "escalation_fraction": 0.0},
        {"name": "always_base_separated", "cpwer": mean_base_sep_cpwer,
         "compute": COMPUTE_BASE, "condition": "separated", "granularity": "utterance",
         "escalation_fraction": 1.0},
        {"name": "cascade_kl@3.30_separated", "cpwer": cas_cpwer,
         "compute": cas_compute, "condition": "separated", "granularity": "utterance",
         "escalation_fraction": cas_frac, "kl_threshold": KL_THRESHOLD},
        {"name": "oracle_cascade_separated", "cpwer": orc_cpwer,
         "compute": orc_compute, "condition": "separated", "granularity": "utterance",
         "escalation_fraction": orc_frac, "note": "worst-tiny-cpWER-first at matched compute"},
        {"name": "random_cascade_separated", "cpwer": rnd_cpwer,
         "compute": rnd_compute, "condition": "separated", "granularity": "utterance",
         "escalation_fraction": rnd_frac, "note": "seeded random at matched compute"},
    ]

    # --- threshold sweep (KL cascade Pareto curve, separated utterance-level)
    sweep: list[dict[str, Any]] = []
    for t in THRESHOLD_SWEEP:
        m = escalation_mask(kl_sep, t)
        cp, co, fr = cascade_aggregate(tiny_sep, base_sep, m, COMPUTE_TINY, COMPUTE_BASE)
        sweep.append({
            "threshold": t, "escalation_fraction": fr, "cpwer": cp, "compute": co,
        })
        policies.append({
            "name": f"cascade_kl@{t}_separated", "cpwer": cp, "compute": co,
            "condition": "separated", "granularity": "utterance",
            "escalation_fraction": fr, "kl_threshold": t, "sweep_point": True,
        })

    # --- Pareto classification (separated utterance-level)
    policies_classified = classify_pareto(policies)
    frontier = [p for p in policies_classified if p["pareto_status"] == "frontier"]

    # --- hypotheses (primary: separated utterance-level cpWER)
    h43a_supported = cas_cpwer < mean_tiny_sep_cpwer - EPS
    h43b_supported = cas_compute < COMPUTE_BASE - EPS
    # H43c: no single-tier policy (always_tiny / always_base) dominates the cascade
    cas_pol = next(p for p in policies_classified
                   if p["name"] == "cascade_kl@3.30_separated")
    single_tier_dominators = [
        p["name"] for p in policies_classified
        if p["name"] in ("always_tiny_separated", "always_base_separated")
        and cas_pol["pareto_status"] == "dominated"
        and p["name"] == cas_pol.get("dominated_by", "")
    ]
    # broader: is the cascade dominated AT ALL by a single-tier policy?
    h43c_supported = not (
        cas_pol["pareto_status"] == "dominated"
        and cas_pol["dominated_by"] in ("always_tiny_separated", "always_base_separated")
    )

    # --- secondary conditions: separated char-level, mixed utterance, mixed char
    secondary: dict[str, Any] = {}
    for cond, tiny_key, base_key, kl_key in [
        ("separated_char", "tiny_sep_char_cer", "base_sep_char_cer", "kl_sep"),
        ("mixed_utterance", "tiny_mix_cpwer", "base_mix_cpwer", "kl_mix"),
    ]:
        tv = [r[tiny_key] for r in rows]
        bv = [r[base_key] for r in rows]
        kv = [r[kl_key] for r in rows]
        m = escalation_mask(kv, KL_THRESHOLD)
        cp, co, fr = cascade_aggregate(tv, bv, m, COMPUTE_TINY, COMPUTE_BASE)
        secondary[cond] = {
            "always_tiny": float(np.mean(tv)),
            "always_base": float(np.mean(bv)),
            "cascade_kl@3.30_cpwer": cp,
            "cascade_kl@3.30_compute": co,
            "cascade_kl@3.30_fraction": fr,
            "h43a_supported": cp < float(np.mean(tv)) - EPS,
            "h43b_supported": co < COMPUTE_BASE - EPS,
        }

    # --- bootstrap CI for the cascade cpWER (separated utterance-level)
    rng = np.random.default_rng(SEED)
    tiny_arr = np.array(tiny_sep)
    base_arr = np.array(base_sep)
    mask_arr = np.array(cascade_mask, dtype=bool)
    boot_cpwers: list[float] = []
    for _ in range(N_BOOT):
        idx = rng.integers(0, n, size=n)
        chosen = np.where(mask_arr[idx], base_arr[idx], tiny_arr[idx])
        boot_cpwers.append(float(chosen.mean()))
    cas_ci = [float(np.percentile(boot_cpwers, 2.5)), float(np.percentile(boot_cpwers, 97.5))]

    # --- write per-window CSV
    csv_fields = [
        "window_id", "overlap_ratio", "overlap_label", "num_speakers",
        "tiny_sep_cpwer", "base_sep_cpwer", "tiny_sep_char_cer", "base_sep_char_cer",
        "tiny_mix_cpwer", "base_mix_cpwer",
        "kl_sep", "kl_mix", "mix_ratio_bucket",
        "cascade_escalated_sep",
    ]
    for r in rows:
        r["cascade_escalated_sep"] = bool(
            escalation_mask(kl_sep, KL_THRESHOLD)[rows.index(r)])
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in csv_fields})

    # --- Pareto frontier CSV (separated utterance-level)
    pareto_fields = ["name", "cpwer", "compute", "escalation_fraction",
                     "pareto_status", "dominated_by", "condition", "granularity"]
    with PARETO_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=pareto_fields)
        wr.writeheader()
        for p in policies_classified:
            wr.writerow({k: p.get(k, "") for k in pareto_fields})

    # --- summary JSON
    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ43: 3-tier cascade (tiny -> KL gate -> base) Pareto analysis",
        "closes_issue": 955,
        "source_data": {
            "aishell4": str(AISHELL4_JSON.relative_to(PROJECT_ROOT)),
            "aishell4_label": "external/sanity-check",
            "aishell4_asr_model": aishell.get("asr_model", "whisper-tiny"),
            "model_scale": str(MODEL_SCALE_CSV.relative_to(PROJECT_ROOT)),
            "model_scale_label": "experimental/frontier",
        },
        "method": (
            "SIMULATION (no ASR run). AISHELL-4 windows transcribed with whisper-tiny "
            "provide real tiny transcripts (for the KL gate) and real tiny cpWER. "
            "whisper-base cpWER is ESTIMATED by scaling tiny cpWER by the model_scale "
            "base/tiny CER ratio at the window's nearest overlap-ratio bucket "
            "(separated ratio = 0.200/0.467 = 0.4283 constant; mixed ratio varies by "
            "overlap). The n-gram KL divergence gate (character bigrams, ASYMMETRIC "
            "Laplace: P empirical, Q add-1 smoothed over Q's own support, corpus-pooled "
            "background, nats) fires on the tiny transcript; windows with KL > 3.30 are "
            "escalated to base. Cascade compute = 1.0*(1-f) + 1.93*f (KL gate cost "
            "negligible). The symmetric both-smoothed-over-union-vocab formulation was "
            "tried first and rejected: V_union=4116 >> N_p~50 damps KL to ~0.09 nats "
            "(max), making threshold 3.30 unreachable (cascade escalates 0% => "
            "degenerate Pareto replicating runtime_cascade's binary cliff). The "
            "asymmetric formulation preserves P's empirical concentration and yields "
            "KL in [0, ~8.5] with mean ~3.4, so threshold 3.30 is a meaningful "
            "operating point. The referenced RQ34 KL implementation "
            "(src/llm_semantic_critic.py / results/frontier/llm_semantic_critic/) is "
            "NOT present in the repo; the KL computation is implemented from first "
            "principles and the 3.30 threshold is used as specified, with a full "
            "threshold sweep tracing the Pareto frontier."
        ),
        "kl_threshold": KL_THRESHOLD,
        "ngram_n": NGRAM_N,
        "compute_model": {
            "tiny": COMPUTE_TINY, "base": COMPUTE_BASE, "kl_gate": COMPUTE_KL_GATE,
            "source": "runtime_cascade FINDINGS (base 1.93x slower than tiny)",
        },
        "base_estimation": {
            "method": "base_cpwer = tiny_cpwer * (base_cer / tiny_cer) at nearest overlap bucket",
            "separated_ratio_const": round(sep_ratio_const, 6),
            "separated_ratio_per_bucket": [
                {"overlap_ratio": r["overlap_ratio"],
                 "cer_tiny": round(r["cer_tiny"], 6),
                 "cer_base": round(r["cer_base"], 6),
                 "ratio": round(r["ratio"], 6)} for r in sep_ratio_table
            ],
            "mixed_ratio_per_bucket": [
                {"overlap_ratio": r["overlap_ratio"],
                 "cer_tiny": round(r["cer_tiny"], 6),
                 "cer_base": round(r["cer_base"], 6),
                 "ratio": round(r["ratio"], 6)} for r in mix_ratio_table
            ],
            "caveat": (
                "model_scale CER is char-level; AISHELL-4 cpWER is utterance-level "
                "(whole Chinese string = 1 token, RQ30). Applying the char-level "
                "improvement ratio to utterance-level cpWER is a simulation "
                "approximation. The char-level cascade (secondary) applies the same "
                "ratio to char-level CER computed directly from AISHELL-4 transcripts, "
                "which is the faithful granularity."
            ),
        },
        "n_windows": n,
        "kl_stats": {
            "separated": {
                "min": round(float(np.min(kl_sep)), 6),
                "max": round(float(np.max(kl_sep)), 6),
                "mean": round(float(np.mean(kl_sep)), 6),
                "median": round(float(np.median(kl_sep)), 6),
                "n_above_threshold": int(sum(cascade_mask)),
                "fraction_above_threshold": round(cas_frac, 6),
            },
        },
        "policies": [
            {k: v for k, v in p.items() if k != "sweep_point"} | {
                "cpwer": round(float(p["cpwer"]), 6) if "cpwer" in p else p.get("cpwer"),
                "compute": round(float(p["compute"]), 6) if "compute" in p else p.get("compute"),
            } for p in policies_classified
        ],
        "pareto_frontier": [
            {"name": p["name"], "cpwer": round(float(p["cpwer"]), 6),
             "compute": round(float(p["compute"]), 6),
             "escalation_fraction": round(float(p.get("escalation_fraction", 0.0)), 6),
             "pareto_status": p["pareto_status"],
             "dominated_by": p["dominated_by"],
             "condition": p.get("condition", ""),
             "granularity": p.get("granularity", "")}
            for p in frontier
        ],
        "threshold_sweep": [
            {"threshold": s["threshold"],
             "escalation_fraction": round(s["escalation_fraction"], 6),
             "cpwer": round(s["cpwer"], 6),
             "compute": round(s["compute"], 6)} for s in sweep
        ],
        "secondary_conditions": {
            k: {kk: (round(vv, 6) if isinstance(vv, float) else vv)
                for kk, vv in v.items()} for k, v in secondary.items()
        },
        "reference_routers": {
            "rq16_corrected_router_cpwer": RQ16_CORRECTED_ROUTER_CPWER,
            "note": (
                "RQ16 corrected router (cpWER 1.04329, PR #912) operates on a DIFFERENT "
                "axis (mixed-vs-separated route selection) than this study (tiny-vs-base "
                "model selection). Included as a reference point; not on the same Pareto "
                "axis and excluded from Pareto classification."
            ),
            "aishell4_baselines": {
                "always_mixed_cpwer": round(mean_tiny_mix_cpwer, 6),
                "always_separated_cpwer": round(mean_tiny_sep_cpwer, 6),
                "oracle_best_cpwer": round(float(np.mean([r["oracle_best_cpwer"] for r in rows])), 6),
            },
        },
        "cascade_bootstrap_ci_95": [round(cas_ci[0], 6), round(cas_ci[1], 6)],
        "hypothesis_verdicts": {
            "H43a": {
                "statement": "3-tier cascade cpWER < always-tiny cpWER at equal-or-lower compute",
                "success_criterion": "cascade cpwer < tiny cpwer",
                "cascade_cpwer": round(cas_cpwer, 6),
                "always_tiny_cpwer": round(mean_tiny_sep_cpwer, 6),
                "cascade_compute": round(cas_compute, 6),
                "cascade_cpwer_ci_95": [round(cas_ci[0], 6), round(cas_ci[1], 6)],
                "supported": bool(h43a_supported),
                "reason": (
                    f"Cascade cpWER {cas_cpwer:.4f} vs always-tiny {mean_tiny_sep_cpwer:.4f} "
                    f"at compute {cas_compute:.4f}x (tiny=1.0x). The KL gate escalates "
                    f"{cas_frac:.1%} of windows to base; the cascade improves cpWER over "
                    f"always-tiny." if h43a_supported else
                    f"Cascade cpWER {cas_cpwer:.4f} is NOT below always-tiny "
                    f"{mean_tiny_sep_cpwer:.4f} (escalation fraction {cas_frac:.1%} "
                    f"did not catch enough high-cpWER windows)."
                ),
            },
            "H43b": {
                "statement": "3-tier cascade compute < always-base compute",
                "success_criterion": "cascade compute < 1.93x",
                "cascade_compute": round(cas_compute, 6),
                "always_base_compute": COMPUTE_BASE,
                "escalation_fraction": round(cas_frac, 6),
                "supported": bool(h43b_supported),
                "reason": (
                    f"Cascade compute {cas_compute:.4f}x < always-base {COMPUTE_BASE}x "
                    f"because escalation fraction {cas_frac:.1%} < 100%." if h43b_supported else
                    f"Cascade compute {cas_compute:.4f}x is not below {COMPUTE_BASE}x "
                    f"(escalation fraction {cas_frac:.1%} = 100%)."
                ),
            },
            "H43c": {
                "statement": "3-tier cascade is Pareto-optimal (no single-tier policy dominates it)",
                "success_criterion": "no policy has both lower cpWER AND lower compute",
                "cascade_pareto_status": cas_pol["pareto_status"],
                "cascade_dominated_by": cas_pol["dominated_by"],
                "single_tier_policies": ["always_tiny_separated", "always_base_separated"],
                "supported": bool(h43c_supported),
                "reason": (
                    f"Cascade is on the Pareto frontier (not dominated by any policy)." if
                    (h43c_supported and cas_pol["pareto_status"] == "frontier") else
                    f"Cascade is dominated by {cas_pol['dominated_by']}; however that "
                    f"dominator is {'a single-tier policy' if cas_pol['dominated_by'] in ('always_tiny_separated','always_base_separated') else 'another cascade point (not single-tier)'}, "
                    f"so H43c (no SINGLE-TIER policy dominates) is "
                    f"{'NOT supported' if not h43c_supported else 'supported'}."
                ),
                "oracle_gap": {
                    "oracle_cpwer_at_matched_compute": round(orc_cpwer, 6),
                    "cascade_cpwer": round(cas_cpwer, 6),
                    "gap": round(cas_cpwer - orc_cpwer, 6),
                    "note": (
                        "The oracle cascade (worst-tiny-cpWER-first ordering at matched "
                        "compute) is NOT a single-tier policy; it is the best-possible "
                        "cascade and an upper bound on KL-gate performance. A positive gap "
                        "means the KL gate's ordering is worse than oracle (expected, since "
                        "the KL gate is not a perfect detector)."
                    ),
                },
            },
        },
        "per_window": [
            {"window_id": r["window_id"],
             "overlap_ratio": r["overlap_ratio"],
             "overlap_label": r["overlap_label"],
             "tiny_sep_cpwer": round(r["tiny_sep_cpwer"], 6),
             "base_sep_cpwer": round(r["base_sep_cpwer"], 6),
             "tiny_sep_char_cer": round(r["tiny_sep_char_cer"], 6),
             "base_sep_char_cer": round(r["base_sep_char_cer"], 6),
             "tiny_mix_cpwer": round(r["tiny_mix_cpwer"], 6),
             "base_mix_cpwer": round(r["base_mix_cpwer"], 6),
             "kl_sep": round(r["kl_sep"], 6),
             "kl_mix": round(r["kl_mix"], 6),
             "cascade_escalated_sep": r["cascade_escalated_sep"]}
            for r in rows
        ],
    }
    OUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- console
    print(f"=== RQ43: 3-tier cascade (tiny -> KL gate -> base) ===")
    print(f"Label: experimental/frontier  |  Closes #955  |  n={n} AISHELL-4 windows")
    print(f"AISHELL-4 ASR model: {aishell.get('asr_model')} (tiny transcripts are real)")
    print(f"KL gate: char bigram KL vs corpus background, threshold {KL_THRESHOLD} nats")
    print(f"Base cpWER estimated via model_scale ratio (sep ratio={sep_ratio_const:.4f})")
    print()
    print(f"{'policy':36s} {'cpwer':>8s} {'compute':>8s} {'frac':>6s} {'pareto':>8s}")
    for p in policies_classified:
        if p.get("sweep_point") and p["name"] not in (
                f"cascade_kl@{KL_THRESHOLD}_separated",):
            continue
        print(f"{p['name']:36s} {float(p['cpwer']):8.4f} {float(p['compute']):8.4f} "
              f"{float(p.get('escalation_fraction',0.0)):6.1%} {p['pareto_status']:>8s}")
    print()
    print(f"Cascade @ KL={KL_THRESHOLD}: cpwer={cas_cpwer:.4f} (CI {cas_ci[0]:.4f},{cas_ci[1]:.4f}), "
          f"compute={cas_compute:.4f}x, escalation={cas_frac:.1%}")
    print(f"Oracle @ matched compute:    cpwer={orc_cpwer:.4f} (gap {cas_cpwer-orc_cpwer:+.4f})")
    print(f"Random @ matched compute:    cpwer={rnd_cpwer:.4f}")
    print(f"always-tiny: {mean_tiny_sep_cpwer:.4f} @ 1.0x | always-base: {mean_base_sep_cpwer:.4f} @ 1.93x")
    print()
    print("Hypothesis verdicts (separated, utterance-level cpWER):")
    print(f"  H43a (cascade < always-tiny): {'SUPPORTED' if h43a_supported else 'NOT SUPPORTED'} "
          f"({cas_cpwer:.4f} vs {mean_tiny_sep_cpwer:.4f})")
    print(f"  H43b (cascade compute < 1.93x): {'SUPPORTED' if h43b_supported else 'NOT SUPPORTED'} "
          f"({cas_compute:.4f}x, frac={cas_frac:.1%})")
    print(f"  H43c (no single-tier dominates cascade): {'SUPPORTED' if h43c_supported else 'NOT SUPPORTED'} "
          f"(cascade pareto={cas_pol['pareto_status']}, dominated_by={cas_pol['dominated_by'] or 'none'})")
    print()
    print(f"Threshold sweep (KL -> frac -> cpwer, compute):")
    for s in sweep:
        print(f"  KL>={s['threshold']:4.2f}: frac={s['escalation_fraction']:5.1%} "
              f"cpwer={s['cpwer']:.4f} compute={s['compute']:.4f}x")
    print()
    print(f"Secondary: separated char-level H43a={secondary['separated_char']['h43a_supported']} "
          f"| mixed utterance H43a={secondary['mixed_utterance']['h43a_supported']}")
    print(f"RQ16 corrected router cpWER (reference, different axis): {RQ16_CORRECTED_ROUTER_CPWER}")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {PARETO_CSV.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
