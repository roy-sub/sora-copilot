#!/usr/bin/env python
"""Render a sample dossier PDF from the worked example, for the media build.

The landing page needs a picture of a dossier page. The honest picture is the document
the product actually emits, so this runs the real renderer over the real worked example
rather than mocking a page — a mock of your own output is the one illustration nobody
ever needs.

It bypasses the HTTP layer, and therefore the plan gate, deliberately: the export is a
paid feature and this is not an export, it is a screenshot source. Nothing is stored and
no credit is spent.

    python scripts/sample_dossier.py /tmp/sample.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import UUID, uuid4

from app.db.repo import MemoryRepo
from app.services import demo, intake
from app.services import determination as determination_service
from app.services import dossier as builder


def main(out: Path) -> None:
    repo = MemoryRepo()
    org = repo.ensure_org_for_user(uuid4(), "sample@example.eu")
    org_id = UUID(str(org["org_id"]))
    operation = demo.seed(repo, org_id)

    determination = repo.latest_determination(operation["id"])
    if determination is None:  # pragma: no cover - the seed always determines
        raise SystemExit("the worked example did not produce a determination")

    facts = repo.list_facts(operation["id"])
    mission = intake.apply_confirmed(dict(operation.get("mission") or {}), facts)
    drone = None
    if drone_id := mission.get("drone_id"):
        drone = repo.get_drone(org_id, UUID(str(drone_id)))

    # The volume chart is the document's only figure, and it is what the map feature is
    # a picture of. Re-derive it from the saved geometry exactly as the export endpoint
    # does, so the chart in the sample is the chart a customer gets.
    geo = determination_service.derive_geo(repo, org_id, UUID(str(operation["id"])))

    data = builder.DossierInput(
        operation=operation,
        organisation=repo.get_org(org_id),
        drone=drone,
        mission=mission,
        determination=determination,
        evidence=repo.list_evidence(operation["id"]),
        geo=geo,
        version=1,
        prose=None,
        outlines=geo,
    )
    out.write_bytes(builder.build(data, "pdf"))
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "sample-dossier.pdf"))
