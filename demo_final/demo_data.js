window.DEMO_DATA = {
  "title": "Overlap-Aware Speaker ASR — Team Research Demo",
  "subtitle": "When Should We Separate? Boundary-aware, Compute-aware, Speaker-aware, and Frontier-assisted ASR",
  "replayNotice": "Replay Demo — all outputs are precomputed from committed research artifacts.",
  "mainCommit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
  "audioDepthCommit": "e4aba457b2950ecc79e235ca46e15d44b07615df",
  "sources": {
    "src_readme": {
      "path": "README.md",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "stable/gold + experimental/frontier summary",
      "note": "Project framing and quick results."
    },
    "src_report": {
      "path": "REPORT.md",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "team research report",
      "note": "Integrated narrative and limitations."
    },
    "src_contributions": {
      "path": "CONTRIBUTIONS.md",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "authoritative contribution record",
      "note": "Member names, roles, and evidence paths."
    },
    "src_status": {
      "path": "docs/implementation-status.md",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "claim boundary matrix",
      "note": "Stable/mainline/frontier status labels."
    },
    "src_results_index": {
      "path": "docs/results-index.md",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "evidence index",
      "note": "Result entry points."
    },
    "src_cer": {
      "path": "results/tables/cer_results.csv",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "stable/gold",
      "note": "Gold CER by route."
    },
    "src_router_perf": {
      "path": "results/tables/routing_performance_v2.csv",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "stable/gold",
      "note": "Router v2 average CER."
    },
    "src_router_dec": {
      "path": "results/tables/routing_decisions_v2.csv",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "stable/gold",
      "note": "Reference-free router choices."
    },
    "src_speaker": {
      "path": "results/tables/speaker_cer_results.csv",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "stable/gold",
      "note": "Speaker-aware CER."
    },
    "src_cpcer": {
      "path": "results/tables/cpcer_lite_results.csv",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "stable/gold",
      "note": "cpCER-lite speaker assignment check."
    },
    "src_cascade": {
      "path": "results/tables/cascade_tiers_performance.csv",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "mainline experimental",
      "note": "Mode B compute-aware cascade tiers."
    },
    "src_sep_tax": {
      "path": "results/frontier/separation_tax/FINDINGS.md",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "experimental/frontier",
      "note": "Separation tax and heavy-tail hallucination mechanism."
    },
    "src_model_scale": {
      "path": "results/frontier/model_scale/FINDINGS.md",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "experimental/frontier",
      "note": "Whisper-base scale finding."
    },
    "src_noise_router": {
      "path": "results/frontier/noise_robust_router/FINDINGS.md",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "experimental/frontier",
      "note": "Noise-robust router."
    },
    "src_emotion": {
      "path": "results/frontier/objective_aware_routing/FINDINGS.md",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "experimental/frontier",
      "note": "Objective-aware text/emotion routing."
    },
    "src_semantic_emotion": {
      "path": "results/frontier/semantic_emotion_tax/FINDINGS.md",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "experimental/frontier",
      "note": "LLM semantic emotion coverage."
    },
    "src_llm_negative": {
      "path": "results/frontier/llm_base_rescore/FINDINGS.md",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "experimental/frontier negative",
      "note": "LLM correction negative result."
    },
    "src_audiodepth_branch": {
      "path": "docs/frontier/audiodepth_one_page.md; docs/frontier/generative_audiodepth.md; resources/audio_depth_maps/deployable/*.png",
      "branch": "origin/frontier/audio-depth-router",
      "commit": "e4aba457b2950ecc79e235ca46e15d44b07615df",
      "evidenceLevel": "branch-only exploratory",
      "note": "AudioDepth is not merged into stable mainline."
    },
    "src_audio_LightOverlap": {
      "path": "resources/mixed_audio/LightOverlap.wav",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "demo audio",
      "note": "Local gold-case mixed audio."
    },
    "src_reference_LightOverlap": {
      "path": "references/reference_transcripts.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "verified_reference",
      "note": "Human-verified reference for LightOverlap."
    },
    "src_transcript_LightOverlap_mixed": {
      "path": "results/transcripts_raw/LightOverlap_mixed_whisper.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "committed transcript artifact",
      "note": "mixed transcript for LightOverlap."
    },
    "src_transcript_LightOverlap_separated": {
      "path": "results/transcripts_speaker/LightOverlap_separated_speaker_transcript.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "referenced artifact missing from main checkout",
      "note": "separated transcript for LightOverlap."
    },
    "src_transcript_LightOverlap_cleaned": {
      "path": "results/transcripts_postprocessed/LightOverlap_separated_speaker_transcript_cleaned.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "committed transcript artifact",
      "note": "cleaned transcript for LightOverlap."
    },
    "src_audio_NoOverlap": {
      "path": "resources/mixed_audio/NoOverlap.wav",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "demo audio",
      "note": "Local gold-case mixed audio."
    },
    "src_reference_NoOverlap": {
      "path": "references/reference_transcripts.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "verified_reference",
      "note": "Human-verified reference for NoOverlap."
    },
    "src_transcript_NoOverlap_mixed": {
      "path": "results/transcripts_raw/NoOverlap_mixed_whisper.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "committed transcript artifact",
      "note": "mixed transcript for NoOverlap."
    },
    "src_transcript_NoOverlap_separated": {
      "path": "results/transcripts_speaker/NoOverlap_separated_speaker_transcript.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "committed transcript artifact",
      "note": "separated transcript for NoOverlap."
    },
    "src_transcript_NoOverlap_cleaned": {
      "path": "results/transcripts_postprocessed/NoOverlap_separated_speaker_transcript_cleaned.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "committed transcript artifact",
      "note": "cleaned transcript for NoOverlap."
    },
    "src_audio_HeavyOverlap": {
      "path": "resources/mixed_audio/HeavyOverlap.wav",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "demo audio",
      "note": "Local gold-case mixed audio."
    },
    "src_reference_HeavyOverlap": {
      "path": "references/reference_transcripts.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "verified_reference",
      "note": "Human-verified reference for HeavyOverlap."
    },
    "src_transcript_HeavyOverlap_mixed": {
      "path": "results/transcripts_raw/HeavyOverlap_mixed_whisper.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "committed transcript artifact",
      "note": "mixed transcript for HeavyOverlap."
    },
    "src_transcript_HeavyOverlap_separated": {
      "path": "results/transcripts_speaker/HeavyOverlap_separated_speaker_transcript.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "referenced artifact missing from main checkout",
      "note": "separated transcript for HeavyOverlap."
    },
    "src_transcript_HeavyOverlap_cleaned": {
      "path": "results/transcripts_postprocessed/HeavyOverlap_separated_speaker_transcript_cleaned.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "committed transcript artifact",
      "note": "cleaned transcript for HeavyOverlap."
    },
    "src_audio_OppositeOverlap": {
      "path": "resources/mixed_audio/OppositeOverlap.wav",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "demo audio",
      "note": "Local gold-case mixed audio."
    },
    "src_reference_OppositeOverlap": {
      "path": "references/reference_transcripts.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "verified_reference",
      "note": "Human-verified reference for OppositeOverlap."
    },
    "src_transcript_OppositeOverlap_mixed": {
      "path": "results/transcripts_raw/OppositeOverlap_mixed_whisper.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "committed transcript artifact",
      "note": "mixed transcript for OppositeOverlap."
    },
    "src_transcript_OppositeOverlap_separated": {
      "path": "results/transcripts_speaker/OppositeOverlap_separated_speaker_transcript.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "referenced artifact missing from main checkout",
      "note": "separated transcript for OppositeOverlap."
    },
    "src_transcript_OppositeOverlap_cleaned": {
      "path": "results/transcripts_postprocessed/OppositeOverlap_separated_speaker_transcript_cleaned.json",
      "branch": "origin/main",
      "commit": "da5464e023a8ed5fd4b2b9358aa502120f24768b",
      "evidenceLevel": "committed transcript artifact",
      "note": "cleaned transcript for OppositeOverlap."
    }
  },
  "assets": {
    "figures": {
      "system": "assets/figures/fig1_system_route_map.png",
      "gold_cer": "assets/figures/fig2_gold_cer_strategy_comparison.png",
      "phase": "assets/figures/fig3_separation_boundary_phase_plane.png",
      "cascade": "assets/figures/fig4_compute_cascade_3d_surface.png",
      "tax_waveform": "assets/figures/fig5_separation_tax_waveform.png",
      "tax_spectrogram": "assets/figures/fig6_separation_tax_spectrogram.png",
      "attractor": "assets/figures/fig7_confident_attractor_scatter.png",
      "model_scale": "assets/figures/model_scale_analysis.png",
      "noise_router": "assets/figures/noise_robust_router.png",
      "emotion_divergence": "assets/figures/emotion_asr_divergence.png",
      "frontier_capstone": "assets/figures/asr_llm_frontier_capstone.png"
    },
    "audiodepth": {
      "heavyMap": "assets/audiodepth/audiodepth_heavy_map.png",
      "lightMap": "assets/audiodepth/audiodepth_light_map.png",
      "oppositeMap": "assets/audiodepth/audiodepth_opposite_map.png"
    }
  },
  "overviewCards": [
    {
      "label": "Router v2 gold average CER",
      "value": "0.120042",
      "evidence": "stable/gold",
      "sourceId": "src_router_perf",
      "note": "Matches oracle on five-case gold benchmark without CER input."
    },
    {
      "label": "Separation-tax crossover",
      "value": "r* = 0.173 mean",
      "evidence": "stable/gold summary; frontier mechanism",
      "sourceId": "src_sep_tax",
      "note": "Low-overlap harm is heavy-tailed hallucination, not uniform degradation."
    },
    {
      "label": "Compute/model-scale boundary",
      "value": "base: 1.93x compute",
      "evidence": "experimental/frontier",
      "sourceId": "src_model_scale",
      "note": "Whisper-base removes the tiny-model separation tax in the evaluated setting."
    }
  ],
  "cases": {
    "mixedWin": {
      "caseId": "LightOverlap",
      "label": "Case A — Mixed-win",
      "why": "Light overlap: router v2 keeps mixed audio because separation inflates insertions/repetitions.",
      "audio": "assets/audio/LightOverlap.wav",
      "audioSource": "resources/mixed_audio/LightOverlap.wav",
      "audioSourceId": "src_audio_LightOverlap",
      "reference": {
        "text": "[SPEAKER_1] 你方是要，那它是怎么缓解我们的空虚的？ [SPEAKER_2] 它让你在那个时间段里拥有了自己。 [SPEAKER_1] 没问题，没问题，先不着急。 [SPEAKER_2] 哪怕这个自己是一个刷抖音的自己。 [SPEAKER_2] 我方这里再稍微解释一下。 [SPEAKER_1] 因为有一个前提性的问题没有讨论。 [SPEAKER_1] 现在讲的熬夜，所谓的熬夜就是晚睡晚起，是吧？ [SPEAKER_2] 其实布洛芬也是一种毒药。 [SPEAKER_1] 好，我先聊晚睡晚起。 [SPEAKER_2] 我方觉得晚睡晚起也是熬夜。 [SPEAKER_2] 晚睡早起也是熬夜了。 [SPEAKER_1] 既然你是晚睡晚起。 [SPEAKER_1] 你上班的时间必定也晚。 [SPEAKER_2] 因为你可以早睡早起。 [SPEAKER_1] 你下班的时间必定也晚。 [SPEAKER_2] 因为你可以为了身体健康。 [SPEAKER_1] 那你个人的生活空间必定也就这么点。 [SPEAKER_2] 早睡晚起。 [SPEAKER_1] 你是怎么多出额外的时间来过自己的生活的？ [SPEAKER_2] 不太一致。 [SPEAKER_2] 我可以给你解释。 [SPEAKER_1] 我的意思是，两点睡十点起。 [SPEAKER_2] 你没有多两个小时。 [SPEAKER_2] 但是你自己的时候是多两个小时。 [SPEAKER_2] 我可以给你解释。",
        "sourcePath": "references/reference_transcripts.json",
        "sourceId": "src_reference_LightOverlap"
      },
      "mixed": {
        "text": "你方式要 那他是怎么缓解我们的空虚的他让你在那个时间段里拥有了自己没问题 没问题 你先不着急哪怕这个自己是一个刷抖音的自己因为有一个前提性的问题 没有讨论我方这里再稍微解释一下他实在讲的熬夜所谓的熬夜就是晚睡晚起 是吧其实部落分义是一种要好 我先聊晚睡晚起方觉得晚睡晚起也是熬夜既然你是晚睡晚起晚睡早起也是熬夜了你上班的时间必定也晚因为你可以早睡早起你下班的时间必定也晚因为你可以为了身体健康健康那你个人的生活空间必定也就这么低早睡晚起你是怎么多出额外的时间来过自己的生活的不太一致我可以给你解释我的意思是2点睡10点起你没有多两个小时但是你自己的时候是多两个吗我可以给你解释",
        "sourcePath": "results/transcripts_raw/LightOverlap_mixed_whisper.json",
        "available": true,
        "sourceId": "src_transcript_LightOverlap_mixed"
      },
      "separated": {
        "text": "Artifact is referenced by result tables but the raw transcript JSON is not bundled in main. No transcript is fabricated in this replay demo.",
        "sourcePath": "results/transcripts_speaker/LightOverlap_separated_speaker_transcript.json",
        "available": false,
        "sourceId": "src_cer"
      },
      "cleaned": {
        "text": "[SPEAKER_1] 你方式要 那他是怎么缓解我们的空虚的 [SPEAKER_2] 他让你在那个时间段里拥有了自己 [SPEAKER_1] 没问题 没问题 你先不着急 [SPEAKER_2] 哪怕这个自己是一个刷抖音的自己 [SPEAKER_2] 我往这里再稍微解释一下 [SPEAKER_1] 因为有一个前提性的问题 没有讨论 [SPEAKER_2] 其实部落分也是一种 [SPEAKER_1] 实在讲的熬夜所谓的熬夜就是晚睡晚起 是吧 [SPEAKER_2] 刚觉得晚睡晚起也是熬夜 [SPEAKER_1] 好 我先聊晚睡晚起 [SPEAKER_2] 晚睡早起也是熬夜了 [SPEAKER_1] 既然你是晚睡晚起 [SPEAKER_1] 你上班的时间必定也晚 [SPEAKER_2] 因为你可以早睡早起 [SPEAKER_2] 因为你可以为了身体健康 [SPEAKER_2] 早睡晚睡 [SPEAKER_1] 那你个人的生活空间必定也就这么点 [SPEAKER_2] 不太一致 [SPEAKER_2] 我可以给你解释 [SPEAKER_1] 你是怎么多出额外的时间来过自己的生活的 [SPEAKER_2] 你没有多两个小时 [SPEAKER_2] 但是你自己的时候是多两个小时 [SPEAKER_1] 我的意思是2点10点起 [SPEAKER_2] 我可以给你解释 [SPEAKER_2] 我可以解释 [SPEAKER_1] 2点10点起",
        "sourcePath": "results/transcripts_postprocessed/LightOverlap_separated_speaker_transcript_cleaned.json",
        "available": true,
        "sourceId": "src_transcript_LightOverlap_cleaned"
      },
      "metrics": {
        "mixedCER": 0.210714,
        "separatedCER": 0.475,
        "cleanedCER": 0.382143,
        "routerV2": "mixed_whisper",
        "oracle": {
          "method": "mixed_whisper",
          "cer": 0.210714,
          "sourceId": "src_cer"
        }
      },
      "sourceId": "src_cer"
    },
    "separatedWin": {
      "caseId": "NoOverlap",
      "label": "Case B — Separated-win",
      "why": "NoOverlap is selected for live transcript comparison because main bundles raw separated JSON; Heavy/Opposite also win by separated CER in the gold table.",
      "audio": "assets/audio/NoOverlap.wav",
      "audioSource": "resources/mixed_audio/NoOverlap.wav",
      "audioSourceId": "src_audio_NoOverlap",
      "reference": {
        "text": "[SPEAKER_1] 你方是要，那它是怎么缓解我们的空虚的？ [SPEAKER_2] 它让你在那个时间段里拥有了自己。 [SPEAKER_1] 没问题，没问题，先不着急。 [SPEAKER_2] 哪怕这个自己是一个刷抖音的自己。 [SPEAKER_2] 我方这里再稍微解释一下。 [SPEAKER_1] 因为有一个前提性的问题没有讨论。 [SPEAKER_1] 现在讲的熬夜，所谓的熬夜就是晚睡晚起，是吧？ [SPEAKER_2] 其实布洛芬也是一种毒药。 [SPEAKER_1] 好，我先聊晚睡晚起。 [SPEAKER_2] 我方觉得晚睡晚起也是熬夜。 [SPEAKER_2] 晚睡早起也是熬夜了。 [SPEAKER_1] 既然你是晚睡晚起。 [SPEAKER_1] 你上班的时间必定也晚。 [SPEAKER_2] 因为你可以早睡早起。 [SPEAKER_1] 你下班的时间必定也晚。 [SPEAKER_2] 因为你可以为了身体健康。 [SPEAKER_1] 那你个人的生活空间必定也就这么点。 [SPEAKER_2] 早睡晚起。 [SPEAKER_1] 你是怎么多出额外的时间来过自己的生活的？ [SPEAKER_2] 不太一致。 [SPEAKER_2] 我可以给你解释。 [SPEAKER_1] 我的意思是，两点睡十点起。 [SPEAKER_2] 你没有多两个小时。 [SPEAKER_2] 但是你自己的时候是多两个。 [SPEAKER_2] 我可以给你解释。",
        "sourcePath": "references/reference_transcripts.json",
        "sourceId": "src_reference_NoOverlap"
      },
      "mixed": {
        "text": "你方式要 那他是怎么缓解我们的空虚的他让你在那个时间段里拥有了自己没问题 没问题 先不着急哪怕这个自己是一个刷抖音的自己因为有一个前提性的问题 没有讨论我方这里再稍微解释一下实在讲的熬夜所谓的熬夜就是晚睡晚起 是吧其实部落分义是一种要好 我先聊晚睡晚起方觉得晚睡晚起也是熬夜既然你是晚睡晚起晚睡早起也上午夜了没问题上班的时间必定也晚因为你可以早睡早起下班的时间必定也晚因为你可以为了身体健康那你个人的生活空间必定也就这么点早睡晚起你是怎么多出额外的时间来过自己的生活的不太一致我可以给你解释我的意思是2点睡10点起你没有多两个小时但是你自己的时候我可以给你解释",
        "sourcePath": "results/transcripts_raw/NoOverlap_mixed_whisper.json",
        "available": true,
        "sourceId": "src_transcript_NoOverlap_mixed"
      },
      "separated": {
        "text": "[SPEAKER_1] 你方式要 那他是怎么缓解我们的空虚的 [SPEAKER_2] 他让你在那个时间段里拥有了自己 [SPEAKER_1] 没问题 没问题 先不着急 [SPEAKER_2] 哪怕这个自己是一个刷抖音的自己 [SPEAKER_2] 我往这里再稍微解释一下 [SPEAKER_1] 因为有一个前提性的问题 没有讨论 [SPEAKER_1] 实在讲的熬夜所谓的熬夜就是晚睡晚起 是吧 [SPEAKER_2] 其实部落分也是一种 [SPEAKER_1] 好 我先聊晚睡晚起 [SPEAKER_2] 我刚觉得晚睡晚起也是熬夜 [SPEAKER_2] 晚睡早起也是熬夜了 [SPEAKER_1] 既然你是晚睡晚起 [SPEAKER_1] 你上班的时间必定也晚 [SPEAKER_2] 因为你可以早睡早起 [SPEAKER_1] 你下班的时间必定也晚 [SPEAKER_2] 因为你可以为了身体健康 [SPEAKER_1] 那你个人的生活空间必定也就这么点 [SPEAKER_2] 早睡晚睡 [SPEAKER_1] 你是怎么多出额外的时间来过自己的生活的 [SPEAKER_2] 不太一致 [SPEAKER_2] 我可以给你解释 [SPEAKER_1] 我的意思是2点睡10点起 [SPEAKER_2] 你没有多两个小时 [SPEAKER_2] 但是你自己的时候是多两个 [SPEAKER_2] 我可以给你解释",
        "sourcePath": "results/transcripts_speaker/NoOverlap_separated_speaker_transcript.json",
        "available": true,
        "sourceId": "src_transcript_NoOverlap_separated"
      },
      "cleaned": {
        "text": "[SPEAKER_1] 你方式要 那他是怎么缓解我们的空虚的 [SPEAKER_2] 他让你在那个时间段里拥有了自己 [SPEAKER_1] 没问题 没问题 先不着急 [SPEAKER_2] 哪怕这个自己是一个刷抖音的自己 [SPEAKER_2] 我往这里再稍微解释一下 [SPEAKER_1] 因为有一个前提性的问题 没有讨论 [SPEAKER_1] 实在讲的熬夜所谓的熬夜就是晚睡晚起 是吧 [SPEAKER_2] 其实部落分也是一种 [SPEAKER_1] 好 我先聊晚睡晚起 [SPEAKER_2] 我刚觉得晚睡晚起也是熬夜 [SPEAKER_2] 晚睡早起也是熬夜了 [SPEAKER_1] 既然你是晚睡晚起 [SPEAKER_1] 你上班的时间必定也晚 [SPEAKER_2] 因为你可以早睡早起 [SPEAKER_2] 因为你可以为了身体健康 [SPEAKER_1] 那你个人的生活空间必定也就这么点 [SPEAKER_2] 早睡晚睡 [SPEAKER_1] 你是怎么多出额外的时间来过自己的生活的 [SPEAKER_2] 不太一致 [SPEAKER_2] 我可以给你解释 [SPEAKER_1] 我的意思是2点睡10点起 [SPEAKER_2] 你没有多两个小时 [SPEAKER_2] 但是你自己的时候是多两个 [SPEAKER_2] 我可以给你解释",
        "sourcePath": "results/transcripts_postprocessed/NoOverlap_separated_speaker_transcript_cleaned.json",
        "available": true,
        "sourceId": "src_transcript_NoOverlap_cleaned"
      },
      "metrics": {
        "mixedCER": 0.215827,
        "separatedCER": 0.053957,
        "cleanedCER": 0.089928,
        "routerV2": "separated_whisper",
        "oracle": {
          "method": "separated_whisper",
          "cer": 0.053957,
          "sourceId": "src_cer"
        }
      },
      "sourceId": "src_cer"
    }
  },
  "allGoldRows": [
    {
      "caseId": "HeavyOverlap",
      "method": "mixed_whisper",
      "cer": 0.386861,
      "sourceId": "src_cer"
    },
    {
      "caseId": "HeavyOverlap",
      "method": "separated_whisper",
      "cer": 0.109489,
      "sourceId": "src_cer"
    },
    {
      "caseId": "HeavyOverlap",
      "method": "separated_whisper_cleaned",
      "cer": 0.145985,
      "sourceId": "src_cer"
    },
    {
      "caseId": "LightOverlap",
      "method": "mixed_whisper",
      "cer": 0.210714,
      "sourceId": "src_cer"
    },
    {
      "caseId": "LightOverlap",
      "method": "separated_whisper",
      "cer": 0.475,
      "sourceId": "src_cer"
    },
    {
      "caseId": "LightOverlap",
      "method": "separated_whisper_cleaned",
      "cer": 0.382143,
      "sourceId": "src_cer"
    },
    {
      "caseId": "MidOverlap",
      "method": "mixed_whisper",
      "cer": 0.178947,
      "sourceId": "src_cer"
    },
    {
      "caseId": "MidOverlap",
      "method": "separated_whisper",
      "cer": 0.273684,
      "sourceId": "src_cer"
    },
    {
      "caseId": "MidOverlap",
      "method": "separated_whisper_cleaned",
      "cer": 0.207018,
      "sourceId": "src_cer"
    },
    {
      "caseId": "NoOverlap",
      "method": "mixed_whisper",
      "cer": 0.215827,
      "sourceId": "src_cer"
    },
    {
      "caseId": "NoOverlap",
      "method": "separated_whisper",
      "cer": 0.053957,
      "sourceId": "src_cer"
    },
    {
      "caseId": "NoOverlap",
      "method": "separated_whisper_cleaned",
      "cer": 0.089928,
      "sourceId": "src_cer"
    },
    {
      "caseId": "OppositeOverlap",
      "method": "mixed_whisper",
      "cer": 0.518116,
      "sourceId": "src_cer"
    },
    {
      "caseId": "OppositeOverlap",
      "method": "separated_whisper",
      "cer": 0.047101,
      "sourceId": "src_cer"
    },
    {
      "caseId": "OppositeOverlap",
      "method": "separated_whisper_cleaned",
      "cer": 0.083333,
      "sourceId": "src_cer"
    }
  ],
  "routerPerformance": [
    {
      "strategy": "fixed_mixed_whisper",
      "average_cer": "0.302093",
      "sample_count": "5"
    },
    {
      "strategy": "fixed_separated_whisper",
      "average_cer": "0.191846",
      "sample_count": "5"
    },
    {
      "strategy": "fixed_separated_whisper_cleaned",
      "average_cer": "0.181681",
      "sample_count": "5"
    },
    {
      "strategy": "oracle_best",
      "average_cer": "0.120042",
      "sample_count": "5"
    },
    {
      "strategy": "rule_router_v1",
      "average_cer": "0.120042",
      "sample_count": "5"
    },
    {
      "strategy": "feature_router_v2",
      "average_cer": "0.120042",
      "sample_count": "5"
    }
  ],
  "riskPerformance": [
    {
      "strategy": "fixed_mixed_whisper",
      "average_cer": "0.302093"
    },
    {
      "strategy": "fixed_separated_whisper",
      "average_cer": "0.191846"
    },
    {
      "strategy": "fixed_separated_whisper_cleaned",
      "average_cer": "0.181681"
    },
    {
      "strategy": "router_v1",
      "average_cer": "0.120042"
    },
    {
      "strategy": "router_v2",
      "average_cer": "0.120042"
    },
    {
      "strategy": "risk_aware_selector",
      "average_cer": "0.134587"
    },
    {
      "strategy": "oracle_best",
      "average_cer": "0.120042"
    }
  ],
  "speakerCer": [
    {
      "case_id": "HeavyOverlap",
      "method": "separated_whisper",
      "speaker_1_cer": "0.05",
      "speaker_2_cer": "0.171642",
      "speaker_macro_cer": "0.110821",
      "speaker_gap": "0.121642",
      "speaker_1_reference_length": "140",
      "speaker_2_reference_length": "134",
      "speaker_1_hypothesis_length": "141",
      "speaker_2_hypothesis_length": "134",
      "observation": "Speaker-aware CER checks whether the method preserves who said what. Speaker quality is relatively balanced across the two speakers."
    },
    {
      "case_id": "HeavyOverlap",
      "method": "separated_whisper_cleaned",
      "speaker_1_cer": "0.121429",
      "speaker_2_cer": "0.171642",
      "speaker_macro_cer": "0.146535",
      "speaker_gap": "0.050213",
      "speaker_1_reference_length": "140",
      "speaker_2_reference_length": "134",
      "speaker_1_hypothesis_length": "131",
      "speaker_2_hypothesis_length": "134",
      "observation": "Speaker-aware CER checks whether the method preserves who said what. Cleaning removed 1 repeated segments, which may reduce hallucinations. Speaker quality is relatively balanced across the two speakers."
    },
    {
      "case_id": "LightOverlap",
      "method": "separated_whisper",
      "speaker_1_cer": "0.132867",
      "speaker_2_cer": "0.255474",
      "speaker_macro_cer": "0.19417",
      "speaker_gap": "0.122607",
      "speaker_1_reference_length": "143",
      "speaker_2_reference_length": "137",
      "speaker_1_hypothesis_length": "156",
      "speaker_2_hypothesis_length": "159",
      "observation": "Speaker-aware CER checks whether the method preserves who said what. Speaker quality is relatively balanced across the two speakers."
    },
    {
      "case_id": "LightOverlap",
      "method": "separated_whisper_cleaned",
      "speaker_1_cer": "0.160839",
      "speaker_2_cer": "0.109489",
      "speaker_macro_cer": "0.135164",
      "speaker_gap": "0.05135",
      "speaker_1_reference_length": "143",
      "speaker_2_reference_length": "137",
      "speaker_1_hypothesis_length": "140",
      "speaker_2_hypothesis_length": "139",
      "observation": "Speaker-aware CER checks whether the method preserves who said what. Cleaning removed 6 repeated segments, which may reduce hallucinations. Speaker quality is relatively balanced across the two speakers."
    },
    {
      "case_id": "MidOverlap",
      "method": "separated_whisper",
      "speaker_1_cer": "0.041958",
      "speaker_2_cer": "0.309859",
      "speaker_macro_cer": "0.175908",
      "speaker_gap": "0.267901",
      "speaker_1_reference_length": "143",
      "speaker_2_reference_length": "142",
      "speaker_1_hypothesis_length": "144",
      "speaker_2_hypothesis_length": "157",
      "observation": "Speaker-aware CER checks whether the method preserves who said what. Large speaker gap indicates uneven recognition quality between speakers."
    },
    {
      "case_id": "MidOverlap",
      "method": "separated_whisper_cleaned",
      "speaker_1_cer": "0.111888",
      "speaker_2_cer": "0.225352",
      "speaker_macro_cer": "0.16862",
      "speaker_gap": "0.113464",
      "speaker_1_reference_length": "143",
      "speaker_2_reference_length": "142",
      "speaker_1_hypothesis_length": "134",
      "speaker_2_hypothesis_length": "136",
      "observation": "Speaker-aware CER checks whether the method preserves who said what. Cleaning removed 4 repeated segments, which may reduce hallucinations. Speaker quality is relatively balanced across the two speakers."
    },
    {
      "case_id": "NoOverlap",
      "method": "separated_whisper",
      "speaker_1_cer": "0.041958",
      "speaker_2_cer": "0.066667",
      "speaker_macro_cer": "0.054312",
      "speaker_gap": "0.024709",
      "speaker_1_reference_length": "143",
      "speaker_2_reference_length": "135",
      "speaker_1_hypothesis_length": "144",
      "speaker_2_hypothesis_length": "133",
      "observation": "Speaker-aware CER checks whether the method preserves who said what. Speaker quality is relatively balanced across the two speakers."
    },
    {
      "case_id": "NoOverlap",
      "method": "separated_whisper_cleaned",
      "speaker_1_cer": "0.111888",
      "speaker_2_cer": "0.066667",
      "speaker_macro_cer": "0.089278",
      "speaker_gap": "0.045221",
      "speaker_1_reference_length": "143",
      "speaker_2_reference_length": "135",
      "speaker_1_hypothesis_length": "134",
      "speaker_2_hypothesis_length": "133",
      "observation": "Speaker-aware CER checks whether the method preserves who said what. Cleaning removed 1 repeated segments, which may reduce hallucinations. Speaker quality is relatively balanced across the two speakers."
    },
    {
      "case_id": "OppositeOverlap",
      "method": "separated_whisper",
      "speaker_1_cer": "0.021429",
      "speaker_2_cer": "0.073529",
      "speaker_macro_cer": "0.047479",
      "speaker_gap": "0.0521",
      "speaker_1_reference_length": "140",
      "speaker_2_reference_length": "136",
      "speaker_1_hypothesis_length": "140",
      "speaker_2_hypothesis_length": "134",
      "observation": "Speaker-aware CER checks whether the method preserves who said what. Speaker quality is relatively balanced across the two speakers."
    },
    {
      "case_id": "OppositeOverlap",
      "method": "separated_whisper_cleaned",
      "speaker_1_cer": "0.092857",
      "speaker_2_cer": "0.073529",
      "speaker_macro_cer": "0.083193",
      "speaker_gap": "0.019328",
      "speaker_1_reference_length": "140",
      "speaker_2_reference_length": "136",
      "speaker_1_hypothesis_length": "130",
      "speaker_2_hypothesis_length": "134",
      "observation": "Speaker-aware CER checks whether the method preserves who said what. Cleaning removed 1 repeated segments, which may reduce hallucinations. Speaker quality is relatively balanced across the two speakers."
    }
  ],
  "cpcerLite": [
    {
      "case_id": "HeavyOverlap",
      "method": "separated_whisper",
      "direct_speaker_macro_cer": "0.110821",
      "swapped_speaker_macro_cer": "0.92388",
      "cpcer_lite": "0.110821",
      "best_mapping": "direct",
      "speaker_assignment_gap": "0.0",
      "observation": "cpCER-lite compares direct and swapped speaker assignments and keeps the better one. Direct mapping is already best, suggesting speaker assignment is consistent."
    },
    {
      "case_id": "HeavyOverlap",
      "method": "separated_whisper_cleaned",
      "direct_speaker_macro_cer": "0.146535",
      "swapped_speaker_macro_cer": "0.908955",
      "cpcer_lite": "0.146535",
      "best_mapping": "direct",
      "speaker_assignment_gap": "0.0",
      "observation": "cpCER-lite compares direct and swapped speaker assignments and keeps the better one. Direct mapping is already best, suggesting speaker assignment is consistent. Cleaning removed 1 segments, which can affect speaker content balance."
    },
    {
      "case_id": "LightOverlap",
      "method": "separated_whisper",
      "direct_speaker_macro_cer": "0.19417",
      "swapped_speaker_macro_cer": "1.017789",
      "cpcer_lite": "0.19417",
      "best_mapping": "direct",
      "speaker_assignment_gap": "0.0",
      "observation": "cpCER-lite compares direct and swapped speaker assignments and keeps the better one. Direct mapping is already best, suggesting speaker assignment is consistent."
    },
    {
      "case_id": "LightOverlap",
      "method": "separated_whisper_cleaned",
      "direct_speaker_macro_cer": "0.135164",
      "swapped_speaker_macro_cer": "0.928692",
      "cpcer_lite": "0.135164",
      "best_mapping": "direct",
      "speaker_assignment_gap": "0.0",
      "observation": "cpCER-lite compares direct and swapped speaker assignments and keeps the better one. Direct mapping is already best, suggesting speaker assignment is consistent. Cleaning removed 6 segments, which can affect speaker content balance."
    },
    {
      "case_id": "MidOverlap",
      "method": "separated_whisper",
      "direct_speaker_macro_cer": "0.175908",
      "swapped_speaker_macro_cer": "0.975303",
      "cpcer_lite": "0.175908",
      "best_mapping": "direct",
      "speaker_assignment_gap": "0.0",
      "observation": "cpCER-lite compares direct and swapped speaker assignments and keeps the better one. Direct mapping is already best, suggesting speaker assignment is consistent."
    },
    {
      "case_id": "MidOverlap",
      "method": "separated_whisper_cleaned",
      "direct_speaker_macro_cer": "0.16862",
      "swapped_speaker_macro_cer": "0.905274",
      "cpcer_lite": "0.16862",
      "best_mapping": "direct",
      "speaker_assignment_gap": "0.0",
      "observation": "cpCER-lite compares direct and swapped speaker assignments and keeps the better one. Direct mapping is already best, suggesting speaker assignment is consistent. Cleaning removed 4 segments, which can affect speaker content balance."
    },
    {
      "case_id": "NoOverlap",
      "method": "separated_whisper",
      "direct_speaker_macro_cer": "0.054312",
      "swapped_speaker_macro_cer": "0.91813",
      "cpcer_lite": "0.054312",
      "best_mapping": "direct",
      "speaker_assignment_gap": "0.0",
      "observation": "cpCER-lite compares direct and swapped speaker assignments and keeps the better one. Direct mapping is already best, suggesting speaker assignment is consistent."
    },
    {
      "case_id": "NoOverlap",
      "method": "separated_whisper_cleaned",
      "direct_speaker_macro_cer": "0.089278",
      "swapped_speaker_macro_cer": "0.899612",
      "cpcer_lite": "0.089278",
      "best_mapping": "direct",
      "speaker_assignment_gap": "0.0",
      "observation": "cpCER-lite compares direct and swapped speaker assignments and keeps the better one. Direct mapping is already best, suggesting speaker assignment is consistent. Cleaning removed 1 segments, which can affect speaker content balance."
    },
    {
      "case_id": "OppositeOverlap",
      "method": "separated_whisper",
      "direct_speaker_macro_cer": "0.047479",
      "swapped_speaker_macro_cer": "0.909664",
      "cpcer_lite": "0.047479",
      "best_mapping": "direct",
      "speaker_assignment_gap": "0.0",
      "observation": "cpCER-lite compares direct and swapped speaker assignments and keeps the better one. Direct mapping is already best, suggesting speaker assignment is consistent."
    },
    {
      "case_id": "OppositeOverlap",
      "method": "separated_whisper_cleaned",
      "direct_speaker_macro_cer": "0.083193",
      "swapped_speaker_macro_cer": "0.894958",
      "cpcer_lite": "0.083193",
      "best_mapping": "direct",
      "speaker_assignment_gap": "0.0",
      "observation": "cpCER-lite compares direct and swapped speaker assignments and keeps the better one. Direct mapping is already best, suggesting speaker assignment is consistent. Cleaning removed 1 segments, which can affect speaker content balance."
    }
  ],
  "cascadeTiers": [
    {
      "case_id": "NoOverlap",
      "tier": "1",
      "selected_method": "separated_whisper",
      "compute_cost": "2.0",
      "instability_score": "0.0",
      "risk_triggered": "False",
      "tier1_method": "separated_whisper",
      "tier2_method": "separated_whisper"
    },
    {
      "case_id": "LightOverlap",
      "tier": "2",
      "selected_method": "separated_whisper_cleaned",
      "compute_cost": "2.1",
      "instability_score": "0.337037",
      "risk_triggered": "True",
      "tier1_method": "mixed_whisper",
      "tier2_method": "separated_whisper_cleaned"
    },
    {
      "case_id": "MidOverlap",
      "tier": "1",
      "selected_method": "mixed_whisper",
      "compute_cost": "1.0",
      "instability_score": "0.233573",
      "risk_triggered": "False",
      "tier1_method": "mixed_whisper",
      "tier2_method": "mixed_whisper"
    },
    {
      "case_id": "HeavyOverlap",
      "tier": "1",
      "selected_method": "separated_whisper",
      "compute_cost": "2.0",
      "instability_score": "0.0",
      "risk_triggered": "False",
      "tier1_method": "separated_whisper",
      "tier2_method": "separated_whisper"
    },
    {
      "case_id": "OppositeOverlap",
      "tier": "2",
      "selected_method": "stronger_model",
      "compute_cost": "2.5",
      "instability_score": "0.6",
      "risk_triggered": "True",
      "tier1_method": "separated_whisper",
      "tier2_method": "stronger_model"
    }
  ],
  "extensions": [
    {
      "title": "Learned Router",
      "contributor": "邵俊霖 / saayaya; team router work",
      "evidence": "mainline experimental",
      "result": "Logistic Regression / Decision Tree with observable features only; no CER leakage in route features.",
      "sourceId": "src_results_index"
    },
    {
      "title": "Compute-aware / Mode B Cascade",
      "contributor": "谢宇轩 (xyx12369)",
      "evidence": "mainline experimental",
      "result": "Tier 1 → Tier 2 → Tier 3 exposes accuracy / cost / coverage trade-offs and reference-free escalation.",
      "sourceId": "src_cascade"
    },
    {
      "title": "Speaker-aware Evaluation",
      "contributor": "张浩豪 / haohaozhang776; evaluation contributors",
      "evidence": "stable/gold",
      "result": "speaker-aware CER and cpCER-lite check who-said-what, not only plain text CER.",
      "sourceId": "src_cpcer"
    },
    {
      "title": "Separation Phase Diagram",
      "contributor": "梁跃川 / liang-yuechuan; 邵俊霖 / saayaya",
      "evidence": "mainline experimental + frontier",
      "result": "Crossover visualization shows separation-help boundary and uncertainty.",
      "sourceId": "src_sep_tax"
    }
  ],
  "frontiers": [
    {
      "group": "Noise / Hallucination / Model Scale",
      "items": [
        "Noise-robust router: 0.778 vs mixed 1.214 / gate 1.531; ~92% oracle gap recovered.",
        "Causal internal-state probe: confident attractor, token-id lock-in earlier than compression ratio.",
        "Model-size analysis: Whisper-base removes tiny-model separation tax under evaluated frontier setting."
      ],
      "sourceIds": [
        "src_noise_router",
        "src_sep_tax",
        "src_model_scale"
      ]
    },
    {
      "group": "Emotion / LLM",
      "items": [
        "Emotion separation tax points opposite to ASR: separation can help emotion while hurting text.",
        "Objective-aware routing decouples text and emotion routes; same CER, lower emotion distortion.",
        "Semantic LLM emotion coverage 0.70 vs lexicon 0.10; LLM repair is negative, 0/26 helped and CER 0.316→0.798."
      ],
      "sourceIds": [
        "src_emotion",
        "src_semantic_emotion",
        "src_llm_negative"
      ]
    },
    {
      "group": "AudioDepth Frontier",
      "items": [
        "Frontier Branch Only; Exploratory Research; Not merged into stable mainline; Not production-ready.",
        "AudioDepth treats overlap as time-frequency occlusion and builds mixed-only acoustic maps for Stage-1 triage.",
        "AudioDepth is a safety confirmer and interpretable auxiliary representation, not the main production router."
      ],
      "sourceIds": [
        "src_audiodepth_branch"
      ]
    }
  ],
  "limitations": [
    "five-case gold benchmark is small",
    "oracle separation differs from a real separator",
    "many frontier references are synthetic or silver",
    "real meeting generalization is not established",
    "some model-scale and AudioDepth results are branch-specific",
    "replay demo is not live inference",
    "raw separated transcript JSON is only bundled for NoOverlap in current main checkout"
  ],
  "evidenceLevels": [
    "stable/gold",
    "synthetic/silver",
    "experimental/frontier",
    "qualitative/demo",
    "branch-only exploratory"
  ],
  "contributors": [
    {
      "name": "王景宏 (ceilf6)（23123994）",
      "role": "Frontier research lead; overlap-hallucination mechanism investigator; ASR×LLM×emotion axis explorer; research-entropy meta-analyst; engineering harness architect.",
      "scope": "~45 merged PRs (#780–#872), 40+ issues, 40+ new modules, 36 frontier result directories, 15+ experimental figures, 6-agent literature review. All frontier work labeled `experimental/frontier`; no gold tables or verified references touched.",
      "highlights": [
        "*Role:** Frontier research lead; overlap-hallucination mechanism investigator; ASR×LLM×emotion axis explorer; research-entropy meta-analyst; engineering harness architect.",
        "*Scope summary:** ~45 merged PRs (#780–#872), 40+ issues, 40+ new modules, 36 frontier result directories, 15+ experimental figures, 6-agent literature review. All frontier work labeled `experimental/frontier`; no gold tables or verified references touched.",
        "--"
      ],
      "evidencePaths": [
        "results/frontier/separation_tax/FINDINGS.md",
        "results/frontier/separation_tax/phase_curve.csv",
        "results/frontier/hallucination_router/routing_curve.csv",
        "results/frontier/hallucination_router/FINDINGS.md",
        "results/frontier/reference_free_qe/qe_signal_table.csv"
      ],
      "sourceId": "src_contributions"
    },
    {
      "name": "吴方舟/wfzark（23123986）",
      "role": "Core technical contributor; route-selection problem framer; main experimental pipeline owner; AudioDepth frontier explorer; team report and",
      "scope": "",
      "highlights": [
        "*Role:** Core technical contributor; route-selection problem framer; main",
        "*when should an overlap-aware ASR system separate speech, keep mixed audio, or",
        "mixed Whisper baseline；"
      ],
      "evidencePaths": [
        "CONTRIBUTIONS.md"
      ],
      "sourceId": "src_contributions"
    },
    {
      "name": "谢宇轩 (xyx12369)",
      "role": "Mode B: 算力感知三层级联识别。",
      "scope": "",
      "highlights": [
        "*Role:** Mode B: 算力感知三层级联识别。",
        "*主要贡献：**",
        "设计并实现参考无关的三层级联架构：Tier 1 (便宜) → Tier 2"
      ],
      "evidencePaths": [
        "src/cascade_tiers.py"
      ],
      "sourceId": "src_contributions"
    },
    {
      "name": "邵俊霖 / saayaya (23124001)",
      "role": "Separation Phase Diagram 修复；Learned Router 设计与实现；bugfix。",
      "scope": "",
      "highlights": [
        "*Role:** Separation Phase Diagram 修复；Learned Router 设计与实现；bugfix。",
        "*主要贡献：**",
        "修复 `separation_phase_diagram.py` 中因合并冲突导致的内容重复和"
      ],
      "evidencePaths": [
        "src/plot_phase_boundary.py",
        "src/learned_router.py",
        "src/llm_repair_loop.py",
        "src/rag_repair.py",
        "src/router_feature_importance.py"
      ],
      "sourceId": "src_contributions"
    },
    {
      "name": "梁跃川 / liang-yuechuan",
      "role": "Mode C: 前沿探索 — 分离相位图 (Separation Phase Diagram) 设计与实现。",
      "scope": "",
      "highlights": [
        "*Role:** Mode C: 前沿探索 — 分离相位图 (Separation Phase Diagram) 设计与实现。",
        "*主要贡献：**",
        "`tests/test_separation_phase_diagram.py`（5 项测试）："
      ],
      "evidencePaths": [
        "src/separation_phase_diagram.py",
        "src/separation_phase_diagram.py"
      ],
      "sourceId": "src_contributions"
    },
    {
      "name": "张浩豪 / haohaozhang776",
      "role": "Mode D: Evaluation System & Cross-Benchmark Analysis（评估系统与跨实验对齐）",
      "scope": "",
      "highlights": [
        "*Role:** Mode D: Evaluation System & Cross-Benchmark Analysis（评估系统与跨实验对齐）",
        "*主要贡献：**",
        "构建统一 evaluation adapter，使 mixed / separated / cleaned / router v2 / cascade outputs 能够在同一评估接口下进行对齐比较，减少不同 pipeline 在格式层面的不一致问题。"
      ],
      "evidencePaths": [
        "CONTRIBUTIONS.md"
      ],
      "sourceId": "src_contributions"
    }
  ]
};
