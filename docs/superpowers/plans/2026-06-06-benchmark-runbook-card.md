# Benchmark Runbook Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a benchmark runbook card artifact that condenses the benchmark handoff stack into a one-page execution card.

**Architecture:** Keep the blocker matrix, execution queue, and session ledger as source layers, then derive a short runbook card that names the first step, why it is first, what evidence must be captured, and what it unlocks next. Keep it as generated markdown plus a tiny CSV row so contributors can consume it both as prose and as structured data.

**Tech Stack:** Python, `unittest`, CSV/JSON/Markdown artifact generation

---

### Task 1: Add runbook-card failing tests

**Files:**
- Modify: `tests/test_compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_runbook_card_rows_summarize_first_action(self) -> None:
    rows = build_benchmark_runbook_card_rows(
        [{"plan_step_id": "phase1_gold_runtime_foundation"}],
        [{"plan_step_id": "phase1_gold_runtime_foundation"}],
        [{"plan_step_id": "phase1_gold_runtime_foundation"}],
    )
    self.assertEqual(rows[0]["recommended_start_step"], "phase1_gold_runtime_foundation")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_runbook_card_rows_summarize_first_action -v`
Expected: FAIL with `ImportError` or `NameError` because `build_benchmark_runbook_card_rows` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
def build_benchmark_runbook_card_rows(
    blocker_rows: list[dict[str, Any]],
    queue_rows: list[dict[str, Any]],
    ledger_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_runbook_card_rows_summarize_first_action -v`
Expected: PASS after the real card logic is implemented.

- [ ] **Step 5: Commit**

```bash
git add tests/test_compute_aware_cascade.py src/compute_aware_cascade.py
git commit -m "feat: summarize cascade benchmark runbook card"
```

### Task 2: Wire runbook-card outputs into artifacts and packet

**Files:**
- Modify: `src/compute_aware_cascade.py`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_benchmark_packet_lines_include_runbook_card(self) -> None:
    lines = build_benchmark_packet_lines([], [], [], [], [], [], [], [], [], [], [
        {"recommended_start_step": "phase1_gold_runtime_foundation"}
    ])
    self.assertIn("## Runbook Card", "\n".join(lines))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_runbook_card -v`
Expected: FAIL because the handoff packet does not render the runbook card section yet.

- [ ] **Step 3: Write minimal implementation**

```python
lines.extend(["", "## Runbook Card", ""])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest tests.test_compute_aware_cascade.ComputeAwareCascadeTest.test_build_benchmark_packet_lines_include_runbook_card -v`
Expected: PASS with the runbook card section present.

- [ ] **Step 5: Commit**

```bash
git add src/compute_aware_cascade.py tests/test_compute_aware_cascade.py
git commit -m "feat: add cascade benchmark runbook card outputs"
```

### Task 3: Refresh generated artifacts and docs

**Files:**
- Modify: `README.md`
- Modify: `docs/project_state.md`
- Modify: `docs/roadmap.md`
- Modify: `REPORT.md`
- Modify: `results/figures/cascade_benchmark_handoff_packet.md`
- Create: `results/figures/cascade_benchmark_runbook_card.md`
- Create: `results/tables/cascade_benchmark_runbook_card.csv`
- Test: `tests/test_compute_aware_cascade.py`

- [ ] **Step 1: Rebuild generated outputs**

Run: `python3 -m src.compute_aware_cascade --dataset synthetic_split`
Expected: Writes the new benchmark runbook card artifacts and refreshed packet output.

- [ ] **Step 2: Run focused verification**

Run: `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
Expected: PASS with the new runbook-card coverage included.

- [ ] **Step 3: Update docs**

```markdown
- `results/figures/cascade_benchmark_runbook_card.md` now gives the first-step action, required evidence, and next unlock as a one-page execution card.
```

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project_state.md docs/roadmap.md REPORT.md results/figures/cascade_benchmark_runbook_card.md results/figures/cascade_benchmark_handoff_packet.md results/tables/cascade_benchmark_runbook_card.csv
git commit -m "docs: publish cascade benchmark runbook card"
```
