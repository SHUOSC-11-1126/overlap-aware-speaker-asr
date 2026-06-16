# Frontier Operator Next-Action Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one operator card that converts the unified frontier go/no-go board into explicit ready-lane and blocked-lane next actions.

**Architecture:** Read the existing unified board plus summary, resolve the highest-priority ready and blocked frontiers, map them to concrete target artifacts, and emit one compact operator card plus one summary row.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for operator lane selection

**Files:**
- Create: `tests/test_frontier_operator_next_action_card.py`

- [ ] **Step 1: Write the failing test**

```python
from src.frontier_operator_next_action_card import build_action_rows, build_summary_row
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_card -v`
Expected: FAIL with missing module or symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def build_action_rows(...):
    ...

def build_summary_row(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_card -v`
Expected: PASS

### Task 2: Generate operator card artifacts

**Files:**
- Create: `src/frontier_operator_next_action_card.py`
- Create: `results/tables/frontier_operator_next_action_card.csv`
- Create: `results/tables/frontier_operator_next_action_card.json`
- Create: `results/tables/frontier_operator_next_action_summary.csv`
- Create: `results/tables/frontier_operator_next_action_summary.json`
- Create: `results/figures/frontier_operator_next_action_card.md`
- Create: `results/figures/frontier_operator_next_action_summary.md`

- [ ] **Step 1: Implement generator**
- [ ] **Step 2: Run generator**

Run: `python3 -m src.frontier_operator_next_action_card`
Expected: writes operator card artifacts under `results/`

- [ ] **Step 3: Inspect generated card**

Run: `sed -n '1,120p' results/figures/frontier_operator_next_action_card.md`
Expected: shows `ready_lane` first and `blocked_lane` second with explicit target artifacts.

### Task 3: Document the operator layer

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add artifact allowlist and concise references**
- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_card tests.test_frontier_go_no_go_board tests.test_frontier_execution_queue_handoff -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add .gitignore tests/test_frontier_operator_next_action_card.py src/frontier_operator_next_action_card.py \
  results/tables/frontier_operator_next_action_* results/figures/frontier_operator_next_action_*.md \
  README.md docs/project_state.md docs/roadmap.md
git commit -m "feat: add frontier operator next-action card"
```
