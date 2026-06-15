from __future__ import annotations

from .audio_depth_zoo_common import FEATURES_CSV, build_hybrid_features_table, rel


def main() -> None:
    rows = build_hybrid_features_table()
    print(f"Wrote {len(rows)} rows to {rel(FEATURES_CSV)}")


if __name__ == "__main__":
    main()
