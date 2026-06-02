# WUFANGZHOU Handoff

## 1. Current Status

Core technical pipeline is complete. The project is ready for final packaging, demo, report polishing, and optional future extensions.

## 2. What Has Been Completed

- Gold benchmark
- ASR baselines
- CER evaluation
- error type analysis
- adaptive router v1/v2
- synthetic silver validation
- held-out split
- cpCER-lite
- risk-aware selector
- documentation alignment
- project maintenance harness

## 3. What WUFANGZHOU Will No Longer Guarantee

- No guarantee of future code review.
- No guarantee of checking future result correctness.
- No guarantee of approving new algorithm additions.
- Future maintainers must read AGENTS.md, docs/project_state.md, docs/roadmap.md, and docs/maintenance_harness.md before modifying the project.

## 4. Recommended Ownership for Remaining Team

- Report owner
- README / reproducibility owner
- Streamlit demo owner
- Literature / external benchmark owner
- Presentation / video owner
- Final submission owner

## 5. Immediate Next Tasks

- Finalize REPORT.md
- Polish README.md
- Build demo/app.py
- Prepare English video script
- Fill contribution percentages
- Prepare final submission folder

## 6. Do Not Do

- Do not mix synthetic silver with gold evaluation.
- Do not tune router on held-out test and claim it is clean.
- Do not use CER/reference as routing input.
- Do not overwrite verified references.
- Do not add new modules without a clear research question and owner.
