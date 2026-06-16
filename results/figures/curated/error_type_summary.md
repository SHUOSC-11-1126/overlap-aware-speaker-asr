# Error Type Summary

## Key Findings

- LightOverlap separated output shows insertion-heavy behavior with repeated hallucinations.
- MidOverlap separated output also shows insertion-heavy behavior, indicating over-generation under moderate overlap.
- HeavyOverlap and OppositeOverlap are dominated by lower error counts under separation, matching the stronger-overlap benefit.

## Selected Diagnostics

| case_id | method | dominant_error_type | repetition_count | removed_count_if_cleaned | observation |
| --- | --- | --- | ---: | ---: | --- |
| NoOverlap | separated_whisper | substitution | 3 | 0 | For NoOverlap separated_whisper, all error counts are lower than mixed, indicating separation is beneficial under strong overlap. |
| LightOverlap | separated_whisper | insertion | 38 | 0 | For LightOverlap separated_whisper, insertion and repetition dominate, suggesting separation-triggered ASR hallucination. |
| MidOverlap | separated_whisper | insertion | 59 | 0 | For MidOverlap separated_whisper, insertion and repetition dominate, suggesting separation-triggered ASR hallucination. |
| HeavyOverlap | separated_whisper | substitution | 3 | 0 | For HeavyOverlap separated_whisper, all error counts are lower than mixed, indicating separation is beneficial under strong overlap. |
| OppositeOverlap | separated_whisper | substitution | 3 | 0 | For OppositeOverlap separated_whisper, all error counts are lower than mixed, indicating separation is beneficial under strong overlap. |

- LightOverlap separated_whisper insertion_count: 54, repetition_count: 38.
- MidOverlap separated_whisper insertion_count: 26, repetition_count: 59.