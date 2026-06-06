# Synthetic Split Cascade Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a synthetic split compute-aware cascade evaluation that extends the current gold-only frontier analysis without touching stable benchmark references.

**Architecture:** Generalize `src/compute_aware_cascade.py` so it can score either gold cases or the held-out synthetic split dataset through dataset-specific loaders and one shared aggregation path. Keep route selection reference-free and use CER only after each strategy has already selected a method.

**Tech Stack:** Python standard library, existing CSV/JSON project tables, optional matplotlib, `unittest`.

---

## File Structure

- Modify `tests/test_compute_aware_cascade.py`: add red-green coverage for synthetic split strategy selection and aggregation.
- Modify `src/compute_aware_cascade.py`: add dataset-aware loaders, synthetic split strategies, and synthetic output writers.
- Modify `README.md`: surface the new command and silver/frontier output links.
- Modify `docs/README.md`: add the new design/plan docs and generated outputs.
- Modify `docs/project_state.md`: record synthetic split cascade validation as `synthetic/silver` frontier evidence.
- Modify `docs/roadmap.md`: mark synthetic split cascade validation as completed.

### Task 1: Lock the New Behavior with Tests

**Files:**
- Modify: `tests/test_compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write failing tests for synthetic split strategy selection and scope aggregation**
- [ ] **Step 2: Run `python3 -m unittest tests.test_compute_aware_cascade -v` and verify RED**
- [ ] **Step 3: Commit the tested requirement framing**

### Task 2: Extend the Cascade Script

**Files:**
- Modify: `src/compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Add dataset-aware input/output path helpers**
- [ ] **Step 2: Implement synthetic split case loading and decision mapping**
- [ ] **Step 3: Add synthetic split-only cascade strategies and scoped aggregation**
- [ ] **Step 4: Run `python3 -m unittest tests.test_compute_aware_cascade -v` and verify GREEN**
- [ ] **Step 5: Commit the code extension**

### Task 3: Generate Outputs and Refresh Docs

**Files:**
- Modify: `README.md`
- Modify: `docs/README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`
- Create: `results/tables/synthetic_split_cascade_performance.csv`
- Create: `results/tables/synthetic_split_cascade_performance.json`
- Create: `results/figures/synthetic_split_cascade_summary.md`
- Create: `results/figures/synthetic_split_cer_runtime_tradeoff.png`

- [ ] **Step 1: Run `python3 -m src.compute_aware_cascade --dataset synthetic_split`**
- [ ] **Step 2: Update docs to link the new silver/frontier outputs**
- [ ] **Step 3: Run `python3 -m src.project_harness` and inspect `git status --short`**
- [ ] **Step 4: Commit the outputs and docs refresh**
