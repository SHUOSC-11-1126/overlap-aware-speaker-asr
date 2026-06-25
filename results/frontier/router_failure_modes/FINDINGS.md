# RQ12: Router v2 Failure-Mode Decomposition on AISHELL-4

> **Label: `experimental/frontier`** — reanalysis-only decomposition of *why* router v2
> fails to beat always-mixed on AISHELL-4 (finding #23: router v2 cpWER 1.206 vs
> always-mixed 1.173). No Whisper / no ASR model is run; this reads the existing
> AISHELL-4 external-validation results and classifies each failure window.
> Closes #895. See `results/external_sanity_check/aishell4/FINDINGS.md` (RQ1, the
> failure surface), `results/frontier/causal_hallucination_probe/FINDINGS.md`
> (finding #21, the confident-attractor mechanism), and
> `results/frontier/silence_aware_gate/FINDINGS.md` (RQ8, the proposed gate cure).

## Executive Summary

Router v2 picks the oracle-worse method on **11 of 77** AISHELL-4 windows (85.7%
routing accuracy). We decomposed the total **routing regret** (router cpWER minus
oracle-best cpWER, summed = 14.5) into four mutually exclusive failure modes and
bootstrapped 95% CIs for each mode's share.

**The dominant failure mode is diverse hallucination on separated tracks that the
compression-ratio (CR) guard cannot detect.** Of the 14.5 total routing regret:

| Failure mode | n | Regret | Share | Bootstrap 95% CI |
|---|--:|------:|------:|---:|
| **separated hallucination — CR-missed** (diverse, low-CR) | 8 | 9.83 | **67.8%** | [33.3%, 100.0%] |
| mixed hallucination (router picked mixed, mixed blew up) | 2 | 4.00 | 27.6% | [0.0%, 61.9%] |
| separated hallucination — CR-caught (repetitive, high-CR) | 1 | 0.67 | 4.6% | [0.0%, 18.2%] |
| wrong-route, non-hallucination (both tracks clean) | 0 | 0.00 | 0.0% | [0.0%, 0.0%] |

**100% of router v2's routing regret is hallucination-driven.** There is not a
single window where the router made a "clean" routing error (picked the slightly
worse of two non-hallucinated transcripts). Every failure is the router picking a
track that catastrophically hallucinated (cpWER > 1.0, i.e. insertions dominate).

**Hypothesis verdicts:**

- **H12a (hallucination > 50% of routing regret): SUPPORTED.** Separated-track
  hallucination alone accounts for 72.4% of routing regret; any hallucination
  (separated + mixed) accounts for 100%.
- **H12b (CR threshold < 50% sensitivity): SUPPORTED.** Of the 37 windows where the
  separated track hallucinated (cpWER > 1.0), Whisper's CR threshold (2.4) catches
  only **1** — a sensitivity of **2.7%** (bootstrap 95% CI [0.0%, 8.8%]). The CR
  signal essentially does not transfer to AISHELL-4.
- **H12c (silence-aware gate fixes > 30%): CANNOT CONFIRM.** The addressable-regret
  upper bound is 72.4% (> 30%), but the conservative CR-caught-only bound is 4.6%
  (< 30%). The CR evidence reveals the hallucination is predominantly *diverse*
  (low CR), not *repetitive* (high CR) — which questions whether the silence-aware
  gate, designed for the repetitive confident-attractor, would actually fix it.

## Method

### Data source (read-only, not overwritten)

`results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
(label `external/sanity-check`, PR #890): 77 windows × 30 s from AISHELL-4 meeting
M_R003S02C01 (6 speakers, oracle-TextGrid separation, Whisper-tiny, MeetEval
cpWER/orcWER). Each window stores the mixed transcript, per-speaker separated
transcripts, mixed/separated cpWER, the router v2 decision + rule, and the
oracle-best cpWER.

### Regret definitions

- **Routing regret** (per window) = `router_v2_cpwer − oracle_best_cpwer` ≥ 0. This
  is the cost of suboptimal routing — the quantity failure modes explain. A window
  is a *failure window* iff routing regret > 0 (router picked the oracle-worse
  method). Total routing regret = 14.5 over 11 failure windows.
- **Regret vs always-mixed** (per window) = `router_v2_cpwer − always_mixed_cpwer`.
  This is the headline finding #23 quantity; summed = +2.5 (avg +0.0325/window).

### Compression-ratio (CR) proxy

The RQ1 JSON did **not** store Whisper's per-segment `compression_ratio`. We
recompute it from the stored transcript text using Whisper's own formula
(`len(utf8_bytes) / len(zlib(bytes))`) on the per-speaker **concatenated** separated
text, taking the max across speakers. This is a documented **lower bound** on
Whisper's true per-segment max CR (concatenating clean + hallucinated segments
dilutes CR). Consequences:
- A window flagged **CR-caught** here is reliably CR-caught in Whisper.
- A window flagged **CR-missed** here *might* still be CR-caught in Whisper — so the
  analysis is **conservative for H12b** (it overestimates CR-misses, underestimates
  sensitivity). The true sensitivity is at least as high as reported, and almost
  certainly still far below 50%.

### Failure-mode classification (mutually exclusive, failure windows only)

| Mode | Condition |
|------|-----------|
| `separated_hallucination_cr_caught` | router picked separated, separated lost, separated cpWER > 1.0, **and** max CR > 2.4 (repetitive hallucination the CR guard WOULD detect) |
| `separated_hallucination_cr_missed` | router picked separated, separated lost, separated cpWER > 1.0, **and** max CR ≤ 2.4 (diverse hallucination the CR guard would MISS) |
| `mixed_hallucination` | router picked mixed, mixed lost, mixed cpWER > 1.0 (the MIXED track hallucinated; separated was clean) |
| `wrong_route_nonhalluc` | router picked the worse method but NEITHER track hallucinated (both cpWER ≤ 1.0) — a pure routing-judgment error |

### Bootstrap

10,000 resamples (seed=42), resampling the 77 windows with replacement and
recomputing each mode's share of total routing regret. CIs are wide because only 11
windows carry regret — this is inherent to a single-meeting evaluation and is
reported honestly.

## Results

### The 11 failure windows

| win | overlap | spk | router pick | mixed | sep | router | regret | maxCR_sep | primary mode |
|----:|:-------:|:---:|:-----------:|------:|----:|-------:|-------:|----------:|--------------|
| 0 | NoOv | 6 | separated | 1.00 | 2.33 | 2.33 | 1.33 | 1.10 | sep-halluc CR-missed |
| 5 | NoOv | 1 | separated | 1.00 | 2.00 | 2.00 | 1.00 | 0.93 | sep-halluc CR-missed |
| 8 | NoOv | 1 | mixed | 4.00 | 1.00 | 4.00 | 3.00 | 0.90 | mixed-hallucination |
| 18 | Heavy | 3 | separated | 1.00 | 1.67 | 1.67 | 0.67 | 2.97 | sep-halluc CR-caught |
| 22 | NoOv | 2 | separated | 1.00 | 2.00 | 2.00 | 1.00 | 1.37 | sep-halluc CR-missed |
| 26 | NoOv | 2 | separated | 1.00 | 3.50 | 3.50 | 2.50 | 1.41 | sep-halluc CR-missed |
| 29 | Light | 2 | mixed | 2.00 | 1.00 | 2.00 | 1.00 | 1.00 | mixed-hallucination |
| 30 | NoOv | 1 | separated | 1.00 | 2.00 | 2.00 | 1.00 | 1.49 | sep-halluc CR-missed |
| 31 | NoOv | 2 | separated | 1.50 | 2.50 | 2.50 | 1.00 | 0.99 | sep-halluc CR-missed |
| 41 | NoOv | 2 | separated | 1.00 | 1.50 | 1.50 | 0.50 | 0.91 | sep-halluc CR-missed |
| 42 | NoOv | 2 | separated | 1.50 | 3.00 | 3.00 | 1.50 | 0.97 | sep-halluc CR-missed |

**8 of 9 separated-hallucination failures are at NoOverlap**, where the router's rule
`overlap==0 and mixed_segments_count > 5 → separated` fires. On the gold benchmark
this rule is correct (separated is clean at NoOverlap); on AISHELL-4 the
oracle-TextGrid separated tracks contain long interior silence gaps that trigger
hallucination, so the rule fires on the wrong stratum. The single HeavyOverlap
failure (w18) is the only CR-caught window — its separated text was repetitive
enough (CR 2.97) for the guard to detect.

### Why the CR signal does not transfer (H12b)

Whisper's compression-ratio guard catches **repetition** (highly compressible text).
On the gold benchmark the confident-attractor produced clean repetition loops (CR up
to 37 in the causal-probe smoke test). On AISHELL-4 the hallucination is **diverse
multilingual gibberish** — e.g. window 0's separated text mixes Chinese, English,
Japanese and Korean characters (`"美國生活差幾個岩是這個但是龫龍來不战..."`,
`"可以 카메 mad將會全部視起來..."`). Diverse text does **not** compress well, so its
CR stays near 1.0–1.5, far below the 2.4 threshold. Of 37 hallucinated separated
tracks, only 1 has CR > 2.4. **The CR guard is the wrong detector for this
hallucination type** — this is the "compression-ratio signal non-transfer."

### Multi-speaker is not the driver (category d)

Only 2 of 11 failure windows have > 2 active speakers (w00 with 6, w18 with 3),
accounting for 13.8% of routing regret. Three failure windows have just **1
speaker** (w05, w08, w30) — even single-speaker oracle-TextGrid tracks hallucinate,
because the separation still leaves silence gaps between that speaker's turns. This
confirms the failure is driven by the **silence-gap stimulus**, not by multi-speaker
confusion.

### Router vs always-mixed decomposition (finding #23)

The router picks separated 25 times: it **wins 16** (separated is genuinely better,
total gain 8.0) and **loses 9** (separated hallucinates, total loss 10.5). The net
is −2.5 (router worse by 0.0325/window). The router's separated picks are *good when
they do not hallucinate*; the problem is purely the hallucination tail. **If the
separated hallucination were eliminated, the router would beat always-mixed**
(router cpWER would fall to ~1.069 vs mixed 1.173).

## Hypothesis Verdicts

### H12a — hallucination > 50% of routing regret: **SUPPORTED**

- Separated-track hallucination share: **72.4%** (regret 10.5 / 14.5).
- Any-hallucination (separated + mixed) share: **100%** (regret 14.5 / 14.5).
- Zero non-hallucination routing errors.

The router's regret is entirely a hallucination problem, not a routing-judgment
problem. The "overlap distribution shift" (category b) is the *proximate* cause —
the NoOverlap rule fires on the wrong stratum — but the *root* cause is that
separated tracks hallucinate at NoOverlap on AISHELL-4.

### H12b — CR threshold < 50% sensitivity: **SUPPORTED**

- Sensitivity = P(max CR > 2.4 | separated cpWER > 1.0) = **1/37 = 2.7%**.
- Bootstrap 95% CI: [0.0%, 8.8%] — the upper bound is far below 50%.

The CR guard is almost completely blind to AISHELL-4 hallucination. This is
conservative (the concatenated-text CR proxy is a lower bound on Whisper's
per-segment max CR), so the true sensitivity is at least as low. The mechanism: the
hallucination is diverse (low CR), not repetitive (high CR), so the CR signal
designed for repetition loops does not transfer.

### H12c — silence-aware gate fixes > 30%: **CANNOT CONFIRM**

The silence-aware gate (`src/silence_aware_gate.py`, RQ8) was designed to remove the
interior-silence stimulus that drives the **repetitive** confident-attractor (Mode R,
finding #21). It was never run on AISHELL-4 (data/Whisper unavailable; see
`results/frontier/silence_aware_gate/FINDINGS.md`), and this reanalysis cannot run it
either. We report two bounds:

- **Upper bound (optimistic):** if the gate perfectly eliminated *all* separated
  hallucination (diverse + repetitive), it would address 72.4% of routing regret
  (> 30%). This assumes the silence stimulus drives both hallucination modes.
- **Conservative bound (CR-caught only):** if the gate only fixes the *repetitive*
  hallucination it was designed for (the 1 CR-caught window), it would address 4.6%
  of routing regret (< 30%).

The CR evidence (H12b) is the crux: 97% of the separated hallucination is **diverse**
(low CR), which the causal probe classified as Mode N (diffuse, non-repetition),
*not* Mode R (repetitive). The silence gate's mechanism — remove silence → stop the
repetition loop — may not apply to Mode N. **H12c is therefore in genuine doubt at
the mechanism level**: the upper bound exceeds 30%, but the conservative bound does
not, and the hallucination type the gate targets (repetitive) is the minority of the
AISHELL-4 failure mass. Resolving H12c requires running the gate on AISHELL-4 audio.

## Limitations

1. **Single meeting, 11 failure windows.** Only M_R003S02C01 was available; the 11
   failure windows make bootstrap CIs wide (e.g. the dominant mode's CI spans
   [33.3%, 100%]). The point estimates are stable, but per-mode fractions should be
   read as indicative, not precise.
2. **CR is a lower-bound proxy.** Recomputed on concatenated per-speaker text, not
   Whisper's per-segment text. This underestimates CR and overestimates CR-misses —
   conservative for H12b. The qualitative conclusion (CR does not transfer) is robust
   because the gap (2.7% vs 50%) is too large to close with the proxy bias.
3. **Reanalysis only — no gate run.** H12c cannot be confirmed without running the
   silence-aware gate on AISHELL-4 audio. The bounds bracket the possible outcome but
   do not measure it.
4. **Oracle-TextGrid separation.** The separated tracks are oracle (true silence
   gaps), not real-separator output (residual noise). The failure modes are specific
   to this separation paradigm; a real separator (Gap M2) may produce different
   hallucination types.
5. **Whisper-tiny only.** A stronger model may hallucinate less and change the
   failure-mode mix.

6. **Oracle and cpWER are utterance-level (whole Chinese string = 1 token).** The
   "85.7% routing accuracy" (11/77 oracle-worse picks) and the entire 11-window
   failure decomposition are computed against an utterance-level oracle, where each
   speaker's full Chinese transcript counts as a single token. RQ30
   (`results/frontier/meeteval_cpwer_validation/`, PR #935) later showed that 48% of
   these 77 windows would have a *different* winner under char-level cpWER — the
   per-window oracle flips on roughly half the windows when tokens are characters
   instead of whole utterances. The failure-mode shares (diverse-hallucination 67.8%,
   mixed-hallucination 27.6%, etc.) are therefore utterance-level quantities; a
   char-level re-decomposition (RQ35) is the required follow-up before claiming the
   "100% of routing regret is hallucination-driven" finding holds at character
   granularity. The qualitative direction (CR does not transfer; hallucination
   dominates) is robust because RQ30 showed the *direction* of mixed-vs-separated is
   preserved, but the precise 11-window failure set and the per-mode regret shares
   should be read as utterance-level.

## What this changes for the project

1. **The router's failure is a hallucination problem, not a routing-logic problem.**
   The router's rules are reasonable; they fail only because separated tracks
   hallucinate on AISHELL-4. Fixing the hallucination (not the routing logic) is the
   lever — and if fixed, the router would beat always-mixed.
2. **The CR guard is the wrong detector for AISHELL-4.** A reference-free gate that
   relies on compression ratio will miss 97% of the hallucination here. The project
   needs a detector for *diverse* hallucination (e.g. language-id entropy,
   no_speech_prob, or the token-id lock-in from finding #21), not repetition CR.
3. **The silence-aware gate's scope is bounded.** It targets Mode R (repetitive); the
   AISHELL-4 failure mass is Mode N (diverse). The gate may still help (silence could
   trigger both modes), but H12c cannot be assumed true — it must be tested by
   running the gate, and a negative result would be a valuable boundary finding
   pointing toward a real separator (Gap M2).

## Reproducibility

- Script: `results/frontier/router_failure_modes/failure_mode_analysis.py`
- Per-window classification: `results/frontier/router_failure_modes/failure_mode_results.csv`
- Summary + CIs: `results/frontier/router_failure_modes/failure_mode_results.json`
- Run: `python3 results/frontier/router_failure_modes/failure_mode_analysis.py`
  (numpy + stdlib only; no scipy, no Whisper, no audio).
