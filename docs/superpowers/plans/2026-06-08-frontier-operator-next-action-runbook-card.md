# Frontier Operator Next-Action Runbook Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one one-page runbook card that condenses the top-level operator brief into a first-action execution card.

**Architecture:** Read the operator brief and operator bridge checklist, promote the ready lane into a runbook row, and emit one compact card in CSV/JSON/Markdown.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for runbook card mapping

**Files:**
- Create: `tests/test_frontier_operator_next_action_runbook_card.py`

- [ ] **Step 1: Write the failing test**

```python
from src.frontier_operator_next_action_runbook_card import build_runbook_card_row
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_runbook_card -v`
Expected: FAIL with missing module or symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def build_runbook_card_row(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_runbook_card -v`
Expected: PASS

### Task 2: Generate runbook card artifacts

**Files:**
- Create: `src/frontier_operator_next_action_runbook_card.py`
- Create: `results/tables/frontier_operator_next_action_runbook_card.csv`
- Create: `results/tables/frontier_operator_next_action_runbook_card.json`
- Create: `results/figures/frontier_operator_next_action_runbook_card.md`

- [ ] **Step 1: Implement generator**
- [ ] **Step 2: Run generator**

Run: `python3 -m src.frontier_operator_next_action_runbook_card`
Expected: writes runbook card artifacts under `results/`

- [ ] **Step 3: Inspect generated card**

Run: `sed -n '1,120p' results/figures/frontier_operator_next_action_runbook_card.md`
Expected: shows the ready frontier, evidence path, and narrow completion signal in one page.

### Task 3: Document the runbook layer

**Files:**
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add artifact allowlist and concise references**
- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_frontier_operator_next_action_runbook_card tests.test_frontier_operator_next_action_operator_brief tests.test_frontier_operator_next_action_bridge_checklist -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add .gitignore tests/test_frontier_operator_next_action_runbook_card.py src/frontier_operator_next_action_runbook_card.py \
  results/tables/frontier_operator_next_action_runbook_card.* results/figures/frontier_operator_next_action_runbook_card.md \
  README.md docs/project_state.md docs/roadmap.md
git commit -m "feat: add frontier operator next-action runbook card"
```
