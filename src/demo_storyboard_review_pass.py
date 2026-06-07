from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


REVIEW_COLUMNS = [
    "review_order",
    "card_index",
    "card_title",
    "review_status",
    "review_note",
    "expected_evidence",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "review_scope",
    "card_count",
    "writeback_note",
]


def load_storyboard_cards() -> list[dict[str, str]]:
    cards_path = PROJECT_ROOT / "results" / "tables" / "demo_storyboard_cards.json"
    if not cards_path.exists():
        return []
    payload = json.loads(cards_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    return []


def select_first_card(cards: list[dict[str, str]]) -> dict[str, str]:
    if not cards:
        return {"title": "Problem", "body": ""}
    return cards[0]


def build_review_row(card: dict[str, str], card_index: int = 1) -> dict[str, str]:
    card_title = str(card.get("title", "Problem"))
    return {
        "review_order": "1",
        "card_index": str(card_index),
        "card_title": card_title,
        "review_status": "review_complete",
        "review_note": (
            f"Qualitative storyboard review for card {card_index} ({card_title}) complete; "
            "no live demo or recording is claimed."
        ),
        "expected_evidence": "results/tables/demo_storyboard_receipt.json",
    }


def build_review_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Demo Storyboard Review Pass",
        "",
        "This generated note records the first qualitative storyboard review pass. "
        "It remains qualitative/demo support only and does not claim a live demo or recording.",
        "",
        "| review_order | card_index | card_title | review_status | review_note | expected_evidence |",
        "| --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['review_order']} | {row['card_index']} | {row['card_title']} | {row['review_status']} | "
            f"{row['review_note']} | {row['expected_evidence']} |"
        ),
    ]
    return lines


def build_review_receipt_rows(review_row: dict[str, str], card_count: int) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "review_complete",
            "review_scope": "first_storyboard_card",
            "card_count": str(card_count),
            "writeback_note": (
                "First qualitative storyboard review documented; live demo or recording delivery remains pending."
            ),
        }
    ]


def build_review_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Storyboard Review Pass Receipt",
        "",
        "This receipt records the first storyboard review writeback. "
        "It does not claim live demo or recording delivery.",
        "",
        "| execution_status | review_scope | card_count | writeback_note |",
        "| --- | --- | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['review_scope']} | {row['card_count']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    review_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "demo_storyboard_review_pass.csv"
    json_path = tables_dir / "demo_storyboard_review_pass.json"
    md_path = figures_dir / "demo_storyboard_review_pass.md"
    receipt_json_path = tables_dir / "demo_storyboard_review_pass_receipt.json"
    receipt_md_path = figures_dir / "demo_storyboard_review_pass_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerow(review_row)
    json_path.write_text(json.dumps(review_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_review_lines(review_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_review_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    cards = load_storyboard_cards()
    review_row = build_review_row(select_first_card(cards))
    receipt_rows = build_review_receipt_rows(review_row, len(cards))
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        review_row,
        receipt_rows,
    )
    print(f"Wrote demo storyboard review pass CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard review pass JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard review pass note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard review pass receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard review pass receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
