# Agent Operating Charter

## Mission

This repository is now an ambitious agentic research workspace. The stable baseline is complete, and future agents are encouraged to explore challenging extensions, new pipelines, new evaluations, and high-risk/high-reward ideas.

The stable baseline should remain preserved, but future work should not be reduced to maintenance only. The project is designed to support creative, boundary-pushing experimentation within clear research boundaries.

## Stable Baseline vs Experimental Frontier

### Stable baseline

- 5 gold benchmark cases
- verified references
- mixed / separated / cleaned ASR
- CER evaluation
- error analysis
- router v1 / v2
- speaker-aware CER
- cpCER-lite
- synthetic validation
- risk-aware selector

### Experimental frontier

- separation phase diagram
- compute-aware cascaded recognition
- speaker profile / voiceprint learning
- external benchmark mini validation
- MeetEval / cpWER compatibility
- local Ollama / LLM correction and critic agent
- multi-agent ASR critic / repair loop
- self-evaluating transcript agent
- active learning / uncertainty-driven manual review
- stronger ASR model comparison
- demo / visualization / GitHub presentation polish

## New Rule Philosophy

Protect stable results, expand through new branches.

Preserve:

- Do not overwrite verified references.
- Do not use ground-truth CER as deployable routing input.
- Do not mix gold and synthetic results without labeling.
- Do not silently overwrite result tables.
- Do not claim silver results as gold.

Encourage:

- Add bold experimental modules when they answer a clear research question.
- Run stronger models if runtime and hardware are documented.
- Add external datasets if licensing and source are documented.
- Use LLM/agentic workflows if outputs are clearly marked as qualitative unless evaluated.
- Create new experimental result directories rather than modifying stable outputs.

## Result Labels

Every experiment or output should be labeled as one of:

- stable/gold
- synthetic/silver
- experimental/frontier
- qualitative/demo
- external/sanity-check
- oracle/analysis-only

## Agent Challenge Modes

Future agents are encouraged to choose an explicit mode and mention it in the commit message or the relevant docs.

### Mode A: Conservative Reproduction

- Reproduce existing results

### Mode B: Focused Extension

- Add one clear module

### Mode C: Frontier Exploration

- Try a risky/high-reward research direction

### Mode D: Presentation / Productization

- Improve demo, README, visualization, video

## Hard Safety Rules

- Do not overwrite verified references unless explicitly requested.
- Do not treat synthetic silver as gold evaluation.
- Do not use CER/reference as routing input.
- Do not mix experimental outputs into stable result tables without a clear label.
- Do not add heavyweight modules without a stated research question, owner, and output path.

## Documentation Discipline

The project should keep its baseline stable, but the docs should continuously point future agents toward the most ambitious useful next step.

Recommended docs to read before making a new proposal:

- `docs/project_state.md`
- `docs/roadmap.md`
- `docs/maintenance_harness.md`
- `docs/README.md`
- `docs/ambitious_research_agenda.md`
- `docs/agent_challenge_board.md`
