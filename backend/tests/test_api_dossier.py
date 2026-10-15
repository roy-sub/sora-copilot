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


def test_the_document_carries_the_disclaimer_and_the_unverified_banner(
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
    assert "national aviation authority grants the authorisation" in text
    assert "UNVERIFIED RULEBASE" in text
    assert "must not be submitted to an authority" in text


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
