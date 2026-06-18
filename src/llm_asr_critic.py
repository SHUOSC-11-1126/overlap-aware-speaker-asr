"""Prosody-grounded LLM x ASR critic: repair separation-induced hallucination + reference-free QE.

Direction B of the emotion/LLM frontier, grounded in the 2025/26 literature (see
docs/emotion_frontier.md References): generative error correction (GER; HyPoradise, ProGRes), the
documented WEAK PROSODY PERCEPTION of speech-LLMs (EmotionThinker, VoxEmo, ProsodyLM), and the
over-correction-in-ill-posed-regions failure mode (Prompt-Based ASR with Speech LLMs, Jan 2026).

Two design commitments:
  1. PROSODY GROUNDING. Because speech-LLMs perceive prosody poorly, we inject EXPLICIT prosodic
     (src/prosody.py) and lexical-emotion (src/lexical_emotion.py) cues into the prompt as text, rather
     than hoping the LLM hears them. This also lets a TEXT LLM (deepseek-r1) reason about affect.
  2. GENERATION-EVALUATION SEPARATION (borrowed from ceilf6/code-tape, this repo's harness lineage):
     the transcript REPAIRER and the quality JUDGE are separate roles / separate LLM calls, so the
     judge never grades its own correction in the same breath. This reduces self-assessment bias.

Falsifiable claims (CER is post-hoc; the LLM never sees the reference):
  C1 (QE)      the judge's reference-free quality score correlates (negatively) with true CER — i.e.
               LLM-as-judge is a usable reference-free quality estimator for separated-track ASR.
  C2 (repair)  GER reduces CER on separation-induced HALLUCINATED tracks (CER>1) WITHOUT worsening
               clean tracks (the over-correction guard holds).
  Kill: if the judge score is uncorrelated with CER AND repair does not net-reduce hallucinated CER (or
        harms clean tracks), the LLM critic adds nothing over the reference-free compression-ratio guard.

The LLM is dependency-injected (LLMFn = Callable[[str], str]); unit tests use a fake. The real backend
is local deepseek-r1 via ollama (offline; weights already on disk). Labels: experimental/frontier;
ASR Whisper-tiny; references synthetic/silver. No gold tables touched. Outputs to
results/frontier/llm_asr_critic/.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .config import PROJECT_ROOT

LLMFn = Callable[[str], str]
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "llm_asr_critic"
CATASTROPHIC_CER = 1.0
CLEAN_CER = 0.30


# ======================================================================================
# Pure parsing + prompt logic (no ollama) -- unit tested with an injected fake LLM
# ======================================================================================
def strip_think(text: str) -> str:
    """Remove deepseek-r1 <think>...</think> reasoning. An unclosed/truncated think block is dropped
    entirely (everything from <think> on), so partial reasoning never leaks into the answer."""
    text = re.sub(r"(?s)<think>.*?</think>", "", text)
    text = re.sub(r"(?s)<think>.*$", "", text)  # unclosed
    return text.strip()


def parse_score(text: str) -> float | None:
    """Extract `SCORE: x` (x in [0,1], clamped). None if absent."""
    m = re.search(r"SCORE:\s*(-?[0-9]*\.?[0-9]+)", strip_think(text), re.IGNORECASE)
    if not m:
        return None
    return max(0.0, min(1.0, float(m.group(1))))


def parse_repair(text: str, fallback: str) -> str:
    """Extract the corrected sentence. Prefer a `修正：`/`修正:`/`Corrected:` marker; else the last
    non-empty line of the post-think output. Falls back to `fallback` (the original) when empty —
    the over-correction guard's last line of defence."""
    body = strip_think(text)
    m = re.search(r"(?:修正|更正|改正|Corrected)\s*[:：]\s*(.+)", body)
    cand = m.group(1).strip() if m else ""
    if not cand:
        lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
        cand = lines[-1] if lines else ""
    cand = cand.strip().strip('"“”')
    return cand or fallback


def build_judge_prompt(transcript: str) -> str:
    return (
        "你是中文语音识别质量评审。判断下面这句识别结果是正常通顺的句子，"
        "还是明显的识别错误/重复幻觉/乱码。只在最后一行输出 “SCORE: x”，"
        "x 为 0 到 1 的小数（1=完全正常，0=严重错误），不要解释。\n"
        f"识别结果：{transcript}\n"
    )


