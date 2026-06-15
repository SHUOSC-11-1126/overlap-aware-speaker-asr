"""GitNexus knowledge-base contract check.

Python port of code-tape's scripts/workflows/contract-check.mjs, adapted for
this Python research repo. Commands:

  bootstrap  install git hooks and print the agent workflow guidance
  local      refresh the GitNexus index (best-effort) and evaluate the
             contract against the working-tree diff (summary advisory)
  gitnexus   refresh the GitNexus index and evaluate against the PR base diff
             (CI mode -- summary enforced as a hard gate)
  check      local or gitnexus depending on the CI env var

The GitNexus index (`.gitnexus/`) is this repo's knowledge base: it lets agents
observe the cascade reaction of a change (detect_changes / query / context /
impact) before touching critical skeleton code. Building it requires
``npx gitnexus``; locally that is best-effort (a flaky/slow index build never
blocks a developer), while CI treats an index-build failure as a hard failure
unless GITNEXUS_OPTIONAL=1.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contract_rules as cr  # noqa: E402
from install_hooks import install_hooks  # noqa: E402

GITNEXUS_VERSION = os.environ.get("GITNEXUS_VERSION", "1.6.5")
DEFAULT_LOCAL_ANALYZE_TIMEOUT_MS = 120_000
DEFAULT_CI_ANALYZE_TIMEOUT_MS = 300_000

REPO_ROOT = Path(__file__).resolve().parents[2]


def main(argv):
    command = argv[1] if len(argv) > 1 else "check"
    try:
        if command == "bootstrap":
            return run_bootstrap()
        if command == "local":
            return run_contract(mode="local")
        if command == "gitnexus":
            return run_contract(mode="ci")
        if command == "check":
            return run_contract(mode="ci" if os.environ.get("CI") else "local")
        raise SystemExit(f"unknown contract command: {command}")
    except SystemExit:
        raise
    except Exception as err:  # pragma: no cover - defensive
        print(str(err), file=sys.stderr)
        return 1


def run_bootstrap():
    rc = install_hooks()
    print("Agent bootstrap complete.")
    print("- Before editing code: run `make quality-predev` (or python3 scripts/harness/quality.py predev)")
    print("- Commit with `git commit` so the pre-commit hook runs the fast quality gate")
    print("- Push with `git push` so the pre-push hook runs the contract + full test gate")
    print("- For critical skeleton changes: read GitNexus detect_changes/query/context/impact output")
    print("- CI remains the final contract gate.")
    return rc


def run_contract(mode):
    gitnexus_rc = run_gitnexus_analyze(mode)

    changed_files = get_changed_files(mode)
    impact_summary = get_impact_summary()
    enforce_summary = mode == "ci"
    result = cr.evaluate_contract(
        changed_files, impact_summary=impact_summary, enforce_summary=enforce_summary
    )

    print_result("GitNexus contract", result)
    return 0 if (result["ok"] and gitnexus_rc == 0) else 1


# ---------------------------------------------------------------------------
# GitNexus index refresh (knowledge base)
# ---------------------------------------------------------------------------


def run_gitnexus_analyze(mode):
    """Refresh the GitNexus index. Returns 0 on success/skip, 1 on a failure
    that should fail the gate (CI only)."""
    if os.environ.get("GITNEXUS_SKIP") == "1":
        print("Skipping GitNexus analyze because GITNEXUS_SKIP=1.")
        return 0

    if shutil.which("npx") is None:
        return _gitnexus_soft_fail(mode, "npx not found; cannot refresh the GitNexus index.")

    timeout_s = resolve_timeout_ms(mode) / 1000.0
    args = ["npx", "--yes", "--prefer-offline", f"gitnexus@{GITNEXUS_VERSION}", "analyze", "--force", "--index-only"]
    print(f"Running GitNexus {GITNEXUS_VERSION} analyze --force --index-only ({mode}, timeout {timeout_s:.0f}s)...")
    try:
        subprocess.run(args, check=True, cwd=str(REPO_ROOT), timeout=timeout_s)
        return 0
    except subprocess.TimeoutExpired:
        return _gitnexus_soft_fail(
            mode,
            f"GitNexus analyze timed out after {timeout_s:.0f}s. "
            "Set GITNEXUS_ANALYZE_TIMEOUT_MS higher, or GITNEXUS_SKIP=1 to skip.",
        )
    except subprocess.CalledProcessError as err:
        return _gitnexus_soft_fail(mode, f"GitNexus analyze failed (exit {err.returncode}).")


def _gitnexus_soft_fail(mode, message):
    """In CI an index-build failure is hard (unless GITNEXUS_OPTIONAL=1).
    Locally it is always advisory so it never blocks a developer."""
    hard = mode == "ci" and os.environ.get("GITNEXUS_OPTIONAL") != "1"
    label = "error" if hard else "warning"
    print(f"GitNexus {label}: {message}", file=sys.stderr if hard else sys.stdout)
    if not hard:
        print("Continuing with the deterministic contract evaluation; index may be stale.")
    return 1 if hard else 0


def resolve_timeout_ms(mode):
    configured = os.environ.get("GITNEXUS_ANALYZE_TIMEOUT_MS")
    if not configured:
        return DEFAULT_CI_ANALYZE_TIMEOUT_MS if mode == "ci" else DEFAULT_LOCAL_ANALYZE_TIMEOUT_MS
    try:
        value = int(configured)
    except ValueError:
        raise SystemExit("GITNEXUS_ANALYZE_TIMEOUT_MS must be a positive integer (milliseconds).")
    if value <= 0:
        raise SystemExit("GITNEXUS_ANALYZE_TIMEOUT_MS must be a positive integer (milliseconds).")
    return value


# ---------------------------------------------------------------------------
# Diff + PR body extraction
# ---------------------------------------------------------------------------


def get_changed_files(mode):
    override = os.environ.get("CONTRACT_CHANGED_FILES")
    if override:
        return [p.strip() for p in override.replace(",", "\n").split("\n") if p.strip()]

    base_ref_name = os.environ.get("GITHUB_BASE_REF")
    if mode == "ci" and base_ref_name:
        base_ref = f"origin/{base_ref_name}"
        if not git_ref_exists(base_ref):
            subprocess.run(
                ["git", "fetch", "--no-tags", "--depth=1", "origin", base_ref_name],
                cwd=str(REPO_ROOT),
            )
        return git_lines(["diff", "--name-only", f"--diff-filter={cr.CONTRACT_DIFF_FILTER}", f"{base_ref}...HEAD"])

    return cr.combine_changed_files(
        git_lines(["diff", "--name-only", f"--diff-filter={cr.CONTRACT_DIFF_FILTER}", "HEAD"]),
        git_lines(["ls-files", "--others", "--exclude-standard"]),
    )


def get_impact_summary():
    env_summary = os.environ.get("GITNEXUS_IMPACT_SUMMARY")
    if env_summary:
        return cr.extract_impact_summary(env_summary)
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path and os.path.exists(event_path):
        with open(event_path, "r", encoding="utf-8") as fh:
            event = json.load(fh)
        body = (event.get("pull_request") or {}).get("body") or ""
        return cr.extract_impact_summary(body)
    return ""


def git_lines(args):
    try:
        output = subprocess.run(
            ["git", "-c", "core.quotePath=false", *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except subprocess.CalledProcessError:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def git_ref_exists(ref):
    return (
        subprocess.run(
            ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
            cwd=str(REPO_ROOT),
            capture_output=True,
        ).returncode
        == 0
    )


def print_result(title, result):
    print(f"\n{title}: {'passed' if result['ok'] else 'failed'}")
    for reason in result.get("reasons", []):
        print(f"- {reason}")
    for warning in result.get("warnings", []):
        print(f"- warning: {warning}")
    if result.get("critical"):
        print("Critical contract files:")
        for item in result["critical"]:
            print(f"- {item['category']}: {item['file']}")
    if result.get("suggestions"):
        print("GitNexus suggestions:")
        for suggestion in result["suggestions"]:
            print(f"- {suggestion}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
