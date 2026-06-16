# Frontier Operator Next-Action Bridge Checklist

This generated checklist turns the top-level frontier operator card into an ordered bridge verification path. It remains experimental/frontier coordination only and does not claim experiment completion.

| checklist_order | action_lane | frontier_name | go_no_go_state | prerequisite_artifact | target_artifact | checklist_goal | bridge_note | next_gate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | ready_lane | meeteval_compatibility | go | results/figures/frontier_operator_next_action_card.md | results/tables/meeteval_cpwer_execution_receipt.json | Verify the operator card lane for meeteval_compatibility before opening the target artifact. | Operator card reports action_lane=ready_lane and go_no_go_state=go for meeteval_compatibility; confirm coordination context before opening the target artifact. | Confirm this bridge before advancing the meeteval_compatibility operator lane. |
| 2 | blocked_lane | external_validation | no_go | results/figures/frontier_operator_next_action_card.md | results/tables/external_validation_license_confirmation_receipt_bridge.json | Verify the operator card lane for external_validation before opening the target artifact. | Operator card reports action_lane=blocked_lane and go_no_go_state=no_go for external_validation; confirm coordination context before opening the target artifact. | Confirm this bridge before advancing the external_validation operator lane. |
