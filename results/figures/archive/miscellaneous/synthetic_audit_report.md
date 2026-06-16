# Synthetic Benchmark Sanity Audit

This audit checks whether the synthetic silver benchmark contains reference construction issues, missing files, or true ASR hallucination patterns.

| sample_id | tier | method | cer | reference_length | hypothesis_length | length_ratio | suspected_issue |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| SyntheticNoOverlap_02 | SyntheticNoOverlap | separated_whisper | 5.307692 | 26 | 150 | 5.769231 | high_length_ratio; possible repetition hallucination or reference mismatch |
| SyntheticNoOverlap_02 | SyntheticNoOverlap | separated_whisper_cleaned | 0.884615 | 26 | 25 | 0.961538 | high_cer_low_length_ratio; possible substitution-heavy ASR error |
| SyntheticLightOverlap_02 | SyntheticLightOverlap | separated_whisper | 0.923077 | 26 | 20 | 0.769231 | high_cer_low_length_ratio; possible substitution-heavy ASR error |
| SyntheticLightOverlap_02 | SyntheticLightOverlap | separated_whisper_cleaned | 0.923077 | 26 | 20 | 0.769231 | high_cer_low_length_ratio; possible substitution-heavy ASR error |
| SyntheticMidOverlap_02 | SyntheticMidOverlap | separated_whisper | 0.961538 | 26 | 26 | 1.0 | high_cer_low_length_ratio; possible substitution-heavy ASR error |
| SyntheticMidOverlap_02 | SyntheticMidOverlap | separated_whisper_cleaned | 0.961538 | 26 | 26 | 1.0 | high_cer_low_length_ratio; possible substitution-heavy ASR error |
| SyntheticHeavyOverlap_02 | SyntheticHeavyOverlap | separated_whisper | 0.961538 | 26 | 26 | 1.0 | high_cer_low_length_ratio; possible substitution-heavy ASR error |
| SyntheticHeavyOverlap_02 | SyntheticHeavyOverlap | separated_whisper_cleaned | 0.961538 | 26 | 26 | 1.0 | high_cer_low_length_ratio; possible substitution-heavy ASR error |
| SyntheticOppositeOverlap_03 | SyntheticOppositeOverlap | mixed_whisper | 0.9 | 20 | 6 | 0.3 | high_cer_low_length_ratio; possible substitution-heavy ASR error |