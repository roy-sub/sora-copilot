"""CSV tables → clingo fact files.

The transcribed CSVs are the source of truth; the ``.lp`` fact files are generated and
must never be hand-edited. This module is inside the engine's purity boundary: stdlib
only, no network, no database.

It refuses to emit anything if a table is malformed, so a broken transcription fails
loudly at generation rather than quietly producing a rulebase with holes in it.
"""

from __future__ import annotations

from pathlib import Path

from app.engine.rulebase.loader import RULEBASE_ROOT, RulebaseError, Table, load_rulebase

GENERATED_DIRNAME = "generated"
GENERATED_FILENAME = "tables.lp"

HEADER = """\
%% GENERATED — do not edit.
%%
%% Produced by app/engine/rulebase/generate.py from the transcribed CSV tables in
%% tables/. Edit the CSV, then run `make rulebase`.
%%
%% Rulebase: {version}
%% Tables:   {count}
%% Verified: {verified} of {count}
"""


def _atom(name: str, *args: object) -> str:
    rendered = ", ".join(_term(a) for a in args)
    return f"{name}({rendered})."


def _term(value: object) -> str:
    if isinstance(value, int):
        return str(value)
    text = str(value)
    # A bare lower-snake-case word is an ASP constant; anything else is a quoted string.
    if text and text[0].islower() and text.replace("_", "").isalnum():
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _int(row: dict[str, str], key: str, table: Table) -> int:
    raw = row.get(key, "")
    try:
        return int(raw)
    except ValueError as exc:
        raise RulebaseError(f"{table.name}.csv: {key}={raw!r} is not an integer") from exc


def _section(title: str, lines: list[str]) -> str:
    return (
        f"\n%% ---------------------------------------------------------------- {title}\n"
        + "\n".join(lines)
        + "\n"
    )


# ------------------------------------------------------------------ per-table emitters


def _thresholds(t: Table) -> list[str]:
    return [_atom("threshold", r["key"], _int(r, "value", t)) for r in t.rows]


def _igrc_columns(t: Table) -> list[str]:
    return [
        _atom("igrc_col", _int(r, "col", t), _int(r, "max_dimension_cm", t), _int(r, "max_speed_cms", t))
        for r in t.rows
    ] + [_atom("igrc_col_label", _int(r, "col", t), r["label"]) for r in t.rows]


def _igrc(t: Table) -> list[str]:
    out: list[str] = []
    for r in t.rows:
        index = _int(r, "band_index", t)
        band = r["density_band"]
        raw_max = r["max_density"]
        if raw_max == "":
            out.append(_atom("igrc_band_unbounded", index, band))
        else:
            out.append(_atom("igrc_band", index, band, int(raw_max)))
        for col in range(1, 6):
            cell = r.get(f"col_{col}", "")
            if cell == "":
                # No fact at all: the absence IS the "outside SORA" signal. Emitting a 0
                # here would be read as iGRC 0, which does not exist.
                continue
            out.append(_atom("igrc_cell", band, col, int(cell)))
    return out


def _m1_m2(t: Table) -> list[str]:
    out: list[str] = []
    for r in t.rows:
        kind, rob = r["kind"], r["robustness"]
        if r["grc_delta"] == "":
            out.append(_atom("mitigation_not_claimable", kind, rob))
            continue
        out.append(_atom("grc_delta", kind, rob, int(r["grc_delta"])))
        if r["precondition"]:
            out.append(_atom("mitigation_precondition", kind, rob, r["precondition"]))
    return out


def _arc(t: Table) -> list[str]:
    out: list[str] = []
    for r in t.rows:
        out.append(
            _atom(
                "arc_rule",
                _int(r, "priority", t),
                r["atypical"] or "*",
                r["altitude_band"] or "*",
                r["controlled_airspace"] or "*",
                r["near_aerodrome"] or "*",
                r["airspace_class"] or "*",
                r["environment"] or "*",
                r["arc"],
                r["rule_id"],
            )
        )
    return out


def _arc_residual(t: Table) -> list[str]:
    return [
        _atom("arc_residual_rule", r["initial_arc"], r["strategic_claimed"], r["residual_arc"], r["rule_id"])
        for r in t.rows
    ]


