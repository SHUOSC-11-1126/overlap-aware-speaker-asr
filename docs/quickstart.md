# Quickstart

This file explains how to set up the mainline project locally without running
large training jobs, downloading unnecessary models, or calling external APIs.

## Recommended Python

Use Python 3.12 when possible, matching the CI configuration in
`.github/workflows/test.yml`.

Avoid using a system default Python 3.14 as the first attempt for full test
runs. It may work in some environments, but it is not the documented baseline
for this repository.

## Core Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Core dependencies are listed in `requirements.txt`:

| Dependency | Why it is core |
|---|---|
| `PyYAML` | Loads project configuration |
| `numpy`, `scipy`, `soundfile` | Audio and numeric utilities |
| `matplotlib` | Result plotting |
| `openai-whisper` | Whisper ASR path |

## Optional Dependency Layers

Install these only when you need the matching path:

```bash
pip install -r requirements-demo.txt       # Streamlit demo
pip install -r requirements-frontier.txt   # MeetEval / frontier experiments
pip install -r requirements-optional.txt   # Optional integrations such as OpenAI SDK
```

Optional dependencies should not block the mainline smoke test.

## Minimal Smoke Test

After installing `requirements.txt`, run:

```bash
python -m src.project_harness
```

This is the preferred first check for documentation cleanup and onboarding. It
does not train models, call external APIs, or run the full test suite.

## Full Test Suite

The full unit suite is:

```bash
python -m unittest discover -s tests -p 'test_*.py' -q
```

Run it after the core environment is installed. This cleanup pass does not
require running the full suite because it reorganizes documentation and
historical Markdown artifacts rather than changing algorithm code.

## Core Result Reproduction

Start from these commands only after the environment is ready:

```bash
python -m src.evaluate_cer --case all
python -m src.adaptive_router_v2
python -m src.risk_aware_selector --case all
python -m src.compute_aware_cascade
python -m src.cascade_tiers
python -m src.project_harness
```

For the full result map, use [results-index.md](results-index.md) rather than
treating every file under `results/figures/` as a required reading or execution
step.

## Demo

The demo path is optional:

```bash
pip install -r requirements-demo.txt
streamlit run demo/app.py
```

The demo is qualitative/demo support. It should not be treated as a live ASR
benchmark claim.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'yaml'` | Core dependencies were not installed | Run `pip install -r requirements.txt` inside the virtual environment |
| Whisper downloads a model on first use | Normal Whisper behavior | Use smoke tests first if you want to avoid model downloads |
| MeetEval import fails | Frontier dependency not installed | Run `pip install -r requirements-frontier.txt` only if you need MeetEval paths |
| OpenAI SDK import fails | Optional integration dependency not installed | Run `pip install -r requirements-optional.txt` only if you need LLM integrations |
| Streamlit command is missing | Demo dependency not installed | Run `pip install -r requirements-demo.txt` |

Do not interpret missing optional dependencies as evidence that the stable
mainline ASR analysis is broken.
