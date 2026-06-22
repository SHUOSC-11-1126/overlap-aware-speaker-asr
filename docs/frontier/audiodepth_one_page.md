# AudioDepth One-page Summary

## Research Question

Can a mixed-audio acoustic depth representation tell us when speaker separation is likely to help ASR, before spending full text-routing compute?

## Vision Analogy

AudioDepth borrows the intuition of RGB-D and depth-style visual recognition: overlap is treated as time-frequency occlusion. The project tests whether logmel energy plus overlap/uncertainty depth-like channels can expose where speakers mask each other.

## What Was Tested

- early AudioDepth-CNN route classification on synthetic/silver split data;
- AudioDepth model-zoo and hybrid fusion with text-instability features;
- controlled route-sensitive v1 and balanced v2 benchmarks under real Whisper;
- deployable mixed-only AudioDepth v2 maps;
- Stage-1 acoustic gate, calibrated gate, and risk-guarded gate;
- Generative AudioDepth as promptable acoustic map/regret prediction.

## What Failed

- The first deployable CNN did not beat `router_v2` on the matched synthetic split.
- Real Whisper gap analysis showed proxy gains do not automatically transfer.
- Cleaned-win anchors still did not produce real Whisper cleaned oracle wins.
- Generative AudioDepth is not reliable enough as a standalone router.

## What Still Looks Useful

- Controlled route-sensitive benchmarks show route choice genuinely matters.
- Balanced v2 proves the learned boundary is not blindly selecting separated.
- AudioDepth embeddings contain modest independent pre-ASR signal.
- Risk-guarded Stage-1 gating can reduce text probing while constraining direct mixed bypass risk.
- Generative maps are useful as safety/interpretable auxiliary evidence.

## Why It Is Not Mainline Yet

Most AudioDepth evidence is controlled silver-plus or diagnostic. The strongest stable claim remains the small manually verified gold benchmark plus `router_v2`; AudioDepth should be framed as a frontier pre-ASR triage branch until micro-gold and external validation exist.

## Minimum Viable Next Experiment

Annotate the Stage 34 micro-gold pack, rerun unified evaluation with gold/silver metrics separated, and test whether a conservative AudioDepth/text router preserves `0` false-safe mixed decisions without relying on high review coverage.
