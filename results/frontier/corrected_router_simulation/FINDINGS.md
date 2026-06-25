# RQ16: End-to-End Corrected-Router Simulation on AISHELL-4

> **Label: `experimental/frontier`** — a reanalysis-only simulation of a corrected router that
> replaces router v2's CR guard with three reference-free detectors (language-id entropy,
> silence-aware gate proxy, mode-specific guards). Does NOT run Whisper or overwrite any
> verified reference / gold table. Closes #908.
>
> Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
> (label `external/sanity-check`, PR #890). Detector primitives and thresholds are lifted from
> RQ13 (`results/frontier/diverse_hallucination_detector/`, PR #904), RQ12
> (`results/frontier/router_failure_modes/`), RQ8 (`results/frontier/silence_aware_gate/`,
> PR #893), and RQ14's mode guards.

## Executive Summary

Router v2 fails to generalize to AISHELL-4: cpWER 1.206 vs always-mixed 1.173 (RQ1, finding
#23), with the failure decomposed in RQ12 as predominantly *diverse* separated-track
hallucination that the CR>2.4 guard misses (2.7% sensitivity). RQ13 then showed a language-id
entropy detector catches that diverse hallucination at 94.6% sensitivity / 92.5% specificity.

This module closes the loop: it simulates an end-to-end **corrected router** that routes to
MIXED whenever any of three reference-free guards flags the separated track — (1) language-id
entropy > 0.409 bits (RQ13), (2) a silence-gap text proxy `length_ratio > 2.0` (RQ8/RQ14), (3)
mode guards `≥3 distinct scripts` or `max CR > 2.4` (RQ14) — and otherwise routes to SEPARATED.

On the 77 AISHELL-4 windows the corrected router achieves **cpWER 1.043**, below always-mixed
(1.173), below router v2 (1.206), and within 0.026 of the oracle (1.017). All three hypotheses
are supported at the point estimate:

| Policy | cpWER | vs always-mixed | vs router v2 |
|--------|------:|----------------:|-------------:|
| always-mixed | 1.173 | — | — |
| always-separated | 1.591 | +0.418 | +0.385 |
| router v2 | 1.206 | +0.033 | — |
| **corrected router** | **1.043** | **−0.130** | **−0.162** |
| oracle best | 1.017 | −0.156 | −0.188 |

The corrected router never does worse than router v2 on any of the 77 windows (H16b CI entirely
below 0), and the language-id entropy detector alone recovers **86.2%** of router v2's regret
gap to oracle (H16c). The dominant finding is that **language-id entropy alone is sufficient on
AISHELL-4**: the silence and mode guards are redundant — their marginal flags either fall on
windows where both routes tie, or are strict subsets of the lang-id flags — so the full
three-guard router is identical to the lang-id-only ablation.

**The headline caveat is in-sample calibration.** All three detector thresholds were calibrated
on these exact 77 windows (RQ13/RQ14), so the cpWER improvement is not an honest out-of-sample
test. The result establishes that a corrected router *could* recover the gap mechanistically,
not that it *would* transfer. See Limitations.

## Method

### Data

77 windows of 30 s from AISHELL-4 meeting `M_R003S02C01` (6 speakers, 38.5 min). Each window
already stores, per route, the cpWER that would result (`always_mixed_cpwer`,
`always_separated_cpwer`, `router_v2_cpwer`, `oracle_best_cpwer`) plus the per-speaker separated
transcripts and the mixed transcript. No ASR is run; the corrected router's per-window cpWER is
the chosen route's stored cpWER.

### Detectors (all reference-free; computed from stored transcripts)

The detector primitives (`script_category`, `language_id_entropy`, `compression_ratio`) are
copied verbatim from RQ13/RQ12 so the thresholds are directly comparable. Per-speaker scores are
aggregated by MAX across the separated tracks (worst-case speaker, the RQ12/RQ13 convention).

1. **Language-id entropy (RQ13).** Shannon entropy (bits) over Unicode script categories (Han,
   Latin, Hiragana, Katakana, Hangul, …) of each per-speaker separated transcript, max across
   speakers. Threshold **0.409 bits** (RQ13's ≥90%-specificity operating point; 94.6%
   sensitivity, 92.5% specificity on the AISHELL-4 hallucination label). Clean Chinese is
   near-monoscript (entropy ≈ 0); diverse multilingual gibberish mixes 4+ scripts (high entropy).
2. **Silence-aware gate proxy (RQ8/RQ14).** The RQ8 gate truncates interior silence gaps > 0.5 s
   on separated tracks. The AISHELL-4 audio is unavailable, so we use RQ14's text proxy:
   `length_ratio = separated_total_length / mixed_text_length`. Oracle-TextGrid separation leaves
   each speaker's speech at its original positions with the rest of the 30 s window silent;
   Whisper's confident-attractor then inserts tokens into the silence, inflating the separated
   transcript far beyond the mixed. **Ratio > 2.0** captures the insertion_dominated mode.
3. **Mode-specific guards (RQ14).** `multilingual_mixing`: ≥ 3 distinct linguistic-content
   script categories (Han, Latin, Hiragana, Katakana, Hangul, Cyrillic, Arabic, Greek, Digit —
   Space/Punct/Other excluded) on the worst-case speaker track. `repetition`: max Whisper
   compression ratio (`len(utf8)/len(zlib)`, RQ12) > 2.4. The mode guard fires if either sub-guard
   fires.

### Decision rule

For each window: if **any** guard flags the separated track → route to MIXED; else → route to
SEPARATED. The corrected router therefore defaults to the ambitious separated route and only
falls back to mixed when a guard detects a likely separated-track failure. Seven ablations are
run: each guard alone, each pair, and all three (the corrected router).

### Statistics

Per-window cpWER is averaged over the 77 windows for each policy. Bootstrap 95% CIs use 10,000
resamples (seed=42) of the 77 windows with replacement. For the hypothesis tests the bootstrap
resamples the per-window paired difference (corrected − comparator) and reports the 2.5/97.5
percentiles. H16c's recovery fraction is bootstrapped per-resample as
`(rv2_gap − lang_gap) / rv2_gap`.

## Results

### Aggregate cpWER (mean over 77 windows, 95% bootstrap CI)

| Policy | cpWER | CI 95% |
|--------|------:|:------|
| always-mixed | 1.1732 | — |
| always-separated | 1.5909 | — |
| router v2 | 1.2056 | — |
| oracle best | 1.0173 | — |
| lang-id entropy alone | **1.0433** | [1.0087, 1.0887] |
| silence gate alone | 1.2392 | [1.1212, 1.3745] |
| mode guards alone | 1.3312 | [1.2056, 1.4719] |
| lang-id + silence | 1.0433 | [1.0087, 1.0887] |
| lang-id + mode | 1.0433 | [1.0087, 1.0887] |
| silence + mode | 1.1266 | [1.0455, 1.2241] |
| **corrected router (all three)** | **1.0433** | [1.0087, 1.0887] |

The lang-id-only, lang-id+silence, lang-id+mode, and full corrected router are **identical**
(1.0433). This is the central structural finding: on AISHELL-4 the silence and mode guards are
redundant once lang-id entropy is in the ensemble.

### Guard behaviour

Guard fire counts (of 77 windows): lang-id 38, silence 27, multilingual 14, repetition 1, mode
(any) 15. The corrected router routes 42 windows to mixed and 35 to separated (router v2 routed
52 to mixed, 25 to separated). Of the corrected router's 35 separated picks, only 2 hallucinate
(separated cpWER > 1.0), versus router v2's 9 hallucinations out of 25 separated picks — the
corrected router picks separated *more often* while hallucinating *far less* when it does.

The redundancy has two clean causes, verified per-window:
- **Mode guards are a strict subset of lang-id flags** (0 mode flags not already caught by
  lang-id). Whenever ≥3 scripts or max CR > 2.4 fires, lang-id entropy is already above 0.409.
- **Silence's marginal flags (4 windows lang-id misses) all have `always_mixed_cpwer ==
  always_separated_cpwer == 1.0`** — both routes are equally clean, so flagging them changes the
  decision but not the cpWER.

### Per-window structure vs always-mixed

The corrected router beats or ties always-mixed on 75/77 windows: 6 wins (total magnitude 12.0),
69 ties, and 2 losses (total magnitude 2.0), for a net of −0.130 cpWER/window. The 6 wins are
windows where the mixed track hallucinated badly (mixed cpWER 2–6) but separated was clean, and
no guard fired, so the corrected router correctly picked separated. The 2 losses (windows 22 and
30) are the only windows where the corrected router does worse than always-mixed: both are
monoscript-Chinese separated hallucinations (separated cpWER 2.0 vs mixed 1.0) that **none** of
the three guards catch — low lang-id entropy (0.14, 0.32 bits), near-unity length ratio (1.02,
1.03), low CR (1.37, 1.49), 1–2 scripts. This is the residual failure mode (call it Mode S:
monoscript semantic hallucination with no length/CR/script footprint).

### Per-window structure vs router v2

The corrected router does **no worse than router v2 on any of the 77 windows** (0 windows where
corrected > router v2). This is why H16b's bootstrap CI is entirely below 0.

## Hypothesis Verdicts

- **H16a — corrected router cpWER < always-mixed cpWER (1.173): SUPPORTED (pointwise; CI
  borderline).** Corrected 1.0433 vs 1.1732, Δ = −0.1299. Bootstrap CI [−0.3117, 0.0000]: the
  upper bound touches but does not cross zero. The improvement is real at the point estimate but
  driven by a small number of large wins (6 wins totalling 12.0) against 2 small losses (2.0);
  the high variance comes from AISHELL-4's lumpy, discrete cpWER values (0, 1, 2, 4, 6). The
  "touches zero" upper bound reflects that 69/77 windows tie and the 6-vs-2 win/loss imbalance
  keeps the resampled mean ≤ 0 in ≥97.5% of resamples.

- **H16b — corrected router cpWER < router v2 cpWER (1.206): SUPPORTED.** Δ = −0.1623, bootstrap
  CI [−0.2879, −0.0606], entirely below 0. The corrected router never loses to router v2 on any
  window, so the improvement is uniformly distributed rather than driven by outliers.

- **H16c — language-id entropy alone recovers > 50% of router v2's regret gap to oracle:
  SUPPORTED.** Router v2's regret gap to oracle is 0.1883 (1.2056 − 1.0173); lang-id alone
  reduces it to 0.0260 (1.0433 − 1.0173), recovering **86.2%** (bootstrap CI [61.3%, 100.0%]).
  Because the silence and mode guards are redundant, lang-id alone is *equal* to the full
  corrected router on AISHELL-4 — the 86.2% recovery IS the corrected router's recovery.

## Honest Limitations

1. **In-sample calibration (the headline caveat).** All three detector thresholds were
   calibrated on these exact 77 AISHELL-4 windows — lang-id entropy 0.409 from RQ13's ROC
   operating point, length-ratio 2.0 and the mode-guard thresholds from RQ14. The corrected
   router's cpWER is therefore an *in-sample* estimate and almost certainly optimistic. This
   simulation establishes that a corrected router *could* mechanistically recover the gap; it
   does **not** show the detectors *would* transfer to a held-out meeting. A proper test needs a
   held-out AISHELL-4 session or leave-one-meeting-out cross-validation, which the single-meeting
   external validation does not permit. Treat the 1.043 as an upper bound on achievable cpWER,
   not a deployable number.

2. **Silence gate is a text proxy, not the RQ8 audio gate.** RQ8's actual gate truncates interior
   silence gaps > 0.5 s via noise-floor-relative RMS VAD on the audio. We do not have the audio,
   so we use the text `length_ratio` proxy from RQ14. The proxy turned out to be redundant with
   lang-id here, but on a real separator (SepFormer residual noise vs oracle-TextGrid true
   silence) the audio gate and the text proxy could diverge. The audio gate's true marginal value
   is unmeasured.

3. **Single meeting, 77 windows.** M_R003S02C01 is 1 of 20 AISHELL-4 test meetings. The cpWER
   values are lumpy and discrete (0, 1, 2, 4, 6), which inflates bootstrap variance and is why
   H16a's CI touches zero despite a 0.130 point improvement. Generalization across meetings is
   untested.

4. **Aggressive default (separated).** The corrected router defaults to separated when no guard
   fires. This relies on the guards catching *all* bad-separated cases; they miss 2 (Mode S,
   above), which are the entirety of the corrected router's losses vs always-mixed. A more
   conservative default (mixed) would avoid those 2 losses but forfeit the 6 large wins.

5. **Oracle-TextGrid-specific.** The failure mode (long interior silence → confident-attractor
   insertions) is an artefact of oracle-TextGrid separation. A real separator produces residual
   noise, not true silence, and the length-ratio / lang-id footprints may differ.

6. **No deployable routing input.** Per the project's hard safety rules, cpWER / references are
   not used as routing input — the guards here are computed only from the hypothesis transcripts
   (lang-id entropy, length ratio, CR, script counts), which is the deployable signal surface.

## Reproducibility

- Script: `python3 results/frontier/corrected_router_simulation/corrected_router_simulation.py`
  (deterministic; numpy + stdlib only; no scipy / sklearn / Whisper).
- Outputs: `simulation_results.csv` (per-window guards, decisions, cpWERs for all 7 ablations)
  and `simulation_results.json` (summary, ablation cpWERs, bootstrap CIs, hypothesis verdicts,
  per-window rows).
- Bootstrap: 10,000 resamples, seed=42.
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).

## What this changes for the project

RQ12/RQ13 diagnosed *why* router v2 fails on AISHELL-4 (diverse separated hallucination that CR
misses) and built a detector (lang-id entropy) that catches it. RQ16 closes the loop and shows
that wiring those detectors into a corrected router **recovers the gap mechanistically**: cpWER
drops from 1.206 (router v2) to 1.043, below always-mixed (1.173) and within 0.026 of oracle,
with lang-id entropy alone doing essentially all the work (86.2% regret-gap recovery).

The negative finding is just as informative: the silence and mode guards are **redundant** on
AISHELL-4 — lang-id entropy subsumes them — and 2 monoscript-Chinese hallucinations (Mode S)
escape every guard, bounding what reference-free transcript-only detectors can achieve. The next
step that would turn this from a mechanistic demonstration into a deployable result is an
**out-of-sample test on a held-out AISHELL-4 meeting** (or leave-one-meeting-out CV) using
thresholds frozen from M_R003S02C01, plus the actual RQ8 audio gate in place of the text proxy.
Until that test is run, the 1.043 figure is an in-sample upper bound.
