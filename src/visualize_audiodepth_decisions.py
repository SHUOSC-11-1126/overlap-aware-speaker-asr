from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from .audio_depth_router_common import PROJECT_ROOT, normalize01, read_csv, rel
from .audiodepth_centric_common import CASCADE_CSV, FIGURE_DIR, GATE_PREDICTIONS_CSV, METADATA_CSV


def pick_cases(rows: list[dict[str, str]], gate: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    selected = []
    wants = [
        ("easy_mixed correct", lambda r: gate[r["sample_id"]]["predicted_gate_label"] == "easy_mixed" and r["selected_route"] == r["oracle_route"]),
        ("separation_helpful correct", lambda r: gate[r["sample_id"]]["predicted_gate_label"] == "likely_separation_helpful" and r["selected_route"] == r["oracle_route"]),
        ("ambiguous_needs_text_probe", lambda r: gate[r["sample_id"]]["predicted_gate_label"] == "ambiguous_needs_text_probe"),
        ("review_risk", lambda r: gate[r["sample_id"]]["predicted_gate_label"] == "review_risk"),
        ("AudioDepth failure", lambda r: r["selected_route"] != r["oracle_route"]),
        ("text router rescue case", lambda r: r.get("stage2_text_probe_called") == "True" and r["selected_route"] == r["oracle_route"]),
    ]
    for label, fn in wants:
        match = next((row for row in rows if fn(row)), None)
        if match and match["sample_id"] not in {row["sample_id"] for row in selected}:
            selected.append({**match, "case_type": label})
    return selected


def panel(arr: np.ndarray, title: str) -> Image.Image:
    img = Image.fromarray(np.uint8(normalize01(arr) * 255), mode="L").convert("RGB")
    img = img.resize((240, 140), Image.Resampling.BILINEAR)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 240, 22), fill=(0, 0, 0))
    draw.text((6, 5), title[:32], fill=(255, 255, 255))
    return img


def main() -> None:
    cascade = [row for row in read_csv(CASCADE_CSV) if row["model_name"] == "audiodepth_stage1_plus_text_stage2"]
    gate = {row["sample_id"]: row for row in read_csv(GATE_PREDICTIONS_CSV)}
    meta = {row["sample_id"]: row for row in read_csv(METADATA_CSV)}
    cases = pick_cases(cascade, gate)
    row_h = 205
    canvas = Image.new("RGB", (1020, max(row_h, row_h * len(cases))), "white")
    draw = ImageDraw.Draw(canvas)
    lines = ["# AudioDepth Decision Examples", ""]
    for idx, row in enumerate(cases):
        y = idx * row_h
        m = meta[row["sample_id"]]
        arr = np.load(PROJECT_ROOT / m["map_path"])
        canvas.paste(panel(arr[0], "C1 logmel"), (0, y + 38))
        canvas.paste(panel(arr[1], "C2 overlap_proxy"), (245, y + 38))
        canvas.paste(panel(arr[2], "C3 uncertainty_proxy"), (490, y + 38))
        text = [
            row["case_type"],
            row["sample_id"],
            f"gate={gate[row['sample_id']]['predicted_gate_label']} conf={gate[row['sample_id']]['confidence']}",
            f"selected={row['selected_route']} oracle={row['oracle_route']}",
            f"CER={row['selected_cer']} gap={row['route_gap']}",
        ]
        yy = y + 46
        for item in text:
            draw.text((748, yy), item[:42], fill=(0, 0, 0))
            yy += 28
        lines.extend(
            [
                f"## {row['case_type']}: {row['sample_id']}",
                "",
                f"- gate prediction: `{gate[row['sample_id']]['predicted_gate_label']}` confidence `{gate[row['sample_id']]['confidence']}`",
                f"- selected route: `{row['selected_route']}` oracle route: `{row['oracle_route']}`",
                f"- route CER: `{row['selected_cer']}` oracle CER: `{row['oracle_cer']}` route gap: `{row['route_gap']}`",
                f"- map path: `{m['map_path']}`",
                "",
            ]
        )
    out = FIGURE_DIR / "audiodepth_decision_examples.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    (FIGURE_DIR / "audiodepth_decision_examples.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote AudioDepth decision examples to {rel(out)}")


if __name__ == "__main__":
    main()
