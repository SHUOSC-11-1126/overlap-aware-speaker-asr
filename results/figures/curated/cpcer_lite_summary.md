# cpCER-lite Summary

## Why cpCER-lite matters

cpCER-lite is a light-weight speaker permutation check: it compares direct speaker assignment against the swapped mapping, then keeps the lower macro CER.

## Average cpCER-lite

- separated_whisper: 0.116538
- separated_whisper_cleaned: 0.124558

## Largest assignment gap

- HeavyOverlap / separated_whisper: 0.0

## Per-case results

| case_id | method | direct_speaker_macro_cer | swapped_speaker_macro_cer | cpCER-lite | best_mapping | speaker_assignment_gap |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| HeavyOverlap | separated_whisper | 0.110821 | 0.92388 | 0.110821 | direct | 0.0 |
| HeavyOverlap | separated_whisper_cleaned | 0.146535 | 0.908955 | 0.146535 | direct | 0.0 |
| LightOverlap | separated_whisper | 0.19417 | 1.017789 | 0.19417 | direct | 0.0 |
| LightOverlap | separated_whisper_cleaned | 0.135164 | 0.928692 | 0.135164 | direct | 0.0 |
| MidOverlap | separated_whisper | 0.175908 | 0.975303 | 0.175908 | direct | 0.0 |
| MidOverlap | separated_whisper_cleaned | 0.16862 | 0.905274 | 0.16862 | direct | 0.0 |
| NoOverlap | separated_whisper | 0.054312 | 0.91813 | 0.054312 | direct | 0.0 |
| NoOverlap | separated_whisper_cleaned | 0.089278 | 0.899612 | 0.089278 | direct | 0.0 |
| OppositeOverlap | separated_whisper | 0.047479 | 0.909664 | 0.047479 | direct | 0.0 |
| OppositeOverlap | separated_whisper_cleaned | 0.083193 | 0.894958 | 0.083193 | direct | 0.0 |

## Artifacts

- cpCER-lite CSV: results/tables/cpcer_lite_results.csv
- cpCER-lite figure: results/figures/cpcer_lite_by_case.png