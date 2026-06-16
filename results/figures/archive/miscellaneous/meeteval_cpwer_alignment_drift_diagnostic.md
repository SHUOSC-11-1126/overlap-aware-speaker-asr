# MeetEval cpWER Alignment Drift Diagnostic

This generated note documents cross-metric drift cases from the alignment audit. It does not claim a finished MeetEval evaluation.

| case_id | hypothesis_source | cpwer_bridge_lite | speaker_macro_cer | alignment_gap | drift_severity | likely_cause | recommended_action | diagnostic_status | observation |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| HeavyOverlap | separated_whisper_cleaned | 0.162827 | 0.146535 | 0.016292 | moderate | HeavyOverlap uses separated_whisper_cleaned; the cleaned separated export path and speaker_macro_cer recomputation diverge under heavy overlap, producing a non-zero cross-metric gap. | Inspect HeavyOverlap cleaned separated segments before treating cpWER bridge-lite as aligned with speaker_macro_cer. | drift_documented | experimental/frontier drift diagnostic only; this does not claim a finished MeetEval evaluation. |
