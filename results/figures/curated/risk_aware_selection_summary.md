# Risk-Aware Final Selector Summary

## Selection Table

| case_id | final_selected_method | risk_level | risk_reasons |
| --- | --- | --- | --- |
| NoOverlap | separated_whisper | medium | method_disagreement_risk |
| LightOverlap | mixed_whisper | high | repetition_hallucination_risk;length_inflation_risk;method_disagreement_risk |
| MidOverlap | mixed_whisper | high | repetition_hallucination_risk;length_inflation_risk;method_disagreement_risk |
| HeavyOverlap | separated_whisper_cleaned | medium | length_inflation_risk;method_disagreement_risk |
| OppositeOverlap | separated_whisper_cleaned | medium | length_inflation_risk;method_disagreement_risk |

## Performance

| strategy | average_cer |
| --- | ---: |
| fixed_mixed_whisper | 0.302093 |
| fixed_separated_whisper | 0.191846 |
| fixed_separated_whisper_cleaned | 0.181681 |
| router_v1 | 0.120042 |
| router_v2 | 0.120042 |
| risk_aware_selector | 0.134587 |
| oracle_best | 0.120042 |

## Deployment Notes

- coverage: 1.000000
- manual_review_count: 0
- The selector is reference-free during decision making; CER is only used after the selection is fixed.