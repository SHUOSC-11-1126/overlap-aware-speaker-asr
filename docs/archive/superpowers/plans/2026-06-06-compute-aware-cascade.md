# Compute-aware Cascade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an experimental compute-aware cascade analysis that reports the CER/cost trade-off of existing ASR routes without changing stable gold outputs.

**Architecture:** Implement one standalone module, `src/compute_aware_cascade.py`, with pure helper functions for testability and a script entry point for writing tables, JSON, a PNG, and a Markdown summary. Keep routing decisions reference-free; CER is loaded only for post-decision scoring.

**Tech Stack:** Python standard library, existing CSV/JSON project tables, optional matplotlib for PNG rendering, `unittest` for tests.

---

## File Structure

- Create `tests/test_compute_aware_cascade.py`: pure unit tests for cost and aggregation behavior.
- Create `src/compute_aware_cascade.py`: cascade data loading, strategy selection, performance aggregation, and output rendering.
- Modify `README.md`: add cascade command and result links.
- Modify `docs/README.md`: add cascade docs and outputs to the docs index.
- Modify `docs/project_state.md`: add the new experimental stage and findings.
- Modify `docs/roadmap.md`: mark compute-aware cascade as started with an offline analysis contribution.

### Task 1: Add Failing Unit Tests

- [ ] **Step 1: Create `tests/test_compute_aware_cascade.py` with behavior-first tests**

```python
from __future__ import annotations

import unittest

from src.compute_aware_cascade import (
    DEFAULT_COST_PROXY,
    build_strategy_rows,
    compute_method_cost,
    choose_budget_cascade_method,
)


class ComputeAwareCascadeTest(unittest.TestCase):
    def test_compute_method_cost_prefers_observed_runtime(self) -> None:
        row = {
            "mixed_runtime_sec": "4.0",
            "separated_runtime_sec": "9.0",
            "cleaned_runtime_sec": "9.5",
        }
        self.assertEqual(compute_method_cost("mixed_whisper", row), 4.0)
        self.assertEqual(compute_method_cost("separated_whisper", row), 9.0)
        self.assertEqual(compute_method_cost("separated_whisper_cleaned", row), 9.5)

    def test_compute_method_cost_falls_back_to_proxy(self) -> None:
        self.assertEqual(compute_method_cost("mixed_whisper", {}), DEFAULT_COST_PROXY["mixed_whisper"])
        self.assertEqual(compute_method_cost("manual_review", {}), DEFAULT_COST_PROXY["manual_review"])

    def test_budget_cascade_uses_reference_free_signals(self) -> None:
        self.assertEqual(choose_budget_cascade_method(0, "low"), "separated_whisper")
        self.assertEqual(choose_budget_cascade_method(1, "high"), "mixed_whisper")
        self.assertEqual(choose_budget_cascade_method(3, "medium"), "separated_whisper_cleaned")

    def test_build_strategy_rows_excludes_manual_review_cer_but_counts_coverage(self) -> None:
        cases = [
            {"case_id": "A", "overlap_level": 0, "risk_level": "low"},
            {"case_id": "B", "overlap_level": 2, "risk_level": "high"},
        ]
        decisions = {
            "router_v2_costed": {"A": "separated_whisper", "B": "mixed_whisper"},
            "risk_aware_costed": {"A": "separated_whisper", "B": "manual_review"},
        }
        cer_lookup = {
            ("A", "mixed_whisper"): 0.5,
            ("A", "separated_whisper"): 0.1,
            ("A", "separated_whisper_cleaned"): 0.2,
            ("B", "mixed_whisper"): 0.3,
            ("B", "separated_whisper"): 0.7,
            ("B", "separated_whisper_cleaned"): 0.6,
        }
        runtime_lookup = {
            "A": {"mixed_runtime_sec": 1.0, "separated_runtime_sec": 2.0, "cleaned_runtime_sec": 2.1},
            "B": {"mixed_runtime_sec": 1.0, "separated_runtime_sec": 2.0, "cleaned_runtime_sec": 2.1},
        }

        rows = build_strategy_rows(cases, decisions, cer_lookup, runtime_lookup)
        risk_row = next(row for row in rows if row["strategy"] == "risk_aware_costed")

        self.assertEqual(risk_row["manual_review_count"], 1)
        self.assertEqual(risk_row["automatic_coverage"], 0.5)
        self.assertEqual(risk_row["sample_count"], 1)
        self.assertEqual(risk_row["average_cer"], 0.1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python3 -m unittest tests.test_compute_aware_cascade -v`

Expected: FAIL because `src.compute_aware_cascade` does not exist.

### Task 2: Implement the Cascade Module

- [ ] **Step 1: Create `src/compute_aware_cascade.py`**

Implement constants, CSV readers, `compute_method_cost`, `choose_budget_cascade_method`, `build_strategy_rows`, output writers, and `main()`.

- [ ] **Step 2: Run the unit tests and verify GREEN**

Run: `python3 -m unittest tests.test_compute_aware_cascade -v`

Expected: all tests pass.

- [ ] **Step 3: Run the script**

Run: `python3 -m src.compute_aware_cascade`

Expected output includes:

```text
Wrote cascade performance: results/tables/cascade_performance.csv
Wrote cascade summary: results/figures/compute_aware_cascade_summary.md
```

### Task 3: Add Documentation Links

- [ ] **Step 1: Update README and docs index**

Add the cascade command to reproduction commands and link `results/figures/compute_aware_cascade_summary.md` plus `results/figures/cer_runtime_tradeoff.png`.

- [ ] **Step 2: Update project state and roadmap**

Record the experimental/frontier label, offline runtime/proxy cost caveat, and the generated output paths.

### Task 4: Verify and Commit on Main

- [ ] **Step 1: Run verification**

Run:

```bash
python3 -m unittest tests.test_compute_aware_cascade -v
python3 -m src.compute_aware_cascade
python3 -m src.project_harness
```

Expected: unit tests pass, cascade outputs are written, harness reports `gold_cases_present: True` and `gold_and_synthetic_separated: True`.

- [ ] **Step 2: Inspect git diff**

Run: `git status --short` and `git diff --stat`.

Expected: only cascade module, tests, docs, and new cascade outputs are changed.

- [ ] **Step 3: Commit and push main**

Run:

```bash
git add README.md docs src tests results/tables/cascade_performance.csv results/tables/cascade_performance.json results/figures/compute_aware_cascade_summary.md results/figures/cer_runtime_tradeoff.png
git commit -m "feat: add compute-aware cascade analysis"
git push origin main
```

Expected: commit succeeds and `main` pushes to origin.

