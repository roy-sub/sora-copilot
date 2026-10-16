"""The authority-ready dossier, as DOCX or PDF.

Sections, in order: cover, ConOps, operational volume, the SORA assessment tables
(iGRC → GRC → ARC → SAIL), the OSO compliance matrix, the mitigation evidence index, an
ERP skeleton, and the **justification appendix** — the full trace, every node with its
rule and citation.

Three rules this module keeps:

1. **Every risk value comes from the stored determination, verbatim.** Nothing here
   recomputes, rounds or re-derives. The tables are a rendering of the record.
2. **The disclaimer appears in every page header**, not only on the cover, because a
   printed page can be read on its own.
3. **An UNVERIFIED rulebase is stated on the cover and on every page.** A dossier built
   on seed tables must not be able to pass for one that was checked.
4. **The two formats are one document.** The content is described once, against the
   ``Writer`` protocol in ``docwriter.py``, and a backend turns it into `.docx` or
   `.pdf`. A PDF whose SAIL did not match the DOCX's would be the worst bug this product
   could ship, so there is no second code path in which it could happen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from app.domain.common import ALTITUDE_BAND_LABELS, DISCLAIMER, altitude_band_of
from app.national import PackError, load_pack, tailor
from app.services import mapimage
from app.services.docwriter import Writer, writer_for

#: What ``POST /dossier`` will render. Anything else is refused rather than silently
#: producing a DOCX under another extension.
DossierFormat = Literal["docx", "pdf"]
FORMATS: tuple[DossierFormat, ...] = ("docx", "pdf")

def unverified_banner(n: int) -> str:
    """The cover-and-every-page banner, counting the tables rather than condemning all.

    Part of the rulebase is checked against the published SORA 2.5 text and part is not.
    A blanket "none of this has been verified" would be false in the direction that
    teaches a reader to skip the banner, and an authority reading the appendix can see
    for itself which tables are named. The appendix lists them; this counts them.
    """
    tables = "table" if n == 1 else "tables"
    verb = "has" if n == 1 else "have"
    return (
        f"UNVERIFIED RULEBASE — {n} of the regulatory {tables} behind this assessment "
        f"{verb} not been checked against the published JARUS SORA 2.5 text. This "
        f"document must not be submitted to an authority."
    )


#: Kept for callers that want the worst case without a count to hand.
UNVERIFIED_BANNER = unverified_banner(1).replace("1 of the regulatory table has", "a regulatory table has")

ENVIRONMENT_LABELS = {
    "controlled_ground_area": "controlled ground area",
    "sparsely_populated": "sparsely populated",
    "populated": "populated",
    "assembly_of_people": "assembly of people",
}

MITIGATION_LABELS = {
    "m1_strategic": "M1 — sheltering",
    "m1_ers": "M1 — ground observation",
    "m2_impact": "M2 — impact reduction",
    "strategic_air": "Strategic air risk mitigation",
    "tactical_air": "Tactical air risk mitigation",
}


@dataclass(frozen=True, slots=True)
class DossierInput:
    """Everything the document renders. Assembled by the caller; nothing is fetched here."""

    operation: dict[str, Any]
    organisation: dict[str, Any]
    drone: dict[str, Any] | None
    mission: dict[str, Any]
    determination: dict[str, Any]
    evidence: list[dict[str, Any]]
    geo: dict[str, Any] | None
    version: int
    #: Optional LLM-written narrative. Absent when no key is configured, and the document
    #: states that rather than leaving a blank section.
    prose: dict[str, str] | None = None
    #: The derived outlines, for the static chart. Absent when nothing has been drawn.
    outlines: dict[str, Any] | None = None







def _sail_text(determination: dict[str, Any]) -> str:
    sail = determination.get("sail")
    return "Certified category" if sail == "certified_category" else f"SAIL {sail}"


def build(data: DossierInput, fmt: DossierFormat = "docx") -> bytes:
    """Render the dossier. Returns the bytes of a `.docx` or a `.pdf`.

    The content below is format-agnostic by construction: everything goes through
    ``Writer``, so the two documents say the same thing or neither does.
    """
    if fmt not in FORMATS:
        raise ValueError(f"unknown dossier format {fmt!r}")

    d = data.determination
    unverified = bool(d.get("warnings"))
    stamp = (
        f"Rulebase {d.get('rulebase_version')} · determination {str(d.get('id'))[:8]}"
        f" · dossier v{data.version}"
    )
    w = writer_for(
        fmt,
        disclaimer=DISCLAIMER,
        stamp=stamp,
        banner=unverified_banner(len(d.get("warnings") or ())) if unverified else None,
    )

    # ---------------------------------------------------------------- cover
    w.title("Specific Operations Risk Assessment", str(data.operation.get("name", "Operation")))
    w.kv_table(
        [
            ("Operator", str(data.organisation.get("name", "—"))),
            ("Operator registration", str(data.organisation.get("operator_registration") or "—")),
            ("Competent authority", _authority(data.organisation)),
            ("Operation", str(data.operation.get("name", "—"))),
            ("Site", str(data.operation.get("site") or "—")),
            ("Outcome", _sail_text(d)),
            ("Rulebase version", str(d.get("rulebase_version"))),
            ("Computed at", str(d.get("computed_at"))),
            ("Mission hash", str(d.get("mission_hash", ""))[:32]),
            ("Dossier version", str(data.version)),
            ("Generated", datetime.now(UTC).strftime("%d %b %Y %H:%M UTC")),
        ]
    )

    if unverified:
        w.heading("Verification status", 2)
        w.warning(unverified_banner(len(d.get("warnings") or ())))
        for warning in d.get("warnings", []):
            w.bullet(str(warning))

    w.paragraph(DISCLAIMER)

    # ---------------------------------------------------------------- ConOps
    w.page_break()
    w.heading("1. Concept of operations")
    if data.prose and data.prose.get("conops"):
        for block in data.prose["conops"].split("\n\n"):
            if block.strip():
                w.paragraph(block.strip())
        w.note(
            "Narrative generated from the facts and values above. No risk value in it "
            "was produced by a language model."
        )
    else:
        _conops_from_facts(w, data)

    w.heading("1.1 Aircraft", 2)
    drone = data.drone or {}
    w.kv_table(
        [
            ("Model", str(drone.get("name", "—"))),
            ("Registration", str(drone.get("registration") or "—")),
            ("Maximum characteristic dimension", f"{drone.get('max_dimension_m', '—')} m"),
            ("MTOM", f"{drone.get('mtom_kg', '—')} kg"),
            ("Cruise speed", f"{drone.get('cruise_speed_ms', '—')} m/s"),
            ("Maximum speed", f"{drone.get('max_speed_ms', '—')} m/s"),
            (
                "Kinetic energy at maximum speed",
                f"{float(drone.get('kinetic_energy_j') or 0) / 1000:.1f} kJ",
            ),
            ("Fitted mitigations", ", ".join(drone.get("fitted_mitigations") or []) or "none"),
        ]
    )

    # ---------------------------------------------------------------- volume
    w.heading("2. Operational volume")
    volume = data.mission.get("volume") or {}
    rows = [
        ("Maximum altitude", f"{volume.get('max_altitude_agl_m', '—')} m AGL"),
        (
            "Altitude band",
            ALTITUDE_BAND_LABELS[altitude_band_of(float(volume.get("max_altitude_agl_m") or 0))],
        ),
        ("Operation type", str(data.mission.get("operation_type", "—")).upper()),
    ]
    if data.geo:
        rows += [
            ("Flight geography", f"{data.geo.get('flight_geography_km2', '—')} km²"),
            ("Contingency volume", f"{data.geo.get('contingency_volume_km2', '—')} km²"),
            ("Ground risk buffer", f"{data.geo.get('ground_risk_buffer_km2', '—')} km²"),
            ("Adjacent area", f"{data.geo.get('adjacent_area_km2', '—')} km²"),
        ]
    w.kv_table(rows)

    _volume_chart(w, data)

    if data.geo and data.geo.get("derivations"):
        w.heading("2.2 How the volumes were derived", 2)
        for derivation in data.geo["derivations"]:
            w.lead_bullet(f"{derivation.get('value_m')} m — ", str(derivation.get("rule", "")))
        w.note(
            "Derived from the drawn flight geography in an equal-area projection. No "
            "volume in this dossier was entered by hand."
        )
    else:
        w.note("The operational volumes have not been derived for this operation.")

    # ---------------------------------------------------------------- the chain
    w.heading("3. SORA assessment")
    w.kv_table(
        [
            ("Intrinsic ground risk class (iGRC)", _or_dash(d.get("igrc"))),
            ("Final ground risk class (GRC)", _or_dash(d.get("final_grc"))),
            ("Initial air risk class (ARC)", str(d.get("initial_arc", "—")).upper()),
            ("Residual air risk class", str(d.get("residual_arc", "—")).upper()),
            ("SAIL", _sail_text(d)),
            ("TMPR", str(d.get("tmpr", "—"))),
            ("Containment", _containment_text(d)),
        ]
    )

    w.heading("3.1 Ground environment", 2)
    w.kv_table(
        [
            ("Ground environment", _environment(data.mission)),
            (
                "Peak population density",
                f"{data.mission.get('population_density_per_km2', '—')} ppl/km²",
            ),
        ]
    )

    w.heading("3.2 Mitigations claimed", 2)
    claims = data.mission.get("mitigations") or {}
    claimed = [(MITIGATION_LABELS.get(k, k), str(v)) for k, v in claims.items() if v and v != "none"]
    if claimed:
        w.kv_table(claimed)
    else:
        w.paragraph("No mitigations claimed.")

    w.heading("3.3 Airspace", 2)
    w.kv_table(
        [
            ("Airspace class", str(data.mission.get("airspace_class", "—")).upper()),
            ("Controlled airspace", _yes_no(data.mission.get("controlled_airspace"))),
            ("Inside the aerodrome environment", _yes_no(data.mission.get("near_aerodrome"))),
            ("Atypical or segregated airspace", _yes_no(data.mission.get("atypical_airspace"))),
        ]
    )

    # ---------------------------------------------------------------- OSO matrix
    w.page_break()
    w.heading("4. Operational safety objectives")
    osos = d.get("osos") or []
    required = [o for o in osos if o.get("required_robustness") != "none"]
    w.paragraph(
        f"{len(required)} of {len(osos)} objectives apply at {_sail_text(d)}. "
        "Objectives that do not apply are listed so that it is clear they were considered."
    )

    by_oso: dict[str, list[dict[str, Any]]] = {}
    for item in data.evidence:
        by_oso.setdefault(str(item.get("oso_id") or ""), []).append(item)

    oso_rows: list[list[str]] = []
    for oso in osos:
        level = str(oso.get("required_robustness", "none"))
        files = by_oso.get(str(oso.get("oso_id", "")), [])
        oso_rows.append(
            [
                str(oso.get("oso_id", "")),
                str(oso.get("title", "")),
                "not applicable" if level == "none" else level,
                "not applicable" if level == "none" else str(oso.get("status", "unmet")),
                ", ".join(str(f.get("filename")) for f in files) if files else "—",
            ]
        )
    w.table(["OSO", "Objective", "Required", "Status", "Evidence"], oso_rows)
    w.note(
        "Required robustness is assigned by the rulebase from the computed SAIL. Evidence "
        "status reflects what has been attached in SORA Copilot, not an authority's view "
        "of its sufficiency."
    )

    # ---------------------------------------------------------------- evidence index
    w.heading("5. Mitigation and evidence index")
    if data.evidence:
        w.table(
            ["File", "Attached to", "Size", "Uploaded"],
            [
                [
                    str(item.get("filename", "")),
                    str(item.get("oso_id") or "the operation"),
                    f"{int(item['bytes']) / 1024:.0f} kB" if item.get("bytes") else "—",
                    str(item.get("uploaded_at", ""))[:10],
                ]
                for item in data.evidence
            ],
        )
    else:
        w.paragraph("No evidence files have been attached to this operation.")

    # ---------------------------------------------------------------- ERP
    w.heading("6. Emergency response plan")
    if data.prose and data.prose.get("erp"):
        for block in data.prose["erp"].split("\n\n"):
            if block.strip():
                w.paragraph(block.strip())
    else:
        w.paragraph(
            "This section is a skeleton. SORA Copilot does not write an emergency response "
            "plan for you: it depends on the site, the crew and the local services, none of "
            "which the tool knows. The headings below are the ones an authority will expect."
        )
        for heading in (
            "Alerting — who is called, in what order, with what information",
            "Containment of the aircraft after a loss of control",
            "Casualty response and first aid provision on site",
            "Securing the area and preserving evidence",
            "Notification of the competent authority and occurrence reporting",
            "Crew debrief and return to service",
        ):
            w.bullet(heading)

    # ---------------------------------------------------------------- the appendix
    w.page_break()
    w.heading("Appendix A — Justification trace")
    w.paragraph(
        "Every conclusion the rules engine reached, the rule that produced it, and the "
        "clause that rule comes from. The engine cannot produce a conclusion without a "
        "justification: a model in which one is missing is rejected as unsatisfiable."
    )

    trace = d.get("trace") or []
    trace_rows: list[list[str]] = []
    for node in trace:
        citation = node.get("citation") or {}
        suffix = "" if citation.get("verified") else "  [UNVERIFIED]"
        page = f", p. {citation.get('page')}" if citation.get("page") else ""
        trace_rows.append(
            [
                str(node.get("conclusion", "")),
                str(node.get("rule_id", "")),
                f"{citation.get('document', '')} · {citation.get('section', '')}{page}{suffix}",
                ", ".join(node.get("premises") or []) or "—",
            ]
        )
    w.table(["Conclusion", "Rule", "Citation", "From"], trace_rows)
    w.note(f"{len(trace)} nodes. Mission hash {d.get('mission_hash', '')}.")

    w.heading("Appendix B — Rulebase provenance", 1)
    w.paragraph(
        f"This determination was computed against rulebase {d.get('rulebase_version')}. "
        "A determination is pinned to the rulebase version it was computed against, so a "
        "later change to the rulebase does not alter this record."
    )
    if unverified:
        for warning in d.get("warnings", []):
            w.bullet(str(warning))

    _submission_checklist(w, data)

    return w.render()


def _volume_chart(w: Writer, data: DossierInput) -> None:
    """The volumes as a chart, drawn from the same geometry the engine read.

    Not a basemap: a dossier is printed and archived, and a third-party tile would be a
    dead reference in a year. What matters in the document is the relationship between
    the volumes and their scale, which this shows exactly.
    """
    outlines = data.outlines or {}
    flight_geography = (data.mission.get("volume") or {}).get("flight_geography")
    if not flight_geography:
        return
    png = mapimage.render(
        flight_geography=flight_geography,
        contingency_volume=outlines.get("contingency_volume"),
        ground_risk_buffer=outlines.get("ground_risk_buffer"),
        adjacent_area=outlines.get("adjacent_area"),
    )
    if png is None:
        return
    w.heading("2.1 Operational volumes", 2)
    w.image(png, 16.0)
    w.note(
        "Drawn from the submitted flight geography and the volumes derived from it. "
        "North is up; the scale bar matches the grid spacing."
    )


def _conops_from_facts(w: Writer, data: DossierInput) -> None:
    """The ConOps written from the facts, with no language model involved."""
    mission = data.mission
    drone = data.drone or {}
    volume = mission.get("volume") or {}
    environment = ENVIRONMENT_LABELS.get(
        str(mission.get("ground_environment")), str(mission.get("ground_environment", "—"))
    )
    w.paragraph(
        f"{data.organisation.get('name', 'The operator')} will conduct "
        f"{str(mission.get('operation_type', '—')).upper()} operations with a "
        f"{drone.get('name', 'the aircraft')}"
        f"{f' ({drone.get('registration')})' if drone.get('registration') else ''} "
        f"at or below {volume.get('max_altitude_agl_m', '—')} m AGL over a {environment} "
        f"ground environment."
    )
    if mission.get("population_density_per_km2") is not None:
        w.paragraph(
            f"The peak population density recorded across the ground risk buffer is "
            f"{mission.get('population_density_per_km2')} people per square kilometre, "
            "which is the row used for the intrinsic ground risk class."
        )
    w.paragraph(
        f"The operation is planned in class {str(mission.get('airspace_class', '—')).upper()} "
        f"airspace. It is {'inside' if mission.get('near_aerodrome') else 'outside'} an "
        f"aerodrome environment and "
        f"{'in' if mission.get('controlled_airspace') else 'outside'} controlled airspace."
    )
    w.note(
        "Written from the confirmed facts. No language model contributed to this section, "
        "and no language model contributed any risk value anywhere in this document."
    )


def _environment(mission: dict[str, Any]) -> str:
    raw = str(mission.get("ground_environment", "—"))
    return ENVIRONMENT_LABELS.get(raw, raw)


def _or_dash(value: Any) -> str:
    return "—" if value is None else str(value)


def _yes_no(value: Any) -> str:
    return "yes" if value else "no"


def _containment_text(determination: dict[str, Any]) -> str:
    containment = determination.get("containment") or {}
    if containment.get("assessment_required"):
        return "assessment required"
    return str(containment.get("level") or "none")


def _authority(organisation: dict[str, Any]) -> str:
    """Named by the country pack, so the document and the app never disagree."""
    try:
        pack = load_pack(str(organisation.get("country") or "EU"))
    except PackError:
        return "the competent authority of the state of registration"
    return f"{pack.authority} ({pack.country})" if pack.country != "EU" else pack.authority


def _submission_checklist(w: Writer, data: DossierInput) -> None:
    """Appendix C — what travels with this document, in the operator's own country.

    Cut to the SAIL the engine produced and the OSOs it required, so the list is this
    operation's rather than a generic one. Every line carries its verification state:
    this project has transcribed no authority publication yet, so every line currently
    reads UNVERIFIED and says where to check it. A compliance appendix that quietly
    presented our reading as the authority's requirement would be the worst kind of
    plausible.
    """
    country = str(data.organisation.get("country") or "EU")
    d = data.determination
    required = frozenset(
        str(o.get("oso_id")) for o in d.get("osos", []) if isinstance(o, dict) and o.get("is_required")
    )
    try:
        pack = load_pack(country)
        due, pending = tailor(country, sail=d.get("sail"), required_osos=required)
    except PackError:
        return

    w.heading(f"Appendix C — Submission checklist: {pack.country_name}", 1)
    w.paragraph(pack.summary)
    if (warning := pack.warning()) is not None:
        w.note(warning)

    for kind, heading in (
        ("process", "Process"),
        ("form", "The authority's forms"),
        ("attachment", "Attachments to this file"),
        ("note", "Open questions"),
        ("contact", "Where it goes"),
    ):
        rows = [i for i in due if i.kind == kind]
        if not rows:
            continue
        w.heading(heading, 2)
        for item in rows:
            detail = f" — {item.detail}" if item.detail else ""
            flag = (
                f"  [UNVERIFIED: {item.source}]" if not item.verified else f"  [{item.source}]"
            )
            w.lead_bullet(item.title, f"{detail}{flag}")

    if pending:
        w.heading("Not due at this SAIL", 2)
        w.paragraph(
            "Listed because raising the SAIL would add them to the file, so the cost of a "
            "less favourable determination is visible before it is incurred."
        )
        for item in pending:
            at = f" (from SAIL {item.min_sail})" if item.min_sail else ""
            w.bullet(f"{item.title}{at}")

    w.note(
        f"{len(due)} items due · {len(pending)} not due at SAIL {_sail_text(d)} · "
        f"{len(data.evidence)} evidence file(s) already attached in SORA Copilot."
    )
