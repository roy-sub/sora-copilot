"""What a member state adds on top of EU 2019/947: process, forms and submission.

This is deliberately *not* rulebase data. Nothing here reaches the engine, and no value
here can change a SAIL — the national overrides that can do that live in
``app/engine/rulebase/sora_2_5/90_national_*.lp`` and are empty until their annex is
transcribed (build spec HARD RULE 3).

What a pack holds is the part of an application that is administrative rather than
analytical: which authority receives the file, in which order the steps happen, which
forms travel with it, and what the operator must attach. Every item carries its own
``verified`` flag and ``source``, so a pack can mix a fact that is certain (the name of
the authority) with one that is not (a fee, a statutory clock) without the uncertainty
leaking across. An unverified item is shown as unverified; it is never silently dropped
and never silently trusted.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: Where an item came from. ``official`` means a named clause of a named document;
#: ``seed`` means this project wrote it and the owner has not confirmed it.
Provenance = Literal["official", "seed"]

ItemKind = Literal["process", "form", "attachment", "contact", "note"]


class PackItem(BaseModel):
    """One checklist line. Carries its own provenance, because packs mix certainties."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[a-z]{2}\.[a-z_]+\.[a-z0-9_]+$", description='e.g. "at.process.register"')
    kind: ItemKind
    title: str
    detail: str = ""
    #: Set when the item is only required above a SAIL, so the checklist can be tailored.
    min_sail: Literal["I", "II", "III", "IV", "V", "VI"] | None = None
    #: Set when the item exists to satisfy a specific OSO.
    osos: tuple[str, ...] = ()
    #: Where to do it, or where the form lives. Never a guessed URL.
    url: str | None = None
    provenance: Provenance = "seed"
    source: str = Field(
        default="",
        description="The document and clause, when provenance is official. Empty for a seed.",
    )

    @property
    def verified(self) -> bool:
        return self.provenance == "official"


class NationalPack(BaseModel):
    """Everything the product knows about applying in one country."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    country: Literal["AT", "DE", "EU"]
    country_name: str
    authority: str
    authority_url: str | None = None
    #: One paragraph the operator reads before the checklist. Plain, and honest about gaps.
    summary: str
    #: True only when every item is official and the engine's national overrides for this
    #: country have been transcribed. False is the normal state and is shown as such.
    complete: bool = False
    items: tuple[PackItem, ...]

    @property
    def unverified_ids(self) -> tuple[str, ...]:
        return tuple(i.id for i in self.items if not i.verified)

    def warning(self) -> str | None:
        """The sentence the operator sees when this pack fed their checklist."""
        unverified = self.unverified_ids
        if not unverified:
            return None
        return (
            f"UNVERIFIED: {len(unverified)} of {len(self.items)} items in the "
            f"{self.country_name} pack are this project's reading of the process, not a "
            f"transcription of anything published by {self.authority}. Confirm each "
            "against the authority before you submit."
        )
