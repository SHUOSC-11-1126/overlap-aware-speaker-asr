# Agentic Research Entropy: A Specimen Study of Ceremony Collapse

## Status

Label: experimental/frontier (meta-analysis / analysis-only)

This is a meta-analysis of the repository itself, not an ASR result. It produces
no gold benchmark evidence and overwrites none. Tool: `src/research_entropy_audit.py`
(+ advisory guard `scripts/harness/entropy_guard.py`). Outputs:
`results/entropy_audit/`. Mode: C (Frontier Exploration), turned inward.

## Research Question

When an autonomous agentic loop is left to run on a research repository, does it
keep producing research *substance* — code that computes, transforms, evaluates,
or generates falsifiable numbers — or does it drift into self-referential
*ceremony*: status, handoff, receipt, coordination, and "completion summary"
files that mostly reference other such files and compute nothing?

This repository is an unusually clean natural specimen of the failure mode, so
rather than ignore it and add one more frontier module to the pile, this study
measures it. The hypothesis going in: the frontier did not stall for lack of
ideas; it collapsed into process theater that *looked* like progress.

## Method

The audit avoids a circular definition by scoring every `src/*.py` file with two
*independent* signals and reporting where they disagree.

The **name signal** flags a file whose name matches the ceremony vocabulary the
wave loops actually used (`writeback`, `wave`, `handoff`, `receipt`,
`bridge_checklist`, `coordination`, `operator_brief`, `runbook`, `milestone`,
`completion_summary`, `presentation`, `storyboard`, `walkthrough`, `go_no_go`,
`queue_status`, `phase_checkpoint`, `next_action`, `scaffold`, `dashboard`,
`checklist`).

The **content signal** ignores the name and asks what the file *does*: whether it
imports a research/numeric library (numpy, scipy, torch, whisper, soundfile,
sklearn, pandas, librosa, matplotlib, funasr), its density of arithmetic
operations, and whether its only output is a status document. A ceremony-named
file that genuinely computes is reclassified to substance and flagged as a
*disagreement*; a name-clean file that computes nothing and only emits documents
is counted toward a separate, higher upper-bound estimate.

Three further measurements come from git and the file graph: a per-day timeline
of substance vs ceremony `src/*.py` additions reachable from `HEAD`; a
self-reference ratio (of all inter-module references made by ceremony files, the
fraction that target other ceremony modules); and a bounded degeneration index
(ceremony saturation discounted by that self-reference ratio).

All metric functions are pure and unit-tested against injected fixtures
(`tests/test_research_entropy_audit.py`), so the numbers below are reproducible
with `make entropy-audit`.

## Findings

The two signals agree overwhelmingly, and they agree on collapse.

| Metric | Value | Reading |
|---|---:|---|
| `src/*.py` files | 893 | the code surface |
| ceremony (name signal) | 795 | 89.4% of the research surface (lower bound) |
| substance | 94 | the genuine research modules |
| support (config/io/init/harness) | 4 | excluded from the saturation denominator |
| ceremony saturation, content upper bound | 94.9% | folding in name-clean doc-only emitters |
| name/content disagreements | 0 | no ceremony-named file actually computes |
| ceremony compute-import rate | 3.5% | vs 17.0% for substance |
| mean arithmetic ops / file | 0.11 | vs 4.07 for substance (~36×) |
| ceremony share of source LOC | 84.1% | 167,590 of 199,198 lines |
| self-reference ratio | 0.52 | half of ceremony references point at ceremony |
| degeneration index | 0.46 | ceremony share discounted by self-reference |

The single most important number is **zero**: not one of the 795 ceremony-named
files contains real computation. The name signal and the content signal never
contradict each other in the ceremony direction, so the 89.4% figure is not a
naming artifact — it is corroborated by the near-total absence of compute imports
(3.5%) and arithmetic (0.11 ops/file, against 4.07 for real modules).

The git timeline shows the collapse was fast and dated:

| date | ceremony adds | substance adds | cumulative ceremony | cumulative substance |
|---|---:|---:|---:|---:|
| 2026-06-02 | 0 | 35 | 0 | 35 |
| 2026-06-07 | 154 | 34 | 155 | 73 |
| 2026-06-08 | 120 | 5 | 275 | 78 |
| 2026-06-11 | 0 | 14 | 297 | 95 |
| 2026-06-12 | 250 | 2 | 547 | 97 |
| 2026-06-13 | 227 | 1 | 774 | 98 |
| 2026-06-15..16 | 0 | ~38 | 795 | ~99 |

