# Evidence Manifest

Main source: `origin/main` `da5464e023a8ed5fd4b2b9358aa502120f24768b`.
AudioDepth source: `origin/frontier/audio-depth-router` `e4aba457b2950ecc79e235ca46e15d44b07615df`.

Replay Demo — all outputs are precomputed from committed research artifacts.

- `src_readme`: `README.md` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `stable/gold + experimental/frontier summary`. Project framing and quick results.
- `src_report`: `REPORT.md` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `team research report`. Integrated narrative and limitations.
- `src_contributions`: `CONTRIBUTIONS.md` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `authoritative contribution record`. Member names, roles, and evidence paths.
- `src_status`: `docs/implementation-status.md` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `claim boundary matrix`. Stable/mainline/frontier status labels.
- `src_results_index`: `docs/results-index.md` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `evidence index`. Result entry points.
- `src_cer`: `results/tables/cer_results.csv` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `stable/gold`. Gold CER by route.
- `src_router_perf`: `results/tables/routing_performance_v2.csv` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `stable/gold`. Router v2 average CER.
- `src_router_dec`: `results/tables/routing_decisions_v2.csv` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `stable/gold`. Reference-free router choices.
- `src_speaker`: `results/tables/speaker_cer_results.csv` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `stable/gold`. Speaker-aware CER.
- `src_cpcer`: `results/tables/cpcer_lite_results.csv` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `stable/gold`. cpCER-lite speaker assignment check.
- `src_cascade`: `results/tables/cascade_tiers_performance.csv` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `mainline experimental`. Mode B compute-aware cascade tiers.
- `src_sep_tax`: `results/frontier/separation_tax/FINDINGS.md` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `experimental/frontier`. Separation tax and heavy-tail hallucination mechanism.
- `src_model_scale`: `results/frontier/model_scale/FINDINGS.md` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `experimental/frontier`. Whisper-base scale finding.
- `src_noise_router`: `results/frontier/noise_robust_router/FINDINGS.md` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `experimental/frontier`. Noise-robust router.
- `src_emotion`: `results/frontier/objective_aware_routing/FINDINGS.md` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `experimental/frontier`. Objective-aware text/emotion routing.
- `src_semantic_emotion`: `results/frontier/semantic_emotion_tax/FINDINGS.md` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `experimental/frontier`. LLM semantic emotion coverage.
- `src_llm_negative`: `results/frontier/llm_base_rescore/FINDINGS.md` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `experimental/frontier negative`. LLM correction negative result.
- `src_audiodepth_branch`: `docs/frontier/audiodepth_one_page.md; docs/frontier/generative_audiodepth.md; resources/audio_depth_maps/deployable/*.png` — branch `origin/frontier/audio-depth-router`, commit `e4aba457b2950ecc79e235ca46e15d44b07615df`, evidence `branch-only exploratory`. AudioDepth is not merged into stable mainline.
- `src_audio_LightOverlap`: `resources/mixed_audio/LightOverlap.wav` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `demo audio`. Local gold-case mixed audio.
- `src_reference_LightOverlap`: `references/reference_transcripts.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `verified_reference`. Human-verified reference for LightOverlap.
- `src_transcript_LightOverlap_mixed`: `results/transcripts_raw/LightOverlap_mixed_whisper.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `committed transcript artifact`. mixed transcript for LightOverlap.
- `src_transcript_LightOverlap_separated`: `results/transcripts_speaker/LightOverlap_separated_speaker_transcript.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `referenced artifact missing from main checkout`. separated transcript for LightOverlap.
- `src_transcript_LightOverlap_cleaned`: `results/transcripts_postprocessed/LightOverlap_separated_speaker_transcript_cleaned.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `committed transcript artifact`. cleaned transcript for LightOverlap.
- `src_audio_NoOverlap`: `resources/mixed_audio/NoOverlap.wav` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `demo audio`. Local gold-case mixed audio.
- `src_reference_NoOverlap`: `references/reference_transcripts.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `verified_reference`. Human-verified reference for NoOverlap.
- `src_transcript_NoOverlap_mixed`: `results/transcripts_raw/NoOverlap_mixed_whisper.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `committed transcript artifact`. mixed transcript for NoOverlap.
- `src_transcript_NoOverlap_separated`: `results/transcripts_speaker/NoOverlap_separated_speaker_transcript.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `committed transcript artifact`. separated transcript for NoOverlap.
- `src_transcript_NoOverlap_cleaned`: `results/transcripts_postprocessed/NoOverlap_separated_speaker_transcript_cleaned.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `committed transcript artifact`. cleaned transcript for NoOverlap.
- `src_audio_HeavyOverlap`: `resources/mixed_audio/HeavyOverlap.wav` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `demo audio`. Local gold-case mixed audio.
- `src_reference_HeavyOverlap`: `references/reference_transcripts.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `verified_reference`. Human-verified reference for HeavyOverlap.
- `src_transcript_HeavyOverlap_mixed`: `results/transcripts_raw/HeavyOverlap_mixed_whisper.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `committed transcript artifact`. mixed transcript for HeavyOverlap.
- `src_transcript_HeavyOverlap_separated`: `results/transcripts_speaker/HeavyOverlap_separated_speaker_transcript.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `referenced artifact missing from main checkout`. separated transcript for HeavyOverlap.
- `src_transcript_HeavyOverlap_cleaned`: `results/transcripts_postprocessed/HeavyOverlap_separated_speaker_transcript_cleaned.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `committed transcript artifact`. cleaned transcript for HeavyOverlap.
- `src_audio_OppositeOverlap`: `resources/mixed_audio/OppositeOverlap.wav` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `demo audio`. Local gold-case mixed audio.
- `src_reference_OppositeOverlap`: `references/reference_transcripts.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `verified_reference`. Human-verified reference for OppositeOverlap.
- `src_transcript_OppositeOverlap_mixed`: `results/transcripts_raw/OppositeOverlap_mixed_whisper.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `committed transcript artifact`. mixed transcript for OppositeOverlap.
- `src_transcript_OppositeOverlap_separated`: `results/transcripts_speaker/OppositeOverlap_separated_speaker_transcript.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `referenced artifact missing from main checkout`. separated transcript for OppositeOverlap.
- `src_transcript_OppositeOverlap_cleaned`: `results/transcripts_postprocessed/OppositeOverlap_separated_speaker_transcript_cleaned.json` — branch `origin/main`, commit `da5464e023a8ed5fd4b2b9358aa502120f24768b`, evidence `committed transcript artifact`. cleaned transcript for OppositeOverlap.

## AudioDepth Boundary

AudioDepth is marked Frontier Branch Only, Exploratory Research, Not merged into stable mainline, and Not production-ready. It is a safety confirmer and interpretable auxiliary representation, not the main production router.
