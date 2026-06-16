# Implementation Status

This file answers a narrow question: what is implemented on `main`, what is
experimental, what is optional, and what is historical.

## Status Label Definition

| Label | Meaning |
|---|---|
| Stable Mainline | Main branch capability with code, test, and result evidence |
| Mainline Experimental | Merged into main but still experimental or evaluation-limited |
| Frontier Scaffold | Exploratory scaffolding, not a stable mainline claim |
| Optional Integration | Requires optional dependencies, external tools, models, or APIs |
| Historical | Kept for traceability, not a primary entry |
| Needs Verification | Evidence is incomplete or requires maintainer confirmation |
| Frontier Branch Only | Exists outside main or requires separate branch review |

## Mainline Capability Matrix

| Area | Status | Evidence Path | Notes |
|---|---|---|---|
| Gold cases | Stable Mainline | `references/`, `resources/mixed_audio/`, `resources/separated_audio/` | Five verified cases are the gold benchmark scope |
| Mixed/separated Whisper | Stable Mainline | `src/transcribe_whisper.py`, `results/transcripts_*`, `results/figures/curated/current_results_summary.md` | Uses existing mixed and separated audio paths |
| CER | Stable Mainline | `src/evaluate_cer.py`, `results/tables/`, `results/figures/curated/current_results_summary.md` | Gold CER is the core metric family |
| Error type analysis | Stable Mainline | `src/evaluate_error_types.py`, `results/error_analysis/`, `results/figures/curated/error_type_summary.md` | Explains insertion/repetition-heavy failure modes |
| Speaker CER | Stable Mainline | `src/evaluate_speaker_cer.py`, `results/figures/curated/speaker_cer_summary.md` | Speaker-aware text evaluation |
| cpCER-lite | Stable Mainline | `src/evaluate_cpcer_lite.py`, `results/figures/curated/cpcer_lite_summary.md` | Lightweight permutation-aware speaker check |
| Router v1/v2 | Mainline Experimental | `src/adaptive_router.py`, `src/adaptive_router_v2.py`, `results/figures/curated/best_method_by_case.md` | Reference-free selection; CER is post-decision evaluation only |
| Risk-aware selector | Mainline Experimental | `src/risk_aware_selector.py`, `results/figures/curated/risk_aware_selection_summary.md` | Deployability/explainability layer, not necessarily best-CER |
| Compute-aware cascade | Mainline Experimental | `src/compute_aware_cascade.py`, `results/figures/curated/compute_aware_cascade_summary.md` | Cost analysis layer with experimental/frontier labeling |
| Cascade tiers / Mode B | Mainline Experimental | `src/cascade_tiers.py`, `tests/test_cascade_tiers.py`, `results/figures/curated/cascade_tiers_summary.md` | Merged to `main`, but its own result files label it experimental/frontier and include modeled stronger routes |
| Synthetic silver validation | Mainline Experimental | `src/evaluate_synthetic_benchmark.py`, `src/evaluate_synthetic_routing.py`, `results/figures/curated/synthetic_routing_summary.md` | Silver/synthetic evidence only, not gold benchmark evidence |
| MeetEval | Optional Integration | `requirements-frontier.txt`, `src/meeteval_*`, `results/figures/curated/meeteval_readiness.md` | Requires optional MeetEval dependency for official paths |
| LLM critic / LLM scaffolding | Optional Integration / Frontier Scaffold | `requirements-optional.txt`, `src/llm_critic_review_pass.py`, `src/llm_repair_loop.py`, `src/rag_repair.py` | Optional API/SDK paths; not the core quantitative claim |
| Speaker-profile scaffolding | Frontier Scaffold | `src/speaker_profile_*`, `results/figures/curated/speaker_profile_audio_proxy_summary.md` | Exploratory support and diagnostics |
| AudioDepth router | Frontier Branch Only / Exploratory Research | `frontier/audio-depth-router`, `docs/frontier/audio-depth-router.md` | Not merged into `main`; needs separate review before merge; large artifacts must not enter main directly |
| Harness | Stable Mainline | `docs/harness/`, `.githooks/`, `scripts/harness/`, `.github/workflows/contract-guard.yml` | Development governance and quality gates |
| ADR | Stable Mainline | `docs/adr/README.md`, `docs/adr/ADR-001-harness-adoption.md` | Decision records for governance |
| CI / tests | Stable Mainline | `.github/workflows/test.yml`, `tests/`, `src/project_harness.py` | Full tests require installed dependencies |

## Claim Boundaries

- Silver validation must not be described as gold benchmark evidence.
- Frontier queues, receipts, writebacks, and coordination targets are not final
  benchmark claims.
- `frontier/audio-depth-router` is a high-risk exploratory research branch, not
  a mainline capability. It may be split and reviewed later, but large
  artifacts, bulk `.npy` / `.png` outputs, model weights, and unverified claims
  must not be merged directly into `main`.
- The mainline research pipeline is comparatively complete, but this does not
  mean every optional or frontier scaffold is production-ready.
