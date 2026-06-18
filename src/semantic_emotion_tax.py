"""The Semantic Emotion Tax: does separation distort the emotion an LLM reads? (experimental/frontier)

Issue #831. Unifies two project directions — ASR×LLM synergy + emotion — by adding a THIRD emotion
modality the project lacked: *semantic* emotion read by a local LLM (deepseek-r1 via ollama, fully
offline). The project already has acoustic prosody (`prosody.py`, arousal-only, valence-blind) and a
lexical reader (`lexical_emotion.py`) that — per its own FINDINGS — fires on only ~2/16 snippets
because debate emotion is largely *implicit*. The 2024–26 ASR×LLM literature (GenSEC-LLM
arXiv:2409.09785; R3 arXiv:2409.15551) makes post-ASR emotion recognition an LLM task, but on clean
single-speaker corpora. Nobody has asked whether the ASR errors *induced by overlap + separation*
distort the emotional meaning an LLM recovers. This module measures exactly that, on the project's
controlled overlap×separation grid with silver clean-text references.

Construct (mirrors the acoustic Emotional Separation Tax, `emotion_separation_tax.py`):
  For each speaker k in a synthetic mixture we have three transcripts — the clean source text (REF,
  silver), the ASR of the raw mixture (MIXED, both speakers), and the ASR of the separated track k
  (SEP). An LLM reads {valence, arousal, stance} from each. Semantic distance d_sem(hyp, ref) is the
  emotion-space distance between an ASR hypothesis reading and the clean-text reading.
    semantic_benefit = d_sem(MIXED, REF) - d_sem(SEP, REF)
    > 0  separation RECOVERS the speaker's emotional meaning
    < 0  separation HURTS it (the mixture already carried it; separation only added ASR error)

Falsifiable hypotheses (emotion has NO ground truth -> silver-anchored on clean source text; the LLM
is dependency-injected so all logic is unit-tested offline with a fake LLM):
  H1 (coverage)  the LLM yields a non-degenerate, graded reading on a far larger fraction of snippets
                 than the lexicon's ~2/16. Falsified if the LLM also collapses to neutral/unparseable.
  H2 (semantic tax)  semantic_benefit is overlap-dependent (<=0 low overlap, >0 high overlap — the
                 emotional twin of the ASR separation tax) AND d_sem tracks CER. USEFUL EITHER WAY: if
                 d_sem stays ~0 even at high CER, the emotional *meaning* is robust to transcription
                 error, which STRENGTHENS the decoupling recipe (text-route emotion is error-robust).
  H3 (modality structure)  is LLM-semantic emotion a complementary third modality, or redundant with
                 acoustic arousal / lexical valence? Report pairwise Pearson/Spearman.
  Kill criterion: LLM readings unparseable/degenerate on >50% of inputs (local reasoning model too weak
                 for offline implicit-emotion reading — itself a bounding result).

Labels: experimental/frontier; ASR Whisper-tiny (cached transcripts); LLM deepseek-r1 (local ollama);
references synthetic/silver (clean source text); CER post-hoc only; NO gold tables touched.
Outputs to results/frontier/semantic_emotion_tax/.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np

from .config import PROJECT_ROOT
from .evaluate_cer import compute_cer
from .lexical_emotion import lexical_emotion
from .prosody import arousal_index, prosodic_features

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "semantic_emotion_tax"
REF_DIR = PROJECT_ROOT / "resources" / "synthetic_overlap" / "references"
TRANS_DIR = PROJECT_ROOT / "results" / "synthetic_transcripts_raw"

# Canonical overlap level per tier (the project's standard 5-point axis). The per-sample silver
# overlap_ratio drifts to fine-grained values (0.125, 0.175, ...) that fragment the tax curve into
# n=2 bins; binning by tier gives clean n=10 levels, matching emotion_separation_tax's OVERLAPS.
TIER_OVERLAP = {
    "SyntheticNoOverlap": 0.0,
    "SyntheticLightOverlap": 0.1,
    "SyntheticMidOverlap": 0.3,
    "SyntheticHeavyOverlap": 0.5,
    "SyntheticOppositeOverlap": 0.8,
}

EMOTION_PROMPT = (
    "你是情感分析器。阅读下面这段中文辩论转写，判断说话人的情感倾向。\n"
    "只输出一行 JSON，不要解释："
    '{{"valence": <-1到1的浮点,负面到正面>, "arousal": <0到1,平静到激动>, '
    '"stance": "<support|oppose|neutral>"}}\n\n'
    '转写："{text}"\n'
)

_VALID_STANCE = ("support", "oppose", "neutral")


# ======================================================================================
# Pure logic (no ollama / Whisper / librosa) -- unit tested
# ======================================================================================
_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_OBJ_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


def _to_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def parse_llm_emotion(raw: Optional[str]) -> Optional[dict]:
    """Robustly extract {'valence','arousal','stance'} from an LLM completion.

    Handles deepseek-r1's <think>...</think> reasoning trace, ```json fences, and bare trailing
    objects. Picks the LAST valid emotion object (the model's final answer). Clamps valence to
    [-1,1], arousal to [0,1], normalizes stance to {support,oppose,neutral}. Returns None if no
    object carrying any emotion key is found.
    """
    if not raw or not isinstance(raw, str):
        return None
    text = _THINK_RE.sub("", raw)
    objs = _OBJ_RE.findall(text) or _OBJ_RE.findall(raw)
    for cand in reversed(objs):
        try:
            obj = json.loads(cand)
        except Exception:
            continue
        if not isinstance(obj, dict) or not any(k in obj for k in ("valence", "arousal", "stance")):
            continue
        v = _to_float(obj.get("valence"))
        a = _to_float(obj.get("arousal"))
        v = 0.0 if v is None else _clamp(v, -1.0, 1.0)
        a = 0.0 if a is None else _clamp(a, 0.0, 1.0)
        s = str(obj.get("stance", "neutral")).strip().lower()
        if s not in _VALID_STANCE:
            s = "neutral"
        return {"valence": round(v, 6), "arousal": round(a, 6), "stance": s}
    return None


def is_degenerate(reading: Optional[dict]) -> bool:
    """A reading carries no signal if it is None, or neutral stance with zero valence and arousal."""
    if reading is None:
        return True
    return (
        reading.get("valence", 0.0) == 0.0
        and reading.get("arousal", 0.0) == 0.0
        and reading.get("stance", "neutral") == "neutral"
    )


def coverage_rate(readings: list[Optional[dict]]) -> float:
    """Fraction of readings that carry a signal (the H1 metric vs the lexicon's firing rate)."""
    if not readings:
        return 0.0
    return round(sum(0 if is_degenerate(r) else 1 for r in readings) / len(readings), 6)


def semantic_distance(ref: Optional[dict], hyp: Optional[dict]) -> dict:
    """Emotion-space distance between two LLM readings. NaN if either reading is missing."""
    if ref is None or hyp is None:
        nan = float("nan")
        return {"valence_dist": nan, "arousal_dist": nan, "stance_changed": nan, "combined": nan}
    vd = abs(ref["valence"] - hyp["valence"])
    ad = abs(ref["arousal"] - hyp["arousal"])
    sc = 0.0 if ref["stance"] == hyp["stance"] else 1.0
    return {
        "valence_dist": round(vd, 6),
        "arousal_dist": round(ad, 6),
        "stance_changed": sc,
        "combined": round(math.sqrt(vd * vd + ad * ad), 6),
    }


def semantic_benefit(mixed_dist: float, sep_dist: float) -> float:
    """> 0 means separation recovers the emotional meaning (lower semantic distance to clean text)."""
    return float(mixed_dist) - float(sep_dist)


def _rankdata(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, x.size + 1, dtype=np.float64)
    return ranks


def correlate(a: list[float], b: list[float]) -> dict:
    """NaN-safe Pearson + Spearman over paired samples; NaN pairs are dropped. Constant -> NaN."""
    aa = np.asarray(a, dtype=np.float64)
    bb = np.asarray(b, dtype=np.float64)
    mask = np.isfinite(aa) & np.isfinite(bb)
    aa, bb = aa[mask], bb[mask]
    out = {"pearson": float("nan"), "spearman": float("nan"), "n": int(aa.size)}
    if aa.size < 2 or np.std(aa) == 0 or np.std(bb) == 0:
        return out
    out["pearson"] = round(float(np.corrcoef(aa, bb)[0, 1]), 6)
    ar, br = _rankdata(aa), _rankdata(bb)
    if np.std(ar) > 0 and np.std(br) > 0:
        out["spearman"] = round(float(np.corrcoef(ar, br)[0, 1]), 6)
    return out


def aggregate_tax(rows: list[dict]) -> dict:
    """Per-overlap mean semantic benefit (NaN-safe) + whether the benefit sign FLIPS across overlap
    (the H2 crossover that would mirror the ASR separation tax)."""
    by_overlap: list[dict] = []
    for ov in sorted({float(r["overlap_ratio"]) for r in rows}):
        at = [r for r in rows if float(r["overlap_ratio"]) == ov]

        def _mean(key: str) -> float:
            vals = [float(r[key]) for r in at if not math.isnan(float(r[key]))]
            return round(float(np.mean(vals)), 6) if vals else float("nan")

        bens = [float(r["semantic_benefit"]) for r in at if not math.isnan(float(r["semantic_benefit"]))]
        by_overlap.append({
            "overlap_ratio": ov,
            "n": len(at),
            "n_valid": len(bens),
            "mean_semantic_benefit": _mean("semantic_benefit"),
            "mean_d_sem_mixed": _mean("d_sem_mixed"),
            "mean_d_sem_sep": _mean("d_sem_sep"),
        })
    signs = {
        np.sign(r["mean_semantic_benefit"])
        for r in by_overlap
        if not math.isnan(r["mean_semantic_benefit"]) and r["mean_semantic_benefit"] != 0.0
    }
    return {"by_overlap": by_overlap, "crossover_detected": len(signs) > 1}


# ======================================================================================
# LLM reader (dependency-injected; ollama in production, fake LLM in tests)
# ======================================================================================
class LlmEmotionReader:
    """Reads {valence, arousal, stance} from a transcript via an injected llm_fn(prompt)->str.

    Caches by text hash so re-reading the same transcript (common: source snippets are reused across
    overlap samples) costs one call. The cache dict is exposed for persistence/resume."""

    def __init__(self, llm_fn: Callable[[str], str], cache: Optional[dict] = None):
        self.llm_fn = llm_fn
        self.cache: dict = cache if cache is not None else {}

    def read(self, text: Optional[str]) -> Optional[dict]:
        if not text or not text.strip():
            return None
        key = hashlib.md5(text.encode("utf-8")).hexdigest()
        if key in self.cache:
            return self.cache[key]
        raw = self.llm_fn(EMOTION_PROMPT.format(text=text))
        parsed = parse_llm_emotion(raw)
        self.cache[key] = parsed
        return parsed


def ollama_emotion_llm(
    model: str = "deepseek-r1:7b",
    host: str = "http://localhost:11434",
    timeout: float = 180.0,
    num_predict: int = 2048,
) -> Callable[[str], str]:
    """Return an llm_fn that calls a local ollama server (mirrors llm_asr_critic.ollama_llm)."""
    import urllib.request

    def _fn(prompt: str) -> str:
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": num_predict},
        }).encode("utf-8")
        req = urllib.request.Request(host + "/api/generate", data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read()).get("response", "")

    return _fn


