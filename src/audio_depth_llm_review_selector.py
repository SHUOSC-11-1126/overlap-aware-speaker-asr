from __future__ import annotations

from .audio_depth_router_common import read_csv, rel, write_csv
from .audio_depth_systematic_common import LLM_REVIEW_CSV, PREDICTIONS_CSV, safe_float


def main() -> None:
    rows = [row for row in read_csv(PREDICTIONS_CSV) if row["model_name"] == "calibrated_confidence_router"]
    candidates = []
    for row in rows:
        confidence = safe_float(row.get("confidence"), 0.0)
        if confidence < 0.72 or row.get("risk_level") == "high":
            candidates.append(
                {
                    "sample_id": row["sample_id"],
                    "predicted_route": row["predicted_route_label"],
                    "confidence": confidence,
                    "risk_reason": row.get("explanation", "low confidence systematic route"),
                    "suggested_action": "llm_critic_review" if confidence >= 0.5 else "manual_review",
                    "transcript_path": "",
                }
            )
    write_csv(LLM_REVIEW_CSV, candidates)
    print(f"Wrote {len(candidates)} LLM/review candidates to {rel(LLM_REVIEW_CSV)}")


if __name__ == "__main__":
    main()
