"""Agentic Research Entropy Audit (experimental/frontier, analysis-only).

Research question
-----------------
When an autonomous agentic loop is allowed to run unsupervised on a research
repository, does it keep producing *research substance* (code that computes,
transforms, evaluates, or generates falsifiable numbers), or does it drift into
self-referential *ceremony* (status / handoff / receipt / coordination files
that mostly reference other such files and compute nothing)?

This module makes that question measurable for *this* repository, which is a
natural specimen of the failure mode. It is deliberately a meta-analysis tool:
it reasons about the repo's own source surface and git history, not about the
ASR domain. Its outputs are labelled ``experimental/frontier`` and are
analysis-only -- they are never gold benchmark evidence.

Design notes
------------
* Top-level imports are stdlib-only so the classification / diff-verdict core
  runs under any ``python3`` (the figure step imports matplotlib lazily and
  degrades gracefully if it is unavailable).
* The advisory git-hook guard lives separately in
  ``scripts/harness/entropy_guard.py`` (stdlib-only, never imports ``src``);
  this module and that guard share the same ceremony vocabulary and diff
  verdict, pinned equal by ``tests/test_research_entropy_audit.py``.
* Two independent signals are reported so the classification is auditable and
  not circular: a *filename* signal (the ceremony token regex) and a *content*
  signal (compute-library imports, arithmetic-operation density, whether the
  file only writes status documents). Files where the two disagree are flagged.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# The ceremony vocabulary observed in this repo's degenerate wave loops. Keep in
# sync with scripts/harness/entropy_guard.CEREMONY_TOKENS (a test enforces it).
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

# Non-research infrastructure that is neither substance nor ceremony.
SUPPORT_PY = frozenset({"__init__.py", "config.py", "io_helpers.py", "project_harness.py"})

# Content signals. The compute-import list is deliberately the precise set of
# research/numeric libraries -- NOT stdlib tokens like "math"/"wave", which would
# false-match this repo's own "wave"-loop vocabulary and destroy the contrast.
COMPUTE_IMPORT_RE = re.compile(
    r"\b(numpy|scipy|torch|whisper|soundfile|sklearn|pandas|librosa|matplotlib|funasr)\b"
)
DOC_WRITE_RE = re.compile(
    r"\.md[\"']|write_text|\.write\(|writelines|json\.dump|csv\.writer|DictWriter"
)
ARITH_RE = re.compile(
    r"[-+*/]=|\bnp\.|\bmean\(|\bsum\(|\bsqrt|\bcorr|\bmedian|\bstd\(|/ *len\(|\* *100|\.corrcoef"
)

# A diff that adds more than this multiple of ceremony-to-substance .py files is
# flagged by the advisory guard.
RATIO_THRESHOLD = 3
COLLAPSE_MIN = 3  # min ceremony adds in a day for it to count as a collapse day


# ---------------------------------------------------------------------------
# Classification (pure)
# ---------------------------------------------------------------------------


def is_ceremony_name(path: str) -> bool:
    """True if the file *name* matches the ceremony vocabulary."""
    return bool(CEREMONY_RE.search(Path(path).name))


def content_signals(text: Optional[str]) -> dict:
    """Cheap, transparent content signals for a python source string."""
    text = text or ""
    loc = text.count("\n") + 1
    compute_import = bool(COMPUTE_IMPORT_RE.search(text))
    writes_doc = bool(DOC_WRITE_RE.search(text))
    arith_ops = len(ARITH_RE.findall(text))
    strlit = sum(
        len(m)
        for m in re.findall(r"\"\"\"[\s\S]*?\"\"\"|'''[\s\S]*?'''|\"[^\"]*\"|'[^']*'", text)
    )
    str_ratio = round(strlit / max(len(text), 1), 4)
    return {
        "loc": loc,
        "compute_import": compute_import,
        "writes_doc": writes_doc,
        "arith_ops": arith_ops,
        "str_ratio": str_ratio,
    }


def _computes(sig: dict) -> bool:
    return bool(sig["compute_import"]) and sig["arith_ops"] >= 3


def classify_python_file(path: str, text: Optional[str] = None) -> dict:
    """Classify a python file as substance / ceremony / support.

    Rules (auditable, two independent signals):
      * ceremony name + does not actually compute -> ceremony
      * ceremony name + actually computes        -> substance (disagreement)
      * non-ceremony name in the support allowlist -> support
      * otherwise                                  -> substance
    """
    name = Path(path).name
    sig = content_signals(text)
    name_ceremony = is_ceremony_name(path)
    # Independent content signal: emits documents but computes nothing.
    content_ceremony = (not sig["compute_import"]) and sig["arith_ops"] < 3 and sig["writes_doc"]
    disagreement = False
    if name_ceremony:
        if _computes(sig):
            klass = "substance"
            disagreement = True
        else:
            klass = "ceremony"
    elif name in SUPPORT_PY:
        klass = "support"
    else:
        klass = "substance"
    return {
        "path": path,
        "name": name,
        "klass": klass,
        "name_ceremony": name_ceremony,
        "content_ceremony": content_ceremony,
        "disagreement": disagreement,
        **sig,
    }


def audit_files(items: Iterable[tuple]) -> dict:
    """Aggregate a (path, text) collection into class counts + content stats."""
    files = [classify_python_file(p, t) for p, t in items]
    counts = {"substance": 0, "ceremony": 0, "support": 0}
    for r in files:
        counts[r["klass"]] += 1
    research = counts["substance"] + counts["ceremony"]
    saturation = (counts["ceremony"] / research) if research else 0.0

    def rate(klass: str, key: str) -> float:
        sub = [f for f in files if f["klass"] == klass]
        return round(sum(1 for f in sub if f[key]) / len(sub), 4) if sub else 0.0

    def mean_arith(klass: str) -> float:
        sub = [f for f in files if f["klass"] == klass]
        return round(sum(f["arith_ops"] for f in sub) / len(sub), 4) if sub else 0.0

    content = {
        "ceremony_compute_import_rate": rate("ceremony", "compute_import"),
        "substance_compute_import_rate": rate("substance", "compute_import"),
        "ceremony_writes_doc_rate": rate("ceremony", "writes_doc"),
        "ceremony_mean_arith": mean_arith("ceremony"),
        "substance_mean_arith": mean_arith("substance"),
    }
    # Content-based corroboration. The name signal (ceremony_saturation) is a
    # conservative lower bound; folding in "substance"-named files that compute
    # nothing and only emit documents gives an upper estimate. Files where the
    # two signals disagree are reported so the classification stays auditable.
    borderline = [
        f["path"]
        for f in files
        if f["klass"] == "substance" and f["content_ceremony"] and not f["name_ceremony"]
    ]
    content["content_ceremony_count"] = sum(1 for f in files if f["content_ceremony"])
    content["borderline_substance_count"] = len(borderline)
    content["borderline_substance_examples"] = sorted(borderline)[:12]
    saturation_content_upper = (
        (counts["ceremony"] + len(borderline)) / research if research else 0.0
    )
    return {
        "total": len(files),
        "counts": counts,
        "ceremony_saturation": round(saturation, 6),
        "ceremony_saturation_content_upper": round(saturation_content_upper, 6),
        "content": content,
        "files": files,
        "disagreements": [f["path"] for f in files if f["disagreement"]],
    }


# ---------------------------------------------------------------------------
# Self-reference graph (pure)
# ---------------------------------------------------------------------------


def referenced_stems(text: str, candidate_stems: Iterable[str]) -> set:
    """Module stems (from candidate_stems) that appear as tokens in text."""
    cands = sorted({s for s in candidate_stems if s}, key=len, reverse=True)
    if not cands or not text:
        return set()
    pat = re.compile(r"\b(" + "|".join(re.escape(s) for s in cands) + r")\b")
    return set(pat.findall(text))


def self_reference_ratio(items: Iterable[tuple]) -> dict:
    """Of all module references made *by ceremony files*, what fraction point at
    other ceremony modules? High closure is the hallmark of the collapse."""
    items = list(items)
    klass_by_stem = {}
    for path, text in items:
        klass_by_stem[Path(path).stem] = classify_python_file(path, text)["klass"]
    known = set(klass_by_stem)
    ceremony_refs = 0
    total_refs = 0
    for path, text in items:
        if classify_python_file(path, text)["klass"] != "ceremony":
            continue
        refs = referenced_stems(text or "", known - {Path(path).stem})
        for s in refs:
            total_refs += 1
            if klass_by_stem.get(s) == "ceremony":
                ceremony_refs += 1
    ratio = (ceremony_refs / total_refs) if total_refs else 0.0
    return {"ceremony_refs": ceremony_refs, "total_refs": total_refs, "ratio": round(ratio, 6)}


# ---------------------------------------------------------------------------
# Git add-history timeline (pure given events)
# ---------------------------------------------------------------------------


def summarize_timeline(add_events: Iterable[tuple]) -> dict:
    """Aggregate (date, path) add-events into a per-day substance/ceremony series.

    Returns by_day rows (with cumulative columns), the day with the most
    ceremony adds, the first 'collapse' day (ceremony > substance and >=
    COLLAPSE_MIN), and the peak daily ceremony:substance ratio.
    """
    per: dict = {}
    for date, path in add_events:
        if not str(path).endswith(".py"):
            continue
        d = per.setdefault(date, {"ceremony": 0, "substance": 0})
        if is_ceremony_name(path):
            d["ceremony"] += 1
        else:
            d["substance"] += 1

    by_day = []
    cum_c = cum_s = 0
    peak_ceremony = -1
    peak_ceremony_day = None
    peak_ratio = 0.0
    first_collapse_day = None
    for date in sorted(per):
        c = per[date]["ceremony"]
        s = per[date]["substance"]
        cum_c += c
        cum_s += s
        by_day.append(
            {
                "date": date,
                "ceremony": c,
                "substance": s,
                "cum_ceremony": cum_c,
                "cum_substance": cum_s,
            }
        )
        if c > peak_ceremony:
            peak_ceremony = c
            peak_ceremony_day = date
        ratio = c / s if s else float(c)
        peak_ratio = max(peak_ratio, ratio)
        if first_collapse_day is None and c > s and c >= COLLAPSE_MIN:
            first_collapse_day = date
    return {
        "by_day": by_day,
        "peak_ceremony_day": peak_ceremony_day,
        "peak_ceremony_adds": max(peak_ceremony, 0),
        "first_collapse_day": first_collapse_day,
        "peak_daily_ratio": round(peak_ratio, 3),
    }


# ---------------------------------------------------------------------------
# Diff verdict + degeneration index (pure)
# ---------------------------------------------------------------------------


def assess_diff(changed_paths: Iterable[str]) -> dict:
    """Advisory verdict for a changeset: is it adding ceremony faster than
    substance? Considers .py adds only; never raises."""
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


def degeneration_index(ceremony_saturation: float, self_ref_ratio: float) -> float:
    """Bounded [0,1] degeneration score: ceremony share weighted by how
    self-referentially closed that ceremony is. 0 = healthy, 1 = fully collapsed."""
    a = max(0.0, min(1.0, ceremony_saturation))
    b = max(0.0, min(1.0, self_ref_ratio))
    return round(a * b, 6)


# ---------------------------------------------------------------------------
# IO wrappers (impure)
# ---------------------------------------------------------------------------


def collect_src_python(root: Optional[Path] = None) -> list:
    root = Path(root or PROJECT_ROOT)
    items = []
    for p in sorted((root / "src").glob("*.py")):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        items.append((f"src/{p.name}", text))
    return items


def git_add_events(root: Optional[Path] = None, pathspec: str = "src/*.py") -> list:
    """(date, path) add-events reachable from HEAD (i.e. landed on this branch)."""
    root = Path(root or PROJECT_ROOT)
    try:
        out = subprocess.run(
            [
                "git",
                "log",
                "--diff-filter=A",
                "--name-only",
                "--format=COMMIT %ad",
                "--date=short",
                "--",
                pathspec,
            ],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, OSError):
        return []
    events = []
    date = None
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("COMMIT "):
            date = line[len("COMMIT ") :].strip()
        elif line.endswith(".py") and date:
            events.append((date, line))
    return events


def _git_changed_files(root: Optional[Path] = None) -> list:
    root = Path(root or PROJECT_ROOT)

    def lines(args):
        try:
            return [
                l.strip()
                for l in subprocess.run(
                    ["git", *args], cwd=str(root), capture_output=True, text=True, check=True
                ).stdout.splitlines()
                if l.strip()
            ]
        except (subprocess.CalledProcessError, OSError):
            return []

    changed = lines(["diff", "--name-only", "--diff-filter=ACMR", "HEAD"])
    untracked = lines(["ls-files", "--others", "--exclude-standard"])
    seen, out = set(), []
    for f in [*changed, *untracked]:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


def compute_report(root: Optional[Path] = None) -> dict:
    root = Path(root or PROJECT_ROOT)
    items = collect_src_python(root)
    summary = audit_files(items)
    selfref = self_reference_ratio(items)
    timeline = summarize_timeline(git_add_events(root))
    di = degeneration_index(summary["ceremony_saturation"], selfref["ratio"])
    return {
        "label": "experimental/frontier (meta-analysis / analysis-only)",
        "universe": "src/*.py reachable from HEAD on the current branch",
        "summary": summary,
        "self_reference": selfref,
        "timeline": timeline,
        "degeneration_index": di,
    }


def write_outputs(report: dict, out_dir) -> list:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "entropy_summary.json"
    classif_path = out_dir / "file_classification.csv"
    timeline_path = out_dir / "entropy_timeline.csv"

    # The per-file detail lives in file_classification.csv; keep the JSON small
    # by dropping the (large) embedded files list from the summary copy.
    json_report = dict(report)
    json_summary = dict(report.get("summary", {}))
    files = json_summary.pop("files", [])
    json_report["summary"] = json_summary
    summary_path.write_text(json.dumps(json_report, ensure_ascii=False, indent=2), encoding="utf-8")

    with classif_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "path",
                "klass",
                "name_ceremony",
                "content_ceremony",
                "compute_import",
                "writes_doc",
                "arith_ops",
                "str_ratio",
                "loc",
                "disagreement",
            ]
        )
        for r in files:
            w.writerow(
                [
                    r.get("path"),
                    r.get("klass"),
                    r.get("name_ceremony"),
                    r.get("content_ceremony"),
                    r.get("compute_import"),
                    r.get("writes_doc"),
                    r.get("arith_ops"),
                    r.get("str_ratio"),
                    r.get("loc"),
                    r.get("disagreement"),
                ]
            )

    by_day = report.get("timeline", {}).get("by_day", [])
    with timeline_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "ceremony", "substance", "cum_ceremony", "cum_substance"])
        for d in by_day:
            w.writerow(
                [d["date"], d["ceremony"], d["substance"], d["cum_ceremony"], d["cum_substance"]]
            )

    return [summary_path, classif_path, timeline_path]


def _load_phase_trend(root: Path) -> list:
    """Read the real ASR separation phase-diagram trend (the substance exemplar),
    if present. Returns [(overlap_bin, help_rate, mean_delta), ...]."""
    path = root / "results" / "tables" / "separation_phase_diagram_trend.csv"
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                rows.append(
                    (
                        float(row["overlap_bin"]),
                        float(row["separation_help_rate"]),
                        float(row["mean_delta_cer_separated"]),
                    )
                )
            except (KeyError, ValueError):
                continue
    return sorted(rows)


def render_figure(report: dict, out_dir, root: Optional[Path] = None):
    """Two phase diagrams side by side: the process-decay curve (this repo's
    substance vs ceremony over time) and the scientific-signal curve (separation
    help-rate vs overlap). Lazily imports matplotlib; returns None if absent."""
    root = Path(root or PROJECT_ROOT)
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as err:  # pragma: no cover - environment dependent
        print(f"[research-entropy-audit] figure skipped (matplotlib unavailable: {err})")
        return None

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    by_day = report.get("timeline", {}).get("by_day", [])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Panel A: process degeneration
    if by_day:
        xs = list(range(len(by_day)))
        labels = [d["date"][5:] for d in by_day]  # MM-DD
        ax1.plot(xs, [d["cum_substance"] for d in by_day], "-o", color="#1b7837",
                 label="cumulative substance", linewidth=2)
        ax1.plot(xs, [d["cum_ceremony"] for d in by_day], "-o", color="#b2182b",
                 label="cumulative ceremony", linewidth=2)
        collapse = report.get("timeline", {}).get("first_collapse_day")
        for i, d in enumerate(by_day):
            if d["date"] == collapse:
                ax1.axvline(i, color="#b2182b", linestyle="--", alpha=0.5)
                ax1.text(i, ax1.get_ylim()[1] * 0.92, " collapse", color="#b2182b", fontsize=9)
        ax1.set_xticks(xs)
        ax1.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax1.legend(loc="upper left", fontsize=9)
    di = report.get("degeneration_index", 0.0)
    sat = report.get("summary", {}).get("ceremony_saturation", 0.0)
    ax1.set_title(f"Process phase diagram: substance vs ceremony\n(ceremony saturation={sat:.0%}, degeneration index={di:.2f})",
                  fontsize=10)
    ax1.set_ylabel("cumulative src/*.py files")
    ax1.grid(True, alpha=0.3)

    # Panel B: the real ASR scientific signal (substance exemplar)
    trend = _load_phase_trend(root)
    if trend:
        ox = [t[0] for t in trend]
        ax2.plot(ox, [t[1] for t in trend], "-o", color="#2166ac", linewidth=2,
                 label="separation help-rate")
        ax2b = ax2.twinx()
        ax2b.plot(ox, [t[2] for t in trend], "--", color="#888888", alpha=0.7,
                  label="mean ΔCER (sep−mix)")
        ax2b.axhline(0, color="#cccccc", linewidth=1)
        ax2b.set_ylabel("mean ΔCER (sep − mixed)", fontsize=9)
        ax2.set_ylim(0, 1.05)
        ax2.legend(loc="lower right", fontsize=9)
    else:
        ax2.text(0.5, 0.5, "separation_phase_diagram_trend.csv not found",
                 ha="center", va="center", transform=ax2.transAxes)
    ax2.set_title("Scientific phase diagram: when does separation help?\n(real gold+silver data — the substance counterpoint)",
                  fontsize=10)
    ax2.set_xlabel("overlap ratio")
    ax2.set_ylabel("separation help-rate")
    ax2.grid(True, alpha=0.3)

    fig.suptitle("Agentic Research Entropy — two phase diagrams of the same workspace",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig_path = out_dir / "agentic_research_entropy.png"
    fig.savefig(fig_path, dpi=130)
    plt.close(fig)
    return fig_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _run_check(root: Optional[Path] = None) -> int:
    changed = _git_changed_files(root)
    v = assess_diff(changed)
    print(
        f"[research-entropy-audit:check] +{v['delta_ceremony']} ceremony / "
        f"+{v['delta_substance']} substance .py -> {v['verdict']}"
    )
    if v["verdict"] == "warn":
        print("  " + v["message"])
    return 0  # advisory: never fails the gate


def main(argv: Optional[list] = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    parser = argparse.ArgumentParser(description="Agentic Research Entropy Audit (analysis-only).")
    parser.add_argument("--check", action="store_true",
                        help="advisory: assess the working-tree diff and warn (always exit 0)")
    parser.add_argument("--out", default="results/entropy_audit",
                        help="output directory (default: results/entropy_audit)")
    parser.add_argument("--no-figure", action="store_true", help="skip the matplotlib figure")
    args = parser.parse_args(argv[1:])

    if args.check:
        return _run_check()

    report = compute_report()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = PROJECT_ROOT / out_dir
    paths = write_outputs(report, out_dir)
    if not args.no_figure:
        fig = render_figure(report, out_dir)
        if fig is not None:
            paths.append(fig)

    s = report["summary"]
    print(f"[research-entropy-audit] label={report['label']}")
    print(
        f"  src/*.py={s['total']}  substance={s['counts']['substance']}  "
        f"ceremony={s['counts']['ceremony']}  support={s['counts']['support']}"
    )
    print(
        f"  ceremony_saturation={s['ceremony_saturation']:.3f} (name signal, lower bound); "
        f"content-upper={s['ceremony_saturation_content_upper']:.3f} "
        f"(+{s['content']['borderline_substance_count']} doc-only 'substance' files)"
    )
    print(
        f"  self_reference_ratio={report['self_reference']['ratio']:.3f}  "
        f"degeneration_index={report['degeneration_index']:.3f}  "
        f"name/content disagreements={len(s['disagreements'])}"
    )
    tl = report["timeline"]
    print(
        f"  timeline: peak ceremony day={tl['peak_ceremony_day']} "
        f"(+{tl['peak_ceremony_adds']}), first collapse={tl['first_collapse_day']}"
    )
    for p in paths:
        try:
            print(f"  wrote {Path(p).relative_to(PROJECT_ROOT)}")
        except ValueError:
            print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
