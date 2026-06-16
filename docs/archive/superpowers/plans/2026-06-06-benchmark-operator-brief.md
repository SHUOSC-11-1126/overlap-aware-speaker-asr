# Benchmark Operator Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a benchmark operator brief artifact that gives a short execution summary for the person about to run the next benchmark step.

**Architecture:** Keep the completion dashboard, runbook card, and session ledger as source layers, then derive a concise operator brief with the current start step, the evidence to collect, and the dominant blocker framing. Publish it as a small CSV row and a markdown note so the handoff packet can open with a plain-language execution summary.

**Tech Stack:** Python, `unittest`, CSV/JSON/Markdown artifact generation

---

### Task 1: Add operator-brief failing tests

**Files:**
- Modify: `tests/test_compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_operator_brief_rows_summarize_operator_context(self) -> None:
    rows = build_benchmark_operator_brief_rows(
        [{"current_start_step": "phase1_gold_runtime_foundation"}],
        [{"recommended_start_step": "phase1_gold_runtime_foundation"}],
        [{"plan_step_id": "phase1_gold_runtime_foundation"}],
    )
    self.assertEqual(rows[0]["operator_step"], "phase1_gold_runtime_foundation")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_operator_brief_rows_summarize_operator_context -v`
Expected: FAIL with `ImportError` or `NameError` because `build_benchmark_operator_brief_rows` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def build_benchmark_operator_brief_rows(
    dashboard_rows: list[dict[str, Any]],
    runbook_rows: list[dict[str, Any]],
    ledger_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_operator_brief_rows_summarize_operator_context -v`
Expected: PASS after the real brief logic is implemented.

- [ ] **Step 5: Commit**

```bash
git add tests/test_compute_aware_cascade.py src/compute_aware_cascade.py
git commit -m "feat: summarize cascade benchmark operator brief"
```

### Task 2: Wire operator-brief outputs into artifacts and packet

**Files:**
- Modify: `src/compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_packet_lines_include_operator_brief(self) -> None:
    lines = build_benchmark_packet_lines([], [], [], [], [], [], [], [], [], [], [], [], [], [], [
        {"operator_step": "phase1_gold_runtime_foundation"}
    ])
    self.assertIn("## Operator Brief", "\n".join(lines))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_operator_brief -v`
Expected: FAIL because the handoff packet does not render the operator brief section yet.

- [ ] **Step 3: Write minimal implementation**

```python
lines.extend(["", "## Operator Brief", ""])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_operator_brief -v`
Expected: PASS with the operator brief section present.

- [ ] **Step 5: Commit**

```bash
git add src/compute_aware_cascade.py tests/test_compute_aware_cascade.py
git commit -m "feat: add cascade benchmark operator brief outputs"
```

### Task 3: Refresh generated artifacts and docs

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`
- Modify: `REPORT.md`
- Modify: `results/figures/cascade_benchmark_handoff_packet.md`
- Create: `results/figures/cascade_benchmark_operator_brief.md`
- Create: `results/tables/cascade_benchmark_operator_brief.csv`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Rebuild generated outputs**

Run: `python3 -m src.compute_aware_cascade --dataset synthetic_split`
Expected: Writes the new benchmark operator brief artifacts and refreshed packet output.

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
Expected: PASS with the new operator-brief coverage included.

- [ ] **Step 3: Update docs**

```markdown
- `results/figures/cascade_benchmark_operator_brief.md` now gives a plain-language summary of what the current benchmark operator should do next.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md REPORT.md results/figures/cascade_benchmark_operator_brief.md results/figures/cascade_benchmark_handoff_packet.md results/tables/cascade_benchmark_operator_brief.csv
git commit -m "docs: publish cascade benchmark operator brief"
```
