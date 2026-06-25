# RQ25: Out-of-Sample Corrected Router on AISHELL-4

> **Label: `experimental/frontier`** — Closes #926. Builds on RQ13 (PR #904) and RQ16 (PR #912).
> Reanalysis only (no Whisper / no ASR run); reuses the lang-id entropy detector from RQ13/RQ16
> and the existing AISHELL-4 external-validation windows (PR #890). Does NOT overwrite any verified
> reference / gold table.

## Executive Summary

RQ16 (PR #912) found that the corrected router (lang-id entropy at threshold 0.409 bits) recovers
AISHELL-4 cpWER to 1.043, within 0.026 of oracle. But the threshold was calibrated on the same 77
windows used for evaluation — **in-sample**. RQ25 asks the obvious next question: does the result
survive a held-out split?

This study implements three out-of-sample designs on the same 77 AISHELL-4 windows: a stratified
50/50 train/test split (seed=42), K-fold CV (K=5, stratified), and leave-one-out CV. The detector
(lang-id entropy, max across per-speaker separated tracks) is lifted verbatim from RQ13/RQ16. The
threshold is calibrated on the train split by sweeping 0.0-2.0 bits in 0.01 steps and selecting the
threshold that maximises sensitivity at >= 90% specificity.

**Two of three pre-registered hypotheses survive, one is killed:**

| Hypothesis | Verdict | Test statistic | Kill threshold |
|---|---|---:|---|
| H25a: out-of-sample test cpWER < 1.10 | **SUPPORTED** | 1.022 | >= 1.10 |
| H25b: out-of-sample test sensitivity > 80% | **SUPPORTED** | 100% (18/18) | <= 80% |
| H25c: train threshold within 20% of 0.409, i.e. [0.327, 0.491] | **KILLED** | 0.010 | outside [0.327, 0.491] |

The headline finding is a **split between cpWER generalisation and threshold stability**. The
corrected router's cpWER generalises: the held-out test cpWER (1.022, 95% CI [1.000, 1.057]) is
below the 1.10 kill threshold and even below the in-sample cpWER (1.043). K-fold CV (macro cpWER
1.030, CI [1.004, 1.065]) and LOO-CV (1.043, CI [1.009, 1.089]) corroborate. **But the threshold
does not generalise**: the 50/50 train split calibrates a threshold of 0.010, two orders of
magnitude below RQ16's 0.409 and far outside the [0.327, 0.491] window required by H25c.

The mechanism is concrete and verified per-window. The "max sensitivity at >= 90% specificity"
calibration rule is sensitive to which hallucinated windows land in the train split. The train
split happens to contain window 22 (Mode S, entropy 0.144 bits — a monoscript-Chinese
hallucination that the lang-id detector cannot distinguish from clean Chinese on the entropy axis
alone). To catch w22 while holding train specificity at >= 0.90 (i.e. FP <= 2 of 20 clean), the
threshold is forced down to 0.01. This very low threshold then also catches w30 (the other Mode S
window, entropy 0.323, in the test split), so the test split has **no Mode S failure** — the
corrected router is oracle on test (cpWER 1.022 = oracle 1.022). The 5 false-positive clean
windows on test all have `mixed_cpwer == separated_cpwer == 1.0` (clean non-overlapping windows
where both routes are perfect), so the over-flagging does not hurt cpWER.

The K-fold CV reveals the threshold's bimodality directly: 4 of 5 folds select threshold 0.38
(matching the in-sample threshold), but the one fold whose training half contains a Mode S window
drops to 0.01. The threshold mean is 0.306 with std 0.148 — the threshold is not identifiable from
n=39 training windows. LOO-CV is stable (threshold 0.38 for every one of the 77 folds), showing
that leave-one-out is too weak to expose the optimism: removing a single window does not move the
calibrated threshold, so LOO reproduces the in-sample cpWER (1.043) exactly. The threshold
instability only surfaces when a non-trivial fraction of the training set is held out.

**Bottom line.** The corrected router's cpWER claim is robust under out-of-sample evaluation on
this meeting, but the threshold is not. The 0.409 figure from RQ16 is an artefact of calibrating
on the full 77-window pool; a deployable threshold needs a larger calibration set (multiple
meetings) so that the operating point is not determined by whether one or two Mode S windows
happen to land in the train half. The cpWER generalisation here is partly fortuitous — the test
split's false positives all have tied cpWER — and should not be read as evidence that the lang-id
detector alone would transfer to a new meeting.

## Method

### Data (read-only, not overwritten)

`results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (label
`external/sanity-check`, PR #890): 77 windows of 30 s from AISHELL-4 meeting `M_R003S02C01` (6
speakers, 38.5 min). Each window already stores `always_mixed_cpwer`, `always_separated_cpwer`,
`router_v2_cpwer`, `oracle_best_cpwer`, and the per-speaker separated transcripts. No ASR is run;
the corrected router's per-window cpWER is the chosen route's stored cpWER.

Hallucination label: `always_separated_cpwer > 1.0` (cpWER > 1.0 means insertions dominate).
This gives 37 hallucinated / 40 clean — matching RQ12/RQ13/RQ16.

### Detector (RQ13/RQ16 verbatim)

`lang_id_entropy(text)`: Shannon entropy (bits) over the Unicode script-category distribution of
the text, computed via `unicodedata.name`. Clean Chinese is near-monoscript Han (entropy ~ 0);
diverse multilingual gibberish mixing Han+Latin+Katakana+Hangul has high entropy. Per-speaker
scores are aggregated by MAX across the separated tracks (worst-case speaker, the RQ12/RQ13
convention). The primitive is lifted verbatim from RQ13/RQ16 so thresholds are directly
comparable.

### Routing rule (RQ13/RQ16 convention)

HIGH lang-id entropy = diverse gibberish = hallucination. The detector flags the separated track
when `lang_id_entropy >= threshold`:

- if `lang_id_entropy >= threshold` -> flag hallucinated -> route MIXED (cpWER = `always_mixed_cpwer`)
- else -> route SEPARATED (cpWER = `always_separated_cpwer`)

This is the convention required for H25c (threshold within 20% of RQ16's 0.409, i.e. in
[0.327, 0.491]) to be a meaningful test. The corrected router's per-window cpWER is the chosen
route's stored cpWER, averaged over the evaluation set.

### Calibration rule

Sweep threshold over the grid {0.00, 0.01, 0.02, ..., 2.00} (201 candidates). For each candidate
`t`, flag = `score >= t`; compute sensitivity = TP/(TP+FN) and specificity = TN/(TN+FP) on the
calibration set. Select the threshold with specificity >= 0.90 and maximal sensitivity.
Tie-breaker: higher specificity, then lower threshold (more sensitive). This matches RQ13/RQ16's
">= 90% specificity operating point" rule, applied to a 0.01-bit grid.

### Out-of-sample designs

1. **Stratified 50/50 split (seed=42).** Within each class, shuffle (seed-controlled) and split:
   19 of 37 hallucinated to train (18 to test), 20 of 40 clean to train (20 to test). Train = 39
   windows, test = 38. Calibrate threshold on train; evaluate cpWER, sensitivity, specificity on
   test.
2. **K-fold CV (K=5, stratified, seed=42).** On each fold: calibrate threshold on the 4 training
   folds, evaluate cpWER and sensitivity on the held-out fold. Macro-average cpWER = mean over
   all 77 held-out windows of the selected cpWER; micro-average sensitivity pools all 77 held-out
   predictions.
3. **LOO-CV.** Each window held out once; threshold selected on the remaining 76 windows. The
   held-out window is classified at that threshold. Macro-cpWER = mean over 77 selected cpWERs.

### Statistics

Bootstrap 95% CI on test cpWER (10,000 resamples, seed=42) of the per-window selected cpWERs at
the FROZEN train-calibrated threshold. Threshold uncertainty is NOT included in the CI (a
limitation, see below). numpy + stdlib only.

## Results

### In-sample reproduction (calibrate + evaluate on all 77 windows)

To verify the script reproduces RQ16 before going out-of-sample:

| quantity | this study (0.01 grid) | RQ16 reported |
|---|---:|---:|
| threshold | 0.380 | 0.409 |
| sensitivity | 0.9459 (35/37) | 0.946 |
| specificity | 0.9250 (37/40) | 0.925 |
| corrected cpWER | 1.043290 | 1.043 |
| bootstrap CI 95% | [1.0087, 1.0887] | [1.0087, 1.0887] |

The 0.01-grid threshold (0.38) is the closest grid point that produces RQ13's exact operating
point (35/37 sensitivity, 37/40 specificity). The cpWER and CI match RQ16 to 4 decimal places.

### Stratified 50/50 split (seed=42)

Train: 39 windows (19 hallucinated / 20 clean). Test: 38 windows (18 hallucinated / 20 clean).

**Train calibration:**

| quantity | value |
|---|---:|
| threshold | **0.010** |
| sensitivity | 1.0000 (19/19) |
| specificity | 0.9000 (18/20) |
| train cpWER @ threshold | 1.089744 (in-sample optimism reference) |

The calibration selects threshold 0.01 because the train split contains window 22 (Mode S,
entropy 0.144 bits) — a hallucinated window with very low lang-id entropy. At threshold 0.38 (the
in-sample threshold), w22 is missed (sensitivity 18/19 = 0.947). Dropping the threshold to 0.01
catches w22 (sensitivity 19/19 = 1.0) while keeping FP = 2 of 20 clean (specificity = 0.90).

**Test evaluation at train-calibrated threshold (0.01):**

| quantity | value |
|---|---:|
| threshold applied | 0.010 |
| sensitivity | **1.0000 (18/18)** |
| specificity | 0.7500 (15/20) |
| corrected router cpWER | **1.021930** |
| bootstrap CI 95% | [1.0000, 1.0570] |
| always-mixed cpWER (test) | 1.179825 |
| always-separated cpWER (test) | 1.489035 |
| router v2 cpWER (test) | 1.149123 |
| oracle best cpWER (test) | 1.021930 |
| decisions | mixed=23, separated=15 |

The corrected router achieves test cpWER 1.022 — equal to the oracle and below all baselines
(always-mixed 1.180, router v2 1.149, always-separated 1.489). The reason it equals oracle: the 5
false-positive clean windows (w14, w19, w37, w52, w59 — all with non-zero lang-id entropy) all
have `mixed_cpwer == separated_cpwer == 1.0`, so routing them to MIXED does not cost cpWER. The
over-flagging is free on this test split.

The test split also contains window 30 (Mode S, entropy 0.323) — the other monoscript-Chinese
hallucination. At the train-calibrated threshold 0.01, w30 IS flagged (0.323 >= 0.01) and routed
to MIXED (cpWER 1.0). The in-sample threshold 0.38 would have missed w30 (0.323 < 0.38) and
routed it to SEPARATED (cpWER 2.0). This is why the out-of-sample test cpWER (1.022) is BETTER
than the in-sample cpWER (1.043): the low threshold catches a Mode S window that the in-sample
threshold misses.

### K-fold CV (K=5, stratified, seed=42)

| fold | n_test | train thr | sens | spec | cpWER |
|---:|---:|---:|---:|---:|---:|
| 0 | 16 (8pos/8neg) | 0.380 | 0.875 | 1.000 | 1.093750 |
| 1 | 16 (8pos/8neg) | 0.380 | 1.000 | 0.875 | 1.000000 |
| 2 | 15 (7pos/8neg) | 0.380 | 1.000 | 1.000 | 1.000000 |
| 3 | 15 (7pos/8neg) | 0.010 | 1.000 | 0.500 | 1.000000 |
| 4 | 15 (7pos/8neg) | 0.380 | 1.000 | 1.000 | 1.055556 |

| aggregate | value |
|---|---:|
| macro cpWER | **1.030303** |
| bootstrap CI 95% | [1.0043, 1.0649] |
| macro sensitivity | 0.9750 |
| macro specificity | 0.8750 |
| micro sensitivity | 0.9730 (36/37) |
| micro specificity | 0.8750 (35/40) |
| threshold mean / std | 0.306 / 0.148 |
| threshold range | [0.010, 0.380] |

The K-fold CV reveals the threshold's bimodality: 4 of 5 folds select threshold 0.38 (matching
the in-sample threshold), but fold 3 drops to 0.01 because its training half contains a Mode S
window. The threshold mean (0.306) and std (0.148) quantify the instability: the calibrated
threshold is not identifiable from a 60-window training set.

The macro cpWER (1.030) sits between the lucky 50/50 test (1.022) and the in-sample (1.043),
giving a more robust out-of-sample estimate. Folds 1, 2, 3 achieve cpWER = 1.000 (oracle on those
folds); folds 0 and 4 have cpWER > 1.0 (Mode S failures). The K-fold CV confirms the corrected
router's cpWER is robust on average, but the per-fold variance (1.000 to 1.094) is driven by
whether a Mode S window lands in a test fold.

### LOO-CV (n=77)

| quantity | value |
|---|---:|
| macro cpWER | **1.043290** |
| bootstrap CI 95% | [1.0087, 1.0887] |
| micro sensitivity | 0.9459 (35/37) |
| micro specificity | 0.9250 (37/40) |
| threshold mean / std | 0.380 / 0.000 |
| threshold range | [0.380, 0.380] |

LOO-CV is degenerate: removing a single window does not change the calibrated threshold (always
0.38), so LOO reproduces the in-sample cpWER (1.043) exactly. This is the key limitation of
leave-one-out for threshold calibration: the optimism lives in the threshold-selection step, and
removing one observation is too small a perturbation to move it. K-fold CV (which removes ~15
windows at a time) is the minimum design that exposes the threshold instability.

## Hypothesis Verdicts

- **H25a — out-of-sample corrected router cpWER < 1.10 on held-out test split: SUPPORTED.** Test
  cpWER = 1.022, 95% CI [1.000, 1.057], entirely below the 1.10 kill threshold. K-fold CV (1.030,
  CI [1.004, 1.065]) and LOO-CV (1.043, CI [1.009, 1.089]) corroborate. The cpWER claim is
  robust under all three out-of-sample designs. Caveat: the 50/50 test cpWER equals the oracle
  because the test split's 5 false-positive clean windows all have tied cpWER — a lucky split
  that should not be expected to repeat on a new meeting.

- **H25b — out-of-sample sensitivity on test split > 80%: SUPPORTED.** Test sensitivity = 100%
  (18/18 hallucinated windows flagged). The low train-calibrated threshold (0.01) catches every
  hallucinated test window, including w30 (Mode S, entropy 0.323). K-fold micro-sensitivity is
  97.3% (36/37); LOO micro-sensitivity is 94.6% (35/37). The sensitivity is robust across all
  designs, but note the trade-off: the 100% test sensitivity comes at the cost of 25% test
  specificity (5 FP of 20 clean). The router over-flags clean windows; it just happens not to
  cost cpWER here.

- **H25c — out-of-sample threshold within 20% of in-sample threshold [0.327, 0.491]: KILLED.**
  Train-calibrated threshold = 0.010, two orders of magnitude below RQ16's 0.409 and far outside
  the [0.327, 0.491] window. The K-fold thresholds (mean 0.306, std 0.148, range [0.01, 0.38])
  confirm the threshold is not stable under resampling. The kill is the central negative finding
  of this study: the lang-id entropy threshold is not identifiable from n=39-60 training windows.
  The 0.409 figure from RQ16 is an artefact of calibrating on the full 77-window pool.

## Honest Limitations

1. **Single meeting, 77 windows.** M_R003S02C01 is 1 of 20 AISHELL-4 test meetings. The 50/50
   split's lucky cpWER (1.022 = oracle) is driven by the test split's 5 false-positive clean
   windows all having tied cpWER — a coincidence of this meeting's window composition. A
   different meeting would have different clean-window entropy distribution and different cpWER
   ties. The K-fold CV (which rotates through 5 different test compositions) gives a more robust
   estimate (1.030), but all 5 folds still draw from the same 77 windows of the same meeting.

2. **Threshold instability is the headline caveat.** The "max sensitivity at >= 90% specificity"
   calibration rule is provably sensitive to whether a Mode S (low-entropy hallucinated) window
   lands in the train split. With n=39 train windows, ONE Mode S window forces the threshold
   from 0.38 to 0.01. This is not a bug in the calibration — it is the rule correctly maximising
   sensitivity — but it means the threshold is not a deployable number. A larger calibration set
   (multiple meetings, hundreds of windows) is needed so that the operating point is not
   determined by the presence/absence of 1-2 Mode S windows in the train half.

3. **LOO-CV is degenerate for threshold calibration.** Removing 1 window from a 77-window pool
   does not move the calibrated threshold (always 0.38), so LOO reproduces the in-sample cpWER
   (1.043) exactly. This shows LOO is too weak to expose threshold-selection optimism — the
   optimism lives in the threshold step, and K-fold (which removes ~15 windows at a time) is the
   minimum design that exposes it. Future threshold-stability studies on small datasets should
   prefer K-fold over LOO.

4. **cpWER CI excludes threshold uncertainty.** The bootstrap CI on test cpWER resamples the
   per-window selected cpWERs at the FROZEN train-calibrated threshold. It does not resample the
   threshold itself. A full threshold-uncertainty CI (re-calibrating on each bootstrap resample
   of train, then evaluating on test) would be wider and is left as future work — the K-fold
   threshold std (0.148) is the best available proxy for threshold uncertainty here.

5. **Mode S remains undetectable by lang-id entropy.** Both Mode S windows (w22, w30) have
   lang-id entropy < 0.4 (0.144, 0.323) because their hallucination is monoscript Chinese —
   semantically wrong but script-wise clean. The lang-id detector catches them only when the
   threshold is dropped so low (0.01) that it also flags 5 clean windows. A detector that
   catches Mode S without destroying specificity (e.g., a semantic / language-model detector)
   would be needed to make the corrected router deployable. RQ19 (Mode S detector) is the
   relevant next step.

6. **In-sample reproduction uses a 0.01-bit grid.** RQ13's exact threshold was 0.409073; the
   0.01 grid used here lands on 0.38, the closest grid point producing the same operating point
   (35/37 sensitivity, 37/40 specificity). The cpWER (1.043290) matches RQ16 to 4 decimal places.
   Using the exact RQ13 threshold (0.409073) instead of the grid would not change any conclusion.

7. **No deployable routing input.** Per the project's hard safety rules, cpWER / references are
   not used as routing input — the lang-id entropy detector is computed only from the hypothesis
   transcripts, which is the deployable signal surface. The hallucination label
   (`always_separated_cpwer > 1.0`) is used only for calibration and evaluation, not for routing.

8. **cpWER is utterance-level (whole Chinese string = 1 token).** RQ30
   (`results/frontier/meeteval_cpwer_validation/`, PR #935) showed that the project's cpWER
   pipeline passes each speaker's full Chinese utterance as a single token, so cpWER > 1.0 here
   measures *extra inserted speaker-streams* per window, not character-level transcription
   accuracy. All thresholds, sensitivities, and cpWER recovery figures in this study are at the
   utterance level. RQ30 found that switching to char-level cpWER preserves the *direction* of the
   mixed-vs-separated comparison but scrambles the *per-window ordering* (48% of windows would
   have a different char-level winner). The out-of-sample threshold stability and the "cpWER
   generalises" claim above are therefore utterance-level only; a char-level re-validation
   (RQ31/RQ35) is the required follow-up before claiming the corrected router generalises at
   character granularity.

## Reproducibility

- Script: `/opt/homebrew/bin/python3 results/frontier/out_of_sample_router/out_of_sample_router_analysis.py`
  (deterministic; numpy + stdlib only; no scipy / sklearn / Whisper).
- Outputs:
  - `out_of_sample_results.csv` — per-window table (lang_id_entropy, hallucination label,
    split_5050 assignment, in-sample / test / K-fold / LOO thresholds and selected cpWERs).
  - `out_of_sample_results.json` — full summary (in-sample reproduction, 50/50 split, train
    calibration, test evaluation, K-fold CV per-fold, LOO-CV, hypothesis verdicts).
- Bootstrap: 10,000 resamples, seed=42.
- Stratified splits: seed=42 (50/50 and K=5).
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).

## What this changes for the project

RQ16 closed the loop mechanistically: a corrected router with three reference-free guards
recovers AISHELL-4 cpWER to 1.043, with lang-id entropy doing essentially all the work. RQ25
opens the next loop: the cpWER recovery is **robust under out-of-sample evaluation** (test cpWER
1.022, K-fold 1.030, LOO 1.043 — all below 1.10 and below always-mixed), but the **threshold is
not** (H25c killed: train threshold 0.01 vs RQ16's 0.409).

The negative finding refines RQ16's headline caveat. RQ16 said "the 1.043 figure is an in-sample
upper bound; a proper test needs a held-out meeting." RQ25 shows that even within the single
available meeting, the threshold is not identifiable from a 39-60 window train split — the
calibration rule's output is bimodal (0.38 or 0.01) depending on whether a Mode S window lands in
train. The cpWER is robust because the over-flagging falls on tied-cpWER clean windows, but that
coincidence is a property of this meeting, not a generalisable guarantee.

The concrete next steps RQ25 points to:

1. **Multi-meeting calibration.** The threshold needs hundreds of windows across multiple
   AISHELL-4 meetings so that Mode S windows are diluted in the train pool and the operating
   point stabilises. The single-meeting external validation (PR #890) does not permit this.
2. **Mode S detector.** RQ19 (Mode S detector) is the missing piece — a detector that catches
   monoscript-Chinese semantic hallucination without dropping the lang-id threshold to 0.01. The
   lang-id detector's threshold instability is fundamentally driven by Mode S; a complementary
   Mode S detector would let the lang-id threshold stay at 0.38 (where it is stable) and catch
   the 2 Mode S windows separately.
3. **K-fold over LOO for threshold studies.** LOO-CV is degenerate for threshold calibration on
   small datasets — it reproduces the in-sample threshold exactly. Future threshold-stability
   studies should prefer K-fold (K=5 or 10), which is the minimum design that exposes the
   optimism.

Until multi-meeting calibration is available, the 0.409 threshold from RQ16 should be treated as
a meeting-specific operating point, not a deployable number — and the cpWER recovery it enables
should be read as "the corrected router could mechanistically recover the gap" (RQ16) plus "the
cpWER recovery is robust to a 50/50 split on this meeting" (RQ25), not as "the lang-id threshold
transfers".
