# Cascade Runtime Normalization Audit

This audit normalizes selected-route runtime by the selected audio duration to estimate route-specific RTF.

## synthetic_split / ALL

| strategy | average_runtime_sec | average_selected_audio_duration_sec | average_rtf | sample_count |
| --- | ---: | ---: | ---: | ---: |
| fixed_mixed_whisper | 0.674 | 4.082594 | 0.163361 | 100 |
| fixed_separated_whisper | 1.10836 | 8.165188 | 0.133284 | 100 |
| fixed_separated_whisper_cleaned | 1.10836 | 8.165188 | 0.133284 | 100 |
| router_v2_synthetic_costed | 0.78127 | 5.415958 | 0.148342 | 100 |
| budget_cascade | 0.94756 | 6.455422 | 0.148228 | 100 |
| cleaned_preferred_cascade | 1.04816 | 6.55787 | 0.156245 | 100 |

## synthetic_split / DEV

| strategy | average_runtime_sec | average_selected_audio_duration_sec | average_rtf | sample_count |
| --- | ---: | ---: | ---: | ---: |
| fixed_mixed_whisper | 0.74366 | 4.088964 | 0.17536 | 50 |
| fixed_separated_whisper | 1.01176 | 8.177928 | 0.122603 | 50 |
| fixed_separated_whisper_cleaned | 1.01176 | 8.177928 | 0.122603 | 50 |
| router_v2_synthetic_costed | 0.76668 | 5.441964 | 0.148484 | 50 |
| budget_cascade | 0.97074 | 6.454404 | 0.151484 | 50 |
| cleaned_preferred_cascade | 0.97074 | 6.454404 | 0.151484 | 50 |

## synthetic_split / TEST

| strategy | average_runtime_sec | average_selected_audio_duration_sec | average_rtf | sample_count |
| --- | ---: | ---: | ---: | ---: |
| fixed_mixed_whisper | 0.60434 | 4.076224 | 0.151362 | 50 |
| fixed_separated_whisper | 1.20496 | 8.152448 | 0.143966 | 50 |
| fixed_separated_whisper_cleaned | 1.20496 | 8.152448 | 0.143966 | 50 |
| router_v2_synthetic_costed | 0.79586 | 5.389952 | 0.148201 | 50 |
| budget_cascade | 0.92438 | 6.45644 | 0.144971 | 50 |
| cleaned_preferred_cascade | 1.12558 | 6.661336 | 0.161006 | 50 |

