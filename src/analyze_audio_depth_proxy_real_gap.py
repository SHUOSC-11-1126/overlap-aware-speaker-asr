from __future__ import annotations

from PIL import Image, ImageDraw

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel, write_csv
from .audio_depth_systematic_common import STRESS_LABELS_CSV, rows_by_sample, safe_float


OUT_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_proxy_real_gap.csv"
OUT_PNG = PROJECT_ROOT / "results" / "figures" / "audio_depth_proxy_real_gap.png"
OUT_MD = PROJECT_ROOT / "results" / "figures" / "audio_depth_proxy_real_gap.md"


def real_gap(row: dict[str, str]) -> float:
    vals = sorted([safe_float(row[f"{r}_cer_real"], 999.0) for r in ["mixed", "separated", "cleaned"]])
    return round(vals[1] - vals[0], 6)


def proxy_gap(row: dict[str, str]) -> float:
    vals = sorted([safe_float(row[f"{r}_cer"], 999.0) for r in ["mixed", "separated", "cleaned"]])
    return round(vals[1] - vals[0], 6)


def draw(rows: list[dict[str, str]]) -> None:
    w, h = 640, 360
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    d.text((20, 15), "Proxy route gap vs real route gap", fill=(0, 0, 0))
    d.line((60, 310, 600, 310), fill=(0, 0, 0))
    d.line((60, 60, 60, 310), fill=(0, 0, 0))
    max_x = max([safe_float(r["proxy_route_gap"]) for r in rows] + [0.1])
    max_y = max([safe_float(r["real_route_gap"]) for r in rows] + [0.1])
    for row in rows:
        x = 60 + int(520 * safe_float(row["proxy_route_gap"]) / max_x)
        y = 310 - int(240 * safe_float(row["real_route_gap"]) / max_y)
        color = (30, 90, 180) if row["oracle_route_match"] == "True" else (190, 60, 45)
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    im.save(OUT_PNG)


def main() -> None:
    proxy = rows_by_sample(STRESS_LABELS_CSV)
    real = read_csv(PROJECT_ROOT / "results" / "tables" / "audio_depth_real_asr_cer.csv")
    rows = []
    for row in real:
        sid = row["sample_id"]
        p = proxy.get(sid, {})
        rows.append(
            {
                "sample_id": sid,
                "proxy_oracle_route": p.get("best_route_label", ""),
                "real_oracle_route": row.get("oracle_route_real", ""),
                "oracle_route_match": str(p.get("best_route_label", "") == row.get("oracle_route_real", "")),
                "proxy_route_gap": proxy_gap(p) if p else "",
                "real_route_gap": real_gap(row),
                "proxy_best_cer": min([safe_float(p.get(f"{r}_cer"), 999.0) for r in ["mixed", "separated", "cleaned"]]) if p else "",
                "real_best_cer": row.get("oracle_cer_real", ""),
                "overlap_ratio": row.get("overlap_ratio", ""),
            }
        )
    write_csv(OUT_CSV, rows)
    draw(rows)
    matches = sum(1 for r in rows if r["oracle_route_match"] == "True")
    OUT_MD.write_text(
        "\n".join(
            [
                "# AudioDepth Proxy-To-Real Gap",
                "",
                f"- Samples compared: `{len(rows)}`",
                f"- Proxy/real oracle route matches: `{matches}`",
                "",
                "`proxy labels are useful for exploration but insufficient for final ASR evidence` when route rankings or route gaps do not transfer to real Whisper CER.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote proxy-real gap analysis to {rel(OUT_CSV)}")


if __name__ == "__main__":
    main()
