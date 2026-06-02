# Roadmap

## Current Status

The core technical work is mostly complete. The repository now has a coherent research story centered on adaptive routing, speaker-aware evaluation, and robustness checks.

## What Is Already Done

- Gold benchmark and references
- ASR baselines
- Post-processing
- Evaluation
- Adaptive routing
- Synthetic validation
- Risk-aware selection
- Context and maintenance docs
- Docs index and markdown audit

## What Should Not Be Expanded Further

- Do not add new ASR models without a clear research need.
- Do not rerun gold results casually.
- Do not turn LLM/RAG into the central quantitative line again.
- Do not keep stacking side branches that do not answer the core question.
- Do not present synthetic silver results as gold.

## Recommended Next Work

1. Final `REPORT.md`
2. Final `README.md`
3. Streamlit demo
4. Presentation / video script
5. Contribution / maintenance polish
6. Separation phase diagram
7. Compute-aware cascade
8. Speaker profile / voiceprint exploration
9. MeetEval compatibility discussion
10. External mini validation

## Suggested Team Ownership

- Technical lead: existing core pipeline owner
- Report owner: documentation lead
- README / reproducibility owner: maintenance lead
- Demo owner: interface / UX lead
- Literature / external benchmark owner: evaluation lead
- Presentation / video owner: communication lead

## Maintenance Principle

Any new module should first be framed as a research question, a scope boundary, and a reproducible output plan. If it does not answer a clear question, it should stay out of the core pipeline and move into a skill card or future work note.
