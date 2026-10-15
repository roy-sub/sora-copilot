"""Operational volumes, areas, and the population density band.

The operator draws the flight geography. Everything else is **derived**: the contingency
volume from the aircraft's speed and the reaction and position-keeping assumptions, the
ground risk buffer from the altitude, the adjacent area from the buffer. No volume is
typed in, and every derivation cites the parameter it used from ``tables/buffers.csv``.

Geometry is stored in EPSG:4326 and reprojected to a local equal-area CRS for area and
buffer maths, because buffering in degrees is wrong by a factor that depends on latitude.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from math import radians, tan
from typing import Any

import numpy as np
from pyproj import CRS, Transformer
from shapely import transform as shapely_transform
from shapely.geometry import Polygon, mapping, shape

from app.domain import GeoJSONPolygon, OperationalVolume
from app.engine.rulebase.loader import load_rulebase

#: Density band ceilings, read from the iGRC table so the two cannot disagree.
GRAVITY = 9.81


class GeoError(ValueError):
    """The geometry cannot be used. Raised rather than deriving from something invalid."""


@dataclass(frozen=True, slots=True)
class BufferParams:
    """The transcribed derivation parameters, with the note each one came with."""

    reaction_time_s: float
    bank_angle_deg: float
    position_error_m: float
    vertical_contingency_m: float
    grb_method: str
    grb_multiplier: float
    adjacent_area_method: str
    adjacent_area_distance_m: float
    verified: bool
    notes: dict[str, str] = field(default_factory=dict)


@lru_cache
def buffer_params(version_dir: str = "sora_2_5") -> BufferParams:
    table = load_rulebase(version_dir)["buffers"]
    rows = {r["parameter"]: r for r in table.rows}

    def num(key: str) -> float:
        try:
            return float(rows[key]["value"])
        except (KeyError, ValueError) as exc:
            raise GeoError(f"buffers.csv is missing a usable {key}") from exc

    return BufferParams(
        reaction_time_s=num("reaction_time"),
        bank_angle_deg=num("bank_angle"),
        position_error_m=num("position_error"),
        vertical_contingency_m=num("vertical_contingency"),
        grb_method=rows["grb_method"]["value"],
        grb_multiplier=num("grb_multiplier"),
        adjacent_area_method=rows["adjacent_area_method"]["value"],
        adjacent_area_distance_m=num("adjacent_area_distance"),
        verified=table.verified,
        notes={k: v["note"] for k, v in rows.items()},
    )


@dataclass(frozen=True, slots=True)
class Derivation:
    """One derived number, with the parameters that produced it."""

    value_m: float
    rule: str
    inputs: dict[str, float]


@dataclass(frozen=True, slots=True)
class DerivedVolumes:
    contingency_lateral_m: float
    contingency_vertical_m: float
    ground_risk_buffer_m: float
    adjacent_area_m: float
    flight_geography_km2: float
    contingency_volume_km2: float
    ground_risk_buffer_km2: float
    adjacent_area_km2: float
    contingency_volume: GeoJSONPolygon
    ground_risk_buffer: GeoJSONPolygon
    adjacent_area: GeoJSONPolygon
    derivations: list[Derivation]
    unverified: bool


def _polygon(geo: GeoJSONPolygon) -> Polygon:
    poly = shape(geo.model_dump())
    if not isinstance(poly, Polygon):
        raise GeoError("the flight geography must be a single Polygon")
    if poly.is_empty:
        raise GeoError("the flight geography is empty")
    if not poly.is_valid:
        # A self-intersecting ring is a drawing mistake, not something to silently repair:
        # buffer(0) would change the area the operator sees.
        raise GeoError("the flight geography is self-intersecting; redraw the outline")
    return poly


def _equal_area_crs(poly: Polygon) -> CRS:
    """A Lambert azimuthal equal-area projection centred on the geometry.

    Centring on the operation keeps area and distance error negligible at the scale of a
    drone corridor, and needs no UTM-zone bookkeeping at a zone boundary.
    """
    lon, lat = poly.centroid.x, poly.centroid.y
    return CRS.from_proj4(
        f"+proj=laea +lat_0={lat:.6f} +lon_0={lon:.6f} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    )


def _reproject(poly: Polygon, transformer: Transformer) -> Polygon:
    """Reproject every vertex in one vectorised call."""

    def move(coords: Any) -> Any:
        x, y = transformer.transform(coords[:, 0], coords[:, 1])
        return np.column_stack([x, y])

    return shapely_transform(poly, move)


def _project(poly: Polygon) -> tuple[Polygon, Transformer, Transformer]:
    crs_4326 = CRS.from_epsg(4326)
    crs_local = _equal_area_crs(poly)
    fwd = Transformer.from_crs(crs_4326, crs_local, always_xy=True)
    rev = Transformer.from_crs(crs_local, crs_4326, always_xy=True)
    return _reproject(poly, fwd), fwd, rev


def _to_geojson(poly: Polygon, rev: Transformer) -> GeoJSONPolygon:
    back = _reproject(poly, rev)
    data = mapping(back)
    # A buffer can round a polygon into a multipolygon only if the input was degenerate,
    # which _polygon already refuses.
    return GeoJSONPolygon.model_validate({"type": "Polygon", "coordinates": data["coordinates"]})


def contingency_lateral(max_speed_ms: float, params: BufferParams) -> Derivation:
    """Reaction distance + half the turn radius at the assumed bank + position error."""
    reaction = max_speed_ms * params.reaction_time_s
    turn_radius = (max_speed_ms**2) / (GRAVITY * tan(radians(params.bank_angle_deg)))
    value = reaction + turn_radius / 2 + params.position_error_m
    return Derivation(
        value_m=round(value, 1),
        rule=(
            f"Reaction distance {reaction:.1f} m at {max_speed_ms:g} m/s over "
            f"{params.reaction_time_s:g} s, plus half the {turn_radius:.1f} m turn radius at "
            f"{params.bank_angle_deg:g}° bank, plus {params.position_error_m:g} m position error."
        ),
        inputs={
            "max_speed_ms": max_speed_ms,
            "reaction_time_s": params.reaction_time_s,
            "bank_angle_deg": params.bank_angle_deg,
            "position_error_m": params.position_error_m,
        },
    )


def ground_risk_buffer(altitude_m: float, contingency_m: float, params: BufferParams) -> Derivation:
    """The 1:1 rule as the conservative default, stated as the assumption it is."""
    if params.grb_method != "one_to_one":
        raise GeoError(
            f"buffers.csv asks for the {params.grb_method!r} ground-risk-buffer method, "
            "which is not implemented. Transcribe the method before using it."
        )
    value = (altitude_m + params.vertical_contingency_m) * params.grb_multiplier
    return Derivation(
        value_m=round(value, 1),
        rule=(
            f"1:1 rule — the buffer equals the contingency volume height: {altitude_m:g} m "
            f"plus {params.vertical_contingency_m:g} m vertical contingency, × "
            f"{params.grb_multiplier:g}. Conservative default, not a ballistic computation."
        ),
        inputs={
            "altitude_m": altitude_m,
            "vertical_contingency_m": params.vertical_contingency_m,
            "grb_multiplier": params.grb_multiplier,
        },
    )


def derive(
    flight_geography: GeoJSONPolygon,
    *,
    max_altitude_agl_m: float,
    max_speed_ms: float,
    version_dir: str = "sora_2_5",
) -> DerivedVolumes:
    """Everything the map step shows, derived from the drawn outline."""
    if max_altitude_agl_m <= 0:
        raise GeoError("the maximum altitude must be above zero")
    if max_speed_ms <= 0:
        raise GeoError("the aircraft's maximum speed must be above zero")

    params = buffer_params(version_dir)
    fg_wgs = _polygon(flight_geography)
    fg, _fwd, rev = _project(fg_wgs)

    lateral = contingency_lateral(max_speed_ms, params)
    grb = ground_risk_buffer(max_altitude_agl_m, lateral.value_m, params)

    cv = fg.buffer(lateral.value_m, quad_segs=24, join_style=2)
    buffer_ring = cv.buffer(grb.value_m, quad_segs=24, join_style=2)
    adjacent = buffer_ring.buffer(params.adjacent_area_distance_m, quad_segs=24, join_style=2)

    km2 = 1_000_000.0
    return DerivedVolumes(
        contingency_lateral_m=lateral.value_m,
        contingency_vertical_m=params.vertical_contingency_m,
        ground_risk_buffer_m=grb.value_m,
        adjacent_area_m=params.adjacent_area_distance_m,
        flight_geography_km2=round(fg.area / km2, 4),
        contingency_volume_km2=round(cv.area / km2, 4),
        ground_risk_buffer_km2=round(buffer_ring.area / km2, 4),
        adjacent_area_km2=round(adjacent.area / km2, 4),
        contingency_volume=_to_geojson(cv, rev),
        ground_risk_buffer=_to_geojson(buffer_ring, rev),
        adjacent_area=_to_geojson(adjacent, rev),
        derivations=[lateral, grb],
        unverified=not params.verified,
    )


def volume_with_derived(volume: OperationalVolume, derived: DerivedVolumes) -> OperationalVolume:
    return volume.model_copy(
        update={
            "contingency_volume": derived.contingency_volume,
            "ground_risk_buffer": derived.ground_risk_buffer,
            "adjacent_area_km": round(derived.adjacent_area_m / 1000, 3),
        }
    )


# ------------------------------------------------------------------ density


@lru_cache
def density_bands(version_dir: str = "sora_2_5") -> list[tuple[str, float | None]]:
    """The iGRC rows, so the geo service and the engine agree on where a band ends."""
    rows = load_rulebase(version_dir)["igrc"].rows
    out: list[tuple[str, float | None]] = []
    for row in sorted(rows, key=lambda r: int(r["band_index"])):
        if int(row["band_index"]) == 0:
            continue  # the controlled ground area is chosen by environment, not density
        raw = row["max_density"]
        out.append((row["density_band"], float(raw) if raw else None))
    return out


def band_for(density_per_km2: float, version_dir: str = "sora_2_5") -> str:
    """The first band whose ceiling the density has not reached."""
    for name, ceiling in density_bands(version_dir):
        if ceiling is None or density_per_km2 < ceiling:
            return name
    return density_bands(version_dir)[-1][0]


@lru_cache
def _environment_hints(version_dir: str = "sora_2_5") -> dict[str, tuple[str, str]]:
    return {
        r["density_band"]: (r["suggested_environment"], r["rationale"])
        for r in load_rulebase(version_dir)["density_environment_hint"].rows
    }


def ground_environment_for(density_per_km2: float, version_dir: str = "sora_2_5") -> tuple[str, str]:
    """A suggested ground environment from the sampled density, and why.

    A **suggestion**, never a decision. The thresholds live in
    ``tables/density_environment_hint.csv`` — which is ours, not the regulation's — so
    they can be reviewed and corrected in the open. The operator is always shown the
    sampled value, the band and this rationale, and can override all of it.

    A controlled ground area and an assembly of people are never suggested: a raster
    cannot tell a fenced compound or a crowd from a housing estate, and the determination
    turns on exactly that distinction.
    """
    band = band_for(density_per_km2, version_dir)
    hint = _environment_hints(version_dir).get(band)
    if hint is None:
        raise GeoError(f"density_environment_hint.csv has no row for the band {band!r}")
    return hint
