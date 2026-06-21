from __future__ import annotations

import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from .generative_audiodepth_common import (
    DATASET_CSV,
    FIGURE_DIR,
    PROJECT_ROOT,
    ROUTES,
    TABLE_DIR,
    TASKS,
    feature_vector,
    load_npy,
    min_route_cer,
    oracle_route,
    read_rows,
    safe_float,
    spearman,
    unique_samples,
    write_csv,
    write_markdown,
)


RELIABILITY_TRAIN = TABLE_DIR / "generative_audiodepth_reliability_train.csv"
RELIABILITY_VALIDATION = TABLE_DIR / "generative_audiodepth_reliability_validation.csv"
RELIABILITY_TEST = TABLE_DIR / "generative_audiodepth_reliability_test.csv"
RELIABILITY_UNSEEN_OVERLAP = TABLE_DIR / "generative_audiodepth_reliability_unseen_overlap.csv"
RELIABILITY_UNSEEN_DOMINANCE = TABLE_DIR / "generative_audiodepth_reliability_unseen_dominance.csv"


def sample_rows(path: Path = DATASET_CSV) -> list[dict[str, str]]:
    return unique_samples(read_rows(path))


def task_rows_for_samples(sample_ids: set[str], path: Path = DATASET_CSV) -> list[dict[str, str]]:
    return [row for row in read_rows(path) if row.get("sample_id") in sample_ids]


def source_tokens(row: dict[str, str]) -> set[str]:
    return {part.strip() for part in row.get("source_utterance_ids", "").replace(",", "|").split("|") if part.strip()}


def source_pair_key(row: dict[str, str]) -> str:
    tokens = sorted(source_tokens(row))
    return "|".join(tokens) if tokens else row.get("sample_id", "")


def group_key(row: dict[str, str]) -> str:
    return f"{source_pair_key(row)}::{row.get('counterfactual_family_id', row.get('sample_id', ''))}"


def write_task_split(path: Path, samples: list[dict[str, str]]) -> None:
    write_csv(path, task_rows_for_samples({row["sample_id"] for row in samples}))


def distribution(rows: list[dict[str, str]], key: str) -> str:
    counts = Counter(row.get(key, "") for row in rows)
    return "; ".join(f"{k}:{v}" for k, v in sorted(counts.items()))


