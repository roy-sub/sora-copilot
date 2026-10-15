#!/usr/bin/env python3
"""Validate the transcribed rulebase tables and report their verification status.

Phase 1: validates every table's provenance header and row shape, and prints which
tables still carry seed values. Refuses (exit 1) on a malformed table — a compliance
product should not build on a table nobody can parse.

Phase 2 adds the CSV → .lp fact generation to this same script, so there is one command
that turns transcriptions into something clingo can read.

Usage:  python scripts/build_rulebase.py [--version-dir sora_2_5] [--strict]
        --strict additionally fails if any table is still unverified, which is what CI
        will use once the official documents have been transcribed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.engine.rulebase.loader import (
    RulebaseError,
    load_rulebase,
    rulebase_version,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version-dir", default="sora_2_5")
    ap.add_argument("--strict", action="store_true", help="fail if any table is unverified")
    args = ap.parse_args()

    try:
        tables = load_rulebase(args.version_dir)
        version = rulebase_version(args.version_dir)
    except RulebaseError as exc:
        print(f"rulebase invalid: {exc}", file=sys.stderr)
        return 1

    print(f"Rulebase {version} · {len(tables)} tables\n")
    width = max(len(n) for n in tables)
    unverified: list[str] = []
    for name, t in sorted(tables.items()):
        mark = "verified  " if t.verified else "UNVERIFIED"
        print(f"  {mark}  {name:<{width}}  {len(t.rows):>3} rows  {t.document} · {t.section}")
        if not t.verified:
            unverified.append(name)

    if unverified:
        print(
            f"\n{len(unverified)} of {len(tables)} tables still carry seed values:\n"
            + "\n".join(f"  app/engine/rulebase/{args.version_dir}/tables/{n}.csv" for n in unverified)
            + "\n\nDeterminations built on these carry an UNVERIFIED warning and the verdict"
            "\nUI shows a banner. Supply the official documents to verify them — see"
            "\ndocs/RULEBASE.md and PLAN.md §8."
        )
        if args.strict:
            return 1
    else:
        print("\nEvery table is verified against its official source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
