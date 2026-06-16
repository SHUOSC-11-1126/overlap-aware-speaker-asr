"""Advisory research-entropy guard for the development harness (stdlib-only).

This is the preventive teeth of the agentic-research-entropy analysis
(``src/research_entropy_audit.py``). It runs inside ``make quality-predev`` and
warns -- never fails -- when the current working-tree diff adds *ceremony*
files (status / handoff / receipt / coordination scaffolding) faster than
research *substance*. The intent is to interrupt the wave-loop failure mode that
once buried this repo under ~800 self-referential files, at the moment a change
is being prepared rather than after the fact.

It is deliberately standalone and stdlib-only: git hooks run under whatever
``python3`` is on PATH (not the project virtualenv), and ``src/__init__.py``
eagerly imports heavy research modules, so importing ``src`` here is unsafe.
The ceremony vocabulary and the diff verdict are kept identical to
``src/research_entropy_audit.py``; ``tests/test_research_entropy_audit.py``
pins them equal so the advisory never drifts from the analysis.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Keep in sync with src/research_entropy_audit.CEREMONY_TOKENS (test-enforced).
CEREMONY_TOKENS = [
    "writeback",
    "wave",
    "handoff",
    "receipt",
    "bridge_checklist",
    "coordination",
    "operator_brief",
    "runbook",
    "milestone",
    "completion_summary",
    "presentation",
    "storyboard",
    "walkthrough",
    "go_no_go",
    "queue_status",
    "phase_checkpoint",
    "next_action",
    "scaffold",
    "dashboard",
    "checklist",
]
CEREMONY_RE = re.compile("|".join(CEREMONY_TOKENS), re.IGNORECASE)

RATIO_THRESHOLD = 3


def is_ceremony_name(path: str) -> bool:
    return bool(CEREMONY_RE.search(os.path.basename(path)))


def assess_diff(changed_paths) -> dict:
    """Advisory verdict for a changeset (mirror of the audit's assess_diff)."""
    dc = ds = 0
    for p in changed_paths or []:
        if not str(p).endswith(".py"):
            continue
        if is_ceremony_name(p):
            dc += 1
        else:
            ds += 1
    verdict = "ok"
    if dc and ds == 0:
        verdict = "warn"
    elif dc > RATIO_THRESHOLD * max(ds, 1):
        verdict = "warn"
    message = ""
    if verdict == "warn":
        message = (
            f"This change adds {dc} ceremony-named .py file(s) and {ds} substance file(s). "
            "Per the charter Board Rule, a task that does not answer a clear research "
            "question should stay out of the core pipeline (skill card / demo note / future work)."
        )
    return {"delta_ceremony": dc, "delta_substance": ds, "verdict": verdict, "message": message}


def _git_lines(args):
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, check=True
        ).stdout
    except (subprocess.CalledProcessError, OSError):
        return []
    return [l.strip() for l in out.splitlines() if l.strip()]


def changed_files():
    changed = _git_lines(["diff", "--name-only", "--diff-filter=ACMR", "HEAD"])
    untracked = _git_lines(["ls-files", "--others", "--exclude-standard"])
    seen, out = set(), []
    for f in [*changed, *untracked]:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def run_guard(changed=None) -> int:
    """Print an advisory verdict for the working-tree diff. ALWAYS returns 0."""
    if changed is None:
        changed = changed_files()
    v = assess_diff(changed)
    print(
        f">>> research-entropy guard (advisory)\n"
        f"    +{v['delta_ceremony']} ceremony / +{v['delta_substance']} substance .py -> {v['verdict']}"
    )
    if v["verdict"] == "warn":
        print("    warning: " + v["message"])
        print("    (advisory only -- this does not block the commit/push)")
    return 0


def main(argv=None) -> int:
    run_guard()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
