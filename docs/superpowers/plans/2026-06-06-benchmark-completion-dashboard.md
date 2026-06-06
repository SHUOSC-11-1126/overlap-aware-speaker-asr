# Benchmark Completion Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a benchmark completion dashboard artifact that summarizes pending phase counts, current start step, and top blocker family in one place.

**Architecture:** Keep the execution summary, runbook card, and milestone card as the source layers, then derive a one-row dashboard that exposes current start, pending phase count, and dominant blocker. Publish it as both a tiny CSV row and a markdown note so the handoff packet can open with a concise completion snapshot.

**Tech Stack:** Python, `unittest`, CSV/JSON/Markdown artifact generation

---

### Task 1: Add completion-dashboard failing tests

**Files:**
- Modify: `tests/test_compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_completion_dashboard_rows_summarize_overall_progress(self) -> None:
    rows = build_benchmark_completion_dashboard_rows(
        [{"phase": "foundation"}],
        [{"recommended_start_step": "phase1_gold_runtime_foundation"}],
        [{"current_start_step": "phase1_gold_runtime_foundation"}],
    )
    self.assertEqual(rows[0]["current_start_step"], "phase1_gold_runtime_foundation")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_completion_dashboard_rows_summarize_overall_progress -v`
Expected: FAIL with `ImportError` or `NameError` because `build_benchmark_completion_dashboard_rows` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def build_benchmark_completion_dashboard_rows(
    summary_rows: list[dict[str, Any]],
    runbook_rows: list[dict[str, Any]],
    milestone_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_completion_dashboard_rows_summarize_overall_progress -v`
Expected: PASS after the real dashboard logic is implemented.

- [ ] **Step 5: Commit**

```bash
git add tests/test_compute_aware_cascade.py src/compute_aware_cascade.py
git commit -m "feat: summarize cascade benchmark completion dashboard"
```

### Task 2: Wire completion-dashboard outputs into artifacts and packet

**Files:**
- Modify: `src/compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_packet_lines_include_completion_dashboard(self) -> None:
    lines = build_benchmark_packet_lines([], [], [], [], [], [], [], [], [], [], [], [], [], [
        {"current_start_step": "phase1_gold_runtime_foundation"}
    ])
    self.assertIn("## Completion Dashboard", "\n".join(lines))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_completion_dashboard -v`
Expected: FAIL because the handoff packet does not render the completion dashboard section yet.

- [ ] **Step 3: Write minimal implementation**

```python
lines.extend(["", "## Completion Dashboard", ""])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_completion_dashboard -v`
Expected: PASS with the completion dashboard section present.

- [ ] **Step 5: Commit**

```bash
git add src/compute_aware_cascade.py tests/test_compute_aware_cascade.py
git commit -m "feat: add cascade benchmark completion dashboard outputs"
```

### Task 3: Refresh generated artifacts and docs

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`
- Modify: `REPORT.md`
- Modify: `results/figures/cascade_benchmark_handoff_packet.md`
- Create: `results/figures/cascade_benchmark_completion_dashboard.md`
- Create: `results/tables/cascade_benchmark_completion_dashboard.csv`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Rebuild generated outputs**

Run: `python3 -m src.compute_aware_cascade --dataset synthetic_split`
Expected: Writes the new benchmark completion dashboard artifacts and refreshed packet output.

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
Expected: PASS with the new completion-dashboard coverage included.

- [ ] **Step 3: Update docs**

```markdown
- `results/figures/cascade_benchmark_completion_dashboard.md` now shows the current start step, dominant blocker family, and pending phase count in one short dashboard.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md REPORT.md results/figures/cascade_benchmark_completion_dashboard.md results/figures/cascade_benchmark_handoff_packet.md results/tables/cascade_benchmark_completion_dashboard.csv
git commit -m "docs: publish cascade benchmark completion dashboard"
```
