# Plan: Frontier Execution Queue Receipt Open Card

1. Add a focused failing unit test for the receipt open card row builder.
2. Extend the execution queue handoff packet coverage so it expects the new receipt open card section.
3. Implement `src/frontier_execution_queue_receipt_open_card.py` using the existing handoff bridge checklist JSON only.
4. Refresh the execution queue handoff packet so it includes the new receipt open card section.
5. Emit CSV, JSON, and Markdown outputs for the new card and refreshed packet under `results/`.
6. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
7. Run focused unit tests around the new card and adjacent execution queue artifacts.
8. Commit docs/plan first, then commit the feature and push both commits to `main`.
