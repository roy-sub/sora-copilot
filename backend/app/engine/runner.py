"""Facts in, Determination out.

Loads the rulebase, grounds the mission facts, solves with ``--models=1``, and hands the
single answer set to the trace formatter.

Three failure modes are deliberately loud rather than forgiving:

* **No model.** An unsatisfiable program means an integrity constraint fired — an invalid
  mitigation claim, a conclusion without a justification, a mission the ARC tree does not
  cover. The runner re-solves against a diagnostic program to say which, because
  "unsatisfiable" is not an answer an operator can act on.
* **More than one model.** That is a rulebase bug, not a runtime ambiguity. Asserted on.
* **A rule with no citation.** Refused by the trace formatter.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from uuid import UUID, uuid4

import clingo

from app.domain import ARC, SAIL, ContainmentRequirement, Determination, Mission, OsoRequirement
from app.domain.common import Robustness
from app.engine import facts as facts_module
from app.engine.rulebase import generate
from app.engine.rulebase.loader import RULEBASE_ROOT, load_rulebase, rulebase_version
from app.engine.trace import Because, build, citation_for

#: Load order matters: core declares the contract, then the steps, then the overrides.
PROGRAM_ORDER = (
    "00_core.lp",
    "10_igrc.lp",
    "20_mitigations.lp",
    "30_arc.lp",
    "40_sail.lp",
    "50_oso.lp",
    "60_containment.lp",
    "70_sts_pdra.lp",
    "90_national_at.lp",
    "90_national_de.lp",
)


class EngineError(RuntimeError):
    """The determination could not be computed. No partial result is ever returned."""


class UnsatisfiableMission(EngineError):
    """The mission violates a rulebase constraint. ``reasons`` says which."""

    def __init__(self, reasons: list[str]) -> None:
        super().__init__("; ".join(reasons) if reasons else "the mission is not satisfiable")
        self.reasons = reasons


@dataclass(frozen=True, slots=True)
class EngineResult:
    """What the solver concluded, before it is shaped into a Determination."""

    igrc: int | None
    grc: int | None
    initial_arc: str | None
    residual_arc: str | None
    sail: str | None
    certified: bool
    tmpr: str
    osos: list[tuple[str, str]]
    containment: tuple[str, bool] | None
    out_of_scope: list[str]
    tainted: list[str]
    becauses: list[Because]
    rulebase_version: str


@lru_cache
def _program(version_dir: str = "sora_2_5") -> str:
    """The rulebase as one program: generated facts first, then the rules."""
    generate.ensure(version_dir)
    root = RULEBASE_ROOT / version_dir
    parts = [generate.generated_path(version_dir).read_text(encoding="utf-8")]
    for name in PROGRAM_ORDER:
        path = root / name
        if not path.is_file():
            raise EngineError(f"rulebase file missing: {path}")
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _symbol_str(symbol: clingo.Symbol) -> str:
    return str(symbol)


def _parse_because(symbol: clingo.Symbol) -> Because:
    conclusion, rule_id, premises = symbol.arguments
    if premises.type == clingo.SymbolType.Function and premises.name == "":
        premise_strs = tuple(str(p) for p in premises.arguments)
    else:
        premise_strs = (str(premises),)
    return Because(
        conclusion=str(conclusion),
        rule_id=rule_id.string if rule_id.type == clingo.SymbolType.String else str(rule_id),
        premises=premise_strs,
    )


def solve(fact_text: str, *, version_dir: str = "sora_2_5") -> EngineResult:
    """Run the rulebase over one mission's facts. Exactly one answer set, or it raises."""
    ctl = clingo.Control(["--models=2", "--warn=none"])
    ctl.add("base", [], _program(version_dir))
    ctl.add("mission", [], fact_text)
    ctl.ground([("base", []), ("mission", [])])

    models: list[list[clingo.Symbol]] = []
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            models.append(model.symbols(shown=True))
            if len(models) > 1:
                break

    if not models:
        raise UnsatisfiableMission(_diagnose(fact_text, version_dir))
    if len(models) > 1:
        raise EngineError(
            "the rulebase produced more than one answer set for this mission. That is a "
            "rulebase bug: a determination must be deterministic."
        )

    return _collect(models[0], version_dir)


