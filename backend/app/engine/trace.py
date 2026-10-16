"""clingo answer set → the justification trace.

Reads ``because/3`` atoms and nothing else. A conclusion without one cannot reach this
module: ``00_core.lp`` carries an integrity constraint that makes such a model
unsatisfiable.

Citations come from ``tables/citations.csv``. A rule id that is missing from that table
is **refused** rather than rendered without a citation, because a node without a citation
is the one thing the product promises never to show.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.domain import ALTITUDE_BAND_LABELS, Citation, Trace, TraceNode
from app.engine.rulebase.loader import load_rulebase

ROOT_CANDIDATES = ("sail", "certified_category")


class TraceError(RuntimeError):
    """The trace cannot be built. Always fatal: a partial trace is not a trace."""


@dataclass(frozen=True, slots=True)
class Because:
    """One ``because/3`` atom, already split into conclusion, rule and premises."""

    conclusion: str
    rule_id: str
    premises: tuple[str, ...]


@lru_cache
def _citations(version_dir: str = "sora_2_5") -> dict[str, Citation]:
    table = load_rulebase(version_dir)["citations"]
    out: dict[str, Citation] = {}
    for row in table.rows:
        page = row.get("page", "")
        out[row["rule_id"]] = Citation(
            document=row["document"],
            section=row["section"],
            page=int(page) if page.isdigit() else None,
            url=row.get("url") or None,
            verified=row.get("verified") == "true",
        )
    return out


def citation_for(rule_id: str, version_dir: str = "sora_2_5") -> Citation:
    try:
        return _citations(version_dir)[rule_id]
    except KeyError as exc:
        raise TraceError(
            f"rule id {rule_id!r} is not in tables/citations.csv. Every rule the engine "
            "can fire must map to a citation, or a trace node would render without one."
        ) from exc


#: How each conclusion predicate reads in a trace, and which SORA step it belongs to.
CONCLUSION_LABELS: dict[str, tuple[str, str]] = {
    "igrc": ("iGRC", "Step 2 — intrinsic ground risk"),
    "igrc_column_used": ("iGRC column", "Step 2 — intrinsic ground risk"),
    "ground_band": ("Population density band", "Step 2 — intrinsic ground risk"),
    "grc": ("GRC", "Step 3 — final ground risk"),
    "grc_mitigation_applied": ("Ground mitigation", "Step 3 — final ground risk"),
    "alt_band": ("Altitude band", "Step 4 — air risk"),
    "environment": ("Operational environment", "Step 4 — air risk"),
    "arc_initial": ("ARC", "Step 4 — air risk"),
    "arc_rule_fired": ("ARC rule", "Step 4 — air risk"),
    "arc_residual": ("Residual ARC", "Step 5 — strategic air risk mitigation"),
    "tmpr": ("TMPR", "Step 6 — tactical air risk mitigation"),
    "sail": ("SAIL", "Step 7 — SAIL"),
    "certified_category": ("Certified category", "Step 7 — SAIL"),
    "oso_required": ("OSO", "Step 8 — operational safety objectives"),
    "containment": ("Containment", "Step 9 — containment"),
    "out_of_scope": ("Outside SORA", "Scope"),
    "national_baseline": ("National annex", "National"),
}


def _predicate(atom: str) -> str:
    return atom.split("(", 1)[0] if "(" in atom else atom


def _args(atom: str) -> list[str]:
    if "(" not in atom:
        return []
    inner = atom[atom.index("(") + 1 : atom.rindex(")")]
    out: list[str] = []
    depth = 0
    current = ""
    in_string = False
    for ch in inner:
        if ch == '"':
            in_string = not in_string
        if not in_string:
            if ch in "([":
                depth += 1
            elif ch in ")]":
                depth -= 1
            elif ch == "," and depth == 0:
                out.append(current.strip())
                current = ""
                continue
        current += ch
    if current.strip():
        out.append(current.strip())
    return out


def _unquote(term: str) -> str:
    if len(term) >= 2 and term[0] == '"' and term[-1] == '"':
        return term[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return term


def readable(atom: str) -> str:
    """One conclusion, in the operator's words rather than the solver's."""
    pred = _predicate(atom)
    args = [_unquote(a) for a in _args(atom)]

    if pred == "certified_category":
        return "Certified category — the operation is outside SORA"
    if pred == "out_of_scope":
        reason = {
            "dimension_or_speed": "the aircraft is beyond the last iGRC column",
            "density_for_this_aircraft": "this aircraft over this population density is not part of SORA",
        }.get(args[0] if args else "", args[0] if args else "")
        return f"Outside SORA — {reason}"
    if pred == "oso_required":
        oso, level = args[0], args[1]
        return f"{oso} not required" if level == "none" else f"{oso} at {level} robustness"
    if pred == "containment":
        level, required = args[0], args[1]
        if level == "none":
            return "Containment — assessment required" if required == "true" else "Containment — none"
        return f"Containment — {level}"
    if pred == "grc_mitigation_applied":
        kind, rob, delta = args[0], args[1], args[2]
        return f"{MITIGATION_NAMES.get(kind, kind)} at {rob} robustness: GRC {delta}"
    if pred == "national_baseline":
        return f"{args[0].upper()} — EU baseline, no national overrides transcribed"

    label = CONCLUSION_LABELS.get(pred, (pred, ""))[0]
    value = args[0] if args else ""
    if pred in ("arc_initial", "arc_residual"):
        value = value.upper()
    if pred == "ground_band":
        value = DENSITY_BAND_NAMES.get(value, value)
    if pred == "alt_band":
        value = ALTITUDE_BAND_LABELS.get(value, value)
    return f"{label} = {value}" if value else label


MITIGATION_NAMES = {
    "m1_strategic": "M1 sheltering",
    "m1_ers": "M1 ground observation",
    "m2_impact": "M2 impact reduction",
    "strategic_air": "Strategic air risk mitigation",
    "tactical_air": "Tactical air risk mitigation",
}

DENSITY_BAND_NAMES = {
    "controlled_ground_area": "controlled ground area",
    "under_5": "under 5 ppl/km²",
    "under_50": "under 50 ppl/km²",
    "under_500": "under 500 ppl/km²",
    "under_5000": "under 5,000 ppl/km²",
    "under_50000": "under 50,000 ppl/km²",
    "over_50000": "over 50,000 ppl/km²",
}

#: Mission facts, which are leaves rather than derived nodes.
FACT_LABELS = {
    "dim_cm": "Maximum characteristic dimension",
    "speed_cms": "Maximum speed",
    "mtom_g": "Maximum take-off mass",
    "alt_cm": "Maximum altitude",
    "density": "Population density",
    "ground_env": "Ground environment",
    "airspace_class": "Airspace class",
    "operation_type": "Operation type",
    "mitigation": "Mitigation claimed",
    "threshold": "Regulatory threshold",
    "country": "Country",
    "fitted": "Fitted equipment",
    "igrc_col": "iGRC column limits",
    "grc_floor": "GRC floor",
    "total_delta": "Total mitigation delta",
    "adjacent_flag": "Adjacent area populated",
    "flag_value": "Airspace flag",
    "sail_default": "SAIL before overrides",
    "grc_default": "GRC before overrides",
    "arc_residual_default": "Residual ARC before overrides",
    "oso": "OSO",
}


def readable_premise(atom: str) -> str:
    """A premise, in the operator's words. Units are converted back from the solver's."""
    pred = _predicate(atom)
    args = [_unquote(a) for a in _args(atom)]

    if pred in CONCLUSION_LABELS:
        return readable(atom)
    if pred == "dim_cm":
        return f"Maximum characteristic dimension {int(args[0]) / 100:g} m"
    if pred == "speed_cms":
        return f"Maximum speed {int(args[0]) / 100:g} m/s"
    if pred == "mtom_g":
        return f"Maximum take-off mass {int(args[0]) / 1000:g} kg"
    if pred == "alt_cm":
        return f"Maximum altitude {int(args[0]) / 100:g} m AGL"
    if pred == "density":
        return f"Population density {int(args[0]):,} ppl/km²"
    if pred == "ground_env":
        return f"Ground environment: {DENSITY_BAND_NAMES.get(args[0], args[0].replace('_', ' '))}"
    if pred == "airspace_class":
        return f"Airspace class {args[0].upper()}"
    if pred == "operation_type":
        return f"Operation type {args[0].upper()}"
    if pred == "mitigation":
        kind, rob = args[0], args[1]
        name = MITIGATION_NAMES.get(kind, kind)
        return f"{name}: not claimed" if rob == "none" else f"{name} claimed at {rob} robustness"
    if pred == "threshold":
        return f"Threshold {args[0]} = {args[1]}"
    if pred == "igrc_col":
        return f"iGRC column {args[0]} limits: {int(args[1]) / 100:g} m and {int(args[2]) / 100:g} m/s"
    if pred == "fitted":
        return f"Fitted: {args[0]}"
    if pred == "total_delta":
        return f"Total mitigation delta {args[0]}"
    if pred == "grc_floor":
        return f"GRC floor {args[0]} — the controlled-area value for this column"
    if pred == "adjacent_flag":
        return "Adjacent area is populated" if args[0] == "true" else "Adjacent area is not populated"
    if pred == "country":
        return f"Country {args[0].upper()}"
    if pred in ("sail_default", "grc_default", "arc_residual_default"):
        return f"{FACT_LABELS[pred]} {args[0]}"
    if pred == "oso":
        return f"{args[0]} — {args[1]}"
    if pred == "flag_value":
        return f"{args[0].replace('_', ' ').capitalize()}: {args[1]}"

    label = FACT_LABELS.get(pred, pred)
    return f"{label} {' '.join(args)}".strip()


#: Premise predicates that are rulebase TABLE data rather than operator input. A table
#: row is a legitimate premise — "the OSO matrix contains this row" — but it must cite
#: the table it came from, not the operator. Citing it as operator input would be a lie
#: about provenance in the one place the product promises never to lie.
TABLE_PREDICATES: dict[str, str] = {
    "threshold": "thresholds",
    "igrc_col": "igrc_columns",
    "igrc_col_label": "igrc_columns",
    "igrc_cell": "igrc",
    "igrc_band": "igrc",
    "igrc_band_unbounded": "igrc",
    "grc_delta": "m1_m2",
    "mitigation_not_claimable": "m1_m2",
    "grc_floor": "igrc",
    "sail_cell": "sail",
    "oso": "oso",
    "oso_level": "oso",
    "containment_rule": "containment",
    "tmpr_rule": "tmpr",
    "arc_rule": "arc",
    "arc_residual_rule": "arc_residual",
}

#: Premise predicates that are intermediate arithmetic over other premises, not inputs.
COMPUTED_PREDICATES = {
    "total_delta",
    "sail_default",
    "grc_default",
    "arc_residual_default",
    "flag_value",
    "adjacent_flag",
}


@lru_cache
def _table_citations(version_dir: str = "sora_2_5") -> dict[str, Citation]:
    """One citation per table, so a table-row premise cites its own source."""
    tables = load_rulebase(version_dir)
    return {
        name: Citation(
            document=t.document,
            section=t.section,
            page=t.page,
            url=t.url,
            verified=t.verified,
        )
        for name, t in tables.items()
    }


def _premise_citation(atom: str, version_dir: str) -> tuple[Citation, str]:
    """The citation for a premise, and the node kind to record it under."""
    pred = _predicate(atom)
    if table := TABLE_PREDICATES.get(pred):
        return _table_citations(version_dir)[table], "default"
    if pred in COMPUTED_PREDICATES:
        return (
            Citation(
                document="Computed from confirmed facts",
                section="Intermediate value",
                verified=True,
            ),
            "default",
        )
    return (
        Citation(document="Operator input", section="Confirmed mission fact", verified=True),
        "fact",
    )


def _kind(conclusion: str, rule_id: str) -> str:
    pred = _predicate(conclusion)
    if pred == "out_of_scope":
        return "rule"
    if rule_id.startswith(("at.", "de.", "pdra.")):
        return "override"
    if rule_id.endswith(".default"):
        return "default"
    return "rule"


def build(becauses: list[Because], version_dir: str = "sora_2_5") -> Trace:
    """The trace, as a flat node list plus the root id.

    Node ids are the conclusion atoms themselves, so premises point at real nodes and the
    tree can be reconstructed without a second index.
    """
    if not becauses:
        raise TraceError("the answer set carried no because/3 atoms")

    by_conclusion = {b.conclusion: b for b in becauses}
    nodes: list[TraceNode] = []
    fact_ids: dict[str, str] = {}

    for b in becauses:
        premise_ids: list[str] = []
        for premise in b.premises:
            if premise in by_conclusion:
                premise_ids.append(premise)
                continue
            # A premise that is not itself a conclusion is a leaf: either a confirmed
            # mission fact, a row of a transcribed table, or an intermediate value.
            if premise not in fact_ids:
                fact_ids[premise] = premise
                citation, kind = _premise_citation(premise, version_dir)
                nodes.append(
                    TraceNode(
                        id=premise,
                        conclusion=readable_premise(premise),
                        rule_id="fact" if kind == "fact" else f"table.{_predicate(premise)}",
                        citation=citation,
                        premises=[],
                        kind=kind,
                    )
                )
            premise_ids.append(premise)

        nodes.append(
            TraceNode(
                id=b.conclusion,
                conclusion=readable(b.conclusion),
                rule_id=b.rule_id,
                citation=citation_for(b.rule_id, version_dir),
                premises=premise_ids,
                kind=_kind(b.conclusion, b.rule_id),
            )
        )

    root = _root_id(by_conclusion)
    # Leaves first, root last, so a renderer that walks the list draws bottom-up.
    order = {"fact": 0, "default": 1, "rule": 2, "override": 3}
    nodes.sort(key=lambda n: (order.get(n.kind, 2), n.id))
    return Trace(nodes=nodes, root_id=root)


def _root_id(by_conclusion: dict[str, Because]) -> str:
    for candidate in ROOT_CANDIDATES:
        for conclusion in by_conclusion:
            if _predicate(conclusion) == candidate:
                return conclusion
    raise TraceError(
        "the answer set has neither a sail/1 nor a certified_category conclusion, so the trace has no root"
    )
