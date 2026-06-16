# Plan: Frontier Operator Next-Action Status Handoff Packet Bridge Checklist Operator Brief Refresh

1. Update the focused packet bridge checklist unit test first so it expects the operator brief target and urgency note.
2. Refresh `src/frontier_operator_next_action_status_handoff_packet_bridge_checklist.py` to use the `status_handoff_operator_brief` JSON.
3. Regenerate CSV, JSON, and Markdown outputs under `results/`.
4. Update `README.md`, `docs/project_state.md`, and `docs/roadmap.md` to describe the refreshed reentry target.
5. Run focused unit tests around the refreshed packet bridge checklist and adjacent `status/handoff` artifacts.
6. Commit docs/plan first, then commit the feature and push both commits to `main`.
