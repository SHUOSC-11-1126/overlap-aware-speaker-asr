# Speaker-aware CER Summary

## Why speaker-aware CER matters

Normal CER only checks whether the words match, but it does not tell us whether the right speaker's content was preserved. Speaker-aware CER measures each speaker track separately, which is useful for assessing speaker attribution quality.

## Average speaker macro CER

- separated_whisper: 0.116538
- separated_whisper_cleaned: 0.124558

## Largest speaker gap

- MidOverlap / separated_whisper: 0.267901

## Per-case results

| case_id | method | speaker_1_cer | speaker_2_cer | speaker_macro_cer | speaker_gap |
| --- | --- | ---: | ---: | ---: | ---: |
| HeavyOverlap | separated_whisper | 0.05 | 0.171642 | 0.110821 | 0.121642 |
| HeavyOverlap | separated_whisper_cleaned | 0.121429 | 0.171642 | 0.146535 | 0.050213 |
| LightOverlap | separated_whisper | 0.132867 | 0.255474 | 0.19417 | 0.122607 |
| LightOverlap | separated_whisper_cleaned | 0.160839 | 0.109489 | 0.135164 | 0.05135 |
| MidOverlap | separated_whisper | 0.041958 | 0.309859 | 0.175908 | 0.267901 |
| MidOverlap | separated_whisper_cleaned | 0.111888 | 0.225352 | 0.16862 | 0.113464 |
| NoOverlap | separated_whisper | 0.041958 | 0.066667 | 0.054312 | 0.024709 |
| NoOverlap | separated_whisper_cleaned | 0.111888 | 0.066667 | 0.089278 | 0.045221 |
| OppositeOverlap | separated_whisper | 0.021429 | 0.073529 | 0.047479 | 0.0521 |
| OppositeOverlap | separated_whisper_cleaned | 0.092857 | 0.073529 | 0.083193 | 0.019328 |

## Artifacts

- Speaker CER CSV: results/tables/speaker_cer_results.csv
- Speaker CER figure: results/figures/speaker_cer_by_case.png