# ======================================================================================
# Data loading (cached transcripts + silver references; no Whisper re-run)
# ======================================================================================
def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _transcript_text(sample_id: str, kind: str) -> Optional[str]:
    p = TRANS_DIR / f"{sample_id}_{kind}_whisper.json"
    if not p.exists():
        return None
    return _load_json(p).get("text", "")


def load_samples(n_per_tier: int = 5) -> list[dict]:
    """Assemble per-(sample, speaker) records: clean ref text, mixed-ASR text, separated-ASR text,
    overlap ratio, and the clean speaker audio path (for the acoustic-arousal triangulation).

    The CLEAN reference text lives in the *_silver_reference.json files (the base reference files are
    `synthetic_placeholder` drafts with empty speaker_*_text). Silver files omit the per-speaker audio
    path, so it is reconstructed from the project's fixed layout.
    """
    refs = sorted(REF_DIR.glob("*_silver_reference.json"))
    by_tier: dict[str, list] = {}
    for r in refs:
        d = _load_json(r)
        if not d.get("speaker_1_text") or not d.get("speaker_2_text"):
            continue  # require real clean text for both speakers
        by_tier.setdefault(d.get("tier", "?"), []).append(d)

    samples: list[dict] = []
    for _tier, items in sorted(by_tier.items()):
        for d in items[:n_per_tier]:
            sid = d["sample_id"]
            tier = d.get("tier", "?")
            mixed = _transcript_text(sid, "mixed")
            if mixed is None:
                continue
            for k in (1, 2):
                samples.append({
                    "sample_id": sid,
                    "tier": tier,
                    "overlap_ratio": TIER_OVERLAP.get(tier, float(d.get("overlap_ratio", 0.0))),
                    "sample_overlap_ratio": float(d.get("overlap_ratio", 0.0)),
                    "speaker": k,
                    "speaker_label": d.get(f"speaker_{k}_label", f"spk{k}"),
                    "ref_text": d.get(f"speaker_{k}_text", "") or "",
                    "mixed_hyp": mixed or "",
                    "sep_hyp": _transcript_text(sid, f"spk{k}") or "",
                    "spk_audio_path": f"resources/synthetic_overlap/audio/{tier}/{sid}_spk{k}.wav",
                })
    return samples


