"""Domain invariants that are easy to break and expensive to get wrong."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain import (
    ALTITUDE_BAND_THRESHOLD_M,
    FLIGHT_LEVEL_600_M,
    Drone,
    GeoJSONPolygon,
    OperationalVolume,
)

SQUARE = GeoJSONPolygon(coordinates=[[[15.4, 47.1], [15.5, 47.1], [15.5, 47.2], [15.4, 47.2], [15.4, 47.1]]])


def test_kinetic_energy_is_computed_not_entered() -> None:
    d = Drone(
        id=uuid4(),
        name="Alta X",
        max_dimension_m=1.32,
        mtom_kg=15.9,
        cruise_speed_ms=18,
        max_speed_ms=22,
    )
    assert d.kinetic_energy_j == pytest.approx(0.5 * 15.9 * 22**2)


def test_explicit_kinetic_energy_is_respected() -> None:
    d = Drone(
        id=uuid4(),
        name="measured",
        max_dimension_m=1.0,
        mtom_kg=10.0,
        cruise_speed_ms=10,
        max_speed_ms=20,
        kinetic_energy_j=1234.0,
    )
    assert d.kinetic_energy_j == 1234.0


@pytest.mark.parametrize(
    ("altitude", "expected"),
    [
        (118.0, "below_150m"),
        (150.0, "below_150m"),  # exactly at the boundary is not "above"
        (150.1, "above_150m"),
        (152.4, "above_150m"),  # 500 ft; the old constant put this in the LOWER band
        (200.0, "above_150m"),
        (18_288.0, "above_150m"),  # exactly FL 600 is not yet above it
        (18_300.0, "above_fl600"),
    ],
)
def test_altitude_band_uses_the_regulation_threshold(altitude: float, expected: str) -> None:
    """Annex C Table C.1 bands: 150 m AGL, and FL 600 above that.

    PLAN.md §0 had recorded the opposite reading — 500 ft converted to 152.4 m — and
    this test asserted it. Table C.1 writes every altitude row as "150 m (~500 ft) AGL":
    150 m is the figure, 500 ft the approximation. An operation between 150.0 m and
    152.4 m was being given the lower air risk band, so the row at 152.4 is the one
    that changed answer.
    """
    v = OperationalVolume(flight_geography=SQUARE, max_altitude_agl_m=altitude)
    assert v.altitude_band == expected


def test_threshold_constant_is_the_tables_own_figure() -> None:
    assert ALTITUDE_BAND_THRESHOLD_M == 150.0
    # 500 ft is 152.4 m, and the table calls it approximate. It is not the boundary.
    assert abs(ALTITUDE_BAND_THRESHOLD_M - 500 * 0.3048) > 2.0


def test_flight_level_600_is_the_top_band() -> None:
    assert FLIGHT_LEVEL_600_M == 18_288.0
