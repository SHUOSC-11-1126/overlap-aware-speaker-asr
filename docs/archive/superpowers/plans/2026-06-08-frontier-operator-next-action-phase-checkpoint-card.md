# Frontier Operator Next-Action Phase Checkpoint Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one phase checkpoint card that isolates the current top-level ready-lane completion signal.

**Architecture:** Read the top-level runbook card, map the frontier/action/completion signal into one checkpoint row, and emit CSV/JSON/Markdown outputs.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for checkpoint row mapping

**Files:**
- Create: `tests/test_frontier_operator_next_action_phase_checkpoint_card.py`

- [ ] **Step 1: Write the failing test**

```python
from src.frontier_operator_next_action_phase_checkpoint_card import build_phase_checkpoint_row
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_phase_checkpoint_card -v`
Expected: FAIL with missing module or symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def build_phase_checkpoint_row(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_phase_checkpoint_card -v`
Expected: PASS

### Task 2: Generate phase checkpoint artifacts

**Files:**
- Create: `src/frontier_operator_next_action_phase_checkpoint_card.py`
- Create: `results/tables/frontier_operator_next_action_phase_checkpoint_card.csv`
- Create: `results/tables/frontier_operator_next_action_phase_checkpoint_card.json`
- Create: `results/figures/frontier_operator_next_action_phase_checkpoint_card.md`

- [ ] **Step 1: Implement generator**
- [ ] **Step 2: Run generator**

Run: `python3 -m src.frontier_operator_next_action_phase_checkpoint_card`
Expected: writes phase checkpoint artifacts under `results/`

- [ ] **Step 3: Inspect generated card**

Run: `sed -n '1,120p' results/figures/frontier_operator_next_action_phase_checkpoint_card.md`
Expected: shows the current frontier, action, and narrow completion signal in one place.

### Task 3: Document the checkpoint layer

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add artifact allowlist and concise references**
- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_phase_checkpoint_card tests.test_frontier_operator_next_action_handoff_packet_bridge_checklist tests.test_frontier_operator_next_action_runbook_card -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add .gitignore tests/test_frontier_operator_next_action_phase_checkpoint_card.py src/frontier_operator_next_action_phase_checkpoint_card.py \
  results/tables/frontier_operator_next_action_phase_checkpoint_card.* results/figures/frontier_operator_next_action_phase_checkpoint_card.md \
  README.md docs/project_state.md docs/roadmap.md
git commit -m "feat: add frontier operator next-action phase checkpoint card"
```
