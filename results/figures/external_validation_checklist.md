# External Validation Checklist

This generated checklist orders the external sanity-check front end before any slice is staged. It does not claim that any external benchmark has already been run.

| dataset_name | label | checklist_order | preflight_step | expected_evidence | next_gate | validation_note |
| --- | --- | ---: | --- | --- | --- | --- |
| AISHELL-4 | external/sanity-check | 1 | Confirm license and choose a tiny sanity-check slice. | results/tables/external_validation_slice_receipt.json | Confirm license, then stage one tiny slice before any evaluation claim. | Closest meeting-style target, so keep it at the front of the external sanity-check queue. |
| AliMeeting | external/sanity-check | 2 | Confirm license and choose one compact overlap-heavy excerpt. | results/tables/external_validation_slice_receipt.json | Confirm license, then stage one tiny slice before any evaluation claim. | Near-term backup if AISHELL-4 access or packaging is slower than expected. |
| AMI | external/sanity-check | 3 | Confirm license and compare one clip against current meeting-style exports. | results/tables/external_validation_slice_receipt.json | Confirm license, then stage one tiny slice before any evaluation claim. | Useful cross-domain reference, but keep the license check explicit before any slice is staged. |
| LibriCSS | external/sanity-check | 4 | Confirm license and choose one overlap condition for a narrow sanity-check. | results/tables/external_validation_slice_receipt.json | Confirm license, then stage one tiny slice before any evaluation claim. | Best reserved for overlap-heavy follow-up after one meeting-style path is already established. |
