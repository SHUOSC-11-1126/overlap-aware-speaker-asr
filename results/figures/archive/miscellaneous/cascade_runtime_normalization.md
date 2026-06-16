# Cascade Runtime Normalization Audit

This audit normalizes selected-route runtime by the selected audio duration to estimate route-specific RTF.

## gold / ALL

| strategy | average_runtime_sec | average_selected_audio_duration_sec | average_rtf | sample_count |
| --- | ---: | ---: | ---: | ---: |
| fixed_mixed_whisper | 5.2198 | 46.8754 | 0.109309 | 5 |
| fixed_separated_whisper | 5.9716 | 93.7508 | 0.064251 | 5 |
| fixed_separated_whisper_cleaned | 5.9716 | 93.7508 | 0.064251 | 5 |
| router_v2_costed | 5.5508 | 73.6904 | 0.080646 | 5 |
| risk_aware_costed | 5.5508 | 73.6904 | 0.080646 | 5 |
| budget_cascade | 5.5508 | 73.6904 | 0.080646 | 5 |