def _sail(t: Table) -> list[str]:
    out: list[str] = []
    for r in t.rows:
        grc = _int(r, "final_grc", t)
        for arc in ("a", "b", "c", "d"):
            out.append(_atom("sail_cell", grc, arc, r[f"arc_{arc}"]))
    return out


def _oso(t: Table) -> list[str]:
    out: list[str] = []
    sails = ["I", "II", "III", "IV", "V", "VI"]
    for r in t.rows:
        oso = r["oso_id"]
        out.append(_atom("oso", oso, r["title"]))
        for roman in sails:
            out.append(_atom("oso_level", oso, roman, r[f"sail_{roman.lower()}"]))
    return out


def _containment(t: Table) -> list[str]:
    out: list[str] = []
    for r in t.rows:
        out.append(
            _atom(
                "containment_rule",
                r["condition_id"],
                r["min_sail"],
                r["max_sail"],
                r["adjacent_area_populated"] or "*",
                r["level"] or "none",
                r["assessment_required"],
                r["rule_id"],
            )
        )
    return out


def _tmpr(t: Table) -> list[str]:
    return [_atom("tmpr_rule", r["residual_arc"], r["tmpr"], r["rule_id"]) for r in t.rows]


def _citations(t: Table) -> list[str]:
    # Citations are resolved in Python when the trace is built, not by the solver. Only
    # the verified flag is needed in ASP, so a rule can mark its own conclusion.
    return [_atom("citation_verified", r["rule_id"]) for r in t.rows if r.get("verified") == "true"]


#: Tables the solver reads. buffers and cf_costs are consumed by services/geo.py and the
#: counterfactual search in Python, so they are deliberately not emitted here.
EMITTERS = {
    "thresholds": _thresholds,
    "igrc_columns": _igrc_columns,
    "igrc": _igrc,
    "m1_m2": _m1_m2,
    "arc": _arc,
    "arc_residual": _arc_residual,
    "sail": _sail,
    "oso": _oso,
    "containment": _containment,
    "tmpr": _tmpr,
    "citations": _citations,
}


def render(version_dir: str = "sora_2_5") -> str:
    """The whole generated fact file, as text."""
    tables = load_rulebase(version_dir)
    missing = sorted(set(EMITTERS) - set(tables))
    if missing:
        raise RulebaseError(f"tables the solver needs are missing: {', '.join(missing)}")

    version = (RULEBASE_ROOT / version_dir / "VERSION").read_text(encoding="utf-8").strip()
    parts = [
        HEADER.format(
            version=version,
            count=len(tables),
            verified=sum(1 for t in tables.values() if t.verified),
        )
    ]
    # Record which tables are unverified as facts, so a rule can taint its own
    # conclusion and the determination carries the warning.
    parts.append(
        _section(
            "provenance",
            [_atom("rulebase_version", version)]
            + [_atom("table_unverified", name) for name, t in sorted(tables.items()) if not t.verified],
        )
    )
    for name, emit in EMITTERS.items():
        parts.append(_section(name, emit(tables[name])))
    return "".join(parts)


def generated_path(version_dir: str = "sora_2_5") -> Path:
    return RULEBASE_ROOT / version_dir / GENERATED_DIRNAME / GENERATED_FILENAME


def write(version_dir: str = "sora_2_5") -> Path:
    text = render(version_dir)
    path = generated_path(version_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def is_stale(version_dir: str = "sora_2_5") -> bool:
    """True when the generated file is absent or older than any CSV or the VERSION."""
    path = generated_path(version_dir)
    if not path.is_file():
        return True
    newest = max(
        p.stat().st_mtime
        for p in [
            *(RULEBASE_ROOT / version_dir / "tables").glob("*.csv"),
            RULEBASE_ROOT / version_dir / "VERSION",
        ]
    )
    return path.stat().st_mtime < newest


def ensure(version_dir: str = "sora_2_5") -> Path:
    """Regenerate when stale, so `make dev` and the tests work with no build step."""
    if is_stale(version_dir):
        return write(version_dir)
    return generated_path(version_dir)
