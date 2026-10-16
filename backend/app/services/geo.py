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
    """The transcribed derivation parameters, with the note each one came with.

    Annex A A.5.2 of AMC1 Article 11. The names are the ones the annex uses, so a
    reviewer can read the CSV, this file and the regulation in the same vocabulary.
    """

    gnss_accuracy_m: float
    position_holding_error_m: float
    map_error_m: float
    reaction_time_s: float
    pitch_angle_max_deg: float
    bank_angle_max_deg: float
    altitude_error_baro_m: float
    altitude_error_gnss_m: float
    vertical_reaction_factor: float
    grb_method: str
    grb_dimension_term: float
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
        gnss_accuracy_m=num("gnss_accuracy"),
        position_holding_error_m=num("position_holding_error"),
        map_error_m=num("map_error"),
        reaction_time_s=num("reaction_time"),
        pitch_angle_max_deg=num("pitch_angle_max"),
        bank_angle_max_deg=num("bank_angle_max"),
        altitude_error_baro_m=num("altitude_error_baro"),
        altitude_error_gnss_m=num("altitude_error_gnss"),
        vertical_reaction_factor=num("vertical_reaction_factor"),
        grb_method=rows["grb_method"]["value"],
        grb_dimension_term=num("grb_dimension_term"),
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
    """S_CV = S_GNSS + S_Pos + S_K + S_R + S_CM, per Annex A A.5.2.3.

    A.5.2.3 gives two forms for the contingency manoeuvre, and which applies depends on
    the airframe: a multirotor stops, a fixed-wing aircraft turns. The aircraft type is
    not recorded anywhere in the mission, so the LARGER of the two is used and the
    derivation says so — a fixed-wing turn at 30 degrees of bank is several times a
    multirotor's stopping distance, and guessing the smaller one would shrink the
    operational volume on an assumption nobody made.
    """
    reaction = max_speed_ms * params.reaction_time_s
    stopping = (max_speed_ms**2) / (2 * GRAVITY * tan(radians(params.pitch_angle_max_deg)))
    turning = (max_speed_ms**2) / (GRAVITY * tan(radians(params.bank_angle_max_deg)))
    manoeuvre = max(stopping, turning)
    shape = "fixed-wing 180° turn" if turning >= stopping else "multirotor stop"
    fixed = params.gnss_accuracy_m + params.position_holding_error_m + params.map_error_m
    value = fixed + reaction + manoeuvre
    return Derivation(
        value_m=round(value, 1),
        rule=(
            f"{params.gnss_accuracy_m:g} m GNSS accuracy + {params.position_holding_error_m:g} m "
            f"position holding + {params.map_error_m:g} m map error + {reaction:.1f} m reaction "
            f"distance at {max_speed_ms:g} m/s over {params.reaction_time_s:g} s + "
            f"{manoeuvre:.1f} m contingency manoeuvre. The manoeuvre is the larger of the two "
            f"forms in Annex A A.5.2.3 — here the {shape} — because the airframe type is not "
            f"recorded."
        ),
        inputs={
            "max_speed_ms": max_speed_ms,
            "gnss_accuracy_m": params.gnss_accuracy_m,
            "position_holding_error_m": params.position_holding_error_m,
            "map_error_m": params.map_error_m,
            "reaction_time_s": params.reaction_time_s,
            "pitch_angle_max_deg": params.pitch_angle_max_deg,
            "bank_angle_max_deg": params.bank_angle_max_deg,
        },
    )


def contingency_height(altitude_m: float, max_speed_ms: float, params: BufferParams) -> Derivation:
    """H_CV = H_FG + H_AM + H_R + H_CM, per Annex A A.5.2.3.

    The altitude error is the GNSS figure rather than the barometric one, and the
    contingency manoeuvre is again the larger of the two forms — which on this axis is
    the multirotor's, not the fixed-wing's.
    """
    altitude_error = max(params.altitude_error_baro_m, params.altitude_error_gnss_m)
    reaction = max_speed_ms * params.vertical_reaction_factor * params.reaction_time_s
    multirotor = 0.5 * (max_speed_ms**2) / GRAVITY
    fixed_wing = 0.3 * (max_speed_ms**2) / GRAVITY
    manoeuvre = max(multirotor, fixed_wing)
    value = altitude_m + altitude_error + reaction + manoeuvre
    return Derivation(
        value_m=round(value, 1),
        rule=(
            f"{altitude_m:g} m flight geography + {altitude_error:g} m altitude measurement "
            f"error (the GNSS figure, not the barometric one) + {reaction:.1f} m reaction "
            f"climb + {manoeuvre:.1f} m contingency manoeuvre."
        ),
        inputs={
            "altitude_m": altitude_m,
            "altitude_error_m": altitude_error,
            "vertical_reaction_factor": params.vertical_reaction_factor,
            "reaction_time_s": params.reaction_time_s,
            "max_speed_ms": max_speed_ms,
        },
    )


