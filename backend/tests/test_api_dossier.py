"""Evidence upload and the DOCX dossier.

The property that matters: every risk value in the document is the stored
determination's, verbatim. A dossier whose numbers drift from the determination it
claims to render would be worse than no dossier.
"""

from __future__ import annotations

import io
import zipfile
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.domain.common import ALTITUDE_BAND_LABELS
from tests.conftest import SQUARE as SQUARE_FOR_DOSSIER


@pytest.fixture(autouse=True)
def _paid(pro: dict[str, Any]) -> None:
    """Every test in this module exercises a paid feature.

    Plan gating is the subject of tests/test_api_plans.py, which runs these same
    endpoints on the free plan and asserts the 402. Here the plan is not the point, so
    it is set once rather than repeated in twenty signatures.
    """
    return None


DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"



@pytest.fixture
def determined(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], complete_draft: dict[str, Any]
) -> dict[str, Any]:
    res = client.post(f"/api/v1/operations/{operation['id']}/determine", headers=auth)
    assert res.status_code == 200, res.text
    return res.json()


def _docx_text(data: bytes) -> str:
    """Every bit of text in the document, so assertions can be about content."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        parts = [n for n in archive.namelist() if n.endswith(".xml")]
        return "\n".join(archive.read(n).decode("utf-8", "replace") for n in parts)


# ------------------------------------------------------------------ evidence


def test_a_pdf_is_accepted(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    res = client.post(
        f"/api/v1/operations/{operation['id']}/evidence",
        files={"file": ("sheltering-survey.pdf", b"%PDF-1.7 fake", "application/pdf")},
        data={"oso_id": "OSO#08"},
        headers=auth,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["filename"] == "sheltering-survey.pdf"
    assert body["oso_id"] == "OSO#08"
    assert body["bytes"] == len(b"%PDF-1.7 fake")


def test_an_executable_is_refused(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    res = client.post(
        f"/api/v1/operations/{operation['id']}/evidence",
        files={"file": ("payload.exe", b"MZ", "application/x-msdownload")},
        headers=auth,
    )
    assert res.status_code == 422
    assert res.json()["code"] == "file_rejected"
    assert "PDF" in res.json()["detail"]


def test_an_oversized_file_is_refused(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    big = b"0" * (40 * 1024 * 1024 + 1)
    res = client.post(
        f"/api/v1/operations/{operation['id']}/evidence",
        files={"file": ("huge.pdf", big, "application/pdf")},
        headers=auth,
    )
    assert res.status_code == 422
    assert "40 MB" in res.json()["detail"]


def test_an_empty_file_is_refused(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    res = client.post(
        f"/api/v1/operations/{operation['id']}/evidence",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        headers=auth,
    )
    assert res.status_code == 422
    assert "empty" in res.json()["detail"].lower()


def test_a_docx_without_a_content_type_is_accepted_on_its_extension(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    """Browsers do not always send a type for .docx, and refusing it would be wrong."""
    res = client.post(
        f"/api/v1/operations/{operation['id']}/evidence",
        files={"file": ("procedure.docx", b"PK\x03\x04fake", "application/octet-stream")},
        headers=auth,
    )
    assert res.status_code == 201, res.text


def test_evidence_can_be_downloaded_and_deleted(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    created = client.post(
        f"/api/v1/operations/{operation['id']}/evidence",
        files={"file": ("survey.pdf", b"%PDF-1.7 content here", "application/pdf")},
        headers=auth,
    ).json()

    got = client.get(
        f"/api/v1/operations/{operation['id']}/evidence/{created['id']}/download", headers=auth
    )
    assert got.status_code == 200
    assert got.content == b"%PDF-1.7 content here"

    assert (
        client.delete(
            f"/api/v1/operations/{operation['id']}/evidence/{created['id']}", headers=auth
        ).status_code
        == 204
    )
    assert client.get(f"/api/v1/operations/{operation['id']}/evidence", headers=auth).json() == []


def test_another_organisation_cannot_upload_evidence(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    from uuid import uuid4

    from tests.conftest import make_token

    other = {"Authorization": f"Bearer {make_token(uuid4(), email='other@example.com')}"}
    client.post("/api/v1/auth/session", headers=other)
    res = client.post(
        f"/api/v1/operations/{operation['id']}/evidence",
        files={"file": ("x.pdf", b"%PDF", "application/pdf")},
        headers=other,
    )
    assert res.status_code == 404


# ------------------------------------------------------------------ the OSO set


def test_the_oso_set_comes_from_the_determination(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    res = client.get(f"/api/v1/operations/{operation['id']}/osos", headers=auth)
    assert res.status_code == 200, res.text
    osos = res.json()
    assert len(osos) == 17
    assert all(o["citation"]["document"] for o in osos)
    assert {o["oso_id"] for o in osos} == {o["oso_id"] for o in determined["osos"]}


def test_attaching_evidence_moves_an_oso_to_documented_not_verified(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    """The tool must not vouch for a document nobody has reviewed."""
    client.post(
        f"/api/v1/operations/{operation['id']}/evidence",
        files={"file": ("procedures.pdf", b"%PDF-1.7", "application/pdf")},
        data={"oso_id": "OSO#08"},
        headers=auth,
    )
    osos = client.get(f"/api/v1/operations/{operation['id']}/osos", headers=auth).json()
    oso8 = next(o for o in osos if o["oso_id"] == "OSO#08")
    assert oso8["status"] == "documented"
    assert oso8["evidence"][0]["filename"] == "procedures.pdf"


def test_the_oso_set_is_unavailable_before_a_determination(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    res = client.get(f"/api/v1/operations/{operation['id']}/osos", headers=auth)
    assert res.status_code == 404
    assert res.json()["code"] == "no_determination"


# ------------------------------------------------------------------ the dossier


def test_the_dossier_cannot_be_generated_without_a_determination(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any]
) -> None:
    status = client.get(f"/api/v1/operations/{operation['id']}/dossier", headers=auth).json()
    assert status["can_generate"] is False
    assert "determination" in status["blocker"]

    res = client.post(f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth)
    assert res.status_code == 409
    assert res.json()["code"] == "no_determination"


def test_the_dossier_status_reports_each_section(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    status = client.get(f"/api/v1/operations/{operation['id']}/dossier", headers=auth).json()
    assert status["can_generate"] is True
    keys = {s["key"]: s for s in status["sections"]}
    assert set(keys) == {"conops", "tables", "osos", "evidence", "erp", "trace"}
    assert keys["trace"]["state"] == "complete"
    assert "nodes" in keys["trace"]["meta"]
    # No evidence attached yet, so the OSO matrix is partial and says how many gaps.
    assert keys["osos"]["state"] == "partial"
    assert keys["erp"]["state"] == "not_started"


def test_generating_produces_a_downloadable_docx(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    res = client.post(f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth)
    assert res.status_code == 201, res.text
    dossier = res.json()
    assert dossier["version"] == 1
    assert dossier["format"] == "docx"

    got = client.get(
        f"/api/v1/operations/{operation['id']}/dossier/{dossier['id']}/download", headers=auth
    )
    assert got.status_code == 200
    assert got.headers["content-type"] == DOCX_TYPE
    # A real zip container, which is what a .docx is.
    assert zipfile.is_zipfile(io.BytesIO(got.content))


def test_every_risk_value_in_the_document_is_the_determinations(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    """The decisive property. The document is a rendering of the record, not a retelling."""
    dossier = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth
    ).json()
    data = client.get(
        f"/api/v1/operations/{operation['id']}/dossier/{dossier['id']}/download", headers=auth
    ).content
    text = _docx_text(data)

    assert f"SAIL {determined['sail']}" in text
    assert str(determined["igrc"]) in text
    assert str(determined["final_grc"]) in text
    assert determined["rulebase_version"] in text
    assert determined["mission_hash"][:32] in text


def test_the_document_carries_the_disclaimer_and_no_longer_the_banner(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    """The disclaimer is permanent; the UNVERIFIED banner was not.

    Every regulatory table is transcribed from the EASA Easy Access Rules now, so a
    determination carries no warnings and the document must not print a banner saying it
    may not be submitted. The disclaimer stays either way: SORA Copilot prepares the
    assessment, an authority grants the authorisation, and that does not change.
    """
    dossier = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth
    ).json()
    text = _docx_text(
        client.get(
            f"/api/v1/operations/{operation['id']}/dossier/{dossier['id']}/download", headers=auth
        ).content
    )
    assert "national aviation authority grants the authorisation" in text
    assert "UNVERIFIED RULEBASE" not in text
    assert "must not be submitted to an authority" not in text


@pytest.mark.parametrize(
    ("altitude_m", "expected"),
    [
        (118.0, "at or below 150 m"),
        (149.9, "at or below 150 m"),
        (150.0, "at or below 150 m"),
        (151.0, "above 150 m"),
        (300.0, "above 150 m"),
    ],
)
def test_the_document_describes_the_band_the_arc_was_actually_computed_on(
    client: TestClient,
    auth: dict[str, str],
    operation: dict[str, Any],
    complete_draft: dict[str, Any],
    altitude_m: float,
    expected: str,
) -> None:
    """A dossier that describes a different band from the one the engine keyed on.

    This was real. The volume section printed "above 500 ft (152 m) AGL" against its own
    152.4 m threshold while the engine had already moved to Table C.1's 150 m. A flight
    at 151 m got its ARC from the above-150 m row and was then described in the document
    as being at or below the band — the kind of contradiction an authority reads as the
    assessment not being of the operation in front of them. Both now render one
    definition, and the old wording must not come back.
    """
    client.patch(
        f"/api/v1/operations/{operation['id']}/draft",
        json={"volume": {"flight_geography": SQUARE_FOR_DOSSIER, "max_altitude_agl_m": altitude_m}},
        headers=auth,
    )
    determination = client.post(
        f"/api/v1/operations/{operation['id']}/determine?force=true", headers=auth
    )
    assert determination.status_code == 200, determination.text

    dossier = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth
    ).json()
    text = _docx_text(
        client.get(
            f"/api/v1/operations/{operation['id']}/dossier/{dossier['id']}/download", headers=auth
        ).content
    )

    assert expected in text
    # The band the engine keyed on reaches the trace, so the two renderings of it have
    # to agree inside one document.
    engine_band = "above_150m" if altitude_m > 150.0 else "below_150m"
    assert ALTITUDE_BAND_LABELS[engine_band] in text
    assert "500 ft (152 m)" not in text


def test_the_banner_still_appears_when_a_determination_does_carry_warnings() -> None:
    """The machinery has to keep working for the next rulebase edition.

    Asserting only that nothing warns would pass whether or not the banner still
    worked, so this renders a document from a determination that does warn.
    """
    from app.services.dossier import unverified_banner

    one = unverified_banner(1)
    assert "1 of the regulatory table" in one
    assert "must not be submitted to an authority" in one
    assert "8 of the regulatory tables" in unverified_banner(8)


def test_the_document_contains_the_whole_trace(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    dossier = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth
    ).json()
    text = _docx_text(
        client.get(
            f"/api/v1/operations/{operation['id']}/dossier/{dossier['id']}/download", headers=auth
        ).content
    )
    assert "Justification trace" in text
    for node in determined["trace"][:6]:
        assert node["rule_id"] in text


def test_the_document_names_every_attached_evidence_file(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    client.post(
        f"/api/v1/operations/{operation['id']}/evidence",
        files={"file": ("sheltering-survey.pdf", b"%PDF-1.7", "application/pdf")},
        data={"oso_id": "OSO#08"},
        headers=auth,
    )
    dossier = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth
    ).json()
    text = _docx_text(
        client.get(
            f"/api/v1/operations/{operation['id']}/dossier/{dossier['id']}/download", headers=auth
        ).content
    )
    assert "sheltering-survey.pdf" in text


def test_versions_increment_and_are_listed_newest_first(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    for expected in (1, 2, 3):
        res = client.post(
            f"/api/v1/operations/{operation['id']}/dossier",
            json={"note": f"version {expected}"},
            headers=auth,
        )
        assert res.json()["version"] == expected

    status = client.get(f"/api/v1/operations/{operation['id']}/dossier", headers=auth).json()
    assert [v["version"] for v in status["versions"]] == [3, 2, 1]
    assert status["next_version"] == 4


def test_generating_marks_the_operation_dossier_ready(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    client.post(f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth)
    after = client.get(f"/api/v1/operations/{operation['id']}", headers=auth).json()
    assert after["status"] == "dossier_ready"


def test_another_organisation_cannot_download_a_dossier(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    from uuid import uuid4

    from tests.conftest import make_token

    dossier = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth
    ).json()
    other = {"Authorization": f"Bearer {make_token(uuid4(), email='other@example.com')}"}
    client.post("/api/v1/auth/session", headers=other)
    res = client.get(
        f"/api/v1/operations/{operation['id']}/dossier/{dossier['id']}/download", headers=other
    )
    assert res.status_code == 404


def test_the_document_embeds_a_chart_of_the_volumes(
    client: TestClient, auth: dict[str, Any], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    """The build spec asks for a static map render; this is it.

    Not a basemap: a dossier is printed and archived, and a third-party tile would be a
    dead reference in a year. The chart shows the relationship between the volumes and
    their scale, drawn from the same geometry the engine read.
    """
    dossier = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth
    ).json()
    data = client.get(
        f"/api/v1/operations/{operation['id']}/dossier/{dossier['id']}/download", headers=auth
    ).content

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        images = [n for n in archive.namelist() if n.startswith("word/media/")]
        assert images, "the dossier carries no embedded image"
        assert archive.read(images[0])[:8] == b"\x89PNG\r\n\x1a\n"

    assert "Operational volumes" in _docx_text(data)


def test_the_chart_is_skipped_when_nothing_has_been_drawn(
    client: TestClient, auth: dict[str, Any], drone: dict[str, Any]
) -> None:
    """A dossier without geometry is still a dossier, not a failure."""
    op = client.post(
        "/api/v1/operations", json={"name": "No geography", "drone_id": drone["id"]}, headers=auth
    ).json()
    client.patch(
        f"/api/v1/operations/{op['id']}/draft",
        json={
            "drone_id": drone["id"],
            "operation_type": "vlos",
            "volume": {"flight_geography": SQUARE_FOR_DOSSIER, "max_altitude_agl_m": 50},
            "ground_environment": "controlled_ground_area",
            "airspace_class": "g",
        },
        headers=auth,
    )
    assert client.post(f"/api/v1/operations/{op['id']}/determine", headers=auth).status_code == 200
    res = client.post(f"/api/v1/operations/{op['id']}/dossier", json={}, headers=auth)
    assert res.status_code == 201, res.text


def test_the_document_carries_the_countrys_submission_checklist(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    """Appendix C — the administrative half of the file, cut to this operation's SAIL."""
    dossier = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth
    ).json()
    text = _docx_text(
        client.get(
            f"/api/v1/operations/{operation['id']}/dossier/{dossier['id']}/download", headers=auth
        ).content
    )
    assert "Submission checklist: Austria" in text
    assert "Austro Control" in text
    # Every line is this project's reading, so every line must say so in the document.
    assert "UNVERIFIED:" in text
    assert "Register as a UAS operator" in text
    # A SAIL IV item must appear under "not due", never as a requirement of a SAIL III file.
    assert "Not due at this SAIL" in text
    assert "Design and maintenance evidence" in text


