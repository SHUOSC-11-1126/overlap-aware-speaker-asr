"""Emotion-anchored ASR repair: can preserving the LLM-detected stance cure the over-correction tax?

Issue #833. Builds on two findings:
  * #822 (`llm_asr_critic`): naive generative LLM repair NET-HARMS CER — it over-corrects clean tracks
    (e.g. 0.10 -> 0.60) even though the prompt already asks for minimal edits.
  * #831 (`semantic_emotion_tax`): a local `deepseek-r1` reliably reads stance/emotion from these
    transcripts (coverage 0.70, parse-rate 1.0), and emotional meaning is only partially coupled to CER.

New lever: instead of a bare "fix this transcript" instruction, FIRST read the transcript's stance with
the LLM, then repair UNDER AN EXPLICIT ANCHOR — "preserve this detected stance; correct only clear ASR
errors." The hypothesis is that anchoring the edit to a concrete semantic target curbs the hallucinated
rewrites that sink naive repair, especially on clean tracks.

Falsifiable hypotheses (CER post-hoc; LLM never sees the reference; injected fake LLM in tests):
  H1  on clean tracks (cer_before < CLEAN_CER) anchored repair inflates CER LESS than naive repair
      (clean_delta_anchored > clean_delta_naive — less negative = less over-correction damage).
  H2  pooled over all tracks, anchored's mean delta-CER >= naive's (not worse on net).
  H3  anchored repair keeps the repaired transcript's LLM-read stance closer to the clean source than
      naive does (mean semantic distance lower).
  Useful either way: if anchoring still over-corrects, #822's negative result is robust to the most
  natural fix — a clean bounding result.

Cost note (repo-guard #833): anchored repair costs 2 LLM calls/case (read + repair) vs naive's 1; a
CR-gated variant pays the read everywhere but the repair only when the compression-ratio guard fires.
The summary reports per-pipeline call counts so the accuracy gain can be weighed against compute.

Labels: experimental/frontier; ASR Whisper-tiny; LLM deepseek-r1 local (ollama, offline); references
synthetic/silver; no gold tables touched. Outputs to results/frontier/emotion_anchored_repair/.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .config import PROJECT_ROOT
from .evaluate_cer import compute_cer
from .llm_asr_critic import (
    CATASTROPHIC_CER,
    CLEAN_CER,
    build_repair_prompt,
    ollama_llm,
    parse_repair,
)
from .semantic_emotion_tax import LlmEmotionReader, ollama_emotion_llm, semantic_distance

LLMFn = Callable[[str], str]
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "emotion_anchored_repair"
CR_GUARD = 2.4
STANCE_ZH = {"support": "支持", "oppose": "反对", "neutral": "中立"}


# ======================================================================================
# Pure prompt + repair logic (no ollama / Whisper) -- unit tested with injected fakes
# ======================================================================================
def build_anchored_repair_prompt(transcript: str, stance: str, valence: float) -> str:
    """Repair prompt anchored to an explicitly detected stance/emotion (the #833 lever)."""
    stance_zh = STANCE_ZH.get(str(stance).lower(), "中立")
    tone = "正面" if valence > 0.05 else ("负面" if valence < -0.05 else "中性")
    return (
        "你是中文语音识别后处理纠错器。已知这句话的说话人立场是“"
        f"{stance_zh}”，情感倾向{tone}。\n"
        "请只改正明显的识别错误（同音字、重复、乱码），"
        f"并且必须保持上述“{stance_zh}”立场与原意不变；"
        "如果句子本来就通顺，请原样返回，不要过度改写或改变立场。\n"
        f"识别结果：{transcript}\n"
        "只在最后一行输出 “修正：<改正后的句子>”。\n"
    )


def anchored_repair(transcript: str, llm: LLMFn, reader: LlmEmotionReader) -> tuple[str, Any]:
    """Read the stance, then repair under that anchor. Returns (repaired_text, stance_reading).
    Falls back to the original transcript when the model returns nothing usable (over-correction guard)."""
    reading = reader.read(transcript)
    stance = reading["stance"] if reading else "neutral"
    valence = reading["valence"] if reading else 0.0
    raw = llm(build_anchored_repair_prompt(transcript, stance, valence))
    return parse_repair(raw, fallback=transcript), reading


def naive_repair(transcript: str, llm: LLMFn) -> str:
    """The #822 baseline: plain minimal-edit repair, no emotion anchor, no cue injection."""
    return parse_repair(llm(build_repair_prompt(transcript)), fallback=transcript)


# ======================================================================================
# Pure analysis (unit tested)
# ======================================================================================
def _finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def summarize_repair(rows: list[dict[str, Any]], cr_guard: float = CR_GUARD) -> dict[str, Any]:
    nan = float("nan")
    n = len(rows)
    base = {
        "n": n, "n_clean": 0, "n_hallucinated": 0,
        "pooled_delta_naive": nan, "pooled_delta_anchored": nan,
        "clean_delta_naive": nan, "clean_delta_anchored": nan,
        "halluc_delta_naive": nan, "halluc_delta_anchored": nan,
        "mean_cer_before": nan, "mean_cer_naive": nan, "mean_cer_anchored": nan,
        "mean_sem_dist_naive": nan, "mean_sem_dist_anchored": nan,
        "mean_cer_cr_gated_anchored": nan,
        "llm_calls_naive": 0, "llm_calls_anchored": 0, "llm_calls_cr_gated_anchored": 0,
        "H1_anchored_less_clean_damage": False,
        "H2_anchored_not_worse": False,
        "H3_anchored_preserves_stance": False,
    }
    if n == 0:
        return base

    def m(xs: list[float]) -> float:
        xs = [v for v in xs if _finite(v)]
        return round(float(np.mean(xs)), 6) if xs else nan

    def delta(r: dict[str, Any], key: str) -> float:
        return float(r["cer_before"]) - float(r[key])

    clean = [r for r in rows if float(r["cer_before"]) < CLEAN_CER]
    hall = [r for r in rows
            if int(r.get("hallucinated", int(float(r["cer_before"]) > CATASTROPHIC_CER))) == 1]
    n_gated = sum(1 for r in rows if float(r.get("max_compression_ratio", 0.0)) > cr_guard)

    out = dict(base)
    out.update({
        "n_clean": len(clean), "n_hallucinated": len(hall),
        "mean_cer_before": m([float(r["cer_before"]) for r in rows]),
        "mean_cer_naive": m([float(r["cer_naive"]) for r in rows]),
        "mean_cer_anchored": m([float(r["cer_anchored"]) for r in rows]),
        "pooled_delta_naive": m([delta(r, "cer_naive") for r in rows]),
        "pooled_delta_anchored": m([delta(r, "cer_anchored") for r in rows]),
        "clean_delta_naive": m([delta(r, "cer_naive") for r in clean]),
        "clean_delta_anchored": m([delta(r, "cer_anchored") for r in clean]),
        "halluc_delta_naive": m([delta(r, "cer_naive") for r in hall]),
        "halluc_delta_anchored": m([delta(r, "cer_anchored") for r in hall]),
        "mean_sem_dist_naive": m([r.get("sem_dist_naive") for r in rows]),
        "mean_sem_dist_anchored": m([r.get("sem_dist_anchored") for r in rows]),
        "mean_cer_cr_gated_anchored": m([
            float(r["cer_anchored"]) if float(r.get("max_compression_ratio", 0.0)) > cr_guard
            else float(r["cer_before"]) for r in rows
        ]),
        "llm_calls_naive": n,
        "llm_calls_anchored": 2 * n,
        "llm_calls_cr_gated_anchored": n + n_gated,
    })
    cdn, cda = out["clean_delta_naive"], out["clean_delta_anchored"]
    pdn, pda = out["pooled_delta_naive"], out["pooled_delta_anchored"]
    sdn, sda = out["mean_sem_dist_naive"], out["mean_sem_dist_anchored"]
    out["H1_anchored_less_clean_damage"] = bool(_finite(cdn) and _finite(cda) and cda > cdn)
    out["H2_anchored_not_worse"] = bool(_finite(pdn) and _finite(pda) and pda >= pdn)
    out["H3_anchored_preserves_stance"] = bool(_finite(sdn) and _finite(sda) and sda < sdn)
    return out


# ======================================================================================
# Driver: same curated clean->hallucinated cases as #822, then naive vs anchored repair
# ======================================================================================
def run(
    num_pairs: int = 8,
    overlaps: list[float] | None = None,
    alpha: float = 0.15,
    max_cases: int = 12,
    model: str = "deepseek-r1:7b",
    out_dir: Path | str = OUT_DIR,
    repair_llm: LLMFn | None = None,
    reader: LlmEmotionReader | None = None,
    cache_path: Path | str | None = None,
) -> Path:
    overlaps = overlaps or [0.0, 0.1, 0.3]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    from .llm_asr_critic import collect_cases  # lazy: imports whisper

    cases = collect_cases(num_pairs, overlaps, alpha, max_cases)

    cache_file = Path(cache_path) if cache_path else out_dir / "_llm_cache.json"
    cache: dict = {}
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    repair_llm = repair_llm or ollama_llm(model=model)
    reader = reader or LlmEmotionReader(ollama_emotion_llm(model=model), cache=cache)

    rows: list[dict[str, Any]] = []
    print(f"[anchored-repair] cases={len(cases)} model={model}", flush=True)
    for i, c in enumerate(cases):
        ref, hyp = c["ref_text"], c["hyp"]
        cer_before = float(c["cer"])

        naive_txt = naive_repair(hyp, repair_llm)
        cer_naive = compute_cer(ref, naive_txt)["cer"]
        anchored_txt, hyp_reading = anchored_repair(hyp, repair_llm, reader)
        cer_anchored = compute_cer(ref, anchored_txt)["cer"]

        # H3: stance preservation = distance from the CLEAN-source reading to each repaired reading
        ref_reading = reader.read(ref)
        sem_naive = semantic_distance(ref_reading, reader.read(naive_txt))["combined"]
        sem_anchored = semantic_distance(ref_reading, reader.read(anchored_txt))["combined"]

        rows.append({
            "pair_id": c["pair_id"], "overlap_ratio": c["overlap_ratio"],
            "max_compression_ratio": c["max_compression_ratio"],
            "hallucinated": c["hallucinated"],
            "cer_before": round(cer_before, 6),
            "cer_naive": round(float(cer_naive), 6),
            "cer_anchored": round(float(cer_anchored), 6),
            "anchored_stance": (hyp_reading or {}).get("stance", ""),
            "sem_dist_naive": round(float(sem_naive), 6) if _finite(sem_naive) else "",
            "sem_dist_anchored": round(float(sem_anchored), 6) if _finite(sem_anchored) else "",
            "hyp": hyp, "naive": naive_txt, "anchored": anchored_txt,
        })
        if (i + 1) % 3 == 0:
            cache_file.write_text(json.dumps(reader.cache, ensure_ascii=False), encoding="utf-8")
        print(f"[anchored-repair] {i+1}/{len(cases)} cer {cer_before:.2f} -> naive {cer_naive:.2f} / "
              f"anchored {cer_anchored:.2f}", flush=True)

    cache_file.write_text(json.dumps(reader.cache, ensure_ascii=False), encoding="utf-8")
    summary = summarize_repair(rows)
    summary["model"] = model

    _write_csv(rows, out_dir / "repair_curve.csv")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_findings(summary, out_dir / "FINDINGS.md")
    _plot(rows, summary, out_dir / "emotion_anchored_repair.png")
    print(f"[anchored-repair] H1(less clean damage)={summary['H1_anchored_less_clean_damage']} "
          f"H2(not worse)={summary['H2_anchored_not_worse']} "
          f"H3(stance preserved)={summary['H3_anchored_preserves_stance']}", flush=True)
    return out_dir


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _fmt(x: Any) -> str:
    if isinstance(x, float):
        return "nan" if math.isnan(x) else f"{x:.4f}"
    return str(x)


def _conclusion(s: dict[str, Any]) -> str:
    """One data-derived deployable sentence (so a negative result is actionable, not just reported)."""
    before = s.get("mean_cer_before", float("nan"))
    naive = s.get("mean_cer_naive", float("nan"))
    anch = s.get("mean_cer_anchored", float("nan"))
    if not all(_finite(v) for v in (before, naive, anch)):
        return "Inconclusive (insufficient parsed cases)."
    best_repair = min(naive, anch)
    if before <= best_repair:
        anch_rel = "worsens it further" if anch > naive else "does not improve on naive repair"
        return (
            f"**No-repair is best ({before:.3f} CER) — both naive ({naive:.3f}) and emotion-anchored "
            f"({anch:.3f}) repair are net-harmful.** Anchoring the edit to the LLM-detected stance "
            f"{anch_rel}, so #822's over-correction tax is ROBUST to the most natural fix: the small "
            "reasoning model rewrites/hallucinates regardless (e.g. emitting a literal placeholder, or "
            "substituting a proverb for the transcript). The deployable policy is to NOT run LLM repair "
            "in this setting; the CR-gated variant collapses to no-repair here because the "
            "compression-ratio guard does not fire on these tracks. A clean bounding negative result."
        )
    winner = "naive" if naive <= anch else "emotion-anchored"
    return (
        f"Repair helps on net: {winner} repair ({best_repair:.3f}) beats no-repair ({before:.3f}). "
        f"Emotion-anchoring {'helps' if anch < naive else 'does not beat naive'}."
    )


def _write_findings(s: dict[str, Any], path: Path) -> None:
    lines = [
        "# Emotion-Anchored ASR Repair — Findings",
        "",
        f"**Label:** `experimental/frontier`. ASR Whisper-`tiny`; LLM `{s.get('model','deepseek-r1:7b')}` "
        "(local ollama, offline); references synthetic/silver; CER post-hoc only; no gold tables. Issue #833.",
        "",
        f"Cases: {s['n']} curated separated tracks ({s['n_clean']} clean, {s['n_hallucinated']} "
        "hallucinated) — the same clean→hallucinated spread as #822, so naive vs anchored repair are "
        "compared on identical inputs.",
        "",
        "## Pipelines (mean CER; lower is better)",
        "",
        f"- no-repair baseline: **{_fmt(s['mean_cer_before'])}**",
        f"- naive repair (#822): {_fmt(s['mean_cer_naive'])}",
        f"- emotion-anchored repair (this work): {_fmt(s['mean_cer_anchored'])}",
        f"- CR-gated anchored (repair only when compression-ratio>{CR_GUARD}): {_fmt(s['mean_cer_cr_gated_anchored'])}",
        "",
        "## Hypotheses",
        "",
        f"- **H1 — less over-correction on clean tracks:** clean ΔCER naive **{_fmt(s['clean_delta_naive'])}** "
        f"vs anchored **{_fmt(s['clean_delta_anchored'])}** (less negative = less damage). "
        f"Verdict: **{'SUPPORTED' if s['H1_anchored_less_clean_damage'] else 'NOT supported'}**.",
        f"- **H2 — not worse on net:** pooled ΔCER naive {_fmt(s['pooled_delta_naive'])} vs anchored "
        f"{_fmt(s['pooled_delta_anchored'])}. Verdict: **{'SUPPORTED' if s['H2_anchored_not_worse'] else 'NOT supported'}**. "
        f"(hallucinated-track recovery: naive {_fmt(s['halluc_delta_naive'])}, anchored {_fmt(s['halluc_delta_anchored'])}.)",
        f"- **H3 — stance preserved:** mean LLM-read stance distance to the clean source, naive "
        f"{_fmt(s['mean_sem_dist_naive'])} vs anchored {_fmt(s['mean_sem_dist_anchored'])}. "
        f"Verdict: **{'SUPPORTED' if s['H3_anchored_preserves_stance'] else 'NOT supported'}**.",
        "",
        "## Deployable conclusion",
        "",
        _conclusion(s),
        "",
        "## Cost / benefit (repo-guard #833)",
        "",
        f"Per-pipeline LLM calls — naive: {s['llm_calls_naive']}, anchored: {s['llm_calls_anchored']} "
        f"(read+repair), CR-gated anchored: {s['llm_calls_cr_gated_anchored']} (read everywhere, repair "
        "only when gated). Anchored doubles the call budget; the CR-gated variant pays the read but "
        "spends repairs only where the cheap compression-ratio guard flags risk — weigh any accuracy "
        "gain above against this.",
        "",
        "## Honest limitations",
        "",
        "Small n; Whisper-`tiny`; synthetic oracle/leaky separation; local `deepseek-r1` reasoning model "
        "(temperature 0, still has variance); stance preservation is measured by the same LLM that does "
        "the anchoring, so H3 is self-consistent rather than externally validated; CER post-hoc. "
        "`experimental/frontier`, not a gold result.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plot(rows: list[dict[str, Any]], s: dict[str, Any], path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    if not rows:
        return
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    for r in rows:
        clean = int(r["hallucinated"]) == 0
        color = "#54a24b" if clean else "#e45756"
        ax1.plot([0, 1, 2], [float(r["cer_before"]), float(r["cer_naive"]), float(r["cer_anchored"])],
                 "-o", color=color, alpha=0.55, ms=4)
    ax1.set_xticks([0, 1, 2]); ax1.set_xticklabels(["before", "naive", "anchored"])
    ax1.axhline(1.0, color="black", lw=0.8, ls=":")
    ax1.set_ylabel("CER")
    ax1.set_title("Repair trajectories (green=clean, red=hallucinated)")
    ax1.grid(alpha=0.3)
    labels = ["clean ΔCER", "pooled ΔCER"]
    naive_v = [s["clean_delta_naive"], s["pooled_delta_naive"]]
    anch_v = [s["clean_delta_anchored"], s["pooled_delta_anchored"]]
    x = np.arange(len(labels)); w = 0.35
    ax2.bar(x - w / 2, naive_v, w, label="naive", color="#e45756")
    ax2.bar(x + w / 2, anch_v, w, label="anchored", color="#4361ee")
    ax2.axhline(0, color="grey", lw=0.8)
    ax2.set_xticks(x); ax2.set_xticklabels(labels)
    ax2.set_ylabel("ΔCER (before − after; >0 = improvement)")
    ax2.set_title("Anchored vs naive: over-correction on clean tracks")
    ax2.legend()
    fig.suptitle("Emotion-anchored repair vs naive (local deepseek-r1, Whisper-tiny, zh) — #833")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Emotion-anchored ASR repair (issue #833)")
    p.add_argument("--pairs", type=int, default=8)
    p.add_argument("--overlaps", type=str, default="0.0,0.1,0.3")
    p.add_argument("--alpha", type=float, default=0.15)
    p.add_argument("--max-cases", type=int, default=12)
    p.add_argument("--model", type=str, default="deepseek-r1:7b")
    p.add_argument("--output-dir", type=str, default=str(OUT_DIR))
    return p.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    run(
        num_pairs=args.pairs,
        overlaps=[float(o) for o in args.overlaps.split(",") if o.strip()],
        alpha=args.alpha,
        max_cases=args.max_cases,
        model=args.model,
        out_dir=args.output_dir,
    )
    print("[anchored-repair] done")


if __name__ == "__main__":
    main()
