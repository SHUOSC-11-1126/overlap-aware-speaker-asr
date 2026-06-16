# Frontier Operator Next-Action Completion Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one completion dashboard that summarizes the current top-level operator chain at a glance.

**Architecture:** Read the top-level operator summary and milestone card, merge them into one dashboard row, and emit CSV/JSON/Markdown outputs.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for dashboard row mapping

**Files:**
- Create: `tests/test_frontier_operator_next_action_completion_dashboard.py`

- [ ] **Step 1: Write the failing test**

```python
from src.frontier_operator_next_action_completion_dashboard import build_dashboard_row
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_completion_dashboard -v`
Expected: FAIL with missing module or symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def build_dashboard_row(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_completion_dashboard -v`
Expected: PASS

### Task 2: Generate dashboard artifacts

**Files:**
- Create: `src/frontier_operator_next_action_completion_dashboard.py`
- Create: `results/tables/frontier_operator_next_action_completion_dashboard.csv`
- Create: `results/tables/frontier_operator_next_action_completion_dashboard.json`
- Create: `results/figures/frontier_operator_next_action_completion_dashboard.md`

- [ ] **Step 1: Implement generator**
- [ ] **Step 2: Run generator**

Run: `python3 -m src.frontier_operator_next_action_completion_dashboard`
Expected: writes dashboard artifacts under `results/`

- [ ] **Step 3: Inspect generated dashboard**

Run: `sed -n '1,120p' results/figures/frontier_operator_next_action_completion_dashboard.md`
Expected: shows current first frontier, blocked frontier, milestone, and dominant blocker in one place.

### Task 3: Document the dashboard layer

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add artifact allowlist and concise references**
- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_completion_dashboard tests.test_frontier_operator_next_action_milestone_card tests.test_frontier_operator_next_action_phase_checkpoint_card -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add .gitignore tests/test_frontier_operator_next_action_completion_dashboard.py src/frontier_operator_next_action_completion_dashboard.py \
  results/tables/frontier_operator_next_action_completion_dashboard.* results/figures/frontier_operator_next_action_completion_dashboard.md \
  README.md docs/project_state.md docs/roadmap.md
git commit -m "feat: add frontier operator next-action completion dashboard"
```
