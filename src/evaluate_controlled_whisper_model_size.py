from __future__ import annotations

from .audio_depth_router_common import PROJECT_ROOT, rel, write_csv


CSV = PROJECT_ROOT / "results" / "tables" / "controlled_whisper_model_size_comparison.csv"
MD = PROJECT_ROOT / "results" / "figures" / "controlled_whisper_model_size_comparison.md"


def main() -> None:
    rows = [
        {"model_size": "base", "status": "completed_in_main_route_eval", "sample_count": 40, "notes": "Base model used for controlled route evaluation."},
        {"model_size": "small", "status": "blocked_model_download_timeout", "sample_count": 0, "notes": "Prior small download did not complete during Stage 25/26 runtime window; not forced."},
    ]
    write_csv(CSV, rows)
    MD.write_text(
        "# Controlled Whisper Model Size Comparison\n\n- `base`: completed in main route evaluation.\n- `small`: blocked by model download time; no stronger-ASR conclusion yet.\n\nStrong ASR may shrink or move mixed/separated boundaries, but this stage does not have completed small-model evidence.\n",
        encoding="utf-8",
    )
    print(f"Wrote model-size comparison to {rel(CSV)}")


if __name__ == "__main__":
    main()
