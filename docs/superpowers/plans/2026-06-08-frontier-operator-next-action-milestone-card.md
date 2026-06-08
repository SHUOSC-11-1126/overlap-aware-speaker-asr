# Frontier Operator Next-Action Milestone Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one milestone card that shows what the current top-level ready-lane checkpoint unlocks next.

**Architecture:** Read the top-level operator summary, map ready and blocked frontiers into one milestone row, and emit CSV/JSON/Markdown outputs.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for milestone row mapping

**Files:**
- Create: `tests/test_frontier_operator_next_action_milestone_card.py`

- [ ] **Step 1: Write the failing test**

```python
from src.frontier_operator_next_action_milestone_card import build_milestone_card_row
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_milestone_card -v`
Expected: FAIL with missing module or symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def build_milestone_card_row(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_milestone_card -v`
Expected: PASS

### Task 2: Generate milestone card artifacts

**Files:**
- Create: `src/frontier_operator_next_action_milestone_card.py`
- Create: `results/tables/frontier_operator_next_action_milestone_card.csv`
- Create: `results/tables/frontier_operator_next_action_milestone_card.json`
- Create: `results/figures/frontier_operator_next_action_milestone_card.md`

- [ ] **Step 1: Implement generator**
- [ ] **Step 2: Run generator**

Run: `python3 -m src.frontier_operator_next_action_milestone_card`
Expected: writes milestone card artifacts under `results/`

- [ ] **Step 3: Inspect generated card**

Run: `sed -n '1,120p' results/figures/frontier_operator_next_action_milestone_card.md`
Expected: shows the current milestone, blocked-frontier unlock, and remaining count.

### Task 3: Document the milestone layer

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add artifact allowlist and concise references**
- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_milestone_card tests.test_frontier_operator_next_action_phase_checkpoint_card tests.test_frontier_operator_next_action_handoff_packet_bridge_checklist -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add .gitignore tests/test_frontier_operator_next_action_milestone_card.py src/frontier_operator_next_action_milestone_card.py \
  results/tables/frontier_operator_next_action_milestone_card.* results/figures/frontier_operator_next_action_milestone_card.md \
  README.md docs/project_state.md docs/roadmap.md
git commit -m "feat: add frontier operator next-action milestone card"
```