def leakage_report(splits: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    token_owner: dict[str, str] = {}
    pair_owner: dict[str, str] = {}
    family_owner: dict[str, str] = {}
    wav_owner: dict[str, str] = {}
    leaks = {"source_utterance": [], "source_pair": [], "counterfactual_family": [], "mixed_wav": []}
    for split, rows in splits.items():
        for row in rows:
            for token in source_tokens(row):
                owner = token_owner.setdefault(token, split)
                if owner != split:
                    leaks["source_utterance"].append(f"{token}:{owner}->{split}")
            pair = source_pair_key(row)
            owner = pair_owner.setdefault(pair, split)
            if owner != split:
                leaks["source_pair"].append(f"{pair}:{owner}->{split}")
            family = row.get("counterfactual_family_id", row.get("sample_id", ""))
            owner = family_owner.setdefault(family, split)
            if owner != split:
                leaks["counterfactual_family"].append(f"{family}:{owner}->{split}")
            wav = row.get("mixed_wav_path", "")
            if wav:
                owner = wav_owner.setdefault(wav, split)
                if owner != split:
                    leaks["mixed_wav"].append(f"{wav}:{owner}->{split}")
    return {
        "source_utterance_leaks": len(leaks["source_utterance"]),
        "source_pair_leaks": len(leaks["source_pair"]),
        "counterfactual_family_leaks": len(leaks["counterfactual_family"]),
        "mixed_wav_leaks": len(leaks["mixed_wav"]),
        "details": leaks,
    }


def map_task_row(sample_id: str, task: str, rows: list[dict[str, str]] | None = None) -> dict[str, str] | None:
    source = rows if rows is not None else read_rows(DATASET_CSV)
    for row in source:
        if row.get("sample_id") == sample_id and row.get("target_task") == task:
            return row
    return None


def map_summary(path_text: str) -> list[float]:
    arr = load_npy(path_text)
    return [
        float(np.mean(arr)),
        float(np.std(arr)),
        float(np.percentile(arr, 10)),
        float(np.percentile(arr, 50)),
        float(np.percentile(arr, 90)),
    ]


def teacher_map_features(row: dict[str, str], dataset_rows: list[dict[str, str]]) -> list[float]:
    feats: list[float] = []
    for task in ["OVERLAP_MAP", "DOMINANCE_MAP", "UNCERTAINTY_MAP"]:
        task_row = map_task_row(row["sample_id"], task, dataset_rows)
        feats.extend(map_summary(task_row["target_path"]) if task_row else [0.0] * 5)
    return feats


def generated_map_features(row: dict[str, str], train_samples: list[dict[str, str]], dataset_rows: list[dict[str, str]]) -> list[float]:
    if not train_samples:
        return [0.0] * 15
    train_x = np.stack([feature_vector(r) for r in train_samples])
    query = feature_vector(row)
    idx = int(np.argmin(np.sum((train_x - query[None, :]) ** 2, axis=1)))
    return teacher_map_features(train_samples[idx], dataset_rows)


def handcrafted_features(row: dict[str, str]) -> list[float]:
    keys = [
        "overlap_proxy_mean",
        "overlap_proxy_std",
        "overlap_proxy_p90",
        "uncertainty_proxy_mean",
        "uncertainty_proxy_std",
        "uncertainty_proxy_p90",
        "overlap_uncertainty_product",
        "route_gap",
    ]
    return [safe_float(row.get(key), 0.0) for key in keys]


def logmel_features(row: dict[str, str]) -> list[float]:
    return [safe_float(row.get(key), 0.0) for key in ["logmel_mean", "logmel_std", "logmel_p90"]]


def true_regrets(row: dict[str, str]) -> list[float]:
    return [safe_float(row.get(f"{route}_regret"), 0.0) for route in ROUTES]


def review_label(row: dict[str, str]) -> int:
    return 1 if row.get("review_needed") == "True" or min_route_cer(row) >= 0.6 or safe_float(row.get("route_gap"), 1.0) <= 0.02 else 0


def separation_helpful_label(row: dict[str, str]) -> int:
    return 1 if safe_float(row.get("mixed_cer"), 1.0) - safe_float(row.get("separated_cer"), 1.0) > 0.03 else 0


def route_gap_bucket(row: dict[str, str]) -> str:
    gap = safe_float(row.get("route_gap"), 0.0)
    if gap <= 0.02:
        return "ambiguous"
    if gap <= 0.15:
        return "small"
    if gap <= 0.45:
        return "medium"
    return "large"


def nearest_neighbor_predict(
    train_x: np.ndarray,
    train_y: list[Any],
    test_x: np.ndarray,
    default: Any,
) -> list[Any]:
    if train_x.size == 0:
        return [default for _ in range(len(test_x))]
    preds = []
    for query in test_x:
        idx = int(np.argmin(np.sum((train_x - query[None, :]) ** 2, axis=1)))
        preds.append(train_y[idx])
    return preds


def standardize(train_x: np.ndarray, test_x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = train_x.mean(axis=0, keepdims=True) if train_x.size else 0.0
    std = train_x.std(axis=0, keepdims=True) if train_x.size else 1.0
    std = np.where(std < 1e-6, 1.0, std)
    return (train_x - mean) / std, (test_x - mean) / std


def classification_metrics(truth: list[Any], pred: list[Any]) -> dict[str, float]:
    if not truth:
        return {"accuracy": 0.0, "macro_f1": 0.0}
    labels = sorted({*truth, *pred})
    acc = sum(t == p for t, p in zip(truth, pred)) / len(truth)
    f1s = []
    for label in labels:
        tp = sum(t == label and p == label for t, p in zip(truth, pred))
        fp = sum(t != label and p == label for t, p in zip(truth, pred))
        fn = sum(t == label and p != label for t, p in zip(truth, pred))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * precision * recall / (precision + recall) if precision + recall else 0.0)
    return {"accuracy": round(acc, 6), "macro_f1": round(float(np.mean(f1s)), 6)}


def regression_metrics(truth: list[float], pred: list[float]) -> dict[str, float]:
    if not truth:
        return {"mae": 0.0, "spearman": 0.0}
    return {
        "mae": round(float(np.mean(np.abs(np.asarray(truth) - np.asarray(pred)))), 6),
        "spearman": spearman([float(x) for x in pred], [float(x) for x in truth]),
    }


def pairwise_rank_accuracy(true_values: list[list[float]], pred_values: list[list[float]]) -> float:
    total = 0
    ok = 0
    for true_vec, pred_vec in zip(true_values, pred_values):
        for i in range(len(true_vec)):
            for j in range(i + 1, len(true_vec)):
                if true_vec[i] == true_vec[j]:
                    continue
                total += 1
                if (true_vec[i] < true_vec[j]) == (pred_vec[i] < pred_vec[j]):
                    ok += 1
    return round(ok / total, 6) if total else 0.0


def route_from_regrets(values: list[float]) -> str:
    return ROUTES[int(np.argmin(np.asarray(values, dtype=np.float32)))]


def selected_cer(row: dict[str, str], route: str) -> float:
    if route == "review":
        return min_route_cer(row)
    return safe_float(row.get(f"{route}_cer"), 1.0)


def policy_metrics(rows: list[dict[str, str]], predicted_routes: dict[str, str], policy_name: str) -> dict[str, Any]:
    selected = [selected_cer(row, predicted_routes.get(row["sample_id"], "mixed")) for row in rows]
    oracle = [min_route_cer(row) for row in rows]
    route_acc = [
        predicted_routes.get(row["sample_id"], "mixed") == oracle_route(row)
        for row in rows
        if predicted_routes.get(row["sample_id"], "mixed") != "review"
    ]
    review_count = sum(predicted_routes.get(row["sample_id"], "mixed") == "review" for row in rows)
    false_safe = sum(
        safe_float(row.get("mixed_cer"), 0.0) >= 0.6 and predicted_routes.get(row["sample_id"], "mixed") == "mixed"
        for row in rows
    )
    high_error_mixed = false_safe
    return {
        "policy_name": policy_name,
        "sample_count": len(rows),
        "selected_route_cer": round(float(np.mean(selected)), 6) if selected else 0.0,
        "realized_regret": round(float(np.mean(np.asarray(selected) - np.asarray(oracle))), 6) if selected else 0.0,
        "route_accuracy": round(sum(route_acc) / len(route_acc), 6) if route_acc else 0.0,
        "false_safe_count": false_safe,
        "high_error_mixed_count": high_error_mixed,
        "review_rate": round(review_count / len(rows), 6) if rows else 0.0,
        "coverage": round(1.0 - review_count / len(rows), 6) if rows else 0.0,
    }


def draw_bar_chart(path: Path, title: str, rows: list[dict[str, Any]], label_key: str, value_key: str) -> None:
    width, height = 980, max(320, 72 + 34 * len(rows))
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((22, 18), title, fill=(0, 0, 0))
    values = [safe_float(row.get(value_key), 0.0) for row in rows]
    max_value = max(values + [1e-6])
    for idx, row in enumerate(rows):
        y = 58 + idx * 34
        label = str(row.get(label_key, ""))[:44]
        value = safe_float(row.get(value_key), 0.0)
        draw.text((22, y), label, fill=(0, 0, 0))
        draw.rectangle((330, y, 330 + int(500 * value / max_value), y + 20), fill=(68, 126, 177))
        draw.text((850, y), f"{value:.4f}", fill=(0, 0, 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)


def route_distribution(rows: list[dict[str, str]]) -> dict[str, int]:
    return dict(Counter(oracle_route(row) for row in rows))


def write_input_audit(extra_lines: list[str] | None = None) -> None:
    files = [
        DATASET_CSV,
        TABLE_DIR / "generative_audiodepth_train.csv",
        TABLE_DIR / "generative_audiodepth_validation.csv",
        TABLE_DIR / "generative_audiodepth_test.csv",
        TABLE_DIR / "generative_route_regret_predictions.csv",
        TABLE_DIR / "generative_audiodepth_distillation.csv",
        TABLE_DIR / "controlled_v2_real_whisper_cer.csv",
        TABLE_DIR / "audiodepth_v2_metadata.csv",
    ]
    rows = sample_rows()
    task_rows = read_rows(DATASET_CSV)
    lines = [
        "# Generative AudioDepth Reliability Input Audit",
        "",
        "Stage 33 reuses the real Stage 32 artifacts in the current branch.",
        "",
        "## Files",
        "",
    ]
    for path in files:
        lines.append(f"- `{path.relative_to(PROJECT_ROOT)}`: {'present' if path.exists() else 'missing'}")
    lines.extend(
        [
            "",
            "## Counts",
            "",
            f"- unique samples: {len(rows)}",
            f"- task rows: {len(task_rows)}",
            f"- task distribution: {distribution(task_rows, 'target_task')}",
            f"- oracle-route distribution: {distribution(rows, 'oracle_route')}",
            f"- target-family distribution: {distribution(rows, 'target_family')}",
            "",
            "## Leakage Risk",
            "",
            "- Teacher map targets may use source tracks and remain analysis-only.",
            "- Student/probe inputs are restricted to mixed-only metadata, generated-map summaries, or held-out teacher-map upper bounds.",
            "- Split checks group by source utterance tokens, source pairs, counterfactual family IDs, and mixed wav paths.",
            "",
            "## Data Sufficiency",
            "",
            "- 60 samples are enough for deterministic reliability probes and failure discovery.",
            "- 60 samples are not enough for a large neural generator or broad deployment claims.",
        ]
    )
    if extra_lines:
        lines.extend(["", "## Stage 33 Notes", "", *extra_lines])
    write_markdown(FIGURE_DIR / "generative_audiodepth_reliability_input_audit.md", lines)
