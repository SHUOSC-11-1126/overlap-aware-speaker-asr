# RQ35: Char-Level cpWER Failure-Mode Characterisation on AISHELL-4

> **Label: `experimental/frontier`** — reanalysis-only decomposition of *which* AISHELL-4
> windows are worst at char-level cpWER and *how* the char-level failure decomposition
> differs from the utterance-level decomposition in RQ12. No Whisper / no ASR model is
> run; this re-runs MeetEval 0.4.3 on the stored AISHELL-4 transcripts at two
> tokenisation granularities and reads the per-window error decomposition. Closes #942.
> Builds on RQ30 (`results/frontier/meeteval_cpwer_validation/`, PR #935 — the
> utterance-vs-char tokenisation finding), RQ12 (`results/frontier/router_failure_modes/`,
> PR #900 — the utterance-level failure decomposition), and RQ19
> (`results/frontier/mode_s_detector/`, PR #919 — the Mode S monoscript residual).

## Executive Summary

RQ12 concluded that **100% of router v2's routing regret on AISHELL-4 was
hallucination-driven** (separated-track hallucination 72.4% + mixed-track
hallucination 27.6%, 0% clean routing errors), measured at *utterance-level* cpWER
(each speaker's whole Chinese string = 1 token). RQ30 then showed the project's
cpWER was utterance-level, not the char-level standard, and that the per-window
oracle flips on ~48% of windows when tokens are characters. RQ35 closes the loop:
**does RQ12's "100% hallucination" finding survive at char-level?** No.

We re-ran MeetEval on all 77 windows at both granularities, using
`CPErrorRate.substitutions/insertions/deletions` for the error-type decomposition.
The char-level aggregate reproduces RQ30's baseline exactly
(always_separated = 0.915831), and the utterance-level failure set reproduces
RQ12's 11 windows exactly — so the two baselines are faithfully recovered before
the char-level re-decomposition is reported.

**The char-level failure decomposition inverts RQ12's headline.** At char-level:

| Failure mode | RQ12 (utterance) | RQ35 (char) |
|---|--:|--:|
| separated hallucination — CR-missed | 67.8% | 19.5% |
| separated hallucination — CR-caught | 4.6% | 0.0% |
| mixed hallucination | 27.6% | 0.0% |
| **wrong-route non-hallucination** | **0.0%** | **80.5%** |
| failure windows (router acc) | 11/77 (85.7%) | 36/77 (53.2%) |

At char-level, **80.5% of routing regret is clean routing-judgment error**
(router picked the slightly-worse of two non-hallucinated tracks), not
hallucination. The mechanism: only **4 of 64** active windows have char-level
separated cpWER > 1.0 (the hallucination threshold), versus **37 of 64** at
utterance-level. Char-level cpWER is much lower in magnitude (aggregate 0.916 vs
1.591) because counting character edits — not whole-speaker-token insertions —
shrinks the apparent cost of hallucinated tracks. With fewer windows over the
hallucination threshold, most char-level failure windows are sub-threshold
routing errors, not catastrophic hallucination.

**Hypothesis verdicts: H35a SUPPORTED, H35b SUPPORTED (with caveat), H35c NOT SUPPORTED.**

- **H35a (top-10 differ, ρ < 0.5): SUPPORTED.** Spearman ρ between char-level and
  utterance-level separated-cpWER rankings = **0.108** (p = 0.351). Top-10 overlap
  = **1/10** (only w23; Jaccard 0.053). The char-level top-10 is dominated by 1.0
  *sentinel* windows (separator produced no output) — 6 of 10 — plus 4 real
  hallucination windows (w0, w23, w51, w65).
- **H35b (subs dominate ins at char-level): SUPPORTED.** For the 36 char-level
  failure windows' separated tracks, char-level substitutions (2,082) ≫
  insertions (161); at utterance-level the same windows have insertions (67) >
  substitutions (64). The shift is exactly as predicted: char-level counts
  character edits, utterance-level counts speaker-stream insertions. **Caveat:**
  char-level *deletions* (3,190) exceed substitutions (2,082), so the fuller
  ordering is dels > subs > ins. H35b's narrow claim (subs > ins) holds; the
  dominant char-level error type is actually deletion, not substitution.
- **H35c (Mode S w22, w30 remain char-level worst): NOT SUPPORTED.** w22 is
  char-level rank **77/77** (cpWER 0.4915 — literally the *best* window) and w30
  is rank 62/77 (cpWER 0.8027). Neither is in the char-level top-10. At
  utterance-level both had cpWER 2.0 (RQ12 failure windows); at char-level both
  flip to **non-failure** windows where separated is oracle-best. Mode S's
  near-duplicate-of-mixed text shares many characters with the reference, so
  per-character cost is moderate, not catastrophic.

## Method

### Data source (read-only, not overwritten)

`results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
(label `external/sanity-check`, PR #890): 77 windows × 30 s from AISHELL-4 meeting
M_R003S02C01 (6 speakers, oracle-TextGrid separation, Whisper-tiny, MeetEval
cpWER/orcWER). Each window stores the mixed transcript, per-speaker separated
transcripts, mixed/separated cpWER, the router v2 decision + rule, and the
oracle-best cpWER. No file is modified.

### Tokenisation (the RQ30 finding, applied faithfully)

Two granularities, both via MeetEval 0.4.3:

- **Char-level** (standard Chinese cpCER convention): insert a space between each
  Chinese character so MeetEval treats each character as one token
  (`"你好世界"` → `"你 好 世 界"`). This is the granularity the Chinese-ASR
  community uses.
- **Utterance-level** (the project's stored convention, RQ30): each speaker's
  whole Chinese string is one token (no whitespace → 1 token per speaker). This
  reproduces the stored values bit-for-bit and is the granularity RQ12 used.

For both granularities we use `cpwer` for the separated track (multi-speaker
reference vs multi-speaker hypothesis) and `orcwer` for the mixed track
(single mixed channel vs multi-speaker reference) — matching RQ30's approach so
the char-level aggregate reproduces RQ30's baseline (always_separated 0.915831).
The `CPErrorRate` result objects expose `substitutions`, `insertions`,
`deletions`, `errors`, `length`, which we read for the error-type decomposition.
Empty-hypothesis windows (separator produced no output) use the project's
1.0 sentinel (matching RQ30's `safe_cpwer`); their breakdown counts are zeroed
and they are flagged `empty=True`, excluded from error-breakdown sums but
included in cpWER means/rankings (to match RQ30's aggregate).

> Note on API: the task brief referenced `CPErrorRate` from `meeteval.io.cpwer`.
> In MeetEval 0.4.3 the class lives in `meeteval.wer` and is returned by the
> `cpwer()` / `orcwer()` functions; the decomposition fields are identical. The
> script uses `from meeteval.wer import cpwer, orcwer` and reads
> `result.substitutions` etc.

### Failure-mode classification (mirrors RQ12, applied at each granularity)

A window is a *failure window* iff `router_cpwer − oracle_best_cpwer > 0` (router
picked the oracle-worse method). Primary modes (mutually exclusive, failure
windows only), using the cpWER > 1.0 hallucination threshold and the CR > 2.4
compression-ratio threshold (CR recomputed from stored text via zlib, identical
to RQ12's lower-bound proxy):

| Mode | Condition |
|------|-----------|
| `separated_hallucination_cr_caught` | router picked separated, separated lost, separated cpWER > 1.0, max CR > 2.4 |
| `separated_hallucination_cr_missed` | router picked separated, separated lost, separated cpWER > 1.0, max CR ≤ 2.4 |
| `mixed_hallucination` | router picked mixed, mixed lost, mixed cpWER > 1.0 |
| `wrong_route_nonhalluc` | router picked the worse method but NEITHER track hallucinated (both cpWER ≤ 1.0) |
| `none` | not a failure window |

The same classifier is run at char-level and utterance-level, so the mode mix
shift is an apples-to-apples comparison.

### Mode S windows

Mode S = the 2 monoscript-Chinese separated hallucinations that escape every
surface detector (RQ19): hallucinated AND `lang_id_entropy < 0.409` AND
`length_ratio < 2.0` AND `cr < 2.4` → exactly **windows 22 and 30**. We use
RQ19's verified label (`is_mode_s = window_id in {22, 30}`) rather than
recomputing lang-id entropy.

### Sanity checks (both pass)

1. Char-level aggregate `always_separated` = **0.915831** = RQ30's reported
   value (bit-for-bit).
2. Utterance-level failure window set = **{0, 5, 8, 18, 22, 26, 29, 30, 31, 41,
   42}** = RQ12's 11 windows exactly (`matches_rq12 = True`).

Recovering both established baselines before reporting the new char-level
decomposition is what makes the mode-mix shift trustworthy.

## Results

### Aggregate cpWER (mean over 77 windows)

| Policy | char-level | utterance-level |
|---|--:|--:|
| always_mixed | 0.910577 | 1.173160 |
| always_separated | 0.915831 | 1.590909 |
| router_v2 | 0.922196 | 1.205628 |
| oracle_best | 0.876847 | 1.017316 |

The char-level column reproduces RQ30. The separation tax (separated − mixed)
shrinks from 0.418 (utterance) to 0.005 (char) — the ~80x inflation RQ30
reported. The router-versus-mixed gap shrinks from +0.033 (utterance) to +0.012
(char).

### H35a — ranking: char-level vs utterance-level top-10 worst (by separated cpWER)

Spearman ρ over all 77 windows = **0.108** (p = 0.351) — far below the 0.5
threshold. Top-10 overlap = **1 of 10** (Jaccard 0.053).

| rank | char-level top-10 | cpWER | utterance-level top-10 | cpWER |
|----:|----:|----:|----:|----:|
| 1 | w0 | 1.6455 | w11 | 4.0000 |
| 2 | w23 | 1.5747 | w23 | 3.0000 |
| 3 | w65 | 1.1320 | w26 | 3.5000 |
| 4 | w51 | 1.0361 | w42 | 3.0000 |
| 5 | w1* | 1.0000 | w45 | 3.0000 |
| 6 | w4* | 1.0000 | w53 | 2.0000 |
| 7 | w7* | 1.0000 | w63 | 2.0000 |
| 8 | w9* | 1.0000 | w68 | 2.0000 |
| 9 | w10* | 1.0000 | w73 | 2.0000 |
| 10 | w13* | 1.0000 | w76 | 2.0000 |

`*` = 1.0 sentinel (separator produced no output). 6 of the char-level top-10
are separator-silence sentinels, not hallucination. Among **active** (non-empty
separated hyp) windows only, the char-level top-10 is
[w0, w23, w65, w51, w21, w66, w67, w15, w24, w48] — still no overlap with RQ12's
failure set beyond w0, and still no Mode S window. **H35a SUPPORTED.**

### H35b — error-type mix: substitutions vs insertions

Error decomposition of the **separated track** (the track whose hallucination
drove RQ12's regret), summed over the 36 char-level failure windows:

| Granularity | substitutions | insertions | deletions | errors | length |
|---|--:|--:|--:|--:|--:|
| char-level (36 failure windows) | **2,082** | 161 | 3,190 | 5,433 | 5,923 |
| utterance-level (same 36 windows) | 64 | **67** | 14 | 145 | 78 |

At char-level, substitutions (2,082) ≫ insertions (161); at utterance-level the
same windows have insertions (67) > substitutions (64). The shift is exactly as
H35b predicts: utterance-level counts whole extra speaker streams as insertions
(the hallucinated speaker tokens beyond the reference speaker count), while
char-level counts character-level edits where overlapping-but-wrong characters
score as substitutions. The char-level top-10 worst shows the same pattern
(subs 393 > ins 192), as do all 64 active windows in aggregate (subs 4,194 >
ins 341). **H35b SUPPORTED.**

**Caveat (reported honestly):** char-level *deletions* (3,190) exceed
substitutions (2,082), so the full char-level error-type ordering is
**dels > subs > ins**. H35b's narrow pre-registered claim is "subs dominate
ins", which holds; but the dominant char-level error type is deletion (the
separated track often *omits* reference characters — especially on
separator-silence windows where the ref has content the hyp lacks), not
substitution. Substitution is the dominant *non-deletion* error type.

### H35c — Mode S windows (w22, w30) in char-level top-10

| window | utter cpWER | utter rank | char cpWER | char rank (all) | char rank (active) | char failure? |
|----:|--:|--:|--:|--:|--:|:--:|
| w22 | 2.000 | (RQ12 fail) | **0.4915** | **77/77** | **64/64** | no |
| w30 | 2.000 | (RQ12 fail) | **0.8027** | 62/77 | 49/64 | no |

Both Mode S windows are **char-level non-failures**: at char-level the router
picked separated and separated is oracle-best (w22: char_sep 0.4915 < char_mix
0.5424; w30: char_sep 0.8027 = char_mix 0.8027). w22 is literally the *best*
window by char-level separated cpWER. **H35c NOT SUPPORTED.**

Mechanism: Mode S is a near-duplicate of the *mixed* transcript (RQ19), and the
mixed audio contains the same speakers as the reference. So the Mode S separated
text shares many characters with the reference (w22: subs 34, ins 1, dels 23 of
118 ref chars — ~52% of reference characters correct). Per-character, Mode S is
moderate-cost, not catastrophic. The utterance-level "2.0" was an artifact of
whole-string-as-token equality: the hyp string ≠ the ref string, so the
utterance-level metric counted it as a full substitution/insertion per speaker.

### Failure-mode mix: the inversion (RQ12 vs RQ35)

| Failure mode | RQ12 utterance-level | RQ35 char-level |
|---|--:|--:|
| separated hallucination — CR-missed | 67.8% (n=8) | 19.5% (n=1) |
| separated hallucination — CR-caught | 4.6% (n=1) | 0.0% (n=0) |
| mixed hallucination | 27.6% (n=2) | 0.0% (n=0) |
| wrong-route non-hallucination | **0.0% (n=0)** | **80.5% (n=35)** |
| total failure windows | 11 (router acc 85.7%) | 36 (router acc 53.2%) |
| total routing regret | 14.5 | 3.49 |

The char-level decomposition **inverts** the utterance-level one. RQ12's
"100% hallucination-driven" becomes "80.5% clean routing-judgment error" at
char-level. Two mechanisms combine:

1. **The hallucination threshold fires far less often.** Only **4 of 64** active
   windows have char-level separated cpWER > 1.0, versus **37 of 64** at
   utterance-level. Char-level cpWER is much lower in magnitude (a hallucinated
   track that inserts 77 extra characters against a 110-character reference
   scores 1.65 at char-level, not the 2.33 it scores at utterance-level where
   each speaker is one token). Fewer windows cross the threshold → fewer
   hallucination classifications.
2. **The oracle flips on more windows.** 36 char-level failure windows vs 11
   utterance-level; the failure-set overlap is just 6 (Jaccard 0.146). Most
   char-level failure windows are sub-threshold on both tracks, so the router's
   error is a small wrong-route pick, not a catastrophic hallucination pick.

The single char-level separated-hallucination failure is **w0** (char_sep
1.6455, CR 1.10 → CR-missed) — the same w0 that was RQ12's top regret window.
The diverse-multilingual-gibberish hallucination on w0 is costly enough to
cross the char-level > 1.0 threshold; most other RQ12 hallucination windows are
not.

### Why Mode S flips from failure to non-failure (the H35c mechanism)

At utterance-level, w22 and w30 had separated cpWER 2.0 because each speaker's
hallucinated string ≠ the reference string → counted as full per-speaker
substitutions/insertions. At char-level, the same windows score 0.49 and 0.80
because Mode S's text is a near-duplicate of the mixed decode, which itself
contains much of the reference content. The router picked separated on both;
at char-level separated is oracle-best (w22) or tied-best (w30), so neither is
a routing failure. This is a concrete instance of RQ30's "per-window oracle
flips on ~48% of windows" finding: the Mode S windows are in the flip set, and
they flip from failure to non-failure.

## Hypothesis Verdicts

### H35a — top-10 differ (ρ < 0.5): **SUPPORTED**

Spearman ρ = 0.108 (p = 0.351); top-10 overlap 1/10 (Jaccard 0.053). The
char-level and utterance-level rankings are essentially uncorrelated — this
reproduces RQ30's per-window ρ ≈ 0.108 on the separated metric and confirms the
worst-window sets are almost disjoint. The only shared top-10 window is w23.

### H35b — subs dominate ins at char-level: **SUPPORTED (with caveat)**

For the char-level failure windows' separated tracks, char-level substitutions
(2,082) ≫ insertions (161); utterance-level same windows have insertions (67) >
substitutions (64). The pre-registered claim holds. **Caveat:** char-level
deletions (3,190) exceed substitutions, so the full ordering is dels > subs >
ins. H35b is supported as stated (subs > ins) but should not be over-read as
"substitutions are the dominant char-level error type" — deletions are.

### H35c — Mode S (w22, w30) remain char-level worst: **NOT SUPPORTED**

w22 is char-level rank 77/77 (cpWER 0.4915, the best window); w30 is rank 62/77
(cpWER 0.8027). Neither is in the char-level top-10. Both flip from utterance-
level failure (cpWER 2.0, separated-hallucination) to char-level non-failure
(separated is oracle-best). Mode S's per-character cost is moderate because its
near-duplicate-of-mixed text shares many characters with the reference. The
utterance-level "2.0" was a whole-string-as-token artifact.

## Honest Limitations

1. **Single meeting, 77 windows.** Only M_R003S02C01 is available. The
   char-level failure set (36 windows) is larger than RQ12's 11, but it is still
   a single-meeting sample; the 80.5% wrong-route share should be read as
   indicative, not as a population estimate. No bootstrap CIs are reported on
   the mode shares (unlike RQ12) because the point of RQ35 is the *direction*
   of the shift (hallucination → wrong-route), which is robust at 4 vs 37
   hallucination windows.

2. **cpWER for mixed uses orcWER (single-channel), matching RQ30.** The task
   brief said "char-level cpWER for all four" metrics; we use `orcwer` for the
   mixed track (single mixed channel vs multi-speaker reference) because that
   is what the project's stored "mixed cpWER" actually is (`orcwer_mixed` in the
   source JSON) and what RQ30 used to establish the char-level baseline. Using
   `cpwer` for the mixed track instead (assigning the single mixed speaker to
   one reference speaker) gives a slightly different mixed value (w0: 0.982 vs
   orcwer 0.964) but does not change any hypothesis verdict — the separation
   tax direction and the ranking are preserved. The script's `compute_cpwer_with_decomp`
   helper is available for a cpwer-for-mixed robustness check.

3. **The 1.0 sentinel inflates the char-level top-10.** 6 of the char-level
   top-10 worst windows are separator-silence sentinels (cpWER = 1.0 by
   convention, not by measurement). We report both the all-windows top-10
   (matches RQ30's ranking convention) and the active-only top-10 (excludes
   sentinels). H35a and H35c verdicts are the same under both; H35c is also
   NOT SUPPORTED on the active-only ranking (w22 rank 64/64, w30 rank 49/64).

4. **CR is a lower-bound proxy (inherited from RQ12).** The CR > 2.4 threshold
   uses concatenated per-speaker text, not Whisper's per-segment text. This is
   conservative for the CR-caught/CR-missed split but does not affect the
   headline hallucination-vs-wrong-route inversion, which rests on the cpWER > 1.0
   threshold (a measured MeetEval quantity, not the CR proxy).

5. **Deletion dominance is partly a separator-silence artefact.** The char-level
   dels > subs > ins ordering is partly driven by windows where the separated
   track omits reference characters (including the 1.0-sentinel windows whose
   breakdown is zeroed but whose non-empty neighbours have high dels). A
   per-window dels decomposition is in the CSV for follow-up. The H35b verdict
   (subs > ins) is robust because it holds at the window level for the
   hallucinated tracks (e.g. w0: subs 103 > ins 77), not just in aggregate.

6. **Oracle-TextGrid separation, Whisper-tiny only (inherited).** The failure
   modes are specific to oracle separation (true silence gaps) and Whisper-tiny.
   A real separator or a stronger model may change the hallucination rate and
   thus the char-level mode mix.

7. **Reanalysis only — no new audio / no gate run.** Like RQ12, this is a
   re-decomposition of stored transcripts. It does not test whether a
   silence-aware gate or a corrected router would change the char-level picture;
   it only characterises the current router v2's char-level failure structure.

## What this changes for the project

1. **RQ12's "100% hallucination-driven" finding does not survive at char-level.**
   At the granularity the Chinese-ASR community uses, router v2's regret is
   80.5% *clean routing-judgment error*, not hallucination. The utterance-level
   metric overstated the hallucination share because whole-speaker tokens
   inflate cpWER above 1.0 for any hallucinated track. The qualitative
   direction (separated worse than mixed; oracle best) is preserved (RQ30), but
   the *failure-mode attribution* is granularity-dependent. Future router work
   should report both granularities and not claim "hallucination is the only
   problem" from utterance-level cpWER alone.

2. **Mode S is an utterance-level artefact at char-level.** The 2-window Mode S
   residual that RQ16/RQ19 could not close (cpWER 1.043 vs 1.017) is, at
   char-level, *not a failure at all* — separated is oracle-best on both Mode S
   windows. The "residual gap" RQ19 documented is largely a tokenisation-granularity
   gap. This does not invalidate RQ19's deployability negative (the detectors
   still cannot catch Mode S at 90% specificity), but it reframes the *cost* of
   Mode S: per-character, the router already handles Mode S correctly.

3. **The char-level routing problem is a routing-logic problem, not a
   hallucination problem.** With 36 char-level failure windows at 53.2% router
   accuracy, the lever at char-level is improving routing judgment on
   sub-threshold (both-tracks-clean) windows, not adding hallucination detectors.
   This is the opposite lever from RQ12's utterance-level conclusion. Both are
   true at their respective granularities; the project should be explicit about
   which granularity a given router improvement targets.

## Reproducibility

- Script: `results/frontier/char_level_failure_modes/char_level_failure_analysis.py`
- Per-window data: `results/frontier/char_level_failure_modes/char_level_failure_results.csv`
  (77 rows; char-level + utterance-level cpWER and sub/ins/del breakdowns for
  separated/mixed/router/oracle, failure-window flags, primary failure modes,
  Mode S flag, max CR).
- Summary + hypothesis verdicts: `results/frontier/char_level_failure_modes/char_level_failure_results.json`
- Tests: `tests/test_char_level_failure.py` (43 tests, pure helpers + MeetEval
  decomposition on synthetic data).
- Run: `/opt/homebrew/bin/python3 results/frontier/char_level_failure_modes/char_level_failure_analysis.py`
  (needs meeteval 0.4.3, scipy, numpy; ~10 s).
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).
