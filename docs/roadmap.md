# Roadmap

## Current Status

The core experimental pipeline is complete. The repository now has a compact research story centered on adaptive routing, speaker-aware evaluation, and robustness checks.

## What Is Already Done

- Gold benchmark and references
- ASR baselines
- Post-processing
- Evaluation
- Adaptive routing
- Synthetic validation
- Risk-aware selection
- Context and maintenance docs

## What Should Not Be Expanded Further

- Do not add new ASR models without a clear research need.
- Do not rerun gold results casually.
- Do not turn LLM/RAG into the central quantitative line again.
- Do not keep stacking more side branches that do not answer the core question.
- Do not present synthetic silver results as gold.

## Recommended Next Work

### A. Final REPORT.md and README.md

Make the paper-style report and repository entry point fully polished.

### B. Streamlit Demo

Build a lightweight demo that shows mixed vs separated vs cleaned vs router decisions.

### C. Presentation / Video Script

Prepare a concise talk track that explains the problem, method, and findings.

### D. Separation Phase Diagram

Quantify when separation helps across overlap ratios.

### E. Compute-aware Cascade

Turn the routing idea into an accuracy-cost policy.

### F. Speaker Profile / Voiceprint Exploration

Explore light enrollment signals for attribution risk detection.

### G. External Mini Validation / MeetEval Compatibility Discussion

Discuss compatibility with meeting transcription evaluation conventions.

## Suggested Team Ownership

- Technical lead: existing core pipeline owner
- Report owner: documentation lead
- README / reproducibility owner: maintenance lead
- Demo owner: interface / UX lead
- Literature / external benchmark owner: evaluation lead
- Presentation / video owner: communication lead

