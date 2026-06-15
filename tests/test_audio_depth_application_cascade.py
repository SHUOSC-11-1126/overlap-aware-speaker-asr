from __future__ import annotations

from src.audio_depth_systematic_common import ROUTE_COSTS


def test_route_cost_ordering() -> None:
    assert ROUTE_COSTS["mixed"] < ROUTE_COSTS["separated"] < ROUTE_COSTS["manual_review"]
