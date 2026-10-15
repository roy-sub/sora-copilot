"""Deterministic fact extraction from the operator's prose.

This is the fallback when no language-model key is configured, and it is also the
reference for what extraction is *allowed* to produce: candidate facts for a fixed set of
fields, each with the span of the operator's own words it came from. It concludes nothing.

It lives outside ``llm.py`` because it is not a language model, and outside ``engine/``
because it is not a rule. It reaches no network and no database, so it is safe to run on
the request path.

Keeping both extractors behind one return type means swapping between them changes which
facts are *proposed*, never what the engine does with them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.common import AirspaceClass, GroundEnvironment, OperationType
from app.domain.fields import label

#: Anything proposed carries a confidence. These are deliberately modest: a regex match
#: on a number is good evidence for the number and weak evidence for what it means.
HIGH = 0.9
MEDIUM = 0.7
LOW = 0.55


@dataclass(frozen=True, slots=True)
class Candidate:
    """One proposed fact. Inert until the operator confirms it."""

    field: str
    value: object
    confidence: float
    source_span: str


def _span(text: str, match: re.Match[str], pad: int = 28) -> str:
    start = max(0, match.start() - pad)
    end = min(len(text), match.end() + pad)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


# ------------------------------------------------------------------ altitude

#: Metres, feet, or a bare number next to an altitude word. "below 120 metres",
#: "at 400 ft", "120 m AGL", "max altitude 90".
_ALT_PATTERNS = (
    re.compile(r"(\d{2,4})\s*(?:m|metre|meter|meters|metres)\b(?:\s*agl)?", re.I),
    re.compile(r"(\d{2,4})\s*(?:ft|feet|foot)\b(?:\s*agl)?", re.I),
)
_FEET_TO_M = 0.3048


def _altitude(text: str) -> Candidate | None:
    for pattern in _ALT_PATTERNS:
        for match in pattern.finditer(text):
            value = float(match.group(1))
            is_feet = bool(re.match(r"ft|feet|foot", match.group(0)[len(match.group(1)) :].strip(), re.I))
            metres = round(value * _FEET_TO_M, 1) if is_feet else value
            # A plausible AGL ceiling. Anything above this is probably a distance or a
            # flight level, not an altitude the operator means to fly at.
            if not 1 <= metres <= 1000:
                continue
            return Candidate("volume.max_altitude_agl_m", metres, HIGH, _span(text, match))
    return None


# ------------------------------------------------------------------ operation type

_OP_WORDS: tuple[tuple[re.Pattern[str], OperationType], ...] = (
    (re.compile(r"\bbvlos\b|beyond visual line of sight", re.I), OperationType.BVLOS),
    (re.compile(r"\bevlos\b|extended visual line of sight", re.I), OperationType.EVLOS),
    (re.compile(r"\bvlos\b|visual line of sight", re.I), OperationType.VLOS),
)


def _operation_type(text: str) -> Candidate | None:
    for pattern, value in _OP_WORDS:
        match = pattern.search(text)
        if match:
            return Candidate("operation_type", value.value, HIGH, _span(text, match))
    return None


# ------------------------------------------------------------------ ground environment

#: Ordered: the first match wins, and the strongest signals come first. A crowd beats
#: farmland, because the consequence of missing a crowd is the whole point of SORA.
_ASSEMBLY = r"\bcrowd|assembly|festival|stadium|concert|gathering|spectators\b"
_CONTROLLED_GROUND = r"\bfenced|closed site|restricted site|compound|our own site|cordoned\b"
_POPULATED = r"\btown|city|residential|housing|built-?up|urban|village centre|industrial estate\b"
_SPARSE = r"\bfarmland|fields|scattered houses|rural|open country|forest|meadow|pasture|sparsely\b"

_GROUND_WORDS: tuple[tuple[re.Pattern[str], GroundEnvironment, float], ...] = (
    (re.compile(_ASSEMBLY, re.I), GroundEnvironment.ASSEMBLY, MEDIUM),
    (re.compile(_CONTROLLED_GROUND, re.I), GroundEnvironment.CONTROLLED, MEDIUM),
    (re.compile(_POPULATED, re.I), GroundEnvironment.POPULATED, MEDIUM),
    (re.compile(_SPARSE, re.I), GroundEnvironment.SPARSELY_POPULATED, MEDIUM),
)


def _ground(text: str) -> Candidate | None:
    for pattern, value, confidence in _GROUND_WORDS:
        match = pattern.search(text)
        if match:
            return Candidate("ground_environment", value.value, confidence, _span(text, match))
    return None


# ------------------------------------------------------------------ airspace

_CLASS_RE = re.compile(r"\bclass\s*([a-g])\b", re.I)
_CONTROLLED_RE = re.compile(r"\bcontrolled airspace|\bCTR\b|\bTMA\b", re.I)
_AERODROME_RE = re.compile(
    r"\baerodrome|airport|airfield|\bLOW[A-Z]\b|\bED[A-Z]{2}\b|runway|approach path", re.I
)
_ATYPICAL_RE = re.compile(r"\batypical|segregated|reserved area|\bEDR\b|danger area", re.I)


def _airspace(text: str) -> list[Candidate]:
    out: list[Candidate] = []
    if match := _CLASS_RE.search(text):
        letter = match.group(1).lower()
        out.append(Candidate("airspace_class", AirspaceClass(letter).value, HIGH, _span(text, match)))
    if match := _CONTROLLED_RE.search(text):
        out.append(Candidate("controlled_airspace", True, MEDIUM, _span(text, match)))
    if match := _AERODROME_RE.search(text):
        # Proximity to an aerodrome is not the same as being inside its environment,
        # which the national annex defines — so this is low confidence on purpose.
        out.append(Candidate("near_aerodrome", True, LOW, _span(text, match)))
    if match := _ATYPICAL_RE.search(text):
        out.append(Candidate("atypical_airspace", True, LOW, _span(text, match)))
    return out


# ------------------------------------------------------------------ density

_DENSITY_RE = re.compile(r"(\d[\d,.]*)\s*(?:people|ppl|persons|inhabitants)\s*(?:per|/)\s*km", re.I)


def _density(text: str) -> Candidate | None:
    match = _DENSITY_RE.search(text)
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    return Candidate("population_density_per_km2", value, HIGH, _span(text, match))


# ------------------------------------------------------------------ mitigations

_PARACHUTE = r"\bparachute|recovery system|\bFTS\b"
_SHELTERING = r"\bsheltering|under cover|indoors|people are sheltered"
_OBSERVER = r"\bground observer|visual observer|\bVO\b|spotter"
_RESTRICTION = r"\bNOTAM|daylight only|corridor confined|operational restriction"

_MITIGATION_WORDS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(_PARACHUTE, re.I), "mitigations.m2_impact", "medium"),
    (re.compile(_SHELTERING, re.I), "mitigations.m1_strategic", "low"),
    (re.compile(_OBSERVER, re.I), "mitigations.m1_ers", "low"),
    (re.compile(_RESTRICTION, re.I), "mitigations.strategic_air", "low"),
)


def _mitigations(text: str) -> list[Candidate]:
    out: list[Candidate] = []
    for pattern, field, level in _MITIGATION_WORDS:
        match = pattern.search(text)
        if match:
            # Low confidence throughout: the words show intent, not that the robustness
            # can be evidenced, and robustness is what changes the GRC.
            out.append(Candidate(field, level, LOW, _span(text, match)))
    return out


# ------------------------------------------------------------------ aircraft

def _aircraft(text: str, fleet: list[dict[str, object]]) -> Candidate | None:
    """Match a model or registration against the operator's own fleet.

    Only the fleet: proposing an aircraft the operator does not own would be inventing
    equipment, and the dimensions of that invention would pick the iGRC column.
    """
    for drone in fleet:
        for key in ("registration", "name"):
            raw = drone.get(key)
            if not isinstance(raw, str) or len(raw) < 3:
                continue
            match = re.search(re.escape(raw), text, re.I)
            if match:
                return Candidate("drone_id", str(drone["id"]), HIGH, _span(text, match))
    # A model name without the registration, e.g. "Alta X" for "Freefly Alta X".
    for drone in fleet:
        name = drone.get("name")
        if not isinstance(name, str):
            continue
        for word in [w for w in name.split() if len(w) > 3]:
            match = re.search(rf"\b{re.escape(word)}\b", text, re.I)
            if match:
                return Candidate("drone_id", str(drone["id"]), MEDIUM, _span(text, match))
    return None


# ------------------------------------------------------------------ the entry point


def extract(text: str, fleet: list[dict[str, object]] | None = None) -> list[Candidate]:
    """Candidate facts from prose. Never a conclusion, never a risk value."""
    fleet = fleet or []
    out: list[Candidate] = []
    for candidate in (
        _aircraft(text, fleet),
        _operation_type(text),
        _altitude(text),
        _ground(text),
        _density(text),
    ):
        if candidate is not None:
            out.append(candidate)
    out.extend(_airspace(text))
    out.extend(_mitigations(text))

    # One proposal per field: a second match for the same field is not more information,
    # it is an ambiguity the operator should not have to adjudicate twice.
    seen: set[str] = set()
    unique: list[Candidate] = []
    for candidate in out:
        if candidate.field in seen:
            continue
        seen.add(candidate.field)
        unique.append(candidate)
    return unique


def summarise(candidates: list[Candidate]) -> str:
    """Prose describing what was extracted. States the boundary explicitly."""
    if not candidates:
        return (
            "Nothing in that reached a fact the wizard holds. Try naming the aircraft, "
            "the altitude, what is underneath, and the airspace."
        )
    names = [label(c.field) for c in candidates]
    listed = names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" and {names[-1]}"
    return (
        f"Picked out {listed}. Nothing here has reached the engine — confirm each one, or "
        "correct it, and the determination runs on what you confirmed."
    )
