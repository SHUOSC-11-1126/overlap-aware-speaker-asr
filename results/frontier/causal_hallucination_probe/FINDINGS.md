# Causal & Internal-State Hallucination Probe — Findings

**Label:** `experimental/frontier`. ASR = Whisper-`tiny` (only cached model, offline).
References `synthetic/silver` (Whisper-`small` on clean snippets); CER is post-hoc only
and **never** a routing input. Stable tables untouched. Issue #855. Mode C.

Module: `src/causal_hallucination_probe.py`. Proposal: `docs/frontier/causal_hallucination_probe.md`.
Literature grounding: `docs/frontier/causal_hallucination_probe_litreview.md`. Reproduce (exact run that
produced the committed artifacts): `python -m src.causal_hallucination_probe --discover-ratios 0.1
--analyze-ratios 0.1,0.3,0.5 --controls 24` (full case-control; ~12 min) or `--smoke` (~20 s).
Tests: `python -m unittest tests.test_causal_hallucination_probe`.

## The question this answers

`separation_tax` closed the *acoustic* loop on the separation tax: the low-overlap penalty
is a heavy hallucination tail of oracle-separated tracks whose long leading-silent region
drives Whisper into runaway repetition; a reference-free **compression-ratio (CR) guard**
ranks the catastrophic tracks at AUC ≈ 1.0 and a guard-gated router closes ~76% of the
offline oracle gap. That rests on two unexamined assumptions this probe attacks: (1) the CR
detector is an OUTPUT signal — computed over the *full* decoded segment, so by the time it
inflates past 2.4 Whisper has *already emitted* the repetition; (2) the mechanism is a black
box. A 3-second smoke test (tone + silence) reproduces the loop (token 7322 × 224) with
`compression_ratio = 37`, `no_speech_prob = 0.82`, yet `avg_logprob = -0.065` — the decoder
is *highly confident* while repeating. This probe looks inside Whisper, asks whether an
internal-state detector fires *causally earlier* than CR, and how much routing gain survives
a causal (prefix-only) decision.

## Design (reference-free; CER post-hoc only)

Two-phase **case-control**, reusing the `separation_tax` harness (`build_mixture` oracle
separation, `compute_cer`, `load_snippet_reference`):

- **Phase 1 — exhaustive discovery.** Decode the sep2 (leading-silence / pro) track for every
  con × pro pairing (11 × 15 = 165) at overlap 0.10 and flag catastrophic (CER > 1). Finds the
  natural case set without cherry-picking.
- **Phase 2 — analysis.** For every catastrophic case + a 24-condition matched clean control
  sample, decode all 3 arms (mixed, sep1, sep2) at overlaps {0.1, 0.3, 0.5} and reduce to
  per-condition separated-route signals: `avg_logprob`, token-id entropy, dominant-token
  fraction, `no_speech_prob`, CR causal latency (smallest character-prefix fraction where
  CR > 2.4), and the **token-id repetition lock-in latency** (smallest emitted-token fraction
  where any period-p loop of ≥ 3 reps completes — the novel trip-wire; p = 1 catches
  single-token loops, p = 6 catches phrase loops like "你是不是在那里").

## Result 0 — the natural catastrophic rate and a two-mode structure

Discovery finds **14 / 165 (8.5%)** of (con, pro) pairings catastrophic on sep2 at r = 0.10.
The catastrophe is **snippet-driven, not uniform**: 7 con snippets (con_001/002/005/006/007/
010/011) and 4 pro snippets (pro_002/003/006/011) account for all cases. Decomposing the 26
analysis-confirmed catastrophic conditions reveals **two distinct hallucination modes**:

| mode | driver | signature | share | lock-in fires? |
|---|---|---|---:|---|
| **R — repetition** | con_001/002/010 (etc.) | single-token or phrase loop; dom ≈ 0.99, entropy ≈ 0.09, avg_logprob ≈ −0.08 | 11 / 26 | yes, at ~2% of stream |
| **N — non-repetition** | pro_006 (across many con) | substitution/deletion-heavy; dom ≈ 0.14, entropy ≈ 2.6, avg_logprob ≈ −0.25 | 15 / 26 | no |

This split is the cleanest structural finding: the separation-tax catastrophe is not one
phenomenon. Mode R is the textbook repetition attractor; Mode N is a diffuse hallucination
that produces a long, wrong, but non-repeating transcript.

## Result 1 — H-M (mechanism): a confident loop, NOT a confidence collapse — SUPPORTED, refined

Catastrophic separated routes are decoded with **higher** decoder confidence and **lower**
token-id entropy than clean routes (66 conditions: 26 catastrophic vs 40 clean):

| group | mean avg_logprob | mean token entropy | mean dominant-token frac | mean no_speech_prob |
|---|---:|---:|---:|---:|
| catastrophic (CER_sep > 1) | **−0.335** | **1.487** | **0.500** | 0.179 |
| clean | −0.739 | 2.330 | 0.140 | 0.256 |

