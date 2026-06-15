from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np

from .audio_depth_router_common import PROJECT_ROOT, ROUTE_LABELS, read_csv, rel, write_csv
from .audio_depth_systematic_common import STRESS_LABELS_CSV, STRESS_MANIFEST_CSV, build_stress_feature_row, rows_by_sample, safe_float
from .evaluate_audio_depth_systematic_router import load_model_predict, router_v2_proxy


TRANSCRIPTS_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_transcripts.csv"
REAL_CER_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_cer.csv"
REAL_LABELS_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_route_labels.csv"
REAL_COMPARISON_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_router_comparison.csv"
SUMMARY_MD = PROJECT_ROOT / "results" / "figures" / "audio_depth_real_asr_summary.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate real Whisper CER for AudioDepth stress validation.")
    parser.add_argument("--systematic-model", default="hybrid_late_fusion_v2")
    return parser.parse_args()


def normalize_for_cer(text: str) -> str:
    text = re.sub(r"\[SPEAKER_[12]\]", "", text or "")
    chars = []
    for char in text.lower():
        if "\u4e00" <= char <= "\u9fff" or char.isalnum():
            chars.append(char)
    return "".join(chars)


def cer(reference: str, hypothesis: str) -> float:
    ref = normalize_for_cer(reference)
    hyp = normalize_for_cer(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, rc in enumerate(ref, start=1):
        curr = [i]
        for j, hc in enumerate(hyp, start=1):
            cost = 0 if rc == hc else 1
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost))
        prev = curr
    return round(prev[-1] / len(ref), 6)


def source_reference_path(source_path: str) -> Path:
    stem = Path(source_path).stem
    for suffix in ["_spk1", "_spk2", "_mixed"]:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    return PROJECT_ROOT / "resources" / "synthetic_overlap_v2" / "references" / f"{stem}_silver_reference.json"


