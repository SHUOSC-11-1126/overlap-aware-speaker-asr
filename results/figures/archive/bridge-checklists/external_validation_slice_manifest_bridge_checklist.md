# External Validation Slice Manifest Bridge Checklist

This generated checklist turns the slice manifest into a row-by-row bridge verification path. It remains external/sanity-check coordination only and does not claim benchmark execution.

| checklist_order | dataset_name | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | AISHELL-4 | results/figures/external_validation_slice_manifest.md | results/figures/external_validation_slice_manifest_receipt.md | Verify the external slice manifest bridge for AISHELL-4 before any staging writeback is advanced. | Open the slice manifest first, then write back through the manifest receipt while staging remains blocked_by_license_gate. | Confirm this bridge before opening the slice manifest receipt target. |