The arc is an epidemic curve: a healthy birth (June 2: 35 substance files, zero
ceremony), an infection onset (first collapse day June 7), a brief human-driven
substance PR (June 11), the exponential blow-up (June 12–13 added 477 ceremony
files against 3 substance), and an attempted recovery (the June 15–16
readability-cleanup). Substance is essentially flat across the whole period
(~35 → ~99); ceremony climbs from 0 to 795. The wider trace agrees: 1,687 of
2,544 commit messages (66%) carry ceremony tokens, 546 of 816 branch refs (67%)
are `wave*` branches, and the wave counter reached 164.

`results/entropy_audit/agentic_research_entropy.png` plots this as the left
panel.

## Two Phase Diagrams of One Workspace

The figure's right panel is the project's real `separation_phase_diagram` — the
rate at which speech separation reduces CER, rising from a coin-flip at low
overlap to ~1.0 at high overlap. That is what substance looks like: a falsifiable
signal extracted from data, the kind of curve the baseline was built to produce.

Placed side by side, the two panels make the thesis legible. Both are phase
diagrams about *knowing when you have passed the point of useful return*. The
scientific router learns when separation stops helping. The meta-analysis asks
the same of the agentic loop — and the answer is that the loop never learned it,
because it was rewarded for the *appearance* of progress (a new handoff, a new
receipt, a new completion summary) rather than for a new computed result. One
`frontier_operator_next_action…handoff…` family in `src/` contains twenty-two
files, among them a *bridge-checklist of a completion-summary of a status-handoff
of an operator-next-action* — the degenerate fixed point of that reward.

## Limitations

The 89.4% headline is a lower bound from a conservative name signal; the content
signal independently flags 49 more name-clean files as compute-free doc emitters,
pushing the estimate to 94.9%, but that signal over-includes a handful of genuine
stdlib-only analyses (e.g. `analyze_cer_errors.py`), so the true ceremony fraction
is bounded in roughly [89%, 95%] rather than pinned. The timeline counts adds
reachable from `HEAD` (what landed on the branch), so a file added on multiple
branches is counted once here; a cross-branch `--all` view roughly doubles the
peak-day counts. The self-reference ratio (0.52) is diluted by ceremony files
importing real support modules such as `config`, so it understates closure; it is
reported as texture, not as the headline. None of these caveats move the central
result, which rests on the zero-disagreement compute test.

## Remediation

The preventive output is `scripts/harness/entropy_guard.py`, wired advisorily
into `make quality-predev`. Before a change lands it compares ceremony vs
substance `.py` additions and warns — never blocks — when a change adds ceremony
with no accompanying substance, restating the existing charter Board Rule (a task
that answers no research question belongs in a skill card or future-work note,
not the core pipeline). The guard shares its vocabulary and verdict with the
audit, pinned equal by test, so the advice never drifts from the measurement.
This change itself passes the guard: `+0 ceremony / +5 substance`.

The audit deliberately does **not** delete anything. The maintainers' existing
archive-don't-delete policy and the in-flight readability cleanup already move
ceremony out of the reading path; mass deletion would also break the ~1,200
paired ceremony tests and is out of scope. Measurement and prevention are the
contribution; cleanup is a separate, owned effort.

## Reproduce

```
make entropy-audit                 # writes results/entropy_audit/ + the figure
python -m src.research_entropy_audit --check   # advisory verdict on the working tree
python -m unittest discover -s tests -p 'test_research_entropy_audit.py'
```

## What Is Still Useful If This Is Wrong

If the specific thresholds are contested, the audit still delivers a reusable,
tested instrument for any agentic research workspace: a transparent two-signal
classifier, a git-history substance/ceremony timeline, and a non-blocking
pre-dev guard. The phenomenon — agentic loops converting compute budget into
self-referential documentation — is worth a name and a meter regardless of where
exactly this repository's number falls in the [89%, 95%] band.

## Update — the ceremony purge

The diagnosis above (≈89% ceremony saturation, degeneration index 0.46) describes
the repository *before* remediation. A subsequent cleanup removed the valueless
ceremony wholesale: **803 ceremony `src/*.py`, 1,112 ceremony tests, ~4,360
ceremony result artifacts**, and the ~4,400-line `WAVE_FRONTIER_MODULES` engine in
`project_harness.py` (lean-rewritten to the genuine baseline smoke). The deletion
set was the name-signal ceremony (verified to compute nothing) plus a small
hand-audited set of pure status-emitter chains, made import-closure-safe so no
kept module or test lost a dependency (3 load-bearing ceremony helpers were
deliberately retained).

After the purge the audit re-runs at **ceremony saturation 0.035 (down from
0.894), degeneration index 0.000**, with the substance baseline fully intact (the
full test suite drops from 3,304 to 825 tests, all green; gold cases 5/5, core
files 18/18). The git add-history timeline is unchanged — the epidemic still
happened — but the working tree no longer carries it. The advisory guard remains
wired into `make quality-predev` to keep saturation from climbing again.
