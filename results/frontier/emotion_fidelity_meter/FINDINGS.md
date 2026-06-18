# Reference-free emotion-fidelity meter: a coarse clean/contaminated gate, not a graded oracle replacement — Findings

**Label:** `experimental/frontier`. No Whisper; speaker embedder = resemblyzer GE2E (offline);
emotion = gain-invariant prosody (`src/prosody.py`); separation = cross-talk leakage. The "true emotion
distortion" used only to *validate* the meter is the oracle clean-source reference (the crutch this
meter aims to remove). No gold tables touched. Outputs in `results/frontier/emotion_fidelity_meter/`.
Reproduce: `python -m src.emotion_fidelity_meter --pairs 8` (8 pairs × overlap {0.1,0.3,0.6,0.9} ×
α {0,0.15,0.3} × 2 speakers = 192 tracks).

## Question

Findings #14/#18 measured emotion preservation and built objective-aware routing using the clean
source's prosody as the reference — an oracle unavailable at deploy time. Can we estimate emotion
fidelity with NO clean reference, from a track's own self-consistency (speaker-embedding stability +
prosodic coherence)?

## Result — partial: a coarse separation-quality gate, weak as a graded fidelity estimate

| validation correlation | value | reading |
|---|---:|---|
| meter vs leakage α (separation quality) | **−0.514** | the meter reliably falls as separation degrades |
| meter vs true emotion distortion (oracle) | −0.198 | only weakly tracks the per-track distortion |

Mean meter by leakage: **0.950** (α=0, oracle-clean) → **0.864** (α=0.15) → **0.866** (α=0.3), while
the true distortion keeps rising (0.000 → 0.099 → 0.160). So the meter:

- **reliably separates clean from contaminated** (0.95 vs ~0.86; r=−0.51 with α) — a usable binary
  "was this track cleanly separated?" gate;
- but **saturates** — it cannot tell α=0.15 from α=0.3 (0.864 ≈ 0.866) even though their true emotion
  distortion clearly differs — so it is a **weak graded** emotion-fidelity predictor (r=−0.20).

## Synthesis

A purely reference-free self-consistency meter (speaker-embedding stability dominant) is good enough to
**flag grossly contaminated tracks** but not to **replace the oracle reference** for fine emotion-
fidelity ranking. For the deployable emotion-aware router (#18), this means: the meter can serve as a
coarse confidence gate (abstain / warn when a separated track looks contaminated), but precise per-
track emotion fidelity still needs either a clean reference or a stronger signal. This is an honest
partial completion of the frontier's "reference-free separator-quality" item, and it bounds how far
self-consistency alone can go.

## Honest limitations

The meter saturates beyond mild leakage; the embedding-consistency term carries most of the signal
(prosodic coherence adds little here); n=192 with the usual high-variance prosody on short tracks (the
robust claims are the *coarse* clean/contaminated separation and the saturation, not the exact
correlations). resemblyzer is an optional frontier dep; the pure meter logic is unit-tested without it
(12 tests) via injected arrays. The validation target (true distortion) is itself the oracle reference
we will not have at deploy — used here only to measure the proxy. `experimental/frontier`. Artifacts:
`fidelity_curve.csv` (192 rows), `fidelity_summary.json`, `emotion_fidelity_meter.png`.
