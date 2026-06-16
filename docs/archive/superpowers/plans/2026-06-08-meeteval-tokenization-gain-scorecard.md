# MeetEval Tokenization Gain Scorecard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small MeetEval scorecard that quantifies the value of character-spaced tokenization on the gold benchmark without changing the stable baseline.

**Architecture:** Read the existing raw official cpWER, character-level official cpWER, and bridge-lite artifacts, derive per-case gain/alignment rows, then emit one scorecard table plus one aggregate summary. Keep the logic isolated in a new generator module and cover the derivation rules with unit tests.

**Tech Stack:** Python, CSV/JSON/Markdown artifact generation, `unittest`

---

### Task 1: Add failing tests for scorecard logic

**Files:**
- Create: `tests/test_meeteval_cpwer_tokenization_gain_scorecard.py`
- Test: `tests/test_meeteval_cpwer_tokenization_gain_scorecard.py`

- [ ] **Step 1: Write the failing test**

```python
from src.meeteval_cpwer_tokenization_gain_scorecard import (
    build_scorecard_rows,
    build_summary_row,
)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_meeteval_cpwer_tokenization_gain_scorecard -v`
Expected: FAIL with `ModuleNotFoundError` or missing symbol error.

- [ ] **Step 3: Write minimal implementation**

```python
def build_scorecard_rows(...):
    ...

def build_summary_row(...):
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_meeteval_cpwer_tokenization_gain_scorecard -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_meeteval_cpwer_tokenization_gain_scorecard.py src/meeteval_cpwer_tokenization_gain_scorecard.py
git commit -m "feat: add meeteval tokenization gain scorecard"
```

### Task 2: Generate scorecard artifacts

**Files:**
- Create: `src/meeteval_cpwer_tokenization_gain_scorecard.py`
- Create: `results/tables/meeteval_cpwer_tokenization_gain_scorecard.csv`
- Create: `results/tables/meeteval_cpwer_tokenization_gain_scorecard.json`
- Create: `results/tables/meeteval_cpwer_tokenization_gain_scorecard_summary.csv`
- Create: `results/tables/meeteval_cpwer_tokenization_gain_scorecard_summary.json`
- Create: `results/figures/meeteval_cpwer_tokenization_gain_scorecard.md`
- Create: `results/figures/meeteval_cpwer_tokenization_gain_scorecard_summary.md`

- [ ] **Step 1: Implement artifact writer**

```python
def write_outputs(rows, summary_row):
    ...
```

- [ ] **Step 2: Run generator**

Run: `python -m src.meeteval_cpwer_tokenization_gain_scorecard`
Expected: writes CSV/JSON/Markdown scorecard artifacts under `results/`

- [ ] **Step 3: Inspect generated summary**

Run: `sed -n '1,120p' results/figures/meeteval_cpwer_tokenization_gain_scorecard_summary.md`
Expected: shows average gain, aligned case count, and the recommended default mode.

- [ ] **Step 4: Commit**

```bash
git add src/meeteval_cpwer_tokenization_gain_scorecard.py results/tables/meeteval_cpwer_tokenization_gain_scorecard* results/figures/meeteval_cpwer_tokenization_gain_scorecard*.md
git commit -m "feat: publish meeteval tokenization gain scorecard"
```

### Task 3: Document the new frontier evidence

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add concise documentation references**

```md
- scorecard path
- what it proves
- experimental/frontier caveat
```

- [ ] **Step 2: Run focused verification**

Run: `python -m unittest tests.test_meeteval_cpwer_official_execution tests.test_meeteval_cpwer_tokenization_gain_scorecard tests.test_meeteval_tokenization_adaptation_handoff_completion_summary -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md
git commit -m "docs: record meeteval tokenization gain scorecard"
```