The decoder is **more confident** (avg_logprob closer to 0) and **more locked** (lower
entropy, higher dominant-token fraction) while producing garbage — confidence is not
calibrated to correctness. **Honest refinement of the smoke-test framing:** `no_speech_prob`
is *not* the catastrophic signal — it is slightly **anti-correlated** here (catastrophic 0.179
< clean 0.256; flagging-AUC 0.33). The 3-second tone-in-silence smoke test read nsp = 0.82
because that input was near-pure silence; on real pro snippets with speech energy, a decoder
in a confident repetition loop assigns *low* probability to the no-speech token (it is busy
"speaking"). So the robust confident-loop signature is **high decoder confidence + low token
entropy + high dominant-token fraction** — the encoder-silence decoupling was smoke-test-
specific. This extends the 2025-26 confident-attractor line (Aparin 2026; Waldendorf ACL
2026; Calm-Whisper; Viakhirev) to the separation-tax oracle-silence regime and reconciles
the nsp discrepancy noted in the litreview.

## Result 2 — H-D (latency): token-id lock-in fires ~10× earlier than CR — SUPPORTED for Mode R

| detector | mean fire fraction of stream | n fired (of 26 cat) |
|---|---:|---:|
| CR guard (output, full-segment) | **0.201** | 22 |
| token-id lock-in (internal, prefix) | **0.022** | 11 |

Where it fires, the lock-in trip-wire catches the catastrophe at **~2% of the emitted
stream** vs CR at **~20%** — a ~10× causal-latency advantage. **Honest scope:** lock-in fires
on the 11 Mode R cases; the 15 Mode N cases never trigger it (their transcript is not a
clean repetition). CR's AUC (0.996) therefore still dominates as a *broad* detector; the
lock-in's contribution is **causal earliness on the repetition tail**, not ranking power.

## Result 3 — H-C (deployability): output-metric gating loses power causally; internal-state wins at tight caps

Forcing the abort-to-mixed decision to a causal prefix cap quantifies the deployability
decay (regret vs the per-condition oracle; `deployability.json`):

| policy | regret @ cap=0.05 | @ cap=0.15 | @ cap=0.30 | @ cap=1.0 (≈offline) |
|---|---:|---:|---:|---:|
| fixed_sep (baseline) | 2.696 | 2.696 | 2.696 | 2.696 |
| causal_cr (prefix CR) | 2.696 | 1.291 | **0.363** | **0.154** |
| **causal_internal (prefix lock-in)** | **1.291** | **1.291** | 1.291 | 1.291 |

**The honest, scoped reading:** at a *tight* causal cap (0.05–0.15, the streaming-realistic
regime where a system must decide before much is emitted), **causal_internal beats
causal_cr** (1.291 vs 2.696 at cap 0.05) — the lock-in catches the repetition tail that CR
structurally cannot see until ~20% of the stream is gone. At a *loose* cap (≥ 0.30), **CR
overtakes** (0.363 vs 1.291) because CR's two-mode coverage (22 vs 11) outweighs lock-in's
latency edge once the cap lets CR fire. **Neither detector alone dominates** — the
deployable design is a union (fire on whichever trips first). This scopes the bold H-C
exactly as the litreview recommended: *output-metric gating* loses power causally at tight
caps; *internal-state gating* recovers it there — consistent with Whisper-CD (2026) showing
decode-time *intervention* survives causally. Our router is complementary gating/abstention.

**Caveat on absolute regret:** this is a case-control set *enriched* for sep-catastrophic
conditions (by design), so fixed_mixed (0.071) and offline_guard (0.110) look near-optimal
here — every case is a sep failure, so always-mixed wins absolutely. The population-
prevalence regret would need a representative sample. The **relative detector comparison**
(causal_internal vs causal_cr at matched caps) is valid and is the contribution.

## What this changes for the project

The separation-tax hallucination is a **confident, two-mode, causally-early-detectable**
phenomenon. The deployable sharpening: a streaming overlap-aware ASR system that gates on
the **token-id lock-in trip-wire** catches the Mode R repetition tail at ~2% of the stream —
~10× before the output compression-ratio (which needs ~20%) — while CR remains necessary
for the Mode N non-repetition minority. The offline `separation_tax` guard-gated router is
the offline ceiling; the **lock-in trip-wire is its streaming-safe realization for the
repetition tail**, and the two-mode split explains *why* no single reference-free detector
has dominated (CR is broad-but-late; lock-in is early-but-narrow).

## Honest limitations

Whisper-`tiny` (only cached model); oracle separation (upper bound — real-separator
artifacts may differ); silver references put a ~0.4 effective CER floor (only CER ≫ 1 tail
interpreted); the analysis is a 26-positive / 40-negative case-control set enriched for
catastrophes, so absolute deployability regrets are inflated and only the *relative*
detector comparison is general; one Chinese-debate snippet corpus (11 con / 15 pro); the
lock-in trip-wire is validated on Whisper-`tiny` only and, per Waldendorf (2026), internal-
state detectors are model/task-specific — portability to other ASR / S2TT is a hypothesis to
test, not an assumption. Mode N (15/26) shows lock-in is not a universal detector.
`experimental/frontier`, not a gold result.
