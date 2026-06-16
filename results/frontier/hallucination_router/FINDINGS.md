# Route by Hallucination, not Overlap — Findings

**Label:** `experimental/frontier` (ASR = Whisper-`tiny`, offline; references synthetic/silver).
Held-out validation on the 100-case synthetic split (50 dev / 50 test), reconstructed
deterministically from `results/tables/synthetic_split_manifest.csv` (the v2 split ships
no audio; mixtures + oracle tracks are regenerated via `build_mixture`). CER is post-hoc
only and is never a routing input. Stable tables untouched. Reproduce:
`python -m src.hallucination_router`.

## Thesis tested

The Separation Tax study showed the "when to separate" decision is really *which input
made Whisper hallucinate* (reference-free compression ratio flags catastrophes at AUC 1.0).
The bold thesis: **route by hallucination, not by overlap** — transcribe both candidates
(mixed and silence-trimmed separated), pick the one with lower reference-free degeneracy,
without ever estimating the overlap ratio.

## Result: the bold thesis is FALSIFIED — but the trim recipe generalizes strongly

Mean CER and regret vs the oracle (min-CER selector):

| policy | dev CER | dev regret | test CER | test regret | reference-free? |
|---|---:|---:|---:|---:|---|
| oracle | 0.410 | 0 | 0.382 | 0 | — |
| fixed_mixed | 1.013 | +0.603 | 0.522 | +0.140 | yes |
| fixed_sep (untrimmed) | 0.465 | +0.055 | 0.718 | +0.336 | yes |
| **fixed_sep_trim** | 0.475 | +0.065 | **0.423** | **+0.041** | **yes** |
| halluc_2way (the thesis) | 0.509 | +0.099 | 0.465 | +0.083 | yes |
| halluc_3way | 0.520 | +0.110 | 0.478 | +0.096 | yes |
| overlap_router (given TRUE overlap) | 0.480 | +0.070 | 0.422 | +0.040 | no |

Two honest conclusions:

1. **Routing by hallucination does not beat routing by overlap, nor even plain
   always-trim.** On held-out test, `halluc_2way` (regret +0.083) is worse than both the
   overlap-router given the true overlap (+0.040) and the trivial `fixed_sep_trim`
   (+0.041). Once the separated route is silence-trimmed it rarely fails catastrophically,
   so the degeneracy-based switch to mixed mostly adds noise. **H2 falsified.**

2. **The Separation Tax silence-trim recipe generalizes — this is the real win.**
   `fixed_sep_trim` cuts regret from `fixed_sep`'s 0.196 → 0.053 over the full split
   (and 0.336 → 0.041 on held-out test) — a **~73% reference-free regret reduction** — and
   on test it *matches* the overlap-oracle router (0.041 vs 0.040) **without using any
   overlap knowledge**. The benefit is largest exactly on the split with the heaviest
   hallucination tail (test `fixed_sep` = 0.718), consistent with the tail mechanism.

A sharper takeaway than the original thesis: **once you silence-trim the separated route,
knowing the overlap barely matters** — the overlap-router's "use mixed below r≈0.17" branch
buys essentially nothing over always-trim on the held-out test (0.422 vs 0.423). The
deployable recommendation is therefore *separate + silence-trim by default*; explicit
mixed-vs-separated routing (by overlap or by degeneracy) adds little once trimming is in
place.

## Honest limitations

Whisper-`tiny` only; silver references; oracle separation (real separators add artifacts —
see the Separation Tax RQ6, where trim must be guard-gated rather than blanket). 100 cases
from one Chinese-debate corpus; concatenation CER, not permutation cpWER. The
`overlap_router` is *given* the true generation overlap (an upper bound on overlap-based
routing); a deployed overlap router would first have to estimate overlap. Frontier
evidence, not a gold result.

## What this changes

Fold a default silence-trim into the separated branch of `adaptive_router_v2` (it is
reference-free and generalizes), and drop the assumption that accurate overlap estimation
is the lever — post-trim it is nearly irrelevant. Artifacts: `routing_curve.csv` (100
rows), `routing_summary.json`.
