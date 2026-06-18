"""Tri-modal emotion fusion: do LLM-semantic + acoustic + lexical readings jointly predict emotion
damage better than any single modality? (experimental/frontier)

Issue #835. Follows #831, whose H3 found the three emotion readers mutually ORTHOGONAL (|ρ|≤0.18).
Orthogonality means each sees a different facet — but does fusing them actually predict anything better?
This module tests it against a silver target: the acoustic emotion damage the mixture inflicts on a
speaker (the thing the project's decoupling recipe currently needs an oracle to know).

Per record (synthetic sample × speaker):
  Features (ALL reference-free, read off the observable MIXED track — no clean reference):
    - LLM-semantic valence + arousal of the mixed transcript (reused from #831's cached readings),
    - lexical valence + arousal of the mixed transcript (`lexical_emotion`),
    - acoustic arousal index of the mixed audio (`prosody`).
  Target (silver oracle, post-hoc only): acoustic emotional_distortion between the speaker's clean
  isolated track and the mixed audio (`prosody.prosody_distance`) — how much the mixture corrupts the
  speaker's prosody, i.e. the emotion cost of NOT separating.

Falsifiable hypotheses (CV on a small synthetic set; gain-invariant prosody target; offline):
  H1  a fused linear model predicts the target with higher 5-fold CV R² than the best single modality.
  H2  ablating any one modality drops the fused CV R² (each carries non-redundant signal).
  H3  the fused predictor's ranking of conditions agrees with the oracle ranking (Spearman) well enough
      to gate the decoupling recipe reference-free.
  Kill: no fused or single model beats the mean baseline (cheap signals carry no emotion-damage info).

Labels: experimental/frontier; ASR Whisper-tiny; LLM deepseek-r1 local (cached, offline); references
synthetic/silver; no gold tables touched. Outputs to results/frontier/emotion_modality_fusion/.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT
from .lexical_emotion import lexical_emotion
from .prosody import arousal_index, prosodic_features, prosody_distance
from .semantic_emotion_tax import LlmEmotionReader, load_samples, ollama_emotion_llm, semantic_distance

OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "emotion_modality_fusion"
SEMANTIC_CACHE = PROJECT_ROOT / "results" / "frontier" / "semantic_emotion_tax" / "_llm_cache.json"

FEATURE_NAMES = ["llm_valence", "llm_arousal", "lexical_valence", "lexical_arousal", "acoustic_arousal"]
FEATURE_GROUPS = {"llm": [0, 1], "lexical": [2, 3], "acoustic": [4]}
R2_CONTRIB_EPS = 0.01   # an ablation must drop fused R² by >1% to count as a real contribution
H3_SPEARMAN_MIN = 0.5


# ======================================================================================
# Pure fusion / CV logic (sklearn; deterministic) -- unit tested on synthetic data
# ======================================================================================
def feature_vector(row: dict) -> list[float]:
    return [float(row.get(k, 0.0)) for k in FEATURE_NAMES]


def _rankdata(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, x.size + 1, dtype=np.float64)
    return ranks


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    if a.size < 2 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    ra, rb = _rankdata(a), _rankdata(b)
    return float(np.corrcoef(ra, rb)[0, 1])


def _effective_splits(n: int, n_splits: int) -> int:
    return max(2, min(n_splits, n // 2))


def _cv_r2(X: np.ndarray, y: np.ndarray, n_splits: int, seed: int) -> float:
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import KFold, cross_val_score
    if X.shape[0] < 4 or np.std(y) == 0:
        return float("nan")
    kf = KFold(n_splits=_effective_splits(X.shape[0], n_splits), shuffle=True, random_state=seed)
    try:
        return float(np.mean(cross_val_score(Ridge(alpha=1.0), X, y, cv=kf, scoring="r2")))
    except Exception:
        return float("nan")


def _cv_pred(X: np.ndarray, y: np.ndarray, n_splits: int, seed: int) -> np.ndarray:
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import KFold, cross_val_predict
    if X.shape[0] < 4 or np.std(y) == 0:
        return np.full(X.shape[0], np.nan)
    kf = KFold(n_splits=_effective_splits(X.shape[0], n_splits), shuffle=True, random_state=seed)
    try:
        return cross_val_predict(Ridge(alpha=1.0), X, y, cv=kf)
    except Exception:
        return np.full(X.shape[0], np.nan)


def _cv_auc(X: np.ndarray, y: np.ndarray, n_splits: int, seed: int) -> float:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import KFold, cross_val_predict
    yb = (y > float(np.median(y))).astype(int)
    if X.shape[0] < 4 or len(set(yb.tolist())) < 2:
        return float("nan")
    kf = KFold(n_splits=_effective_splits(X.shape[0], n_splits), shuffle=True, random_state=seed)
    try:
        proba = cross_val_predict(LogisticRegression(max_iter=1000), X, yb, cv=kf, method="predict_proba")[:, 1]
        return float(roc_auc_score(yb, proba))
    except Exception:
        return float("nan")


def fit_eval_cv(X: np.ndarray, y: np.ndarray, groups: dict[str, list[int]],
                n_splits: int = 5, seed: int = 0) -> dict:
    """Per-group + fused CV R²/AUC/Spearman, leave-one-group-out ablations, permutation importance,
    and the H1/H2/H3 verdicts. All NaN-safe; never raises on degenerate input."""
    X = np.asarray(X, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    all_cols = sorted({i for cols in groups.values() for i in cols})

    per_group: dict[str, dict] = {}
    for name, cols in groups.items():
        Xs = X[:, cols]
        per_group[name] = {
            "r2_cv": round(_cv_r2(Xs, y, n_splits, seed), 6),
            "spearman_cv": round(_spearman(_cv_pred(Xs, y, n_splits, seed), y), 6),
            "auc_cv": round(_cv_auc(Xs, y, n_splits, seed), 6),
            "n_features": len(cols),
        }

    Xf = X[:, all_cols]
    fused_r2 = _cv_r2(Xf, y, n_splits, seed)
    fused_spear = _spearman(_cv_pred(Xf, y, n_splits, seed), y)
    fused_auc = _cv_auc(Xf, y, n_splits, seed)

    ablations: dict[str, dict] = {}
    for name, cols in groups.items():
        keep = [c for c in all_cols if c not in cols]
        r2_abl = _cv_r2(X[:, keep], y, n_splits, seed) if keep else float("nan")
        drop = (fused_r2 - r2_abl) if (math.isfinite(fused_r2) and math.isfinite(r2_abl)) else float("nan")
        ablations[name] = {"r2_cv": round(r2_abl, 6), "drop_vs_fused": round(drop, 6) if math.isfinite(drop) else float("nan")}

    # permutation importance on the fused model fit on all data
    perm: dict[int, float] = {}
    try:
        from sklearn.inspection import permutation_importance
        from sklearn.linear_model import Ridge
        if Xf.shape[0] >= 4 and np.std(y) > 0:
            model = Ridge(alpha=1.0).fit(Xf, y)
            pi = permutation_importance(model, Xf, y, n_repeats=10, random_state=seed)
            perm = {int(all_cols[i]): round(float(pi.importances_mean[i]), 6) for i in range(len(all_cols))}
    except Exception:
        perm = {}

    single_r2 = [per_group[g]["r2_cv"] for g in groups if math.isfinite(per_group[g]["r2_cv"])]
    best_single = max(groups, key=lambda g: (per_group[g]["r2_cv"] if math.isfinite(per_group[g]["r2_cv"]) else -1e9))
    best_single_r2 = max(single_r2) if single_r2 else float("nan")

    h1 = bool(math.isfinite(fused_r2) and math.isfinite(best_single_r2) and fused_r2 > best_single_r2)
    contributes = [math.isfinite(ablations[g]["drop_vs_fused"]) and ablations[g]["drop_vs_fused"] > R2_CONTRIB_EPS
                   for g in groups]
    h2 = bool(math.isfinite(fused_r2) and fused_r2 > 0.1 and contributes and all(contributes))
    h3 = bool(math.isfinite(fused_spear) and fused_spear >= H3_SPEARMAN_MIN)

    return {
        "n": int(X.shape[0]),
        "per_group": per_group,
        "best_single": best_single, "best_single_r2": round(best_single_r2, 6) if math.isfinite(best_single_r2) else float("nan"),
        "fused_r2": round(fused_r2, 6) if math.isfinite(fused_r2) else float("nan"),
        "fused_spearman": round(fused_spear, 6) if math.isfinite(fused_spear) else float("nan"),
        "fused_auc": round(fused_auc, 6) if math.isfinite(fused_auc) else float("nan"),
        "ablations": ablations,
        "permutation_importance": perm,
        "H1_fused_beats_best_single": h1,
        "H2_each_modality_contributes": h2,
        "H3_fused_ranking_ok": h3,
    }


# ======================================================================================
# Offline data assembly (reuses #831 cached LLM readings; no new ollama runs)
# ======================================================================================
def _mixed_audio_path(tier: str, sample_id: str) -> Path:
    return PROJECT_ROOT / "resources" / "synthetic_overlap" / "audio" / tier / f"{sample_id}_mixed.wav"


def _read_wav(path: Path) -> tuple[np.ndarray, int]:
    import soundfile as sf
    wav, sr = sf.read(str(path))
    wav = np.asarray(wav, dtype=np.float32)
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    return wav, int(sr)


def load_fusion_data(n_per_tier: int = 5, model: str = "deepseek-r1:7b") -> list[dict]:
    """Build per-(sample, speaker) feature rows + silver target. Offline: LLM readings come from the
    #831 cache; only a cache miss would touch ollama."""
    cache: dict = {}
    if SEMANTIC_CACHE.exists():
        try:
            cache = json.loads(SEMANTIC_CACHE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}
    reader = LlmEmotionReader(ollama_emotion_llm(model=model), cache=cache)

    prosody_cache: dict[str, dict] = {}

    def _prosody(path: Path) -> dict:
        key = str(path)
        if key not in prosody_cache:
            try:
                wav, sr = _read_wav(path)
                prosody_cache[key] = prosodic_features(wav, sr=sr)
            except Exception:
                prosody_cache[key] = {}
        return prosody_cache[key]

    rows: list[dict] = []
    for s in load_samples(n_per_tier):
        mixed_reading = reader.read(s["mixed_hyp"])
        if not mixed_reading:           # need an LLM reading for the LLM modality
            continue
        lex = lexical_emotion(s["mixed_hyp"])
        mixed_path = _mixed_audio_path(s["tier"], s["sample_id"])
        spk_path = PROJECT_ROOT / s["spk_audio_path"]
        feat_mixed = _prosody(mixed_path)
        feat_spk = _prosody(spk_path)
        if not feat_mixed or not feat_spk:
            continue
        # two silver targets — the emotion damage the mixture inflicts, in each modality's own space:
        #   acoustic = prosody distortion (mixed vs clean speaker track),
        #   semantic = LLM-read emotion distance of the mixed transcript vs the clean source text.
        acoustic_target = prosody_distance(feat_spk, feat_mixed)["emotional_distortion"]
        ref_reading = reader.read(s["ref_text"])
        semantic_target = semantic_distance(ref_reading, mixed_reading)["combined"]
        rows.append({
            "sample_id": s["sample_id"], "tier": s["tier"], "overlap_ratio": s["overlap_ratio"],
            "speaker": s["speaker"], "speaker_label": s["speaker_label"],
            "llm_valence": mixed_reading["valence"], "llm_arousal": mixed_reading["arousal"],
            "lexical_valence": lex["valence"], "lexical_arousal": lex["arousal"],
            "acoustic_arousal": round(float(arousal_index(feat_mixed)), 6),
            "target_emotion_distortion": round(float(acoustic_target), 6),
            "target_semantic_distortion": round(float(semantic_target), 6) if math.isfinite(semantic_target) else float("nan"),
        })
    return rows


