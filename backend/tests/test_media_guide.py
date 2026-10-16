"""The media guide must address files the app will actually request.

`docs/Media Setup Guide.md` carries a finished prompt per asset, and someone will
generate sixteen files from it and drop them in. If a path or a dimension has drifted
from `media-manifest.ts`, every one of them lands somewhere the app never looks — and
the failure is silent, because `MediaSlot` falls back to its placeholder. The site would
look exactly as it did before, after an afternoon of generating assets.

So the guide is checked against the manifest rather than trusted. It lives in the
backend suite only because that is where the test runner is.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST = ROOT / "frontend" / "src" / "lib" / "media-manifest.ts"
GUIDE = ROOT / "docs" / "Media Setup Guide.md"

#: `src:` is the asset; `poster:` is a video's fallback frame, which also has to exist.
_ASSET = re.compile(r'(?:src|poster):\s*"(/media/[^"]+)"')
_ENTRY = re.compile(r'"([a-z0-9-]+)":\s*\{(.*?)\n  \}', re.S)
#: A row of the guide's index table: | 1 | `frontend/public/media/x.mp4` | video | 1440 × 810 | …
_ROW = re.compile(
    r"^\|\s*\d+\s*\|\s*`frontend/public(/media/[^`]+)`\s*\|\s*(\w+)\s*\|\s*(\d+)\s*×\s*(\d+)",
    re.MULTILINE,
)


def manifest_assets() -> set[str]:
    return set(_ASSET.findall(MANIFEST.read_text(encoding="utf-8")))


def manifest_dimensions() -> dict[str, tuple[str, str]]:
    out: dict[str, tuple[str, str]] = {}
    for _, body in _ENTRY.findall(MANIFEST.read_text(encoding="utf-8")):
        src = re.search(r'src:\s*"([^"]+)"', body)
        width = re.search(r"w:\s*(\d+)", body)
        height = re.search(r"h:\s*(\d+)", body)
        if src and width and height:
            out[src.group(1)] = (width.group(1), height.group(1))
    return out


def guide_rows() -> list[tuple[str, str, str, str]]:
    return _ROW.findall(GUIDE.read_text(encoding="utf-8"))


def test_both_files_exist_and_parse() -> None:
    """A vacuous pass would be worse than a failure."""
    assert MANIFEST.is_file() and GUIDE.is_file()
    assert len(manifest_assets()) >= 15
    assert len(guide_rows()) >= 15


def test_the_guide_covers_every_asset_the_app_requests() -> None:
    listed = {row[0] for row in guide_rows()}
    missing = sorted(manifest_assets() - listed)
    assert not missing, (
        "the app requests these but the guide gives no prompt for them, so nobody "
        f"working from it would produce them: {missing}"
    )


def test_the_guide_asks_for_nothing_the_app_would_ignore() -> None:
    listed = {row[0] for row in guide_rows()}
    extra = sorted(listed - manifest_assets())
    assert not extra, f"the guide asks for files the app never loads: {extra}"


@pytest.mark.parametrize("row", guide_rows(), ids=lambda r: r[0])
def test_every_listed_dimension_matches_the_manifest(row: tuple[str, str, str, str]) -> None:
    """`MediaSlot` reserves the manifest's ratio; a mismatch is a layout shift."""
    path, _kind, width, height = row
    expected = manifest_dimensions().get(path)
    if expected is None:
        return  # a poster frame, which has no entry of its own
    assert expected == (width, height), (
        f"{path}: the guide asks for {width}×{height}, the manifest reserves "
        f"{expected[0]}×{expected[1]}"
    )


def test_every_asset_has_a_prompt_in_its_own_fence() -> None:
    """Each prompt must be copy-pasteable on its own, which is the point of the guide."""
    text = GUIDE.read_text(encoding="utf-8")
    fences = text.count("```")
    assert fences % 2 == 0, "an unclosed code fence would swallow the rest of the guide"
    # One per asset, plus the shared brand block and the closing shell block.
    assert fences // 2 >= len(guide_rows()) + 1


def test_the_guide_refuses_to_reproduce_real_authority_logos() -> None:
    """The site states no endorsement is implied; the artwork must not imply one."""
    text = GUIDE.read_text(encoding="utf-8")
    # Anchored on the section heading, not the first mention — the first mention is the
    # index table, which carries no guidance at all.
    start = text.index("## 8. Referenced frameworks row")
    section = text[start : text.index("## 9", start)]
    assert "Do **not** reproduce real agency logos" in section
    assert "no emblems" in section
    assert "no endorsement" in section.lower()
