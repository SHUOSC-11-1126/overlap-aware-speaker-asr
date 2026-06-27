# RQ53: Emotion-Aware Routing Simulation

> **Label: `experimental/frontier`** — a reanalysis-only simulation that fuses RQ36's cached LLM emotion
> readings with RQ16's corrected-router decisions to simulate four text+emotion routing policies on the
> 77 AISHELL-4 windows. Does NOT run Whisper, run any ASR model, make new LLM calls, or overwrite any
> verified reference / gold table. Closes #957.
>
> Source data (all read-only):
> - `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (`external/sanity-check`, PR #890) — 77 windows.
> - `results/frontier/llm_emotion_hallucination/llm_responses_cache.json` (`qualitative/demo`, RQ36, PR #956) — cached `reliable` field.
> - `results/frontier/corrected_router_simulation/simulation_results.json` (`experimental/frontier`, RQ16, PR #912) — corrected-router decisions.

## Executive Summary

The project's stable baseline established that "the emotion separation tax is opposite of the ASR tax" —
separation HELPS emotion but HURTS ASR. RQ16 then showed a text-based corrected router (lang-id entropy
detector) recovers AISHELL-4 cpWER to **1.043**, and RQ36 showed a local LLM reads Mode S hallucinated
transcripts as "reliable" (within 1 SD of clean). RQ53 asks the natural fusion question: **when the
text-based router and an emotion-based signal disagree, which signal should win? Can a decoupled
text+emotion router beat the text-only corrected router?**

This module answers with a clean **negative**. We simulate four policies by combining RQ16's
`corrected_decision` (the text signal) with RQ36's cached `reliable` field (the emotion signal) on the
77 AISHELL-4 windows, with no new LLM calls:

| Policy | cpWER | 95% CI | mixed / separated |
|--------|------:|:-------|:-----------------:|
| always-mixed | 1.1732 | — | 77 / 0 |
| always-separated | 1.5909 | — | 0 / 77 |
| **text-only (RQ16 baseline)** | **1.0433** | [1.0087, 1.0887] | 42 / 35 |
| emotion-only | 1.4102 | [1.2554, 1.5844] | 19 / 58 |
| AND (conservative) | 1.0823 | [1.0152, 1.1797] | 46 / 31 |
| OR (aggressive) | 1.3712 | [1.2305, 1.5336] | 15 / 62 |

Neither fusion policy beats the text-only baseline. **H53a is KILLED** (AND cpWER 1.082 > 1.043): the
conservative policy that routes MIXED whenever *either* signal fires picks up harmful emotion-driven false
alarms. **H53b is KILLED** (OR cpWER 1.371 ≥ 1.043): the aggressive policy that routes MIXED only when
*both* signals agree drops 27 windows to a hallucinated separated track. **H53c is SUPPORTED**
(disagreement 40.3% > 20%): the signals are genuinely decoupled — but the decoupling does not help ASR
routing, because the disagreements are dominated by cases where the text signal is right and the emotion
signal is wrong.

The mechanistic finding: the text signal (lang-id entropy) **strictly dominates** the emotion signal for
ASR routing. The emotion signal's disagreements with the text signal are predominantly the RQ36 failure
mode generalised — the LLM reads hallucinated transcripts as "reliable" — so fusing the emotion signal
adds noise the text signal has already correctly resolved. The decoupled text+emotion router does not
exist as a cpWER improvement; the text-only corrected router remains the best policy.

## Method

### Data

77 windows of 30 s from AISHELL-4 meeting `M_R003S02C01`. Each window already stores the cpWER that would
result from each route (`always_mixed_cpwer`, `always_separated_cpwer`). No ASR is run; each policy's
per-window cpWER is the chosen route's stored cpWER, averaged over the 77 windows.

### Signals (both reference-free; both computed from cached artefacts)

- **Text signal** (`text_unreliable`): RQ16's corrected-router decision. RQ16 routes to MIXED when any of
  three reference-free guards flags the separated track (lang-id entropy > 0.409 bits, length-ratio > 2.0,
  or mode guards). We take `text_unreliable = (RQ16 corrected_decision == "mixed")` directly from RQ16's
  per-window output — no detector is recomputed.
- **Emotion signal** (`emotion_unreliable`): RQ36's cached LLM `reliable` field on the concatenated
  per-speaker separated transcript (the track the objective-aware router reads emotion from). We reproduce
  RQ36's exact cache key (sha1 of the concatenated transcript, first 16 hex) to look up each window's
  cached reading, so no new LLM call is made. `emotion_unreliable = (reliable == False)`. For the 10
  silent windows whose transcript is empty (and therefore have no cache entry), we use RQ36's documented
  fail-open default (`reliable = True`), so the emotion signal says "reliable" — consistent with RQ36's
  `_defaults()` policy. 67 of 77 windows have a real cached emotion reading.

### Policies

| Policy | Rule | Type |
|--------|------|------|
| Text-only | route MIXED iff `text_unreliable` | baseline (RQ16) |
| Emotion-only | route MIXED iff `emotion_unreliable` | emotion signal alone |
| AND (conservative) | route MIXED if `text_unreliable` OR `emotion_unreliable` | fail-safe: prefer mixed |
| OR (aggressive) | route MIXED only if `text_unreliable` AND `emotion_unreliable` | fail-ambitious: prefer separated |

cpWER for a policy = mean over 77 windows of the chosen route's stored cpWER. The text-only policy
reproduces RQ16's 1.04329 exactly (verified by smoke test), confirming the simulation is consistent with
the cached baseline.

### Statistics

Per-window cpWER is averaged over the 77 windows for each policy. Bootstrap 95% CIs use 10,000 resamples
(seed=42) of the 77 per-window cpWERs with replacement. The pre-registered hypothesis kill conditions use
the exact text-only cpWER (1.04329) as the threshold.

## Results

### Aggregate cpWER (mean over 77 windows, 95% bootstrap CI)

| Policy | cpWER | CI 95% | vs text-only | mixed / separated |
|--------|------:|:-------|-------------:|:-----------------:|
| text-only (RQ16) | **1.0433** | [1.0087, 1.0887] | — | 42 / 35 |
| emotion-only | 1.4102 | [1.2554, 1.5844] | +0.367 | 19 / 58 |
| AND (conservative) | 1.0823 | [1.0152, 1.1797] | +0.039 | 46 / 31 |
| OR (aggressive) | 1.3712 | [1.2305, 1.5336] | +0.328 | 15 / 62 |
| always-mixed (ref) | 1.1732 | — | +0.130 | 77 / 0 |
| always-separated (ref) | 1.5909 | — | +0.548 | 0 / 77 |

The text-only corrected router is the best policy. Emotion-only is the worst non-trivial policy (worse
than always-mixed), confirming the emotion signal is a poor ASR router on its own. Both fusion policies
are worse than text-only.

### Signal disagreement (H53c)

| Cross-tab | Count | Fraction |
|-----------|------:|---------:|
| both unreliable | 15 | 19.5% |
| both reliable | 31 | 40.3% |
| text unreliable, emotion reliable | 27 | 35.1% |
| emotion unreliable, text reliable | 4 | 5.2% |
| **disagree** | **31** | **40.3%** |

Restricted to the 67 windows with an actual emotion reading, disagreement is 31/67 = **46.3%**. Either
way the signals disagree on far more than 20% of windows, so H53c is supported: the text and emotion
signals are genuinely decoupled.

The disagreement is heavily asymmetric: 27 of the 31 disagreements (87%) are cases where the **text
signal says unreliable but the emotion signal says reliable**. This is the RQ36 finding generalised beyond
Mode S — the LLM reads many hallucinated transcripts (not just the 2 monoscript Mode S cases) as
"reliable", so the emotion signal's `reliable` field misses hallucinations that the lang-id entropy
detector catches.

### Why AND fails (H53a killed)

The AND policy routes MIXED whenever *either* signal fires, so it adds the 4 windows where only the
emotion signal says "unreliable" to the text-only router's 42 mixed decisions (46 total). These 4 emotion-
only flags are **false alarms for ASR routing**: 3 of the 4 are windows where both routes tie at cpWER
1.0 (no effect), but the 4th — window 08 — has `always_mixed_cpwer = 4.0` vs
`always_separated_cpwer = 1.0`. Routing it to MIXED costs 3.0 cpWER. Net: AND gains nothing on the 3 ties
and loses 3.0 on window 08, for a total cpWER of 1.082 vs text-only's 1.043 (Δ = +0.039). The emotion
signal's unique "unreliable" calls are not detecting ASR hallucination — they are detecting something
else (likely genuine emotion-relevant transcript noise that the ASR route is indifferent to).

### Why OR fails (H53b killed)

The OR policy routes MIXED only when *both* signals agree the track is unreliable, so it drops the 27
windows where text says unreliable but emotion says reliable from MIXED to SEPARATED (15 mixed decisions,
down from 42). 20 of those 27 windows are hurt by the drop (separated cpWER > mixed cpWER), for a total
cpWER loss of 25.25. This is the RQ36 failure mode directly: the LLM's `reliable` field reads
hallucinated transcripts as reliable, so requiring the emotion signal to *agree* lets hallucinations
through that the text signal alone would have caught. The OR policy is barely better than emotion-only
(1.371 vs 1.410) and far worse than text-only.

## Hypothesis Verdicts

- **H53a — AND policy cpWER ≤ text-only (1.043): KILLED.** AND cpWER 1.0823, Δ = +0.0390. The conservative
  fusion picks up harmful emotion-driven false alarms (notably window 08, +3.0 cpWER) that the text-only
  router correctly left on the separated route. Fail-open on emotion does not help ASR routing.

- **H53b — OR policy cpWER < text-only (1.043): KILLED.** OR cpWER 1.3712, Δ = +0.3279. The aggressive
  fusion requires the emotion signal to agree, but the emotion signal reads hallucinated transcripts as
  reliable (RQ36), so 20 of the 27 dropped windows hallucinate on the separated route (total loss 25.25
  cpWER). Requiring emotion agreement is strictly worse than trusting the text signal alone.

- **H53c — text and emotion disagree on > 20% of windows: SUPPORTED.** Disagreement 40.3% (31/77) overall,
  46.3% (31/67) on windows with a real emotion reading. The signals are genuinely decoupled — but the
  decoupling is dominated by the emotion signal being wrong where the text signal is right (27/31
  disagreements), so the decoupling does not translate into a cpWER improvement.

## Honest Limitations

1. **Cached emotion readings, not fresh calls.** This is a simulation over RQ36's cached `reliable` field.
   The cache has 67 entries for the 77 AISHELL-4 windows (10 silent windows have no transcript and use the
   fail-open default). A different LLM, prompt, or run could change the emotion readings and therefore the
   fusion result. The negative conclusion is robust to this in one direction — a *better* emotion signal
   would be needed to overturn it, and RQ36 already showed the LLM misses Mode S, so the direction of the
   bias (emotion too optimistic) is the documented failure mode.

2. **In-sample, single meeting.** All three source artefacts are calibrated on / computed for these exact
   77 windows of M_R003S02C01. The text-only 1.043 is itself an in-sample upper bound (RQ16's stated
   caveat), so the fusion policies' failure to beat it is an honest in-sample negative: even with the
   threshold tuned on the same data, the emotion signal does not add value. Generalisation to a held-out
   AISHELL-4 meeting is untested for all four policies.

3. **Binary emotion signal only.** We use only the LLM's boolean `reliable` field. The continuous
   `confidence` and `arousal`/`valence` fields RQ36 cached are not used. A policy that weights the emotion
   signal by confidence (or uses arousal/valence as a secondary feature) could in principle do better; we
   deliberately test the simplest decoupled fusion to establish whether the *direction* of improvement
   exists, and it does not.

4. **Emotion signal is fail-open on silent windows.** The 10 silent windows (no transcript) default to
   `reliable = True`. This matches RQ36's documented `_defaults()` policy, and all 10 windows tie at
   cpWER 1.0 on both routes (so the choice does not affect any policy's cpWER), but it is a modelling
   assumption worth stating.

5. **cpWER is utterance-level (whole Chinese string = 1 token).** This is RQ16/RQ30's stated limitation:
   the project's cpWER pipeline passes each speaker's full Chinese utterance as a single token to
   MeetEval, so cpWER > 1.0 counts extra inserted speaker-streams, not character-level errors. The fusion
   comparison inherits this granularity. A char-level re-validation (RQ31) is the required follow-up
   before claiming the negative is robust at character level.

6. **No deployable routing input.** Per the project's hard safety rules, cpWER / references are not used
   as routing input. The text signal here is RQ16's reference-free detector output (deployable); the
   emotion signal is RQ36's LLM judgment on the hypothesis transcript (also reference-free, but
   qualitative/demo quality). Neither uses ground truth.

## Reproducibility

- Script: `python3 results/frontier/emotion_aware_routing/emotion_aware_routing_analysis.py`
  (deterministic; numpy + stdlib only; no scipy / sklearn / Whisper / ollama).
- Tests: `python3 -m unittest tests.test_emotion_aware_routing -v` (84 tests, including 14 smoke tests on
  the real artefacts that pin the verified 77-window count, the 1.04329 text-only baseline, the 67/77
  emotion-reading coverage, and the 40.3% disagreement).
- Outputs: `emotion_aware_routing_results.json` (per-policy cpWERs + CIs + decision counts,
  disagreement cross-tab, hypothesis verdicts, per-window rows).
- Bootstrap: 10,000 resamples, seed=42.
- Source data: three read-only JSON artefacts (not modified).

## What this changes for the project

RQ16 closed the loop on the text-based corrected router (1.043 cpWER, lang-id entropy doing essentially
all the work). RQ36 then showed the LLM emotion reader is unreliable exactly where the ASR router needs
reliability — it reads hallucinated transcripts as "reliable". RQ53 closes the fusion question those two
opened: **a decoupled text+emotion router does not improve cpWER over the text-only corrected router.**

The negative is informative. The two signals disagree on 40% of windows, so the *opportunity* for fusion
existed — but the disagreements are overwhelmingly cases where the text signal is right and the emotion
signal is wrong (the RQ36 failure mode generalised beyond Mode S). Neither conservative fusion (AND, which
adds emotion false alarms) nor aggressive fusion (OR, which requires emotion agreement and lets
hallucinations through) helps. The text signal strictly dominates the emotion signal for ASR routing.

This is consistent with the stable baseline's "opposite tax" finding: the emotion signal is optimised for
emotion, not ASR, so fusing it into an ASR router adds noise rather than information. The natural next
direction is not tighter fusion of the same boolean `reliable` field, but either (a) a confidence-weighted
emotion signal that down-weights the LLM's optimistic readings, or (b) an entirely different emotion
signal (e.g. prosodic / acoustic arousal) that does not inherit the LLM's transcript-reading failure mode.
Until one of those is shown to add value, the text-only corrected router remains the project's best
ASR-routing policy on AISHELL-4.
