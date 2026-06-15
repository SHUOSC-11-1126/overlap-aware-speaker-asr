"""GitNexus knowledge-base contract rules for overlap-aware-speaker-asr.

This is a Python port of code-tape's ``scripts/workflows/contract-rules.mjs``,
re-targeted at this repository's stable-baseline surfaces. It is intentionally
stdlib-only so it can run inside a git hook under any ``python3`` (>=3.8),
without activating the project virtualenv or importing the research ``src``
package.

The contract encodes three of the four Harness pillars:

* knowledge base -- the critical-skeleton classification mirrors the
  GitNexus "cascade reaction" surfaces that must be reasoned about before edit;
* TDD -- touching a critical *code* module requires its paired test in the
  same change (red->green->refactor, enforced mechanically);
* SDD -- touching authority specs / verified references / gold results
  requires a structured impact summary (and, for research artefacts, an
  explicit result label drawn from the project charter).

The "engineering camp" scoring / auto-merge / progress machinery from
code-tape is deliberately *not* ported -- it is out of scope for this repo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

# git diff --name-only --diff-filter -- include Added, Copied, Deleted,
# Modified, Renamed, Type-changed, Unmerged, Unknown, Broken. Same surface as
# code-tape: a deletion of a critical file is as load-bearing as an edit.
CONTRACT_DIFF_FILTER = "ACDMRTUXB"

# ---------------------------------------------------------------------------
# Structured impact summary contract (SDD pillar)
# ---------------------------------------------------------------------------

# Canonical field keys plus bilingual aliases. The repo's docs are English-
# leaning while GitNexus output and the upstream contract are Chinese, so we
# accept either spelling and normalise to the canonical key.
IMPACT_FIELD_ALIASES = {
    "risk_level": ["风险等级", "risk level", "risk", "risklevel"],
    "skeleton_change": ["关键骨架变更", "critical skeleton change", "skeleton change", "skeleton"],
    "gitnexus_impact": ["gitnexus 影响面", "gitnexus impact", "gitnexus", "impact surface"],
    "verification": ["验证结果", "verification", "verified", "tests run"],
    # Conditional: only required when verified references / gold tables move.
    "result_label": ["结果标签", "result label", "label"],
}

REQUIRED_IMPACT_FIELDS = ["risk_level", "skeleton_change", "gitnexus_impact", "verification"]

IMPACT_PLACEHOLDERS = {"", "-", "无", "none", "n/a", "na", "todo", "待补充", "tbd", "xxx"}

RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

# Result labels from the project charter (AGENTS.md / docs/maintenance_harness.md).
# Accept both the short token and the compound "stable/gold" style forms.
RESULT_LABEL_TOKENS = {"gold", "silver", "frontier", "demo", "oracle", "external"}


# ---------------------------------------------------------------------------
# Critical-skeleton classification (knowledge-base + TDD pillars)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CriticalRule:
    """One critical-skeleton surface of the repository.

    enforcement:
      * ``paired-test``  -- each touched ``src/<name>.py`` needs a changed
        ``tests/test_<name>*.py`` in the same diff (per-module TDD gate).
      * ``category-test`` -- the category as a whole needs at least one
        changed file matching ``test_pattern`` (code-tape's original model).
      * ``summary-only`` -- no test gate, but the change is research/spec
        sensitive and must be explained in the structured impact summary.
    """

    category: str
    matches: Callable[[str], bool]
    enforcement: str = "summary-only"
    test_pattern: Optional[re.Pattern] = None
    # When True, this category also requires the conditional result_label field
    # (verified references and gold result tables -- the charter's "do not
    # silently overwrite" / "do not claim silver as gold" rules).
    requires_result_label: bool = False
    description: str = ""


def _src_module_name(file: str) -> Optional[str]:
    """Return ``foo`` for ``src/foo.py`` (top-level research modules only)."""
    m = re.match(r"^src/([^/]+)\.py$", file)
    return m.group(1) if m else None


# Gold result tables tracked by src/project_harness.py CORE_FILES. Overwriting
# these silently is a charter violation, so they are a first-class category.
GOLD_RESULT_TABLES = (
    "results/tables/cer_results.csv",
    "results/tables/routing_performance_v2.csv",
    "results/tables/error_type_summary.csv",
    "results/tables/speaker_cer_results.csv",
    "results/tables/cpcer_lite_results.csv",
    "results/tables/risk_aware_performance.csv",
)

# Authority documents -- the SDD spine. Editing these reframes what every
# future agent treats as ground truth, so they gate like critical code.
AUTHORITY_DOCS = (
    "README.md",
    "REPORT.md",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/README.md",
    "docs/project_state.md",
    "docs/roadmap.md",
    "docs/technical_implementation_plan.md",
    "docs/technical_implementation_plan_v2.md",
    "docs/maintenance_harness.md",
    "docs/ambitious_research_agenda.md",
    "docs/agent_challenge_board.md",
)

# Core router modules (router v1 / v2). Per-module paired tests exist as
# tests/test_adaptive_router_*.py etc.
_ROUTER_PREFIXES = ("src/adaptive_router", "src/router_")

# Core evaluation + selection modules (CER / speaker-CER / cpCER-lite /
# error analysis / risk-aware selector).
_EVAL_MODULES = {
    "src/evaluate_cer.py",
    "src/evaluate_error_types.py",
    "src/evaluate_speaker_cer.py",
    "src/evaluate_cpcer_lite.py",
    "src/risk_aware_selector.py",
    "src/analyze_cer_errors.py",
}


CRITICAL_RULES: list[CriticalRule] = [
    CriticalRule(
        category="router-core",
        matches=lambda f: f.endswith(".py") and any(f.startswith(p) for p in _ROUTER_PREFIXES),
        enforcement="paired-test",
        description="Adaptive router v1/v2 decision logic.",
    ),
    CriticalRule(
        category="evaluation-core",
        matches=lambda f: f in _EVAL_MODULES,
        enforcement="paired-test",
        description="CER / speaker-CER / cpCER-lite / error-analysis / risk-aware selector.",
    ),
    CriticalRule(
        category="harness",
        matches=lambda f: (
            f.startswith("scripts/harness/")
            or f.startswith(".githooks/")
            or f.startswith(".github/workflows/")
            or f == "Makefile"
        ),
        enforcement="category-test",
        test_pattern=re.compile(r"^scripts/harness/tests/|^tests/test_harness"),
        description="Quality-gate infrastructure: hooks, CI workflows, contract scripts.",
    ),
    CriticalRule(
        category="references",
        matches=lambda f: f.startswith("references/"),
        enforcement="summary-only",
        requires_result_label=True,
        description="Verified reference transcripts -- must not be overwritten silently.",
    ),
    CriticalRule(
        category="gold-results",
        matches=lambda f: f in GOLD_RESULT_TABLES,
        enforcement="summary-only",
        requires_result_label=True,
        description="Stable gold result tables -- must not be silently overwritten.",
    ),
    CriticalRule(
        category="authority-docs",
        matches=lambda f: f in AUTHORITY_DOCS or f.startswith("docs/harness/") or f.startswith("docs/adr/"),
        enforcement="summary-only",
        description="Authority / SDD documents that define ground truth for agents.",
    ),
]


@dataclass
class Classification:
    critical: list = field(default_factory=list)  # list[{file, category}]
    non_critical: list = field(default_factory=list)  # list[str]


def normalize_files(files):
    """De-dupe, normalise separators, drop blanks -- order-preserving."""
    seen = set()
    out = []
    for f in files or []:
        if not f:
            continue
        norm = f.replace("\\", "/").strip()
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def classify_contract_paths(files):
    result = Classification()
    for file in normalize_files(files):
        rule = next((r for r in CRITICAL_RULES if r.matches(file)), None)
        if rule:
            result.critical.append({"file": file, "category": rule.category})
        else:
            result.non_critical.append(file)
    return result


def combine_changed_files(changed, untracked):
    return normalize_files([*(changed or []), *(untracked or [])])


def _rule_for(category):
    return next((r for r in CRITICAL_RULES if r.category == category), None)


def _missing_paired_tests(category, normalized):
    """For paired-test categories: every touched src module needs a test."""
    reasons = []
    rule = _rule_for(category)
    if rule is None:
        return reasons
    touched_modules = [f for f in normalized if rule.matches(f)]
    for module_file in touched_modules:
        name = _src_module_name(module_file)
        if name is None:
            # Non src/<name>.py file inside the category; fall back to
            # requiring any test change for it.
            expected = "tests/test_"
            has_test = any(t.startswith("tests/test_") for t in normalized)
        else:
            expected = f"tests/test_{name}"
            has_test = any(t.startswith(expected) for t in normalized)
        if not has_test:
            reasons.append(
                f"Missing paired test for critical module: {module_file} "
                f"(add or update {expected}*.py in the same change)"
            )
    return reasons


def evaluate_contract(changed_files, impact_summary="", enforce_summary=True):
    """Evaluate the knowledge-base contract for a diff.

    Returns a dict with: ok, reasons, warnings, suggestions, critical,
    non_critical. Mirrors evaluateGitNexusContract in contract-rules.mjs.

    ``enforce_summary`` controls whether the *structured impact summary*
    requirements are hard failures (``reasons``) or advisory (``warnings``).
    Structural gates (paired tests / category tests) are always hard. Locally
    (pre-push) there is no PR body, so callers pass ``enforce_summary=False``
    and let CI -- which has the PR body -- be the hard summary gate.
    """
    normalized = normalize_files(changed_files)
    classification = classify_contract_paths(normalized)
    reasons = []
    warnings = []
    suggestions = [
        "Run GitNexus detect_changes to inspect current diff impact.",
        "Use query/context/impact on touched symbols before editing critical skeleton code.",
        "Summarize the GitNexus impact result in the PR self-check.",
    ]

    base = {
        "critical": classification.critical,
        "non_critical": classification.non_critical,
    }

    if not classification.critical:
        warnings.append(
            "No critical contract surface changed; GitNexus analysis is advisory for this diff."
        )
        return {"ok": True, "reasons": reasons, "warnings": warnings, "suggestions": suggestions, **base}

    touched_categories = []
    for item in classification.critical:
        if item["category"] not in touched_categories:
            touched_categories.append(item["category"])

    needs_result_label = False
    for category in touched_categories:
        rule = _rule_for(category)
        if rule is None:
            continue
        if rule.requires_result_label:
            needs_result_label = True
        if rule.enforcement == "paired-test":
            reasons.extend(_missing_paired_tests(category, normalized))
        elif rule.enforcement == "category-test":
            if rule.test_pattern is not None and not any(
                rule.test_pattern.search(f) for f in normalized
            ):
                reasons.append(f"Missing contract test for critical category: {category}")

    summary_reasons = validate_impact_summary(impact_summary, require_result_label=needs_result_label)
    if enforce_summary:
        reasons.extend(summary_reasons)
    else:
        warnings.extend(summary_reasons)

    return {
        "ok": len(reasons) == 0,
        "reasons": reasons,
        "warnings": warnings,
        "suggestions": suggestions,
        **base,
    }


# ---------------------------------------------------------------------------
# Impact summary parsing / validation
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(
    r"^#{1,6}\s*GitNexus\s*(影响分析摘要|impact\s*summary)\s*$", re.IGNORECASE | re.UNICODE
)
_FIELD_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?([^:*：]+?)(?:\*\*)?\s*[:：]\s*(.*)\s*$", re.UNICODE)


def extract_impact_summary(text):
    """Slice the section under a 'GitNexus 影响分析摘要' / 'GitNexus Impact Summary'
    heading out of a PR body. Falls back to the whole text if no heading.
    """
    if not text:
        return ""
    lines = text.split("\n")
    heading_index = next((i for i, line in enumerate(lines) if _HEADING_RE.match(line.strip())), -1)
    if heading_index == -1:
        return text.strip()
    section = []
    for line in lines[heading_index + 1 :]:
        if re.match(r"^#{1,6}\s+\S", line.strip()):
            break
        section.append(line)
    return "\n".join(section).strip()


def _canonical_field(raw_key):
    key = raw_key.strip().lower()
    for canonical, aliases in IMPACT_FIELD_ALIASES.items():
        if key == canonical:
            return canonical
        if key in (a.lower() for a in aliases):
            return canonical
    return None


def parse_impact_fields(value):
    fields = {}
    for line in value.split("\n"):
        m = _FIELD_RE.match(line)
        if not m:
            continue
        canonical = _canonical_field(m.group(1))
        if canonical and canonical not in fields:
            fields[canonical] = m.group(2).strip()
    return fields


def _is_placeholder(value):
    return value.strip().lower() in IMPACT_PLACEHOLDERS


def _result_label_ok(value):
    v = value.strip().lower()
    if not v:
        return False
    # Accept "gold", "stable/gold", "synthetic/silver", "external sanity-check", etc.
    return any(token in v for token in RESULT_LABEL_TOKENS)


def validate_impact_summary(value, require_result_label=False):
    normalized = (value or "").strip()
    if _is_placeholder(normalized):
        return [
            "Missing structured GitNexus impact summary. Fill the PR template "
            "fields for critical skeleton changes."
        ]

    fields = parse_impact_fields(normalized)
    reasons = []

    for field_key in REQUIRED_IMPACT_FIELDS:
        if field_key not in fields:
            reasons.append(f"Missing GitNexus impact summary field: {field_key}")
        elif _is_placeholder(fields[field_key]):
            reasons.append(f"GitNexus impact summary field is empty or placeholder: {field_key}")

    risk = fields.get("risk_level", "").upper()
    if risk and risk not in RISK_LEVELS:
        reasons.append("Invalid GitNexus risk level. Use LOW, MEDIUM, HIGH, or CRITICAL.")

    impact = fields.get("gitnexus_impact", "").lower()
    if impact and (
        "detect_changes" not in impact or not re.search(r"\b(query|context|impact)\b", impact)
    ):
        reasons.append(
            "GitNexus impact field must mention detect_changes and one of query/context/impact."
        )

    if require_result_label:
        label = fields.get("result_label", "")
        if not label or _is_placeholder(label):
            reasons.append(
                "Missing result label. Verified references / gold tables changed: "
                "add a Result label field (gold|silver|frontier|demo|oracle|external)."
            )
        elif not _result_label_ok(label):
            reasons.append(
                "Invalid result label. Use one of gold, silver, frontier, demo, "
                "oracle, external (or charter compound forms)."
            )

    return reasons
