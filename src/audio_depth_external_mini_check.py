from __future__ import annotations

from pathlib import Path

from .audio_depth_router_common import PROJECT_ROOT, rel, write_csv
from .audio_depth_systematic_common import EXTERNAL_MINI_CSV, SYSTEMATIC_FIGURE_PREFIX


def main() -> None:
    external_roots = [PROJECT_ROOT / "resources" / "external", PROJECT_ROOT / "resources" / "external_validation"]
    wavs = []
    for root in external_roots:
        if root.exists():
            wavs.extend(root.rglob("*.wav"))
    if not wavs:
        rows = [
            {
                "status": "blocked_no_external_audio",
                "needed_data": "one or more external meeting-style WAV files plus optional transcript/reference metadata",
                "prediction_count": 0,
                "evidence_type": "external/sanity-check blocked",
            }
        ]
        write_csv(EXTERNAL_MINI_CSV, rows)
        (SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_external_mini.md").write_text(
            "# AudioDepth External Mini Check\n\nStatus: blocked. No external audio samples were found under `resources/external` or `resources/external_validation`, so this stage did not claim external prediction evidence.\n",
            encoding="utf-8",
        )
        print(f"Wrote blocked external mini report to {rel(EXTERNAL_MINI_CSV)}")
        return
    rows = [{"sample_id": path.stem, "audio_path": rel(path), "status": "available_unscored", "evidence_type": "external/sanity-check"} for path in wavs]
    write_csv(EXTERNAL_MINI_CSV, rows)
    (SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_external_mini.md").write_text(
        f"# AudioDepth External Mini Check\n\nFound `{len(rows)}` external WAV files. This pass records availability only; CER is not computed without references.\n",
        encoding="utf-8",
    )
    print(f"Wrote external mini availability to {rel(EXTERNAL_MINI_CSV)}")


if __name__ == "__main__":
    main()
