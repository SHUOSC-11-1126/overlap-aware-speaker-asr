# External Validation Go-No-Go Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small external-validation decision board that shows whether the first AISHELL-4 slice can move toward staging, and what exact blocker still prevents that.

**Architecture:** Read the existing external-validation checkpoint artifacts, normalize their statuses into per-checkpoint go/no-go rows, then emit one board plus one summary card. Keep all logic isolated in one new generator and cover the status mapping with unit tests.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for decision logic

**Files:**
- Create: `tests/test_external_validation_go_no_go_board.py`
- Test: `tests/test_external_validation_go_no_go_board.py`

- [ ] **Step 1: Write the failing test**

```python
from src.external_validation_go_no_go_board import (
    classify_go_no_go_state,
    build_summary_row,
)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_external_validation_go_no_go_board -v`
Expected: FAIL with missing module or symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def classify_go_no_go_state(...):
    ...

def build_summary_row(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_external_validation_go_no_go_board -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_external_validation_go_no_go_board.py src/external_validation_go_no_go_board.py
git commit -m "feat: add external validation go-no-go board"
```

### Task 2: Generate go-no-go artifacts

**Files:**
- Create: `src/external_validation_go_no_go_board.py`
- Create: `results/tables/external_validation_go_no_go_board.csv`
- Create: `results/tables/external_validation_go_no_go_board.json`
- Create: `results/tables/external_validation_go_no_go_summary.csv`
- Create: `results/tables/external_validation_go_no_go_summary.json`
- Create: `results/figures/external_validation_go_no_go_board.md`
- Create: `results/figures/external_validation_go_no_go_summary.md`

- [ ] **Step 1: Implement board generator**

```python
def build_checkpoint_rows(...):
    ...

def write_outputs(...):
    ...
```

- [ ] **Step 2: Run generator**

Run: `python3 -m src.external_validation_go_no_go_board`
Expected: writes board and summary artifacts under `results/`

- [ ] **Step 3: Inspect generated summary**

Run: `sed -n '1,120p' results/figures/external_validation_go_no_go_summary.md`
Expected: shows overall blocked state, primary blocker, and next action.

- [ ] **Step 4: Commit**

```bash
git add src/external_validation_go_no_go_board.py results/tables/external_validation_go_no_go_* results/figures/external_validation_go_no_go_*.md
git commit -m "feat: publish external validation go-no-go board"
```

### Task 3: Document the new external frontier evidence

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add concise references**

```md
- board path
- what blocker it confirms
- external/sanity-check caveat
```

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_external_validation_go_no_go_board tests.test_external_validation_slice_staging_execution_status tests.test_external_validation_slice_staging_readiness -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md
git commit -m "docs: record external validation go-no-go board"
```