def load_reference(sample: dict[str, str]) -> dict[str, str]:
    path = source_reference_path(sample["source_spk1"])
    if not path.exists():
        return {"reference_text": "", "reference_type": "missing", "reference_path": rel(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        "reference_text": payload.get("full_text") or payload.get("text", ""),
        "speaker_1_text": payload.get("speaker_1_text", ""),
        "speaker_2_text": payload.get("speaker_2_text", ""),
        "reference_type": payload.get("reference_type", "silver_reference"),
        "reference_path": rel(path),
    }


def route_texts(rows: list[dict[str, str]]) -> dict[str, str]:
    by_route = {row["route"]: row.get("text", "") for row in rows if row.get("status") == "ok"}
    if "separated" not in by_route and "spk1" in by_route and "spk2" in by_route:
        by_route["separated"] = f"[SPEAKER_1] {by_route['spk1']}\n[SPEAKER_2] {by_route['spk2']}"
    if "cleaned" not in by_route and "separated" in by_route:
        by_route["cleaned"] = normalize_for_cer(by_route["separated"])
    return by_route


def route_value(cers: dict[str, float], route: str) -> float:
    value = cers.get(route)
    if value is None:
        return float("nan")
    return value


def mean_valid(values: list[float]) -> float:
    valid = [value for value in values if np.isfinite(value)]
    return round(float(np.mean(valid)), 6) if valid else float("nan")


def main() -> None:
    args = parse_args()
    manifest = rows_by_sample(STRESS_MANIFEST_CSV)
    proxy_labels = rows_by_sample(STRESS_LABELS_CSV)
    transcript_rows = read_csv(TRANSCRIPTS_CSV)
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in transcript_rows:
        grouped.setdefault(row["sample_id"], []).append(row)
    feature_rows = []
    for sample_id in grouped:
        if sample_id in manifest and sample_id in proxy_labels:
            feature_rows.append(build_stress_feature_row(manifest[sample_id], proxy_labels[sample_id]))
    systematic_predictions = {row["sample_id"]: row for row in load_model_predict(args.systematic_model, feature_rows)}
    cer_rows = []
    label_rows = []
    for sample_id, rows in grouped.items():
        if sample_id == "__total__" or sample_id not in manifest:
            continue
        sample = manifest[sample_id]
        reference = load_reference(sample)
        texts = route_texts(rows)
        cers = {route: cer(reference["reference_text"], texts.get(route, "")) for route in ROUTE_LABELS if route in texts}
        oracle_route = min(cers, key=cers.get) if cers else "missing"
        router_v2_route = router_v2_proxy(build_stress_feature_row(sample, proxy_labels.get(sample_id, {"mixed_cer": 0, "separated_cer": 0, "cleaned_cer": 0, "best_route_label": "mixed"})))
        systematic_route = systematic_predictions.get(sample_id, {}).get("predicted_route_label", "missing")
        row = {
            "sample_id": sample_id,
            "split": sample.get("split", ""),
            "overlap_ratio": sample.get("overlap_ratio", ""),
            "reference_type": reference["reference_type"],
            "reference_path": reference["reference_path"],
            "mixed_cer_real": cers.get("mixed", ""),
            "separated_cer_real": cers.get("separated", ""),
            "cleaned_cer_real": cers.get("cleaned", ""),
            "oracle_route_real": oracle_route,
            "router_v2_route": router_v2_route,
            "best_systematic_router": args.systematic_model,
            "best_systematic_router_route": systematic_route,
            "systematic_router_cer_real": route_value(cers, systematic_route),
            "router_v2_cer_real": route_value(cers, router_v2_route),
            "oracle_cer_real": route_value(cers, oracle_route),
            "evidence_type": "real_whisper_asr_against_synthetic_silver_reference",
        }
        cer_rows.append(row)
        label_rows.append(
            {
                "sample_id": sample_id,
                "oracle_route_real": oracle_route,
                "oracle_cer_real": row["oracle_cer_real"],
                "label_source": "real_whisper_cer_argmin",
                "reference_type": reference["reference_type"],
                "evidence_type": row["evidence_type"],
            }
        )
    comparison = []
    methods = {
        "fixed_mixed_real": [safe_float(row.get("mixed_cer_real"), float("nan")) for row in cer_rows],
        "fixed_separated_real": [safe_float(row.get("separated_cer_real"), float("nan")) for row in cer_rows],
        "fixed_cleaned_real": [safe_float(row.get("cleaned_cer_real"), float("nan")) for row in cer_rows],
        "router_v2_real": [safe_float(row.get("router_v2_cer_real"), float("nan")) for row in cer_rows],
        f"{args.systematic_model}_real": [safe_float(row.get("systematic_router_cer_real"), float("nan")) for row in cer_rows],
        "oracle_real": [safe_float(row.get("oracle_cer_real"), float("nan")) for row in cer_rows],
    }
    for name, values in methods.items():
        comparison.append({"method": name, "average_cer_real": mean_valid(values), "sample_count": len([v for v in values if np.isfinite(v)]), "evidence_type": "real_whisper_asr_against_synthetic_silver_reference"})
    write_csv(REAL_CER_CSV, cer_rows)
    write_csv(REAL_LABELS_CSV, label_rows)
    write_csv(REAL_COMPARISON_CSV, sorted(comparison, key=lambda row: safe_float(row["average_cer_real"], 99.0)))
    best = min(comparison, key=lambda row: safe_float(row["average_cer_real"], 99.0)) if comparison else {}
    SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.write_text(
        "\n".join(
            [
                "# AudioDepth Real Whisper ASR Summary",
                "",
                f"- Samples evaluated: `{len(cer_rows)}`",
                f"- Reference: `synthetic/silver_reference`",
                f"- Best aggregate row: `{best.get('method', '')}` CER `{best.get('average_cer_real', '')}`",
                f"- Systematic router: `{args.systematic_model}`",
                "",
                "This file is Stage 24 real Whisper ASR evidence. It does not overwrite Stage 23 `synthetic/silver_proxy` tables.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote real ASR CER comparison to {rel(REAL_COMPARISON_CSV)}")


if __name__ == "__main__":
    main()