def ground_risk_buffer(
    contingency_height_m: float, characteristic_dimension_m: float, params: BufferParams
) -> Derivation:
    """S_GRB = H_CV + CD/2 — the 1:1 rule of Annex A A.5.2.4.

    The annex offers three alternatives that are smaller: a ballistic approach for
    rotorcraft, a parachute termination, and a fixed-wing glide. Each needs evidence the
    engine does not hold, so the conservative one is used and the derivation says which.
    """
    if params.grb_method != "one_to_one":
        raise GeoError(
            f"buffers.csv asks for the {params.grb_method!r} ground-risk-buffer method, "
            "which is not implemented. Transcribe the method before using it."
        )
    dimension_term = characteristic_dimension_m * params.grb_dimension_term
    value = contingency_height_m + dimension_term
    return Derivation(
        value_m=round(value, 1),
        rule=(
            f"1:1 rule — the buffer is the contingency volume height plus half the "
            f"characteristic dimension: {contingency_height_m:g} m + {dimension_term:.2f} m. "
            f"Conservative default, not a ballistic, parachute or glide computation."
        ),
        inputs={
            "contingency_height_m": contingency_height_m,
            "characteristic_dimension_m": characteristic_dimension_m,
            "grb_dimension_term": params.grb_dimension_term,
        },
    )


def adjacent_area(max_speed_ms: float, version_dir: str = "sora_2_5") -> Derivation:
    """Step #8's adjacent ground area: 3 minutes at maximum speed, floored and capped.

    S.4.8.3(b)(i): "the distance flown by the UA in 3 minutes at maximum speed", not
    below 5 km and not above 35 km. The seed used a flat 1 km ring, which is under the
    floor for every aircraft.
    """
    rows = {r["key"]: r for r in load_rulebase(version_dir)["thresholds"].rows}

    def metres(key: str) -> float:
        return float(rows[key]["value"]) / 100.0

    seconds = float(rows["adjacent_area_seconds"]["value"])
    low, high = metres("adjacent_area_min"), metres("adjacent_area_max")
    flown = max_speed_ms * seconds
    value = min(max(flown, low), high)
    if value == low:
        why = f"{flown:.0f} m is below the {low / 1000:g} km floor"
    elif value == high:
        why = f"{flown:.0f} m is above the {high / 1000:g} km cap"
    else:
        why = "between the 5 km floor and the 35 km cap"
    return Derivation(
        value_m=round(value, 1),
        rule=(
            f"{seconds / 60:g} minutes at {max_speed_ms:g} m/s is {flown:.0f} m — {why}, "
            f"so the adjacent ground area reaches {value / 1000:g} km beyond the "
            f"operational volume."
        ),
        inputs={"max_speed_ms": max_speed_ms, "seconds": seconds, "min_m": low, "max_m": high},
    )


def derive(
    flight_geography: GeoJSONPolygon,
    *,
    max_altitude_agl_m: float,
    max_speed_ms: float,
    characteristic_dimension_m: float = 0.0,
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
    height = contingency_height(max_altitude_agl_m, max_speed_ms, params)
    grb = ground_risk_buffer(height.value_m, characteristic_dimension_m, params)
    adj = adjacent_area(max_speed_ms, version_dir)

    cv = fg.buffer(lateral.value_m, quad_segs=24, join_style=2)
    buffer_ring = cv.buffer(grb.value_m, quad_segs=24, join_style=2)
    adjacent = buffer_ring.buffer(adj.value_m, quad_segs=24, join_style=2)

    km2 = 1_000_000.0
    return DerivedVolumes(
        contingency_lateral_m=lateral.value_m,
        contingency_vertical_m=round(height.value_m - max_altitude_agl_m, 1),
        ground_risk_buffer_m=grb.value_m,
        adjacent_area_m=adj.value_m,
        flight_geography_km2=round(fg.area / km2, 4),
        contingency_volume_km2=round(cv.area / km2, 4),
        ground_risk_buffer_km2=round(buffer_ring.area / km2, 4),
        adjacent_area_km2=round(adjacent.area / km2, 4),
        contingency_volume=_to_geojson(cv, rev),
        ground_risk_buffer=_to_geojson(buffer_ring, rev),
        adjacent_area=_to_geojson(adjacent, rev),
        derivations=[lateral, height, grb, adj],
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
