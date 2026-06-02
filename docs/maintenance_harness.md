# Maintenance Harness

This document explains how to keep the project maintainable and prevent it from bloating into an unfocused research pile.

## Result Hierarchy

1. Gold results
2. Synthetic silver results
3. Held-out synthetic split
4. Optional future experiments

## Before Adding a New Module, Answer:

- What research question does it answer?
- Which existing limitation does it address?
- What files will it read?
- What files will it write?
- Will it modify gold results?
- Is it reproducible?
- Who owns it?

## Naming Conventions

- Scripts in `src/`
- Result tables in `results/tables/`
- Figures in `results/figures/`
- Docs in `docs/`
- Skills in `docs/skills/`
- Experimental audio in `resources/`

## Reproducibility Policy

- Do not overwrite verified references.
- Do not overwrite gold results unless explicitly rerunning a documented stage.
- Prefer versioned outputs for new experimental branches.
- Keep synthetic silver separate from gold.

## Recommended Command Discipline

```powershell
python -m src.adaptive_router_v2
python -m src.evaluate_error_types --case all
python -m src.evaluate_speaker_cer --case all
python -m src.evaluate_cpcer_lite --case all
python -m src.risk_aware_selector --case all
python -m src.router_ablation
python -m src.router_ablation_split
```

## Maintenance Goal

The project should remain:

- understandable
- reproducible
- extendable by multiple people
- resistant to scope creep