def build_repair_prompt(transcript: str, prosody_summary: str = "", lexical_summary: str = "") -> str:
    cues = ""
    if prosody_summary or lexical_summary:
        cues = ("已知说话人副语言线索（仅供参考，不要照抄进文本）："
                f"{prosody_summary} {lexical_summary}\n")
    return (
        "你是中文语音识别后处理纠错器。只改正明显的识别错误（同音字、重复、乱码），"
        "保持原意与说话风格；如果句子本来就通顺，请原样返回，不要过度改写。\n"
        f"{cues}"
        f"识别结果：{transcript}\n"
        "只在最后一行输出 “修正：<改正后的句子>”。\n"
    )


def judge_quality(transcript: str, llm: LLMFn) -> float:
    """Reference-free quality score in [0,1] (NaN if the model gave no parseable score)."""
    score = parse_score(llm(build_judge_prompt(transcript)))
    return float("nan") if score is None else score


def repair_transcript(transcript: str, llm: LLMFn, prosody_summary: str = "", lexical_summary: str = "") -> str:
    """Generative error correction with an over-correction guard (keeps the original if the model
    returns nothing usable)."""
    return parse_repair(llm(build_repair_prompt(transcript, prosody_summary, lexical_summary)), fallback=transcript)


# ======================================================================================
# Pure analysis (unit tested)
# ======================================================================================
def _pearson(x: list[float], y: list[float]) -> float:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if x.size < 2 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def summarize_critic(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """C1: corr(judge_score, CER) vs the cheap compression-ratio signal (which QE signal wins?).
    C2: mean CER reduction (before-after) on hallucinated vs clean, plus whether a reference-free gate
    (compression-ratio or the judge itself) makes selective repair safe."""
    js = [float(r["judge_score"]) for r in rows]
    cer = [float(r["cer"]) for r in rows]
    cr = [float(r.get("max_compression_ratio", 0.0)) for r in rows]
    hall = [r for r in rows if int(r.get("hallucinated", int(float(r["cer"]) > CATASTROPHIC_CER))) == 1]
    clean = [r for r in rows if float(r["cer_before"]) < CLEAN_CER]

    def mean_red(rs: list[dict[str, Any]]) -> float:
        vals = [float(r["cer_before"]) - float(r["cer_after"]) for r in rs]
        return round(float(np.mean(vals)), 6) if vals else float("nan")

    def gated_after(gate: Callable[[dict[str, Any]], bool]) -> float:
        # selective repair: apply the LLM repair only when the gate fires, else keep the original
        vals = [float(r["cer_after"]) if gate(r) else float(r["cer_before"]) for r in rows]
        return round(float(np.mean(vals)), 6) if vals else float("nan")

    pj, pc = _pearson(js, cer), _pearson(cr, cer)
    return {
        "n": len(rows), "n_hallucinated": len(hall), "n_clean": len(clean),
        "pearson_judge_cer": round(pj, 6),
        "pearson_cr_cer": round(pc, 6),
        "qe_winner": ("compression_ratio" if abs(pc) > abs(pj) else "llm_judge") if (pc == pc and pj == pj) else "n/a",
        "mean_cer_reduction_hallucinated": mean_red(hall),
        "mean_cer_reduction_clean": mean_red(clean),
        "mean_cer_before": round(float(np.mean([float(r["cer_before"]) for r in rows])), 6) if rows else float("nan"),
        "mean_cer_after_naive_repair": round(float(np.mean([float(r["cer_after"]) for r in rows])), 6) if rows else float("nan"),
        "mean_cer_after_cr_gated": gated_after(lambda r: float(r.get("max_compression_ratio", 0.0)) > 2.4),
        "mean_cer_after_judge_gated": gated_after(lambda r: r.get("judge_score") not in ("", None) and float(r["judge_score"]) < 0.5),
    }


# ======================================================================================
# Real backend: local deepseek-r1 via ollama (offline; lazy)
# ======================================================================================
def ollama_llm(model: str = "deepseek-r1:7b", num_predict: int = 700, host: str = "http://localhost:11434") -> LLMFn:
    import urllib.request

    def call(prompt: str) -> str:
        body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                           "options": {"temperature": 0.0, "num_predict": num_predict}}).encode()
        req = urllib.request.Request(f"{host}/api/generate", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.load(resp).get("response", "")

    return call


# ======================================================================================
# Driver: curate separated-track cases spanning clean->hallucinated, then judge + repair
# ======================================================================================
def _prosody_summary(wav: np.ndarray) -> str:
    from .prosody import arousal_index, prosodic_features
    a = arousal_index(prosodic_features(np.asarray(wav, dtype=np.float32)))
    level = "高唤醒/激动" if a > 1.0 else ("中等" if a > 0.6 else "低唤醒/平静")
    return f"声学唤醒度={a:.2f}({level})"


def _lexical_summary(text: str) -> str:
    from .lexical_emotion import lexical_emotion
    e = lexical_emotion(text)
    pol = "正面" if e["valence"] > 0.05 else ("负面" if e["valence"] < -0.05 else "中性")
    return f"文本情感倾向={pol}(valence={e['valence']:.2f})"


def collect_cases(num_pairs: int, overlaps: list[float], alpha: float, max_cases: int) -> list[dict[str, Any]]:
    """Build separated single-speaker tracks across overlaps/leakage, transcribe, keep a spread of CER
    (a mix of clean and hallucinated) so both critic claims are testable."""
    import whisper

    from .emotion_separation_tax import active_region, leak
    from .evaluate_cer import compute_cer
    from .generate_synthetic_overlap import build_mixture, read_mono_audio
    from .separation_tax_phase import select_pairs, transcribe_with_signals

    plans = select_pairs(num_pairs)
    model = whisper.load_model("tiny")
    cands: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        for overlap in overlaps:
            _, t1, t2, _ = build_mixture(s1, s2, overlap)
            for wav, ref_text in ((leak(t1, t2, alpha), plan.con_text), (leak(t2, t1, alpha), plan.pro_text)):
                sig = transcribe_with_signals(model, np.asarray(wav, dtype=np.float32), "greedy")
                hyp = sig["text"]
                cer = compute_cer(ref_text, hyp)["cer"]
                cands.append({
                    "pair_id": pi, "overlap_ratio": overlap, "ref_text": ref_text, "hyp": hyp,
                    "cer": round(cer, 6), "max_compression_ratio": round(float(sig["max_compression_ratio"]), 4),
                    "prosody_summary": _prosody_summary(wav), "lexical_summary": _lexical_summary(hyp),
                    "hallucinated": int(cer > CATASTROPHIC_CER),
                })
    # Balanced spread so BOTH claims are testable: ~half hallucinated (CER>1), ~half clean
    # (lowest CER). A QE judge can only be evaluated if clean cases are present too.
    hall = sorted([c for c in cands if c["hallucinated"]], key=lambda c: c["cer"])
    clean = sorted([c for c in cands if not c["hallucinated"]], key=lambda c: c["cer"])
    half = max(1, max_cases // 2)

    def spread(xs: list[dict[str, Any]], k: int) -> list[dict[str, Any]]:
        if len(xs) <= k:
            return xs
        step = len(xs) / k
        return [xs[int(i * step)] for i in range(k)]

    keep = spread(clean, half) + spread(hall, max_cases - half)
    return keep


def run_critic(out_dir: Path, num_pairs: int, overlaps: list[float], alpha: float, max_cases: int,
               model: str, ground: bool = True) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = collect_cases(num_pairs, overlaps, alpha, max_cases)
    from .evaluate_cer import compute_cer

    llm = ollama_llm(model=model)
    print(f"[llm-critic] cases={len(cases)} model={model} ground={ground}", flush=True)
    rows: list[dict[str, Any]] = []
    for i, c in enumerate(cases):
        score = judge_quality(c["hyp"], llm)                       # JUDGE role
        ps = c["prosody_summary"] if ground else ""
        ls = c["lexical_summary"] if ground else ""
        repaired = repair_transcript(c["hyp"], llm, ps, ls)        # REPAIR role (separate call)
        cer_after = compute_cer(c["ref_text"], repaired)["cer"]
        rows.append({
            "pair_id": c["pair_id"], "overlap_ratio": c["overlap_ratio"],
            "cer": c["cer"], "judge_score": round(score, 6) if score == score else "",
            "cer_before": c["cer"], "cer_after": round(cer_after, 6),
            "cer_reduction": round(c["cer"] - cer_after, 6),
            "hallucinated": c["hallucinated"], "max_compression_ratio": c["max_compression_ratio"],
            "hyp": c["hyp"], "repaired": repaired,
        })
        print(f"[llm-critic] {i + 1}/{len(cases)} cer={c['cer']:.2f} score={rows[-1]['judge_score']} "
              f"cer_after={cer_after:.2f}", flush=True)

    curve = out_dir / "critic_curve.csv"
    with curve.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    score_rows = [r for r in rows if r["judge_score"] != ""]
    summary = summarize_critic([{**r, "judge_score": r["judge_score"]} for r in score_rows])
    summary["model"] = model
    summary["grounded"] = ground
    (out_dir / "critic_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[llm-critic] C1 corr(judge,CER)={summary['pearson_judge_cer']}  "
          f"C2 CER reduction hallucinated={summary['mean_cer_reduction_hallucinated']} "
          f"clean={summary['mean_cer_reduction_clean']}", flush=True)
    print(f"[llm-critic] wrote {curve} + critic_summary.json (rows={len(rows)})", flush=True)
    return {"summary": summary, "n_rows": len(rows)}


def render_figure(out_dir: Path) -> Path | None:
    """Two panels: (C1) reference-free QE — judge score & compression-ratio vs CER; (C2) repair
    before→after CER by case. Reads the committed critic_curve.csv."""
    curve = out_dir / "critic_curve.csv"
    if not curve.exists():
        return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    with curve.open(encoding="utf-8-sig") as fh:
        rows = [r for r in csv.DictReader(fh)]
    cer = [float(r["cer"]) for r in rows]
    cr = [float(r["max_compression_ratio"]) for r in rows]
    js = [float(r["judge_score"]) for r in rows if r["judge_score"] != ""]
    cer_j = [float(r["cer"]) for r in rows if r["judge_score"] != ""]
    s = summarize_critic([r for r in rows if r["judge_score"] != ""])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.8))
    ax1.scatter(cer_j, js, color="#4c78a8", label=f"LLM judge (r={s['pearson_judge_cer']})")
    ax1b = ax1.twinx()
    ax1b.scatter(cer, cr, color="#e45756", marker="x", label=f"compression ratio (r={s['pearson_cr_cer']})")
    ax1.set_xlabel("true CER"); ax1.set_ylabel("LLM judge score", color="#4c78a8")
    ax1b.set_ylabel("compression ratio", color="#e45756")
    ax1.set_title(f"Reference-free QE: cheap signal wins (winner={s['qe_winner']})")
    ax1.grid(alpha=0.3)
    for r in rows:
        c = "#e45756" if int(r["hallucinated"]) == 1 else "#54a24b"
        ax2.plot([0, 1], [float(r["cer_before"]), float(r["cer_after"])], "-o", color=c, alpha=0.6, ms=4)
    ax2.set_xticks([0, 1]); ax2.set_xticklabels(["before", "after repair"])
    ax2.axhline(1.0, color="black", lw=0.8, ls=":")
    ax2.set_ylabel("CER"); ax2.set_ylim(0, min(3.0, max(cer) + 0.3))
    ax2.set_title(f"GER repair over-corrects (clean Δ={s['mean_cer_reduction_clean']}, "
                  f"halluc Δ={s['mean_cer_reduction_hallucinated']})")
    ax2.grid(alpha=0.3)
    fig.suptitle("Local 7B LLM × ASR critic: judge dominated by compression-ratio; repair net-harms (Whisper-tiny, zh)")
    fig.tight_layout()
    fig_path = out_dir / "llm_asr_critic.png"
    fig.savefig(fig_path, dpi=160)
    plt.close(fig)
    print(f"[llm-critic] wrote {fig_path}", flush=True)
    return fig_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prosody-grounded LLM x ASR critic experiment (frontier).")
    p.add_argument("--pairs", type=int, default=8)
    p.add_argument("--overlaps", type=str, default="0.0,0.1,0.3")
    p.add_argument("--alpha", type=float, default=0.15)
    p.add_argument("--max-cases", type=int, default=16)
    p.add_argument("--model", type=str, default="deepseek-r1:7b")
    p.add_argument("--no-ground", action="store_true", help="Ablate the prosody/lexical cue injection.")
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    run_critic(Path(args.out_dir), args.pairs, [float(o) for o in args.overlaps.split(",") if o.strip()],
               args.alpha, args.max_cases, args.model, ground=not args.no_ground)


if __name__ == "__main__":
    main()
