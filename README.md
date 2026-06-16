# Overlap-Aware Speaker ASR

## Project in One Sentence

This repository studies when speech separation helps or hurts multi-speaker ASR, and provides a documented research pipeline for adaptive routing, speaker-aware evaluation, and carefully labeled frontier experiments.

## What This Project Does

- Maintains a five-case gold benchmark for overlap-aware ASR evaluation.
- Compares mixed Whisper, separated speaker-track Whisper, and cleaned separated transcripts.
- Reports CER, error-type analysis, speaker CER, and cpCER-lite style speaker attribution checks.
- Provides adaptive router v1/v2 and a risk-aware selector for reference-free transcript choice.
- Includes compute-aware cascade analysis and Mode B cascade tiers as mainline experimental work.
- Keeps synthetic silver validation separate from gold benchmark claims.
- Provides optional scaffolding for MeetEval, LLM critic/repair, speaker-profile work, and demo support.
- Uses CI, tests, ADRs, and a harness workflow to protect the stable baseline.

## What This Project Does Not Claim

- It does not claim to train a new ASR foundation model.
- It does not claim to train a new speech separation model.
- It does not treat synthetic silver validation as gold benchmark evidence.
- It does not use ground-truth CER as a routing input.
- It does not treat frontier scaffolding, coordination records, receipts, or writebacks as stable mainline claims.
- It does not claim that `frontier/audio-depth-router` is ready to merge directly into `main`.

## Current Status

See [docs/implementation-status.md](docs/implementation-status.md) for the detailed status matrix.

| Area | Status |
|---|---|
| Gold benchmark, Whisper baselines, CER/error/speaker-aware evaluation | Stable Mainline |
| Router v1/v2, risk-aware selector, compute-aware cascade | Mainline Experimental |
| Mode B / cascade tiers | Mainline Experimental |
| Synthetic validation | Mainline Experimental; silver evidence only |
| MeetEval, LLM, speaker-profile, demo support | Optional Integration / Frontier Scaffold |
| AudioDepth router | Frontier Branch Only |

## Quickstart

Use a Python version aligned with CI, preferably Python 3.12. The core install is:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m src.project_harness
```

If you see `ModuleNotFoundError: No module named 'yaml'`, install the core requirements first; it is usually an environment setup issue, not evidence that the project code is broken.

Full setup, optional dependencies, smoke tests, demo setup, and troubleshooting are in [docs/quickstart.md](docs/quickstart.md).

## Results

Start with [docs/results-index.md](docs/results-index.md) and [results/README.md](results/README.md).

Recommended result entry points:

- [Current results summary](results/figures/curated/current_results_summary.md)
- [Adaptive routing summary](results/figures/curated/best_method_by_case.md)
- [Risk-aware selector summary](results/figures/curated/risk_aware_selection_summary.md)
- [Compute-aware cascade summary](results/figures/curated/compute_aware_cascade_summary.md)
- [Mode B cascade tiers summary](results/figures/curated/cascade_tiers_summary.md)

Historical wave, receipt, writeback, checklist, and demo presentation records have been moved under `results/figures/archive/`. They are useful for traceability, but they are not final benchmark claims.

## Repository Map

| Path | Purpose |
|---|---|
| `src/` | Research scripts, evaluation modules, routing logic, and generated frontier helpers |
| `tests/` | Unit tests and harness coverage |
| `docs/` | Curated setup, status, result, branch, governance, and archive documentation |
| `docs/harness/` | Development harness: hooks, knowledge-base contract, SDD, and TDD workflow |
| `docs/adr/` | Architecture and approach decision records |
| `resources/` | Small audio inputs, snippets, synthetic assets, and references |
| `results/` | Curated result summaries plus archived generated records |
| `scripts/` | Harness and maintenance support scripts |

## Mainline vs Frontier

- `main` is the stable review baseline.
- `frontier/audio-depth-router` is a high-risk experimental branch with many artifacts and model-like outputs; it needs separate review and should be split before any merge.
- `wave*`, `frontier/wave*`, and `demo-wave*` branches are mostly historical coordination/writeback trails.
- `improve/*` and `cursor/*` branches with no diff against `main` are cleanup candidates, but this pass does not delete remote branches.

See [docs/branch-audit.md](docs/branch-audit.md) for the branch cleanup policy.

## Documentation

| Need | Read |
|---|---|
| Run locally | [docs/quickstart.md](docs/quickstart.md) |
| Understand what is implemented | [docs/implementation-status.md](docs/implementation-status.md) |
| Find core results | [docs/results-index.md](docs/results-index.md) |
| Understand result storage | [results/README.md](results/README.md) |
| Understand branch status | [docs/branch-audit.md](docs/branch-audit.md) |
| Understand archive policy | [docs/archive-plan.md](docs/archive-plan.md) |
| Review course contribution records | [docs/contributions/README.md](docs/contributions/README.md) |
| Review AudioDepth frontier strategy | [docs/frontier/audio-depth-router.md](docs/frontier/audio-depth-router.md) |
| Review governance | [docs/harness/](docs/harness/) and [docs/adr/](docs/adr/) |

Historical planning and generated coordination records are indexed from [docs/archive/README.md](docs/archive/README.md).

## Development Governance

The repository uses a lightweight harness inspired by code-tape:

- [Harness overview](docs/harness/README.md)
- [Knowledge-base contract](docs/harness/knowledge_base_contract.md)
- [SDD policy](docs/harness/sdd.md)
- [TDD policy](docs/harness/tdd.md)
- [ADR index](docs/adr/README.md)

## Contributors

Contributor details live in [CONTRIBUTIONS.md](CONTRIBUTIONS.md). The README intentionally keeps contributor history short so the project entry point remains readable.

- [Contribution Records](docs/contributions/README.md): course submission contribution statements and team contribution evidence.

## License / Citation / Acknowledgements

TODO: Maintainers should decide the final License, Citation, and Acknowledgements text. This cleanup does not invent licensing or citation claims.
