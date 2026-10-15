#!/usr/bin/env python3
"""Write the OpenAPI schema to openapi.json, which the frontend client is generated from.

Keeping this a file on disk rather than a live fetch means the typed client can be
regenerated without a running backend, and the schema diff shows up in review.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import create_app

OUT = Path(__file__).resolve().parent.parent / "openapi.json"


def main() -> int:
    schema = create_app().openapi()
    OUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(OUT.parent.parent)} · {len(schema.get('paths', {}))} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
