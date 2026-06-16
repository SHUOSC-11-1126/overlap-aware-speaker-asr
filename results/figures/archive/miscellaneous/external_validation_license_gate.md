# External Validation License Gate

This generated checklist records the license gate for the first external sanity-check slice. It does not claim that any external audio has been downloaded or evaluated.

| dataset_name | label | license_status | gate_order | gate_step | gate_note | next_gate |
| --- | --- | --- | ---: | --- | --- | --- |
| AISHELL-4 | external/sanity-check | pending_confirmation | 1 | Confirm official AISHELL-4 license terms before staging any local audio. | Read the official release page and record whether local reuse is permitted for a tiny sanity-check slice. | Document the license decision in the slice receipt before downloading audio. |
| AISHELL-4 | external/sanity-check | pending_confirmation | 2 | Verify attribution and redistribution constraints for any excerpt used in the repo. | Keep the external slice explicitly labeled external/sanity-check and separate from gold benchmark claims. | Only after the license gate is documented should any audio staging begin. |
