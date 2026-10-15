"""`python -m app.engine.cli mission.json` — run the engine with no web, no database.

The engine is the product's credibility, so it has to be runnable and reviewable on its
own. This prints the chain, the trace and every UNVERIFIED warning.

Usage:
    python -m app.engine.cli mission.json
    python -m app.engine.cli mission.json --json
    python -m app.engine.cli mission.json --counterfactuals
    python -m app.engine.cli --example            # print a mission template
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.domain import Mission
from app.engine.counterfactual import Aircraft, suggest
from app.engine.runner import UnsatisfiableMission, determine

EXAMPLE: dict[str, Any] = {
    "mission": {
        "id": "00000000-0000-0000-0000-000000000001",
        "org_id": "00000000-0000-0000-0000-000000000002",
        "drone_id": "00000000-0000-0000-0000-000000000003",
        "operation_type": "bvlos",
        "volume": {
            "flight_geography": {
                "type": "Polygon",
                "coordinates": [
                    [[15.40, 47.10], [15.50, 47.10], [15.50, 47.20], [15.40, 47.20], [15.40, 47.10]]
                ],
            },
            "max_altitude_agl_m": 118,
        },
        "ground_environment": "sparsely_populated",
        "population_density_per_km2": 84,
        "airspace_class": "g",
        "near_aerodrome": True,
        "altitude_band": "below_500ft",
        "controlled_airspace": False,
        "atypical_airspace": False,
        "mitigations": [{"kind": "m1_strategic", "robustness": "low", "evidence_status": "claimed"}],
        "country": "AT",
    },
    "aircraft": {
        "max_dimension_m": 1.32,
        "mtom_kg": 15.9,
        "max_speed_ms": 22,
        "fitted": ["parachute", "fts"],
    },
    "adjacent_area_populated": False,
}


def _load(path: Path) -> tuple[Mission, Aircraft, bool]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if "mission" not in raw:
        raise SystemExit(
            f"{path}: expected an object with a 'mission' key (and 'aircraft'). "
            "Run with --example to print a template."
        )
    mission_raw = dict(raw["mission"])
    mission_raw.setdefault("id", str(uuid4()))
    mission_raw.setdefault("org_id", str(uuid4()))
    mission_raw.setdefault("drone_id", str(uuid4()))
    ac = raw.get("aircraft", {})
    missing = [k for k in ("max_dimension_m", "mtom_kg", "max_speed_ms") if k not in ac]
    if missing:
        raise SystemExit(f"{path}: aircraft is missing {', '.join(missing)}")
    return (
        Mission.model_validate(mission_raw),
        Aircraft(
            max_dimension_m=float(ac["max_dimension_m"]),
            mtom_kg=float(ac["mtom_kg"]),
            max_speed_ms=float(ac["max_speed_ms"]),
            fitted=tuple(ac.get("fitted", [])),
        ),
        bool(raw.get("adjacent_area_populated", False)),
    )


def _print_human(d: Any, mission: Mission, cfs: list[Any]) -> None:
    sail = d.sail if isinstance(d.sail, str) else d.sail.value
    print(f"\nRulebase {d.rulebase_version}   mission {d.mission_hash[:12]}\n")
    print("  CHAIN")
    print(f"    iGRC            {d.igrc}")
    print(f"    final GRC       {d.final_grc}")
    print(f"    ARC             {d.initial_arc.value}")
    print(f"    residual ARC    {d.residual_arc.value}")
    print(f"    SAIL            {sail}")
    print(f"    TMPR            {d.tmpr}")
    required = [o for o in d.osos if o.is_required]
    print(f"    OSOs            {len(required)} required of {len(d.osos)}")
    containment = (
        "assessment required" if d.containment.assessment_required else (d.containment.level or "none")
    )
    print(f"    containment     {containment}")

    print(f"\n  TRACE  ({len(d.trace)} nodes)")
    for node in d.trace:
        cite = f"{node.citation.document} · {node.citation.section}"
        flag = "" if node.citation.verified else "  [UNVERIFIED]"
        print(f"    {node.kind:8} {node.conclusion}")
        print(f"             {node.rule_id}  —  {cite}{flag}")

    if cfs:
        print(f"\n  COUNTERFACTUALS  ({len(cfs)})")
        for c in cfs:
            s = c.resulting_sail if isinstance(c.resulting_sail, str) else c.resulting_sail.value
            print(f"    SAIL {s:4} {c.title}")
            print(f"             {c.chain_effect}")
            print(f"             evidence: {c.evidence_required}")

    if d.warnings:
        print(f"\n  WARNINGS  ({len(d.warnings)})")
        for w in d.warnings:
            print(f"    - {w}")
        print(
            "\n  This determination rests on tables that have NOT been verified against\n"
            "  the official SORA 2.5 text. It must not be submitted to an authority."
        )
    print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m app.engine.cli", description=__doc__)
    ap.add_argument("mission", nargs="?", type=Path, help="JSON file with 'mission' and 'aircraft'")
    ap.add_argument("--json", action="store_true", help="emit the Determination as JSON")
    ap.add_argument("--counterfactuals", action="store_true", help="also search for lower-SAIL changes")
    ap.add_argument("--example", action="store_true", help="print a mission template and exit")
    args = ap.parse_args(argv)

    if args.example:
        print(json.dumps(EXAMPLE, indent=2))
        return 0
    if args.mission is None:
        ap.error("a mission file is required (or use --example)")

    mission, aircraft, adjacent = _load(args.mission)
    try:
        d = determine(
            mission,
            drone_max_dimension_m=aircraft.max_dimension_m,
            drone_mtom_kg=aircraft.mtom_kg,
            drone_max_speed_ms=aircraft.max_speed_ms,
            drone_fitted=list(aircraft.fitted),
            adjacent_area_populated=adjacent,
        )
    except UnsatisfiableMission as exc:
        print("The mission could not be assessed:", file=sys.stderr)
        for reason in exc.reasons:
            print(f"  - {reason}", file=sys.stderr)
        return 2

    cfs = suggest(mission, aircraft, adjacent_area_populated=adjacent) if args.counterfactuals else []

    if args.json:
        print(json.dumps(d.model_dump(mode="json"), indent=2))
    else:
        _print_human(d, mission, cfs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
