from __future__ import annotations

from collections import Counter, defaultdict

from .generative_audiodepth_common import (
    DATASET_CSV,
    TEST_CSV,
    TRAIN_CSV,
    UNSEEN_DOMINANCE_CSV,
    UNSEEN_OVERLAP_CSV,
    VALIDATION_CSV,
    FIGURE_DIR,
    dataset_fieldnames,
    read_rows,
    safe_float,
    stable_bucket,
    write_csv,
    write_markdown,
)


def group_key(row: dict[str, str]) -> str:
    source_ids = row.get("source_utterance_ids") or row["sample_id"]
    family_id = row.get("counterfactual_family_id") or row["sample_id"]
    return f"{source_ids}::{family_id}"


def split_rows(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[group_key(row)].append(row)
    splits = {"train": [], "validation": [], "test": []}
    ordered = sorted(groups.items(), key=lambda item: stable_bucket(item[0], 10_000))
    n = len(ordered)
    train_cut = max(1, int(round(n * 0.70)))
    validation_cut = max(train_cut + 1, int(round(n * 0.85))) if n > 2 else train_cut
    for idx, (_key, group) in enumerate(ordered):
        if idx < train_cut:
            splits["train"].extend(group)
        elif idx < validation_cut:
            splits["validation"].extend(group)
        else:
            splits["test"].extend(group)
    return splits


def sample_ids(rows: list[dict[str, str]]) -> set[str]:
    return {row["sample_id"] for row in rows}


def leakage_report(splits: dict[str, list[dict[str, str]]]) -> dict[str, str]:
    keys_by_split = {name: {group_key(row) for row in rows} for name, rows in splits.items()}
    ids_by_split = {name: sample_ids(rows) for name, rows in splits.items()}
    pair_names = [("train", "validation"), ("train", "test"), ("validation", "test")]
    group_leaks = []
    sample_leaks = []
    for a, b in pair_names:
        if keys_by_split[a] & keys_by_split[b]:
            group_leaks.append(f"{a}/{b}:{len(keys_by_split[a] & keys_by_split[b])}")
        if ids_by_split[a] & ids_by_split[b]:
            sample_leaks.append(f"{a}/{b}:{len(ids_by_split[a] & ids_by_split[b])}")
    return {
        "source_or_counterfactual_group_leakage": "; ".join(group_leaks) if group_leaks else "none",
        "exact_sample_leakage": "; ".join(sample_leaks) if sample_leaks else "none",
    }


def challenge_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    unseen_overlap = [row for row in rows if row.get("target_task") and safe_float(row.get("overlap_ratio"), 0.0) >= 0.5]
    unseen_dominance = [row for row in rows if row.get("dominance_type") in {"speaker_A_dominant", "speaker_B_dominant"}]
    return unseen_overlap, unseen_dominance


def write_audit(splits: dict[str, list[dict[str, str]]], unseen_overlap: list[dict[str, str]], unseen_dominance: list[dict[str, str]]) -> None:
    leak = leakage_report(splits)
    lines = [
        "# Generative AudioDepth Split Audit",
        "",
        "Rows are split by source utterance IDs plus counterfactual family ID, not by individual target-task rows.",
        "",
        "## Split Counts",
        "",
    ]
    for name in ["train", "validation", "test"]:
        rows = splits[name]
        lines.append(f"- {name}: {len(rows)} target rows / {len(sample_ids(rows))} samples")
    lines.extend(
        [
            f"- unseen_overlap_test: {len(unseen_overlap)} target rows / {len(sample_ids(unseen_overlap))} samples",
            f"- unseen_dominance_test: {len(unseen_dominance)} target rows / {len(sample_ids(unseen_dominance))} samples",
            "",
            "## Leakage Checks",
            "",
            f"- source/counterfactual group leakage: {leak['source_or_counterfactual_group_leakage']}",
            f"- exact sample leakage: {leak['exact_sample_leakage']}",
            "",
            "## Target Task Distribution",
            "",
        ]
    )
    for name, rows in splits.items():
        lines.append(f"- {name}: {dict(Counter(row['target_task'] for row in rows))}")
    write_markdown(FIGURE_DIR / "generative_audiodepth_split_audit.md", lines)


def main() -> None:
    rows = read_rows(DATASET_CSV)
    splits = split_rows(rows)
    unseen_overlap, unseen_dominance = challenge_rows(splits["test"] + splits["validation"])
    write_csv(TRAIN_CSV, splits["train"], dataset_fieldnames())
    write_csv(VALIDATION_CSV, splits["validation"], dataset_fieldnames())
    write_csv(TEST_CSV, splits["test"], dataset_fieldnames())
    write_csv(UNSEEN_OVERLAP_CSV, unseen_overlap, dataset_fieldnames())
    write_csv(UNSEEN_DOMINANCE_CSV, unseen_dominance, dataset_fieldnames())
    write_audit(splits, unseen_overlap, unseen_dominance)
    print(
        "Wrote generative AudioDepth splits: "
        f"train={len(splits['train'])}, validation={len(splits['validation'])}, test={len(splits['test'])}"
    )


if __name__ == "__main__":
    main()
