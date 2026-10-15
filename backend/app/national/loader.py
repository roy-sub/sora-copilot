"""Loads the country packs and tailors one to an operation.

A pack is read once and validated whole: a malformed pack raises rather than loading
partially, for the same reason a half-read regulatory table does. Tailoring is pure —
it filters the pack by the SAIL the engine already produced and by which OSOs that
determination requires. It never computes anything about risk.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError

from app.national.models import NationalPack, PackItem

PACKS_ROOT = Path(__file__).resolve().parent / "packs"

#: SAIL is ordinal, so "required from SAIL III" needs an order, not a set.
SAIL_ORDER = ("I", "II", "III", "IV", "V", "VI")


class PackError(RuntimeError):
    """A country pack is malformed. Always fatal: a partial checklist is a wrong one."""


@lru_cache
def load_pack(country: str) -> NationalPack:
    path = PACKS_ROOT / f"{country.lower()}.json"
    if not path.is_file():
        raise PackError(f"no national pack for {country!r} (expected {path.name})")
    try:
        pack = NationalPack.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        raise PackError(f"{path.name} is malformed: {exc}") from exc
    if pack.country != country.upper():
        raise PackError(f"{path.name} declares country {pack.country!r}, not {country.upper()!r}")
    seen: set[str] = set()
    for item in pack.items:
        if item.id in seen:
            raise PackError(f"{path.name}: two items share the id {item.id!r}")
        if not item.id.startswith(f"{country.lower()}."):
            raise PackError(f"{path.name}: item {item.id!r} is not prefixed with {country.lower()!r}")
        seen.add(item.id)
    return pack


@lru_cache
def available() -> tuple[NationalPack, ...]:
    """Every pack on disk, in a stable order."""
    codes = sorted(p.stem for p in PACKS_ROOT.glob("*.json"))
    if not codes:
        raise PackError(f"no country packs found in {PACKS_ROOT}")
    return tuple(load_pack(code) for code in codes)


def _applies(item: PackItem, sail: str | None, required_osos: frozenset[str]) -> bool:
    if item.min_sail is not None:
        if sail is None or sail not in SAIL_ORDER:
            # No SAIL yet (or a certified-category operation): a SAIL-gated item cannot
            # be shown as due, but it is not hidden either — see `pending` below.
            return False
        if SAIL_ORDER.index(sail) < SAIL_ORDER.index(item.min_sail):
            return False
    # An item tied to specific OSOs is due only when the determination required one of
    # them. With no required set yet, it stays due: hiding it would understate the file.
    return not (item.osos and required_osos) or bool(set(item.osos) & required_osos)


def tailor(
    country: str,
    *,
    sail: str | None,
    required_osos: frozenset[str] = frozenset(),
) -> tuple[list[PackItem], list[PackItem]]:
    """Split a pack into (due now, not due at this SAIL).

    Both halves are returned rather than filtering silently: an operator who is about to
    raise their SAIL needs to see what that would add to the file.
    """
    pack = load_pack(country)
    due = [i for i in pack.items if _applies(i, sail, required_osos)]
    pending = [i for i in pack.items if i not in due]
    return due, pending
