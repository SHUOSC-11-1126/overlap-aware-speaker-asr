# Plan: Frontier Operator Next-Action Status Handoff Phase Checkpoint Bridge Checklist

1. Add a focused unit test for the phase checkpoint bridge checklist row builder.
2. Implement `src/frontier_operator_next_action_status_handoff_phase_checkpoint_bridge_checklist.py` using the existing phase checkpoint card JSON only.
3. Extend the top-level packet section list so it includes the new bridge layer.
4. Emit CSV, JSON, and Markdown outputs for the new checklist and refresh the packet artifacts under `results/`.
5. Update `.gitignore`, `README.md`, `docs/project_state.md`, and `docs/roadmap.md`.
6. Run focused unit tests around the new checklist, checkpoint, milestone, and packet chain.
7. Commit docs/plan first, then commit the feature and push both commits to `main`.
