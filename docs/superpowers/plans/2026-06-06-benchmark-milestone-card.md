# Benchmark Milestone Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a benchmark milestone card artifact that summarizes the next milestone, what current step unlocks it, and how many phases remain.

**Architecture:** Keep the runbook card, dependency graph, and execution summary as source layers, then derive a tiny milestone card that highlights the immediate completion boundary and the remaining path. Emit both a small CSV row and a markdown note so the handoff packet can present a short “where we are / what comes next” view.

**Tech Stack:** Python, `unittest`, CSV/JSON/Markdown artifact generation

---

### Task 1: Add milestone-card failing tests

**Files:**
- Modify: `tests/test_compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_milestone_card_rows_summarize_next_milestone(self) -> None:
    rows = build_benchmark_milestone_card_rows(
        [{"recommended_start_step": "phase1_gold_runtime_foundation"}],
        [{"plan_step_id": "phase1_gold_runtime_foundation"}],
        [{"phase": "foundation"}],
    )
    self.assertEqual(rows[0]["current_start_step"], "phase1_gold_runtime_foundation")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_milestone_card_rows_summarize_next_milestone -v`
Expected: FAIL with `ImportError` or `NameError` because `build_benchmark_milestone_card_rows` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def build_benchmark_milestone_card_rows(
    runbook_rows: list[dict[str, Any]],
    dependency_rows: list[dict[str, Any]],
    summary_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_milestone_card_rows_summarize_next_milestone -v`
Expected: PASS after the real milestone logic is implemented.

- [ ] **Step 5: Commit**

```bash
git add tests/test_compute_aware_cascade.py src/compute_aware_cascade.py
git commit -m "feat: summarize cascade benchmark milestone card"
```

### Task 2: Wire milestone-card outputs into artifacts and packet

**Files:**
- Modify: `src/compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_packet_lines_include_milestone_card(self) -> None:
    lines = build_benchmark_packet_lines([], [], [], [], [], [], [], [], [], [], [], [
        {"current_start_step": "phase1_gold_runtime_foundation"}
    ])
    self.assertIn("## Milestone Card", "\n".join(lines))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_milestone_card -v`
Expected: FAIL because the handoff packet does not render the milestone card section yet.

- [ ] **Step 3: Write minimal implementation**

```python
lines.extend(["", "## Milestone Card", ""])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_milestone_card -v`
Expected: PASS with the milestone card section present.

- [ ] **Step 5: Commit**

```bash
git add src/compute_aware_cascade.py tests/test_compute_aware_cascade.py
git commit -m "feat: add cascade benchmark milestone card outputs"
```

### Task 3: Refresh generated artifacts and docs

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`
- Modify: `REPORT.md`
- Modify: `results/figures/cascade_benchmark_handoff_packet.md`
- Create: `results/figures/cascade_benchmark_milestone_card.md`
- Create: `results/tables/cascade_benchmark_milestone_card.csv`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Rebuild generated outputs**

Run: `python3 -m src.compute_aware_cascade --dataset synthetic_split`
Expected: Writes the new benchmark milestone card artifacts and refreshed packet output.

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
Expected: PASS with the new milestone-card coverage included.

- [ ] **Step 3: Update docs**

```markdown
- `results/figures/cascade_benchmark_milestone_card.md` now shows the next milestone, what the first step unlocks, and how many phases remain.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md REPORT.md results/figures/cascade_benchmark_milestone_card.md results/figures/cascade_benchmark_handoff_packet.md results/tables/cascade_benchmark_milestone_card.csv
git commit -m "docs: publish cascade benchmark milestone card"
```
