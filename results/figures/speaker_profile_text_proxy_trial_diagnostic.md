# Speaker Profile Text-Proxy Trial Diagnostic

This generated diagnostic records all-gold text-profile proxy trial results. It does not claim voiceprint success or improved speaker attribution.

Summary: `5/5` cases prefer swapped alignment; average confidence gap = 0.413131.

| case_id | best_profile_alignment | profile_confidence_gap | proxy_method | diagnostic_status | diagnostic_note |
| --- | --- | ---: | --- | --- | --- |
| NoOverlap | swapped | 0.422118 | text_overlap_profile | text_proxy_diagnostic_complete | Text-profile proxy for NoOverlap reports swapped alignment with gap 0.422118; this is a risk signal only, not speaker identification. |
| LightOverlap | swapped | 0.418882 | text_overlap_profile | text_proxy_diagnostic_complete | Text-profile proxy for LightOverlap reports swapped alignment with gap 0.418882; this is a risk signal only, not speaker identification. |
| MidOverlap | swapped | 0.406764 | text_overlap_profile | text_proxy_diagnostic_complete | Text-profile proxy for MidOverlap reports swapped alignment with gap 0.406764; this is a risk signal only, not speaker identification. |
| HeavyOverlap | swapped | 0.411129 | text_overlap_profile | text_proxy_diagnostic_complete | Text-profile proxy for HeavyOverlap reports swapped alignment with gap 0.411129; this is a risk signal only, not speaker identification. |
| OppositeOverlap | swapped | 0.406764 | text_overlap_profile | text_proxy_diagnostic_complete | Text-profile proxy for OppositeOverlap reports swapped alignment with gap 0.406764; this is a risk signal only, not speaker identification. |

## Diagnostic conclusion

All gold cases prefer swapped text-profile alignment; text proxy is useful as a warning sign but not deployment-ready attribution.

Next method direction: `embedding_or_voiceprint_baseline`