def _collect(symbols: list[clingo.Symbol], version_dir: str) -> EngineResult:
    igrc = grc = None
    initial_arc = residual_arc = sail = None
    certified = False
    tmpr = "none"
    osos: list[tuple[str, str]] = []
    containment: tuple[str, bool] | None = None
    out_of_scope: list[str] = []
    tainted: list[str] = []
    becauses: list[Because] = []
    version = rulebase_version(version_dir)

    for s in symbols:
        name = s.name
        args = s.arguments
        if name == "because":
            becauses.append(_parse_because(s))
        elif name == "igrc":
            igrc = args[0].number
        elif name == "grc":
            grc = args[0].number
        elif name == "arc_initial":
            initial_arc = str(args[0])
        elif name == "arc_residual":
            residual_arc = str(args[0])
        elif name == "sail":
            sail = args[0].string
        elif name == "tmpr":
            tmpr = str(args[0])
        elif name == "oso_required":
            osos.append((args[0].string, str(args[1])))
        elif name == "containment":
            containment = (str(args[0]), str(args[1]) == "true")
        elif name == "out_of_scope":
            out_of_scope.append(str(args[0]))
        elif name == "tainted":
            tainted.append(str(args[0]))
        elif name == "rulebase_version":
            version = args[0].string

    certified = bool(out_of_scope) or sail is None
    return EngineResult(
        igrc=igrc,
        grc=grc,
        initial_arc=initial_arc,
        residual_arc=residual_arc,
        sail=sail,
        certified=certified,
        tmpr=tmpr,
        osos=sorted(osos),
        containment=containment,
        out_of_scope=sorted(out_of_scope),
        tainted=sorted(tainted),
        becauses=becauses,
        rulebase_version=version,
    )


#: Each integrity constraint, restated as a query so an unsatisfiable mission can be
#: explained instead of merely refused.
DIAGNOSTICS: tuple[tuple[str, str, str], ...] = (
    (
        "invalid_claim",
        "invalid_claim(K, R)",
        "{0} cannot be claimed at {1} robustness — the table does not offer that level",
    ),
    (
        "unmet_precondition",
        "unmet_precondition(K, R, P)",
        "{0} at {1} robustness requires {2}, which this aircraft does not have fitted",
    ),
    (
        "arc_no_match",
        "arc_gap",
        "no row of the ARC decision table matches this mission — the table has a gap",
    ),
    (
        "unjustified",
        "unjustified(X)",
        "the rulebase concluded {0} without a justification, which is a rulebase bug",
    ),
    (
        "pdra_unknown",
        "pdra_unknown(P)",
        "{0} is not a shortcut this rulebase knows",
    ),
)

#: A copy of the program with the constraints replaced by reportable atoms, so the
#: diagnostic solve succeeds and can be read.
_DIAGNOSTIC_SUFFIX = """
%% Diagnostic overlay: restates each integrity constraint as a reportable atom.
unjustified(X) :- conclusion_atom(X), not justified(X).
arc_gap :- not arc_row_matches(_).
pdra_unknown(P) :- pdra_declared(P), not pdra_known(P).
#show invalid_claim/2.
#show unmet_precondition/3.
#show unjustified/1.
#show arc_gap/0.
#show pdra_unknown/1.
"""


def _diagnose(fact_text: str, version_dir: str) -> list[str]:
    """Why the mission was unsatisfiable, in the operator's words."""
    program = _program(version_dir)
    # Strip the constraints so the diagnostic program has a model to report from.
    stripped = "\n".join(line for line in program.splitlines() if not line.strip().startswith(":-"))
    ctl = clingo.Control(["--models=1", "--warn=none"])
    try:
        ctl.add("base", [], stripped + _DIAGNOSTIC_SUFFIX)
        ctl.add("mission", [], fact_text)
        ctl.ground([("base", []), ("mission", [])])
    except RuntimeError as exc:  # a malformed overlay should not mask the real failure
        return [f"the mission is not satisfiable, and the diagnostic pass failed: {exc}"]

    found: list[str] = []
    with ctl.solve(yield_=True) as handle:
        for model in handle:
            for s in model.symbols(shown=True):
                args = [a.string if a.type == clingo.SymbolType.String else str(a) for a in s.arguments]
                for name, _, template in DIAGNOSTICS:
                    if s.name == name:
                        pretty = [
                            facts_module.MITIGATION_NAMES.get(a, a)
                            if hasattr(facts_module, "MITIGATION_NAMES")
                            else a
                            for a in args
                        ]
                        found.append(template.format(*(pretty or ["?"] * 3)))
            break
    if not found:
        found.append(
            "the mission is not satisfiable and no single constraint explains it; this is "
            "a rulebase bug rather than an input error"
        )
    return sorted(set(found))