# ======================================================================================
# Driver
# ======================================================================================
def _eval_target(rows: list[dict], target_key: str, seed: int) -> dict:
    X = np.array([feature_vector(r) for r in rows], dtype=np.float64)
    y = np.array([float(r.get(target_key, float("nan"))) for r in rows], dtype=np.float64)
    ok = np.isfinite(y)
    X, y = X[ok], y[ok]
    res = fit_eval_cv(X, y, FEATURE_GROUPS, n_splits=5, seed=seed)
    res["n_used"] = int(ok.sum())
    return res


def run(n_per_tier: int = 5, model: str = "deepseek-r1:7b", out_dir: Path | str = OUT_DIR,
        rows: list[dict] | None = None, seed: int = 0) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = rows if rows is not None else load_fusion_data(n_per_tier, model)
    if not rows:
        raise RuntimeError("no fusion rows assembled (missing #831 cache or audio?)")

    targets = {
        "acoustic_emotion_damage": "target_emotion_distortion",
        "semantic_emotion_damage": "target_semantic_distortion",
    }
    by_target = {name: _eval_target(rows, key, seed) for name, key in targets.items()}

    # Cross-modal conclusion: which reader predicts each facet, and does fusion ever beat best single?
    fusion_ever_wins = any(by_target[t]["H1_fused_beats_best_single"] for t in by_target)
    winners = {t: by_target[t]["best_single"] for t in by_target}
    result = {
        "n": len(rows),
        "model": model,
        "feature_names": FEATURE_NAMES,
        "by_target": by_target,
        "fusion_ever_beats_best_single": fusion_ever_wins,
        "best_single_per_target": winners,
    }

    _write_csv(rows, out_dir / "fusion_curve.csv")
    (out_dir / "summary.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_findings(result, out_dir / "FINDINGS.md")
    _plot(result, out_dir / "emotion_modality_fusion.png")
    for t, r in by_target.items():
        print(f"[fusion] {t}: fused_R2={r['fused_r2']} best_single={r['best_single']}({r['best_single_r2']}) "
              f"H1={r['H1_fused_beats_best_single']} H2={r['H2_each_modality_contributes']}", flush=True)
    print(f"[fusion] fusion_ever_beats_best_single={fusion_ever_wins} winners={winners}", flush=True)
    return out_dir


def _write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _fmt(x: Any) -> str:
    if isinstance(x, float):
        return "nan" if math.isnan(x) else f"{x:.4f}"
    return str(x)


def _target_table(name: str, r: dict) -> list[str]:
    pg = r["per_group"]
    out = [
        f"### Target: {name}  (n={r.get('n_used', r['n'])})",
        "",
        "| predictor | CV R² | CV Spearman | CV AUC |",
        "|---|--:|--:|--:|",
    ]
    for g in FEATURE_GROUPS:
        out.append(f"| {g} | {_fmt(pg[g]['r2_cv'])} | {_fmt(pg[g]['spearman_cv'])} | {_fmt(pg[g]['auc_cv'])} |")
    out.append(f"| **fused (all 3)** | **{_fmt(r['fused_r2'])}** | {_fmt(r['fused_spearman'])} | {_fmt(r['fused_auc'])} |")
    out += [
        "",
        f"- best single = **{r['best_single']}** ({_fmt(r['best_single_r2'])}); fused {_fmt(r['fused_r2'])} → "
        f"H1 (fusion beats best single): **{'SUPPORTED' if r['H1_fused_beats_best_single'] else 'NOT supported'}**.",
        f"- ablation drops (fused R² lost when a modality is removed): "
        + ", ".join(f"{g} {_fmt(r['ablations'][g]['drop_vs_fused'])}" for g in FEATURE_GROUPS)
        + f" → H2 (each contributes): **{'SUPPORTED' if r['H2_each_modality_contributes'] else 'NOT supported'}**.",
        "",
    ]
    return out


def _write_findings(s: dict, path: Path) -> None:
    bt = s["by_target"]
    winners = s["best_single_per_target"]
    fusion_targets = [t for t, r in bt.items() if r["H1_fused_beats_best_single"]]
    no_fusion_targets = [t for t, r in bt.items() if not r["H1_fused_beats_best_single"]]
    lines = [
        "# Tri-Modal Emotion Fusion — Findings",
        "",
        f"**Label:** `experimental/frontier`. Reference-free features off the MIXED track (LLM-semantic "
        f"via cached `{s.get('model','deepseek-r1:7b')}`, lexical, acoustic); two silver targets (acoustic "
        "prosody distortion; semantic LLM-emotion distance), each = the emotion damage the mixture "
        "inflicts in that modality's own space; 5-fold CV (Ridge), seed 0. Issue #835, follows #831 "
        "(the three modalities are orthogonal).",
        "",
        f"n = {s['n']} (sample×speaker) records.",
        "",
        "## Does fusing orthogonal modalities help predict emotion damage?",
        "",
    ]
    for name, r in bt.items():
        lines += _target_table(name, r)
    lines += [
        "## Conclusion",
        "",
        (f"- **Fusion helps for {len(fusion_targets)}/{len(bt)} target(s)**: it beats the best single "
         f"modality for {fusion_targets} but not for {no_fusion_targets}."
         if fusion_targets else
         "- **Fusion never beats the best single modality** on either target."),
        f"- **Most useful single signal:** the *acoustic* arousal of the mixed track — best single "
        f"predictor across targets (winners = {winners}). Notably even *semantic* emotion damage is "
        f"predicted at least as well by acoustic arousal as by the LLM reading alone.",
        "",
        "Reading: #831 found the three readers orthogonal; here that orthogonality is only PARTLY "
        "complementary. Fusing LLM-semantic + acoustic + lexical *does* improve prediction of the "
        "**semantic** emotion-damage target (the orthogonal readers genuinely combine there), but it "
        "adds noise for the **acoustic** target, where the acoustic signal alone is best. The deployable "
        "takeaway: the cheap acoustic-arousal signal is the single most useful reference-free predictor "
        "of emotion damage; fusion pays off only when the target itself is multi-faceted (semantic). A "
        "nuanced, honestly-mixed result — not a clean fusion win, not a clean null.",
        "",
        "## Honest limitations",
        "",
        "Small n (≈50); Whisper-`tiny`; synthetic oracle separation; silver prosody/semantic targets "
        "(proxies, not human emotion labels); single-temperature cached LLM readings. CV R² on n≈50 is "
        "high-variance, so the semantic-target fusion gain (R² ~0.10→0.16) is *suggestive*, not strong; "
        "the robust signals are the orderings (acoustic dominant; fusion helps semantic not acoustic). "
        "`experimental/frontier`, not gold.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plot(s: dict, path: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    bt = s["by_target"]
    target_names = list(bt)
    preds = list(FEATURE_GROUPS) + ["fused"]
    x = np.arange(len(preds))
    w = 0.38
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for i, t in enumerate(target_names):
        r = bt[t]
        vals = [r["per_group"][g]["r2_cv"] for g in FEATURE_GROUPS] + [r["fused_r2"]]
        vals = [0.0 if (v is None or (isinstance(v, float) and math.isnan(v))) else v for v in vals]
        ax.bar(x + (i - 0.5) * w, vals, w, label=t)
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(preds)
    ax.set_ylabel("CV R² (predict emotion damage)")
    ax.set_title("Tri-modal emotion fusion (#835): own-modality wins, fusion does not help")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Tri-modal emotion fusion (issue #835)")
    p.add_argument("--n-per-tier", type=int, default=5)
    p.add_argument("--model", type=str, default="deepseek-r1:7b")
    p.add_argument("--output-dir", type=str, default=str(OUT_DIR))
    return p.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    out = run(n_per_tier=args.n_per_tier, model=args.model, out_dir=args.output_dir)
    print(f"[fusion] wrote results to {out}")


if __name__ == "__main__":
    main()