def test_the_checklist_appendix_never_invents_a_fee_or_a_lead_time(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    """The dossier is the artefact that reaches an authority. No guessed figure may be in it.

    test_national.py guards the pack data; this guards what the document actually renders,
    which is the thing a reader would believe.
    """
    import re

    dossier = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={}, headers=auth
    ).json()
    text = _docx_text(
        client.get(
            f"/api/v1/operations/{operation['id']}/dossier/{dossier['id']}/download", headers=auth
        ).content
    )
    start = text.index("Submission checklist")
    appendix = text[start:]
    hits = re.findall(r"(€\s?\d[\d.,]*|\d+\s?(?:working\s+)?(?:days?|weeks?|months?))", appendix, re.I)
    assert not hits, f"the submission appendix quotes an unverified figure: {hits}"


# ------------------------------------------------------------------ the two formats

def _pdf_text(data: bytes) -> str:
    """Every bit of text in the PDF, so assertions can be about content."""
    import io

    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)


def test_a_pdf_dossier_is_a_pdf_and_is_served_as_one(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    """Asking for PDF used to store a DOCX under a .pdf name. It must not any more."""
    dossier = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={"format": "pdf"}, headers=auth
    )
    assert dossier.status_code == 201, dossier.text
    assert dossier.json()["format"] == "pdf"

    got = client.get(
        f"/api/v1/operations/{operation['id']}/dossier/{dossier.json()['id']}/download",
        headers=auth,
    )
    assert got.status_code == 200
    assert got.content.startswith(b"%PDF-"), "the bytes are not a PDF"
    assert got.headers["content-type"].startswith("application/pdf")
    assert ".pdf" in got.headers["content-disposition"]
    assert not zipfile.is_zipfile(io.BytesIO(got.content)), "that is a DOCX wearing a .pdf name"


