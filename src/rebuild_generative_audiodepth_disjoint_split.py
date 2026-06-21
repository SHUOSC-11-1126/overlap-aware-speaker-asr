from __future__ import annotations

import random
from collections import Counter, defaultdict

from .generative_audiodepth_common import FIGURE_DIR, read_rows, safe_float, write_csv, write_markdown
from .generative_audiodepth_reliability_common import (
    RELIABILITY_TEST,
    RELIABILITY_TRAIN,
    RELIABILITY_UNSEEN_DOMINANCE,
    RELIABILITY_UNSEEN_OVERLAP,
    RELIABILITY_VALIDATION,
    group_key,
    leakage_report,
    route_distribution,
    sample_rows,
    source_tokens,
    write_input_audit,
    write_task_split,
)


def connected_components(samples: list[dict[str, str]]) -> list[list[dict[str, str]]]:
    token_to_indices: dict[str, list[int]] = defaultdict(list)
    for idx, row in enumerate(samples):
        tokens = source_tokens(row) or {row["sample_id"]}
        for token in tokens:
            token_to_indices[token].append(idx)
    parent = list(range(len(samples)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for indices in token_to_indices.values():
        for idx in indices[1:]:
            union(indices[0], idx)
    groups: dict[int, list[dict[str, str]]] = defaultdict(list)
    for idx, row in enumerate(samples):
        groups[find(idx)].append(row)
    return sorted(groups.values(), key=lambda rows: sorted(row["sample_id"] for row in rows)[0])


def split_groups(samples: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    tokens = sorted({token for row in samples for token in source_tokens(row)})
    best: tuple[tuple[int, int, int, int], dict[str, str], dict[str, list[dict[str, str]]]] | None = None
    for train_token_count in range(12, min(21, len(tokens) - 5)):
        for validation_token_count in range(3, min(8, len(tokens) - train_token_count - 1)):
            for seed in range(2500):
                shuffled = tokens[:]
                random.Random(seed).shuffle(shuffled)
                assignment = {}
                for idx, token in enumerate(shuffled):
                    if idx < train_token_count:
                        assignment[token] = "train"
                    elif idx < train_token_count + validation_token_count:
                        assignment[token] = "validation"
                    else:
                        assignment[token] = "test"
                splits = {"train": [], "validation": [], "test": []}
                for row in samples:
                    owners = {assignment[token] for token in source_tokens(row)}
                    if len(owners) == 1:
                        splits[next(iter(owners))].append(row)
                counts = {name: len(rows) for name, rows in splits.items()}
                score = (
                    min(counts.values()),
                    sum(counts.values()),
                    counts["test"],
                    counts["validation"],
                )
                if best is None or score > best[0]:
                    best = (score, assignment, splits)
    if best is None:
        return {"train": [], "validation": [], "test": []}
    return best[2]


def challenge_splits(samples: list[dict[str, str]], test_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    overlap_values = sorted(safe_float(row.get("overlap_ratio"), 0.0) for row in samples)
    high_overlap_cut = overlap_values[int(len(overlap_values) * 0.75)] if overlap_values else 0.5
    unseen_overlap = [row for row in test_rows if safe_float(row.get("overlap_ratio"), 0.0) >= high_overlap_cut]
    dominance_counts = Counter(row.get("dominance_type", "") for row in samples)
    rare_dominance = {name for name, _ in dominance_counts.most_common()[::-1][:1]}
    unseen_dominance = [row for row in test_rows if row.get("dominance_type", "") in rare_dominance]
    if not unseen_overlap:
        unseen_overlap = sorted(test_rows, key=lambda r: safe_float(r.get("overlap_ratio"), 0.0), reverse=True)[: max(1, len(test_rows) // 2)]
    if not unseen_dominance:
        unseen_dominance = test_rows[: max(1, len(test_rows) // 2)]
    return unseen_overlap, unseen_dominance


def main() -> None:
    samples = sample_rows()
    existing = {
        "train": read_rows(RELIABILITY_TRAIN),
        "validation": read_rows(RELIABILITY_VALIDATION),
        "test": read_rows(RELIABILITY_TEST),
    }
    splits = split_groups(samples)
    leaks = leakage_report(splits)
    unseen_overlap, unseen_dominance = challenge_splits(samples, splits["test"])
    write_task_split(RELIABILITY_TRAIN, splits["train"])
    write_task_split(RELIABILITY_VALIDATION, splits["validation"])
    write_task_split(RELIABILITY_TEST, splits["test"])
    write_task_split(RELIABILITY_UNSEEN_OVERLAP, unseen_overlap)
    write_task_split(RELIABILITY_UNSEEN_DOMINANCE, unseen_dominance)
    write_csv(
        RELIABILITY_UNSEEN_OVERLAP,
        read_rows(RELIABILITY_UNSEEN_OVERLAP),
    )
    lines = [
        "# Generative AudioDepth Reliability Split Audit",
        "",
        "The split is rebuilt from unique samples and then expanded back to task rows.",
        "",
        "| split | samples | task rows | groups | oracle routes | target families |",
        "|---|---:|---:|---:|---|---|",
    ]
    for name, rows in splits.items():
        task_count = len(read_rows({"train": RELIABILITY_TRAIN, "validation": RELIABILITY_VALIDATION, "test": RELIABILITY_TEST}[name]))
        lines.append(
            f"| {name} | {len(rows)} | {task_count} | {len({group_key(r) for r in rows})} | {route_distribution(rows)} | {dict(Counter(r.get('target_family','') for r in rows))} |"
        )
    lines.extend(
        [
            "",
            f"- source-token connected components: {len(connected_components(samples))}",
            f"- retained strict source-disjoint samples: {sum(len(rows) for rows in splits.values())}",
            f"- dropped cross-partition samples: {len(samples) - sum(len(rows) for rows in splits.values())}",
            "",
            "## Challenge Splits",
            "",
            f"- unseen overlap samples: {len(unseen_overlap)}",
            f"- unseen dominance samples: {len(unseen_dominance)}",
            "",
            "## Leakage Checks",
            "",
            f"- source utterance leaks: {leaks['source_utterance_leaks']}",
            f"- source pair leaks: {leaks['source_pair_leaks']}",
            f"- counterfactual family leaks: {leaks['counterfactual_family_leaks']}",
            f"- mixed wav leaks: {leaks['mixed_wav_leaks']}",
            "",
            "## Teacher Boundary",
            "",
            "Source-track teacher maps remain target construction artifacts only. Student/probe inference uses mixed-only metadata or generated summaries.",
        ]
    )
    write_markdown(FIGURE_DIR / "generative_audiodepth_reliability_split_audit.md", lines)
    write_input_audit([f"Reliability split leakage summary: {leaks}"])
    print(f"wrote reliability split train={len(splits['train'])} validation={len(splits['validation'])} test={len(splits['test'])}")


if __name__ == "__main__":
    main()