def _acoustic_arousal(audio_path: str) -> float:
    """Label-free acoustic arousal index of the clean speaker track. NaN if audio cannot be read."""
    if not audio_path:
        return float("nan")
    try:
        import soundfile as sf

        full = Path(audio_path)
        if not full.is_absolute():
            full = PROJECT_ROOT / audio_path
        wav, sr = sf.read(str(full))
        wav = np.asarray(wav, dtype=np.float32)
        if wav.ndim > 1:
            wav = wav.mean(axis=1)
        return float(arousal_index(prosodic_features(wav, sr=int(sr))))
    except Exception:
        return float("nan")


# ======================================================================================
# Driver
# ======================================================================================
def run(
    n_per_tier: int = 5,
    model: str = "deepseek-r1:7b",
    out_dir: Path | str = OUT_DIR,
    llm_fn: Optional[Callable[[str], str]] = None,
    compute_acoustic: bool = True,
    cache_path: Optional[Path | str] = None,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cache_file = Path(cache_path) if cache_path else out_dir / "_llm_cache.json"
    cache: dict = {}
    if cache_file.exists():
        try:
            cache = _load_json(cache_file)
        except Exception:
            cache = {}
    reader = LlmEmotionReader(llm_fn or ollama_emotion_llm(model), cache=cache)

    samples = load_samples(n_per_tier)
    rows: list[dict] = []
    ref_readings: list[Optional[dict]] = []
    lex_fires: list[int] = []
    tri_llm_val, tri_lex_val, tri_llm_aro, tri_aco = [], [], [], []

    for i, s in enumerate(samples):
        ref_r = reader.read(s["ref_text"])
        mix_r = reader.read(s["mixed_hyp"])
        sep_r = reader.read(s["sep_hyp"])
        d_mix = semantic_distance(ref_r, mix_r)["combined"]
        d_sep = semantic_distance(ref_r, sep_r)["combined"]
        benefit = (
            semantic_benefit(d_mix, d_sep)
            if not (math.isnan(d_mix) or math.isnan(d_sep))
            else float("nan")
        )
        cer_mix = compute_cer(s["ref_text"], s["mixed_hyp"])["cer"]
        cer_sep = compute_cer(s["ref_text"], s["sep_hyp"])["cer"]
        lex = lexical_emotion(s["ref_text"])
        fires = (lex["n_pos"] + lex["n_neg"]) > 0
        aco = _acoustic_arousal(s["spk_audio_path"]) if compute_acoustic else float("nan")

        rows.append({
            "sample_id": s["sample_id"], "tier": s["tier"], "overlap_ratio": s["overlap_ratio"],
            "sample_overlap_ratio": s.get("sample_overlap_ratio", s["overlap_ratio"]),
            "speaker": s["speaker"], "speaker_label": s["speaker_label"],
            "ref_valence": ref_r["valence"] if ref_r else float("nan"),
            "ref_arousal": ref_r["arousal"] if ref_r else float("nan"),
            "ref_stance": ref_r["stance"] if ref_r else "",
            "d_sem_mixed": d_mix, "d_sem_sep": d_sep, "semantic_benefit": benefit,
            "cer_mixed": cer_mix, "cer_sep": cer_sep, "cer_benefit": cer_mix - cer_sep,
            "lexical_valence": lex["valence"], "lexical_fires": int(fires),
            "acoustic_arousal": aco,
        })
        ref_readings.append(ref_r)
        lex_fires.append(1 if fires else 0)
        if ref_r is not None:
            tri_llm_val.append(ref_r["valence"]); tri_lex_val.append(lex["valence"])
            tri_llm_aro.append(ref_r["arousal"]); tri_aco.append(aco)

        # periodic cache persistence so a long ollama run is resumable
        if (i + 1) % 5 == 0:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(reader.cache, f)

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(reader.cache, f)

    # H1 coverage: LLM vs lexicon on the clean reference texts
    llm_cov = coverage_rate(ref_readings)
    lex_cov = round(float(np.mean(lex_fires)), 6) if lex_fires else 0.0

    # H2 separation tax + cross-links to CER.
    # NOTE: with oracle separation the separated track ~= the clean source, so d_sem(sep) and cer(sep)
    # are both ~0 with no variance — correlating within the sep arm is degenerate. The principled test
    # of "does ASR error distort the emotional meaning?" pools BOTH arms (the contaminated mixed arm
    # spans high CER / high d_sem; the clean sep arm spans ~0 / ~0), covering the full quality range.
    agg = aggregate_tax(rows)
    pooled_dsem = [r["d_sem_mixed"] for r in rows] + [r["d_sem_sep"] for r in rows]
    pooled_cer = [r["cer_mixed"] for r in rows] + [r["cer_sep"] for r in rows]
    dsem_vs_cer_pooled = correlate(pooled_dsem, pooled_cer)
    dsem_vs_cer_mixed_arm = correlate([r["d_sem_mixed"] for r in rows], [r["cer_mixed"] for r in rows])
    benefit_vs_cerbenefit = correlate(
        [r["semantic_benefit"] for r in rows], [r["cer_benefit"] for r in rows]
    )

    # H3 modality triangulation
    triangulation = {
        "llm_valence_vs_lexical_valence": correlate(tri_llm_val, tri_lex_val),
        "llm_arousal_vs_acoustic_arousal": correlate(tri_llm_aro, tri_aco),
        "lexical_valence_vs_acoustic_arousal": correlate(tri_lex_val, tri_aco),
    }

    n_parsed = sum(1 for r in ref_readings if r is not None)
    summary = {
        "n_samples": len(samples),
        "n_per_tier": n_per_tier,
        "model": model,
        "H1_coverage": {
            "llm_coverage_rate": llm_cov,
            "lexical_firing_rate": lex_cov,
            "llm_recovers_more": llm_cov > lex_cov,
        },
        "H2_semantic_tax": {
            **agg,
            "d_sem_vs_cer_pooled": dsem_vs_cer_pooled,
            "d_sem_vs_cer_mixed_arm": dsem_vs_cer_mixed_arm,
            "semantic_benefit_vs_cer_benefit": benefit_vs_cerbenefit,
        },
        "H3_triangulation": triangulation,
        "parse_health": {
            "ref_readings_parsed": n_parsed,
            "ref_readings_total": len(ref_readings),
            "parse_rate": round(n_parsed / len(ref_readings), 6) if ref_readings else 0.0,
            "kill_criterion_tripped": (len(ref_readings) > 0 and n_parsed / len(ref_readings) < 0.5),
        },
    }

    _write_csv(rows, out_dir / "semantic_tax_curve.csv")
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    _write_findings(summary, out_dir / "FINDINGS.md")
    _plot(agg, llm_cov, lex_cov, out_dir / "semantic_emotion_tax.png")
    return out_dir


def _write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _fmt(x: Any) -> str:
    if isinstance(x, float):
        return "nan" if math.isnan(x) else f"{x:.4f}"
    return str(x)


def _write_findings(summary: dict, path: Path) -> None:
    h1 = summary["H1_coverage"]
    h2 = summary["H2_semantic_tax"]
    h3 = summary["H3_triangulation"]
    ph = summary["parse_health"]
    lines = [
        "# The Semantic Emotion Tax — Findings",
        "",
        "**Label:** `experimental/frontier`. ASR Whisper-`tiny` (cached transcripts); LLM "
        f"`{summary['model']}` (local ollama, offline); references synthetic/silver (clean source "
        "text); CER post-hoc only; no gold tables touched. Issue #831.",
        "",
        f"Grid: {summary['n_samples']} (sample×speaker) records, {summary['n_per_tier']}/tier across "
        "5 overlap levels (0.0/0.1/0.3/0.5/0.8). The LLM reads {valence,arousal,stance} from each "
        "transcript; emotion has no ground truth, so the clean source text is the silver anchor "
        "(exactly as the verified transcript anchors CER).",
        "",
        f"**Parse health:** {ph['ref_readings_parsed']}/{ph['ref_readings_total']} reference readings "
        f"parsed ({_fmt(ph['parse_rate'])}). Kill criterion (>50% unparseable) "
        f"{'TRIPPED' if ph['kill_criterion_tripped'] else 'not tripped'}.",
        "",
        "## H1 — Coverage: does the LLM read implicit emotion the lexicon misses?",
        "",
        f"- LLM non-degenerate coverage: **{_fmt(h1['llm_coverage_rate'])}**",
        f"- Lexicon firing rate (same texts): **{_fmt(h1['lexical_firing_rate'])}**",
        f"- Verdict: LLM recovers {'MORE' if h1['llm_recovers_more'] else 'NOT more'} emotion signal "
        "than the fixed lexicon.",
        "",
        "## H2 — The Semantic Emotion Tax (separation: help or hurt the *meaning*?)",
        "",
        "| overlap | n | mean semantic benefit | mean d_sem(mixed) | mean d_sem(sep) |",
        "|---:|---:|---:|---:|---:|",
    ]
    for r in h2["by_overlap"]:
        lines.append(
            f"| {r['overlap_ratio']} | {r['n']} | {_fmt(r['mean_semantic_benefit'])} | "
            f"{_fmt(r['mean_d_sem_mixed'])} | {_fmt(r['mean_d_sem_sep'])} |"
        )
    dvc = h2["d_sem_vs_cer_pooled"]
    dvm = h2["d_sem_vs_cer_mixed_arm"]
    bvc = h2["semantic_benefit_vs_cer_benefit"]
    lines += [
        "",
        f"- Overlap crossover (benefit sign flips low→high overlap): **{h2['crossover_detected']}**",
        f"- d_sem ↔ CER, pooled over both arms: Pearson **{_fmt(dvc['pearson'])}**, Spearman "
        f"{_fmt(dvc['spearman'])} (n={dvc['n']}) — does ASR error move the emotional meaning? (headline)",
        f"- d_sem ↔ CER, within the contaminated mixed arm only: Pearson {_fmt(dvm['pearson'])}, "
        f"Spearman {_fmt(dvm['spearman'])} (n={dvm['n']}).",
        f"- semantic_benefit ↔ CER_benefit: Pearson {_fmt(bvc['pearson'])}, Spearman "
        f"{_fmt(bvc['spearman'])} (n={bvc['n']}) — do emotion and ASR want the same separate/mixed call?",
        "",
        "Reading: a positive d_sem↔CER correlation means ASR errors DO distort the recoverable "
        "emotional meaning (a real semantic tax); a near-zero correlation means the emotional meaning "
        "is robust to transcription error — which *strengthens* the project's decoupling recipe (the "
        "text route can carry emotion despite CER). NB: with oracle separation the separated arm sits "
        "near (0 CER, 0 d_sem), so the pooled correlation is the valid full-range test.",
        "",
        "## H3 — Is LLM-semantic emotion a complementary third modality?",
        "",
        "| pair | Pearson | Spearman | n |",
        "|---|---:|---:|---:|",
    ]
    for name, c in h3.items():
        lines.append(f"| {name} | {_fmt(c['pearson'])} | {_fmt(c['spearman'])} | {c['n']} |")
    lines += [
        "",
        "Low pairwise correlation ⇒ the three readers (acoustic arousal, lexical valence, "
        "LLM-semantic) capture *different* facets of emotion — the LLM is additive, not redundant.",
        "",
        "## Honest limitations",
        "",
        "Small n; Whisper-`tiny`; synthetic oracle separation (the separated track is the isolated "
        "source, an upper bound on a real separator); local `deepseek-r1` reasoning model with "
        "temperature 0 (still has reading variance); emotion is silver-anchored on clean source text, "
        "not human emotion labels — this measures *semantic emotion preservation*, a proxy, not "
        "classified-emotion accuracy. `experimental/frontier`, not a gold result.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plot(agg: dict, llm_cov: float, lex_cov: float, path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    by = agg["by_overlap"]
    ov = [r["overlap_ratio"] for r in by]
    ben = [r["mean_semantic_benefit"] for r in by]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    ax1.axhline(0, color="grey", lw=0.8)
    ax1.plot(ov, ben, "o-", color="#b5179e")
    ax1.set_xlabel("overlap ratio")
    ax1.set_ylabel("mean semantic benefit  (mixed − sep d_sem)")
    ax1.set_title("Semantic Emotion Tax of separation\n(>0: separation recovers meaning)")
    ax2.bar(["LLM (deepseek-r1)", "lexicon"], [llm_cov, lex_cov], color=["#4361ee", "#adb5bd"])
    ax2.set_ylim(0, 1)
    ax2.set_ylabel("emotion-signal coverage")
    ax2.set_title("H1: implicit-emotion coverage")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="The Semantic Emotion Tax (issue #831)")
    p.add_argument("--n-per-tier", type=int, default=5)
    p.add_argument("--model", type=str, default="deepseek-r1:7b")
    p.add_argument("--output-dir", type=str, default=str(OUT_DIR))
    p.add_argument("--no-acoustic", action="store_true", help="skip librosa acoustic-arousal triangulation")
    return p.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    out = run(
        n_per_tier=args.n_per_tier,
        model=args.model,
        out_dir=args.output_dir,
        compute_acoustic=not args.no_acoustic,
    )
    print(f"[semantic_emotion_tax] wrote results to {out}")


if __name__ == "__main__":
    main()