# ------------------------------------------------------------------ the public entry


def mission_hash(mission: Mission, rulebase: str) -> str:
    """Canonical hash of the confirmed mission plus the rulebase, for idempotency."""
    payload = json.dumps(
        {"mission": mission.model_dump(mode="json"), "rulebase": rulebase},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def determine(
    mission: Mission,
    *,
    drone_max_dimension_m: float,
    drone_mtom_kg: float,
    drone_max_speed_ms: float,
    drone_fitted: list[str] | None = None,
    adjacent_area_populated: bool = False,
    version_dir: str = "sora_2_5",
    determination_id: UUID | None = None,
) -> Determination:
    """The whole chain: facts → clingo → trace → a Determination with a pinned rulebase."""
    fact_text = facts_module.render(
        mission,
        drone_max_dimension_m=drone_max_dimension_m,
        drone_mtom_kg=drone_mtom_kg,
        drone_max_speed_ms=drone_max_speed_ms,
        drone_fitted=drone_fitted,
        adjacent_area_populated=adjacent_area_populated,
    )
    result = solve(fact_text, version_dir=version_dir)
    trace = build(result.becauses, version_dir)

    titles = _oso_titles(version_dir)
    osos = [
        OsoRequirement(
            oso_id=oso_id,
            title=titles.get(oso_id, oso_id),
            required_robustness=Robustness(level),
            citation=citation_for("sora25.oso.assignment", version_dir),
        )
        for oso_id, level in result.osos
    ]

    if result.containment is not None:
        level, required = result.containment
        containment = ContainmentRequirement(
            level=None if level == "none" else level,
            assessment_required=required,
            note=(
                "Containment robustness depends on the adjacent area. The containment "
                "table has not been verified against the official text, so no level is "
                "asserted."
                if required
                else ""
            ),
            citation=citation_for("sora25.containment.assessment_required", version_dir),
        )
    else:
        containment = ContainmentRequirement(
            assessment_required=False,
            note="Not applicable: the operation is outside SORA.",
        )

    sail_value: SAIL | str = SAIL(result.sail) if result.sail is not None else "certified_category"

    warnings = _warnings(result, version_dir)

    return Determination(
        id=determination_id or uuid4(),
        operation_id=mission.id,
        rulebase_version=result.rulebase_version,
        mission_hash=mission_hash(mission, result.rulebase_version),
        # None, not 0: an operation outside SORA has no iGRC and no GRC.
        igrc=result.igrc,
        final_grc=result.grc,
        initial_arc=ARC(result.initial_arc) if result.initial_arc else ARC.D,
        residual_arc=ARC(result.residual_arc) if result.residual_arc else ARC.D,
        sail=sail_value,
        osos=osos,
        containment=containment,
        tmpr=result.tmpr,
        trace=trace.nodes,
        warnings=warnings,
        computed_at=datetime.now(UTC),
    )


@lru_cache
def _oso_titles(version_dir: str = "sora_2_5") -> dict[str, str]:
    return {r["oso_id"]: r["title"] for r in load_rulebase(version_dir)["oso"].rows}


def _warnings(result: EngineResult, version_dir: str) -> list[str]:
    """Every UNVERIFIED table that fed this determination, plus any scope note.

    These are shown, not logged. A determination built on a seed table says so on the
    screen the operator reads and in every page of the export.
    """
    tables = load_rulebase(version_dir)
    out: list[str] = []
    for name in sorted(tables):
        table = tables[name]
        if table.verified:
            continue
        if name in ("cf_costs",):  # ranks suggestions only; never touches a determination
            continue
        warning = table.warning()
        if warning:
            out.append(warning)
    for reason in result.out_of_scope:
        out.append(f"Outside SORA: {reason.replace('_', ' ')}.")
    return out


def rulebase_files(version_dir: str = "sora_2_5") -> list[Path]:
    """Every file that makes up the rulebase, for the dossier's provenance appendix."""
    root = RULEBASE_ROOT / version_dir
    return [generate.generated_path(version_dir), *(root / n for n in PROGRAM_ORDER)]
