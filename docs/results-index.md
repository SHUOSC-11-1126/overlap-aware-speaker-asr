# Results Index

This file is the curated map for result summaries. It separates reviewer-facing
results from generated historical records.

## Recommended Reading Order

1. [Current results summary](../results/figures/curated/current_results_summary.md)
2. [Adaptive routing summary](../results/figures/curated/best_method_by_case.md)
3. [Risk-aware selector summary](../results/figures/curated/risk_aware_selection_summary.md)
4. [Compute-aware cascade summary](../results/figures/curated/compute_aware_cascade_summary.md)
5. [Mode B cascade tiers summary](../results/figures/curated/cascade_tiers_summary.md)
6. Historical records under `results/figures/archive/`, only when traceability is needed

## Core Summaries

| File | Purpose | Evidence Type | Priority |
|---|---|---|---|
| `results/figures/curated/current_results_summary.md` | Main result overview | gold + synthetic/silver labels | High |
| `results/figures/curated/best_method_by_case.md` | Adaptive routing by case | gold | High |
| `results/figures/curated/error_type_summary.md` | Error mode interpretation | gold | High |
| `results/figures/curated/speaker_cer_summary.md` | Speaker-aware CER | gold | High |
| `results/figures/curated/cpcer_lite_summary.md` | Permutation-aware speaker check | gold | High |

## Router and Cascade Summaries

| File | Purpose | Evidence Type | Priority |
|---|---|---|---|
| `results/figures/curated/risk_aware_selection_summary.md` | Risk-aware selector behavior | gold | High |
| `results/figures/curated/compute_aware_cascade_summary.md` | Cost-aware cascade | experimental/frontier | High |
| `results/figures/curated/cascade_tiers_summary.md` | Mode B tiered cascade | experimental/frontier | High |
| `results/figures/curated/cascade_tiers_comparison_summary.md` | Mode B strategy comparison | experimental/frontier | Medium |
| `results/figures/curated/cascade_pareto.md` | Pareto audit | experimental/frontier | Medium |
| `results/figures/curated/cascade_recommendations.md` | Cascade recommendation card | experimental/frontier | Medium |
| `results/figures/curated/cascade_decision_matrix.md` | Cascade decision matrix | experimental/frontier | Medium |

## Silver / Synthetic Summaries

| File | Purpose | Evidence Type | Priority |
|---|---|---|---|
| `results/figures/curated/synthetic_routing_summary.md` | Synthetic routing behavior | synthetic/silver | High |
| `results/figures/curated/synthetic_split_routing_summary.md` | Held-out split routing | synthetic/silver | High |
| `results/figures/curated/synthetic_split_cascade_summary.md` | Synthetic split cascade | synthetic/silver + experimental/frontier | Medium |

## Optional Frontier Summaries

| File | Purpose | Evidence Type | Priority |
|---|---|---|---|
| `results/figures/curated/meeteval_compatibility_note.md` | MeetEval compatibility note | optional/frontier | Medium |
| `results/figures/curated/meeteval_readiness.md` | MeetEval readiness | optional/frontier | Medium |
| `results/figures/curated/speaker_profile_audio_proxy_summary.md` | Speaker-profile proxy summary | frontier scaffold | Medium |

## Frontier Research Notes

| File | Purpose | Treat As |
|---|---|---|
| `docs/frontier/audio-depth-router.md` | AudioDepth router merge strategy and claim boundary | Frontier Branch Only / Exploratory Research; not a final result claim |
| `docs/frontier/agentic_research_entropy.md` | Meta-analysis of substance-vs-ceremony collapse in this workspace (`results/entropy_audit/`) | experimental/frontier (analysis-only); not an ASR result |
| `results/frontier/decoder_cure_noise/FINDINGS.md` | Decoder-domain cures (beam / native halluc-silence) under noise: negative result — the noise-robust cure is NOT in the decoder (`results/frontier/decoder_cure_noise/`) | experimental/frontier; Whisper-tiny + silver refs; not a gold result |
| `results/frontier/semantic_emotion_tax/FINDINGS.md` | The Semantic Emotion Tax (ASR×LLM + emotion, #831): a local LLM reads implicit emotion 7× more than the lexicon (0.70 vs 0.10 coverage), is orthogonal to acoustic-arousal and lexical-valence (a complementary 3rd emotion modality), and emotion *meaning* is only partially coupled to CER (pooled d_sem↔CER ρ=0.51) — separation recovers more emotional meaning as overlap rises | experimental/frontier; Whisper-tiny + deepseek-r1 (local ollama) + silver refs; not a gold result |
| `results/frontier/emotion_anchored_repair/FINDINGS.md` | Emotion-anchored ASR repair (ASR×LLM + emotion, #833): NEGATIVE — anchoring repair to the LLM-detected stance does NOT cure the over-correction tax (#822); it slightly worsens it (no-repair 0.924 < naive 1.082 < anchored 1.122). The small reasoning model rewrites/hallucinates regardless (literal placeholder, proverb substitution); deployable policy = do not LLM-repair here, CR-guard never fires | experimental/frontier; Whisper-tiny + deepseek-r1 (local ollama) + silver refs; not a gold result |
| `results/frontier/emotion_modality_fusion/FINDINGS.md` | Tri-modal emotion fusion (ASR×LLM + emotion, #835): #831's orthogonality is only PARTLY complementary — fusing LLM-semantic + acoustic + lexical helps predict the SEMANTIC emotion-damage target (CV R² 0.10→0.16) but HURTS the acoustic target; acoustic-arousal is the single most useful reference-free predictor of emotion damage. Nuanced mixed result | experimental/frontier; Whisper-tiny + deepseek-r1 (local ollama) + silver refs; not a gold result |
| `results/frontier/noise_robust_router/FINDINGS.md` | Reference-free noise-robust router (#814 capstone): routing mixed-vs-(separate+speaker-gate) by the gated output's decoder degeneracy (compression-ratio) BEATS both fixed strategies (router 0.778 vs always-mixed 1.214, always-gate 1.531) and recovers ~92% of the per-utterance oracle gap (0.738); Pearson(CR, gate−mixed CER)=0.82 — degeneracy strongly tracks the separation tax under noise. A clean POSITIVE result | experimental/frontier; Whisper-tiny + Resemblyzer + silver refs; not a gold result |

## Frontier Research: AudioDepth

AudioDepth is documented as a frontier exploratory research line in
[AudioDepth Router Exploratory Study](frontier/audio-depth-router.md). Its
controlled and frontier results should be read as exploratory evidence unless
explicitly linked to verified mainline benchmarks. The results index does not
restore raw frontier dumps, archived wave/writeback files, large `.npy` arrays,
or bulk visualization outputs to the primary reading path.

## Historical Archive

The generated wave / receipt / writeback / bridge-checklist archive that
previously lived under `results/figures/archive/` was removed in the ceremony
purge (see `docs/frontier/agentic_research_entropy.md`). It is recoverable from
git history if ever needed, but it carried no research value and is no longer
part of the repository.
