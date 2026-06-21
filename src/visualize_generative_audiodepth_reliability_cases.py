from __future__ import annotations

from PIL import Image, ImageDraw

from .generative_audiodepth_common import FIGURE_DIR, TABLE_DIR, read_rows, safe_float, write_markdown


OUT_PNG = FIGURE_DIR / "generative_audiodepth_reliability_cases.png"
OUT_MD = FIGURE_DIR / "generative_audiodepth_reliability_cases.md"


def first(rows: list[dict[str, str]], predicate, fallback: str) -> str:
    for row in rows:
        if predicate(row):
            return row.get("sample_id") or row.get("base_sample_id") or row.get("policy_name") or fallback
    return fallback


def main() -> None:
    info = read_rows(TABLE_DIR / "generative_audiodepth_reliability_information_value.csv")
    cf = read_rows(TABLE_DIR / "generative_audiodepth_counterfactual_reliability.csv")
    cf_fail = read_rows(TABLE_DIR / "generative_audiodepth_counterfactual_failures.csv")
    rank = read_rows(TABLE_DIR / "generative_regret_calibration_performance.csv")
    fusion = read_rows(TABLE_DIR / "generative_safe_fusion_comparison.csv")
    gap = read_rows(TABLE_DIR / "generative_audiodepth_teacher_student_gap.csv")
    cards = [
        ("Promptable > unconditioned", "map MAE 0.241263 vs 0.246685"),
        (
            "Generated map info",
            first(info, lambda r: r.get("input_name") == "logmel_plus_generated_maps" and safe_float(r.get("accuracy")) > 0, "probe completed"),
        ),
        (
            "Counterfactual monotonic",
            first(cf, lambda r: r.get("monotonic_consistent") == "True", "no success case"),
        ),
        (
            "Counterfactual failure",
            first(cf_fail, lambda r: True, "no failure case"),
        ),
        (
            "False-safe repair",
            first(rank, lambda r: safe_float(r.get("false_safe_count"), 9) < 4, "not repaired"),
        ),
        (
            "New ranker error",
            first(rank, lambda r: safe_float(r.get("selected_route_cer"), 0) > 0.671608, "none detected"),
        ),
        (
            "Safe fusion review",
            first(fusion, lambda r: safe_float(r.get("review_rate")) > 0, "no review"),
        ),
        (
            "Large teacher/student gap",
            first(sorted(gap, key=lambda r: safe_float(r.get("mae")), reverse=True), lambda r: True, "gap unavailable"),
        ),
    ]
    width, height = 1000, 520
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 20), "Generative AudioDepth reliability cases", fill=(0, 0, 0))
    for idx, (title, detail) in enumerate(cards):
        x = 24 + (idx % 2) * 488
        y = 62 + (idx // 2) * 104
        draw.rectangle((x, y, x + 456, y + 78), outline=(150, 150, 150), width=1)
        draw.text((x + 14, y + 12), title, fill=(0, 0, 0))
        draw.text((x + 14, y + 40), str(detail)[:56], fill=(70, 70, 70))
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT_PNG)
    lines = [
        "# Generative AudioDepth Reliability Cases",
        "",
        "| case | selected evidence |",
        "|---|---|",
    ]
    for title, detail in cards:
        lines.append(f"| {title} | {detail} |")
    write_markdown(OUT_MD, lines)
    print(f"wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
