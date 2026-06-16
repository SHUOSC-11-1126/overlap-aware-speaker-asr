# Harness entry points for overlap-aware-speaker-asr.
#
# This is the npm-scripts analogue for a repo without npm: a single ergonomic
# surface over scripts/harness/*. The git hooks call scripts/harness/quality.py
# directly (no make dependency on the critical path); this Makefile is for
# humans and agents.
#
# Pillars: Git hooks (hooks-install), knowledge base + contract
# (contract-*), SDD (PR template + authority-doc contract), TDD (paired-test
# gate inside the contract + quality-precommit test run).

PYTHON ?= python3

.PHONY: help hooks-install agent-bootstrap quality-predev quality-precommit \
        quality-ci quality-local contract-local contract-check \
        contract-gitnexus test harness-smoke entropy-audit

help:
	@echo "Harness targets:"
	@echo "  make agent-bootstrap   install hooks + print the agent workflow"
	@echo "  make quality-predev    bootstrap + GitNexus index + contract (advisory)"
	@echo "  make quality-precommit fast gate: full unittest suite (pre-commit hook)"
	@echo "  make quality-local     pre-push gate: contract + full test suite (pre-push hook)"
	@echo "  make quality-ci        CI gate: tests + project_harness smoke"
	@echo "  make contract-local    GitNexus index refresh + contract (working tree)"
	@echo "  make contract-gitnexus GitNexus index refresh + contract (CI / PR base)"
	@echo "  make test              run the unittest suite"
	@echo "  make harness-smoke     run python -m src.project_harness"
	@echo "  make entropy-audit     run the agentic-research-entropy audit (analysis-only)"

hooks-install:
	$(PYTHON) scripts/harness/install_hooks.py

agent-bootstrap:
	$(PYTHON) scripts/harness/contract_check.py bootstrap

quality-predev:
	$(PYTHON) scripts/harness/quality.py predev

quality-precommit:
	$(PYTHON) scripts/harness/quality.py precommit

quality-ci:
	$(PYTHON) scripts/harness/quality.py ci

quality-local:
	$(PYTHON) scripts/harness/quality.py local

contract-local:
	$(PYTHON) scripts/harness/contract_check.py local

contract-check:
	$(PYTHON) scripts/harness/contract_check.py check

contract-gitnexus:
	$(PYTHON) scripts/harness/contract_check.py gitnexus

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py'

harness-smoke:
	$(PYTHON) -m src.project_harness

entropy-audit:
	@PY=$$( [ -x .venv/bin/python3 ] && echo .venv/bin/python3 || echo $(PYTHON) ); \
	echo "Running research-entropy audit with $$PY"; \
	$$PY -m src.research_entropy_audit
