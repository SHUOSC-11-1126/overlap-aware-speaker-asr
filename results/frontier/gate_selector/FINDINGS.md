# Reference-free gate SELECTION: testing finding #12's asserted key — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny`; references synthetic/silver; speaker embedder
Resemblyzer GE2E (256-d, pretrained, offline). CER is post-hoc only, never an input to any pick. No
gold tables touched; outputs in `results/frontier/gate_selector/` (top level = full 288-condition
experiment; `overlap_low/` and `overlap_high/` are the regime splits). Grid: 8 pairs × 3 noise types
(white/pink/babble) × 3 SNR (10/5/0 dB) × 2 overlap regimes (low {0.1,0.3}, high {0.6,0.8}) =
**288 conditions**, 16 separated-track samples each. Reproduce:
`pip install -r requirements-frontier.txt` then
`python -m src.gate_selector --pairs 8 --overlaps 0.1,0.3` and `--overlaps 0.6,0.8`. Re-analyze any
policy offline with `--from-csv` (no Whisper).

## Question (closing the arc opened by #11/#12)

Finding #12 asserted — but never tested — that "the residual region's own spectral flatness" is the
right reference-free key to choose between the flatness gate (#11, broadband-noise cure) and the
speaker gate (#12, moderate-babble cure): high flatness → broadband → flatness gate; low → speech-like
→ speaker gate. The #12 grid contained a sharp falsifiable risk: at 0 dB babble the residual is
speech-like (the naive rule says "speaker gate") yet the speaker gate was the *worst* arm there. So we
built the selector — a per-utterance pick in {none, flatness, speaker} keyed on residual flatness plus
a speaker-similarity-contrast catastrophe guard — and asked whether it beats every fixed strategy and
recovers the oracle gate-selection gain.

## The signal works; the premise does not

**The selection signal is excellent.** Residual spectral flatness separates the three noise types
essentially perfectly (pairwise rank-AUC 1.0): mean residual flatness white **0.48–0.54**, pink
**0.16**, babble **0.09**. Even pink (spectrally 1/f-tilted, not flat) is rank-separable from babble.
H3's *signal* half holds decisively.

**But the asserted action is wrong**, because the arm residual flatness selects *for* — the flatness
gate — is itself the harmful arm in this grid. Applied unconditionally the flatness gate over-crops
and inflates CER (combined mean **1.445**, the worst of all strategies; catastrophic **3.55** at white
0 dB high-overlap vs speaker 1.90). It only helped #11 under *selective* CR-gating on ~7% of tracks.
So perfectly identifying broadband noise routes the selector straight into harm.

## Pooled CER by overlap regime (16 samples/cell; lower better)

| strategy | low overlap (0.1/0.3) | high overlap (0.6/0.8) | combined (288) | tail P(CER>1) comb. |
|---|---:|---:|---:|---:|
| mixed (no separation) | **0.932** | 1.628 | 1.280 | 0.08 |
| raw separation | 1.239 | 1.344 | 1.291 | 0.15 |
| always flatness gate (#11) | 1.514 | 1.377 | 1.445 | 0.14 |
| **always speaker gate (#12)** | 1.345 | **1.125** | **1.235** | 0.09 |
| **selector (reference-free, this work)** | 1.416 | 1.238 | 1.327 | 0.10 |
| oracle gate-selection (upper bound) | 0.999 | 0.845 | 0.922 | 0.04 |

What is true:

1. **H1 is FALSIFIED.** The selector never beats every fixed arm. In *both* regimes and combined,
   **always-speaker dominates the selector** (1.235 vs 1.327 combined). Its only differentiated move —
   routing high-flatness (white) tracks to the flatness gate — is exactly the harmful one, so a
   selector that *sometimes* picks flatness is strictly worse than one that *never* does. There is
   nothing to select: one arm (speaker) dominates the only competitor worth switching to.

2. **The speaker gate is a BROAD cure, not the narrow one #12 reported.** Pooled across all noise
   types, SNRs, and both overlaps it is the best fixed gate, and at high overlap it cuts raw-separation
   CER 1.344 → 1.125 while halving the catastrophic tail vs raw sep (0.14 → 0.09). #12's "moderate
   babble only" framing understated it; the per-cell reversals between #12 and this run (e.g. babble
   5–10 dB) are the n=16 high-variance tails #12 itself flagged — the pooled direction is the robust
   claim.

3. **The flatness gate is harmful applied unconditionally** (worst strategy combined). This bounds #11:
   its broadband cure is real only inside the selective CR-guard, not as a standing gate.

4. **Overlap, not noise type, is the real decision variable.** Mixed wins at low overlap (0.932 vs
   raw-sep 1.239); separation+speaker-gate wins at high overlap (1.125 vs mixed 1.628). This is the
   project's overlap-router thesis (core finding #1, router_v2) re-confirmed under additive noise, with
   the speaker gate as the post-separation cure — *not* a new gate-selection layer.

## The ceiling: no reference-free type-keyed selector can win

Because residual flatness identifies noise type at AUC 1.0, the *ceiling* of any perfect
flatness-keyed selector is the best fixed noise-type → arm map. That ceiling (CER **1.209** combined)
barely improves on always-speaker (1.235) and its chosen map is `{white: none, pink: speaker, babble:
speaker}` — i.e. "use the speaker gate, and don't gate white." It never chooses the flatness gate. So
even a perfect type classifier converges to "always-speaker (minus white)"; the selection problem the
project posed at the gate level has no win available. The `flat_hi` sensitivity sweep confirms this:
selector CER is flat (1.33–1.59) across thresholds 0.05–0.6 with no operating point reaching
always-speaker.

## Synthesis: the deployable answer is one gate + an overlap router, not gate selection

The reference-free-router thesis does **not** extend to gate selection here, for a clean reason: it
requires two arms each best in an identifiable region, but one arm (speaker gate) dominates and the
other (flatness gate) is dominated. The actionable system is therefore *not* a gate selector — it is
(a) make the speaker gate the **default** post-separation cure (broadly best, low tail, fully offline),
and (b) keep the decision where it actually lives: **separate-vs-mixed by overlap**, which router_v2
already targets via reference-free overlap/repetition signals. The concrete next build is a
reference-free overlap estimator feeding that separate-vs-mixed switch under noise — gate *choice* is
settled (speaker).

## Honest limitations

Whisper-`tiny`; silver references; synthetic oracle separation; synthetic white/pink/babble (real
babble differs). n=16/cell with heavy CER tails → per-cell point estimates are high-variance; the
robust claims are the *pooled directions* (always-speaker > selector > always-flatness in both regimes;
flatness gate harmful unconditionally; flatness AUC ≈ 1.0; ceiling ≈ always-speaker), not exact
per-cell means. The selector's pure logic is unit-tested without resemblyzer/whisper via an injected
embedder (`tests/test_gate_selector.py`, 21 tests); resemblyzer is an optional frontier dep. This is a
*falsification with a positive byproduct*: the asserted selection key is sound as a signal but useless
as a router because its target arm is dominated, and the byproduct is a stronger, broader claim for the
speaker gate. `experimental/frontier`, not a gold result. Artifacts: `selector_curve.csv` (288 rows),
`selector_summary.json`, `gate_selector.png`, and the per-regime splits in `overlap_low/` and
`overlap_high/`.
