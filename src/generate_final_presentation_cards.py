from __future__ import annotations

from PIL import Image, ImageDraw

from .audiodepth_centric_common import FIGURE_DIR


def canvas(title: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (1400, 820), (250, 251, 248))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 1400, 92), fill=(32, 48, 67))
    draw.text((44, 30), title, fill=(255, 255, 255))
    return img, draw


def card(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], title: str, lines: list[str], fill: tuple[int, int, int]) -> None:
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=8, fill=fill, outline=(205, 210, 214), width=2)
    draw.text((x1 + 24, y1 + 20), title, fill=(20, 28, 36))
    y = y1 + 62
    for line in lines:
        draw.text((x1 + 24, y), line, fill=(38, 48, 58))
        y += 34


def timeline() -> None:
    img, draw = canvas("AudioDepth Frontier Timeline")
    stages = [
        ("Stage 21", "MVP", "AudioDepth maps + weak first router"),
        ("Stage 22", "Model Zoo", "MLP / CNN / hybrid fusion improved silver split"),
        ("Stage 24-25", "Real Whisper Gap", "Proxy gains did not transfer cleanly"),
        ("Stage 26", "Controlled Benchmark", "Route-sensitive real-ASR evidence"),
        ("Stage 27", "Balanced v2", "Router not blindly selecting separated"),
        ("Stage 28-30", "AudioDepth Gate", "Mixed-only gate, calibration, risk guard"),
        ("Stage 31", "Safety Ledger", "Claims, limits, review guard"),
    ]
    x = 70
    y = 250
    for idx, (stage, title, detail) in enumerate(stages):
        draw.ellipse((x, y, x + 34, y + 34), fill=(69, 123, 157))
        draw.text((x - 12, y - 46), stage, fill=(20, 28, 36))
        draw.text((x - 18, y + 50), title, fill=(20, 28, 36))
        draw.text((x - 46, y + 88), detail, fill=(70, 80, 90))
        if idx < len(stages) - 1:
            draw.line((x + 34, y + 17, x + 172, y + 17), fill=(69, 123, 157), width=4)
        x += 184
    img.save(FIGURE_DIR / "final_project_timeline.png")


def key_results() -> None:
    img, draw = canvas("Final Key Results")
    card(draw, (54, 130, 430, 330), "Stable Gold", ["router_v2 CER 0.120042", "matches oracle on 5 verified cases", "gold/manual verified"], (239, 246, 238))
    card(draw, (512, 130, 888, 330), "Synthetic Frontier", ["model-zoo best CER 0.165545", "AudioDepth MVP CER 0.436666", "synthetic/silver"], (244, 241, 232))
    card(draw, (970, 130, 1346, 330), "Controlled Real-ASR", ["hybrid CER 0.256816", "oracle CER 0.255923", "silver-plus real Whisper"], (237, 246, 250))
    card(draw, (54, 400, 430, 620), "Balanced v2", ["router CER 0.502854", "router_v2 CER 0.643520", "not blindly separated"], (239, 246, 238))
    card(draw, (512, 400, 888, 620), "AudioDepth Gate", ["Stage 29 CER 0.533160", "probe reduction 0.716667", "false-safe 0.183333"], (244, 241, 232))
    card(draw, (970, 400, 1346, 620), "Risk Guard", ["balanced CER 0.529082", "direct false-safe 0", "Stage-2 risk remains"], (237, 246, 250))
    draw.text((54, 710), "Takeaway: AudioDepth is strongest as a safety-aware pre-ASR acoustic triage module, not a production router.", fill=(20, 28, 36))
    img.save(FIGURE_DIR / "final_key_results_card.png")


def evidence_levels() -> None:
    img, draw = canvas("Evidence Levels")
    rows = [
        ("gold/manual verified", "router_v2 gold cases", 0.95),
        ("real Whisper sampled validation", "controlled / balanced v2 slices", 0.78),
        ("controlled silver-plus", "AudioDepth gate / risk guard", 0.68),
        ("synthetic silver", "model zoo and hybrid fusion", 0.52),
        ("proxy simulation", "cost and stress cascades", 0.38),
        ("diagnostic only", "feature probes and gap audits", 0.28),
        ("roadmap only", "AST / WavLM / LLM repair", 0.16),
    ]
    y = 150
    for level, example, width in rows:
        draw.text((78, y + 10), level, fill=(20, 28, 36))
        draw.rectangle((420, y, 420 + int(760 * width), y + 34), fill=(69, 123, 157))
        draw.rectangle((420, y, 1180, y + 34), outline=(190, 196, 202))
        draw.text((1210, y + 8), example, fill=(60, 70, 80))
        y += 78
    img.save(FIGURE_DIR / "final_evidence_levels.png")


def architecture() -> None:
    img, draw = canvas("Final System Architecture")
    boxes = [
        ((70, 310, 250, 410), "Input audio"),
        ((330, 260, 570, 460), "AudioDepth\nStage-1 gate"),
        ((660, 260, 910, 460), "Stage-2\ntext router"),
        ((1000, 150, 1270, 230), "mixed ASR"),
        ((1000, 290, 1270, 370), "separated ASR"),
        ((1000, 430, 1270, 510), "cleaned separated"),
        ((1000, 570, 1270, 650), "review / abstain"),
    ]
    for xy, label in boxes:
        card(draw, xy, label, [], (239, 246, 238))
    arrows = [
        ((250, 360), (330, 360)),
        ((570, 360), (660, 360)),
        ((910, 360), (1000, 190)),
        ((910, 360), (1000, 330)),
        ((910, 360), (1000, 470)),
        ((910, 360), (1000, 610)),
    ]
    for (x1, y1), (x2, y2) in arrows:
        draw.line((x1, y1, x2, y2), fill=(32, 48, 67), width=4)
        draw.polygon([(x2, y2), (x2 - 14, y2 - 8), (x2 - 14, y2 + 8)], fill=(32, 48, 67))
    draw.text((330, 510), "mixed-only logmel + overlap + uncertainty proxies", fill=(60, 70, 80))
    draw.text((660, 510), "transcript instability remains necessary", fill=(60, 70, 80))
    draw.text((70, 705), "Risk guard blocks unsafe direct bypass; Stage-2 review guard handles high-error mixed fallback.", fill=(20, 28, 36))
    img.save(FIGURE_DIR / "final_system_architecture.png")


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    timeline()
    key_results()
    evidence_levels()
    architecture()
    print("Wrote final presentation cards.")


if __name__ == "__main__":
    main()
