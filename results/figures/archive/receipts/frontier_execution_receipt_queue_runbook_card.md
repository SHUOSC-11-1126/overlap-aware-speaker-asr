# Frontier Execution Receipt Queue Runbook Card

This generated runbook card condenses the first receipt-queue action into a one-page execution card. It remains experimental/frontier coordination only and does not claim benchmark execution.

- Recommended frontier: `meeteval_compatibility`
- Recommended action: `Update execution_status in results/tables/meeteval_cpwer_execution_receipt.json after a real frontier run and bridge verification.`
- Required evidence: `results/figures/frontier_execution_receipt_queue_handoff.md; results/figures/frontier_execution_receipt_queue_handoff_bridge_checklist.md`
- Completion signal: `receipt queue verification is complete and the target receipt results/tables/meeteval_cpwer_execution_receipt.json is ready to update`
- Urgency: queue_status=queue_complete; ready_receipt_count=3; pending_receipt_count=0
- Runbook note: Start with meeteval_compatibility as the current first receipt-queue target after confirming the handoff and bridge layers. This remains coordination-only and does not claim benchmark execution.
