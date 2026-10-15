"""Domain invariants that are easy to break and expensive to get wrong."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain import ALTITUDE_BAND_THRESHOLD_M, Drone, GeoJSONPolygon, OperationalVolume

SQUARE = GeoJSONPolygon(
    coordinates=[[[15.4, 47.1], [15.5, 47.1], [15.5, 47.2], [15.4, 47.2], [15.4, 47.1]]]
)


def test_kinetic_energy_is_computed_not_entered() -> None:
    d = Drone(
        id=uuid4(), name="Alta X", max_dimension_m=1.32, mtom_kg=15.9,
        cruise_speed_ms=18, max_speed_ms=22,
    )
    assert d.kinetic_energy_j == pytest.approx(0.5 * 15.9 * 22**2)


def test_explicit_kinetic_energy_is_respected() -> None:
    d = Drone(
        id=uuid4(), name="measured", max_dimension_m=1.0, mtom_kg=10.0,
        cruise_speed_ms=10, max_speed_ms=20, kinetic_energy_j=1234.0,
    )
    assert d.kinetic_energy_j == 1234.0


@pytest.mark.parametrize(
    ("altitude", "expected"),
    [
        (118.0, "below_500ft"),
        (150.0, "below_500ft"),      # the design's old round number is still below the band
        (152.4, "below_500ft"),      # exactly 500 ft is not "above"
        (152.5, "above_500ft"),
        (200.0, "above_500ft"),
    ],
)
def test_altitude_band_uses_the_regulation_threshold(altitude: float, expected: str) -> None:
    """SORA keys the air-risk tree on 500 ft AGL = 152.4 m, not the round 150 m.

    PLAN.md §0 records the decision; this test is what stops it drifting back.
    """
    v = OperationalVolume(flight_geography=SQUARE, max_altitude_agl_m=altitude)
    assert v.altitude_band == expected


def test_threshold_constant_is_500_feet() -> None:
    assert pytest.approx(500 * 0.3048) == ALTITUDE_BAND_THRESHOLD_M