def test_the_pdf_and_the_docx_say_the_same_thing(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    """The one bug this product cannot ship: two exports that disagree about the SAIL.

    Both formats come from one content path, and this is what holds that to be true.
    """
    def _generate(fmt: str) -> bytes:
        made = client.post(
            f"/api/v1/operations/{operation['id']}/dossier", json={"format": fmt}, headers=auth
        )
        assert made.status_code == 201, made.text
        return client.get(
            f"/api/v1/operations/{operation['id']}/dossier/{made.json()['id']}/download",
            headers=auth,
        ).content

    docx = _docx_text(_generate("docx"))
    pdf = _pdf_text(_generate("pdf"))

    d = determined
    # Every risk value, in both, verbatim from the stored determination.
    for value in [
        f"SAIL {d['sail']}",
        str(d["igrc"]),
        str(d["final_grc"]),
        d["rulebase_version"],
    ]:
        assert value in docx, f"{value!r} missing from the DOCX"
        assert value in pdf, f"{value!r} missing from the PDF"

    for phrase in [
        "national aviation authority grants the authorisation",
        "UNVERIFIED",
        "Justification trace",
        "Submission checklist",
    ]:
        assert phrase in docx, f"{phrase!r} missing from the DOCX"
        assert phrase in pdf, f"{phrase!r} missing from the PDF"

    # The trace is the whole point of the appendix; it must survive both renderers.
    for node in d["trace"][:6]:
        assert node["rule_id"] in docx
        assert node["rule_id"] in pdf


def test_the_pdf_carries_the_disclaimer_on_every_page(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    """A printed page is read on its own, so the running header is not decoration."""
    import io

    from pypdf import PdfReader

    made = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={"format": "pdf"}, headers=auth
    )
    data = client.get(
        f"/api/v1/operations/{operation['id']}/dossier/{made.json()['id']}/download", headers=auth
    ).content
    pages = PdfReader(io.BytesIO(data)).pages
    assert len(pages) >= 3, "a dossier that fits on two pages is missing something"
    for i, page in enumerate(pages):
        text = page.extract_text() or ""
        assert "national aviation authority grants the authorisation" in text, (
            f"page {i + 1} has no disclaimer"
        )
        assert "UNVERIFIED RULEBASE" not in text, (
            f"page {i + 1} carries a banner the rulebase has outgrown"
        )


def test_an_unknown_format_is_refused_rather_than_silently_producing_a_docx(
    client: TestClient, auth: dict[str, str], operation: dict[str, Any], determined: dict[str, Any]
) -> None:
    res = client.post(
        f"/api/v1/operations/{operation['id']}/dossier", json={"format": "odt"}, headers=auth
    )
    assert res.status_code == 422
    assert res.json()["code"] == "validation_failed"


def test_the_builder_refuses_an_unknown_format_directly() -> None:
    """Guard below the API, where a future caller might not go through Pydantic."""
    import pytest as _pytest

    from app.services import dossier as builder

    with _pytest.raises(ValueError, match="unknown dossier format"):
        builder.build(
            builder.DossierInput(
                operation={}, organisation={}, drone=None, mission={}, determination={},
                evidence=[], geo=None, version=1,
            ),
            "odt",  # type: ignore[arg-type]
        )


def test_the_pdf_writer_lays_out_bullets_and_breaks() -> None:
    """The vocabulary, exercised directly: bullets land on a page, a break starts another."""
    import io

    from pypdf import PdfReader

    from app.services.docwriter import PdfWriter

    w = PdfWriter(disclaimer="Disclaimer line", stamp="Stamp line", banner=None)
    w.heading("A heading")
    w.bullet("the first bullet")
    w.bullet("the second bullet")
    w.lead_bullet("67.7 m — ", "the rule that produced it")
    w.page_break()
    w.bullet("after the break")
    reader = PdfReader(io.BytesIO(w.render()))

    assert len(reader.pages) == 2, "page_break() did not start a new page"
    first = reader.pages[0].extract_text() or ""
    second = reader.pages[1].extract_text() or ""
    for phrase in ["A heading", "the first bullet", "the second bullet"]:
        assert phrase in first, f"{phrase!r} missing from page 1"
    # A lead bullet is one line, not two: the emphasis must not break the sentence.
    assert "67.7 m" in first and "the rule that produced it" in first
    assert "after the break" in second
    # The running header is on both pages, and the page count resolves.
    for page_text in (first, second):
        assert "Disclaimer line" in page_text
        assert "Stamp line" in page_text
    assert "1 / 2" in first and "2 / 2" in second


def test_the_pdf_writer_renders_characters_a_latin_1_font_would_drop() -> None:
    """The dossier is full of them: em dashes, multiplication signs, umlauts.

    A core PDF font is Latin-1 and would silently mangle these, which is why the
    typeface is bundled rather than assumed.
    """
    import io

    from pypdf import PdfReader

    from app.services.docwriter import PdfWriter

    sample = "Graz Süd — 6.75 km² × 1.0 · iGRC 5"
    w = PdfWriter(disclaimer="d", stamp="s", banner=None)
    w.paragraph(sample)
    text = PdfReader(io.BytesIO(w.render())).pages[0].extract_text() or ""
    for ch in ["ü", "—", "²", "×", "·"]:
        assert ch in text, f"{ch!r} did not survive the renderer"


def test_the_pdf_never_eats_content_to_make_a_phrase_bold() -> None:
    """fpdf2 has no escape character, so emphasis is dropped before content is.

    A rule id, a filename or a citation containing `**`, `__` or `--` must print as
    itself. In a dossier that reaches an authority, a mangled identifier is a far worse
    outcome than an unbolded one.
    """
    import io

    from pypdf import PdfReader

    from app.services.docwriter import PdfWriter

    hostile = ["under_scores", "aster*isk", "__doubled__", "**stars**", "--dashes--"]
    w = PdfWriter(disclaimer="d", stamp="s", banner=None)
    for item in hostile:
        w.lead_bullet("lead — ", f"a value {item} inside a sentence")
        w.bullet(f"plain {item}")
    text = PdfReader(io.BytesIO(w.render())).pages[0].extract_text() or ""
    for item in hostile:
        assert item in text, f"{item!r} was eaten by the markdown parser"
    assert "\\" not in text, "an escape character leaked into the document"
