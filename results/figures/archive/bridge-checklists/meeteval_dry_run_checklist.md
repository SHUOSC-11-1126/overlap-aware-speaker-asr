# MeetEval Dry Run Checklist

This generated checklist orders the verified cases for a single diagnostic dry run. It does not claim that MeetEval or cpWER has been run.

| case_id | hypothesis_source | dry_run_priority | operator_step | expected_evidence | validation_note |
| --- | --- | --- | --- | --- | --- |
| NoOverlap | separated_whisper | preferred | Validate one exported case end-to-end before any cpWER-style claim. | results/tables/meeteval_dry_run_receipt.json | Raw separated source is available, so this is the cleanest first dry-run candidate. |
| LightOverlap | separated_whisper_cleaned | secondary | Validate one exported case end-to-end before any cpWER-style claim. | results/tables/meeteval_dry_run_receipt.json | Cleaned fallback is available, but it should stay behind raw separated source cases in the dry-run queue. |
| MidOverlap | separated_whisper_cleaned | secondary | Validate one exported case end-to-end before any cpWER-style claim. | results/tables/meeteval_dry_run_receipt.json | Cleaned fallback is available, but it should stay behind raw separated source cases in the dry-run queue. |
| HeavyOverlap | separated_whisper_cleaned | secondary | Validate one exported case end-to-end before any cpWER-style claim. | results/tables/meeteval_dry_run_receipt.json | Cleaned fallback is available, but it should stay behind raw separated source cases in the dry-run queue. |
| OppositeOverlap | separated_whisper_cleaned | secondary | Validate one exported case end-to-end before any cpWER-style claim. | results/tables/meeteval_dry_run_receipt.json | Cleaned fallback is available, but it should stay behind raw separated source cases in the dry-run queue. |
