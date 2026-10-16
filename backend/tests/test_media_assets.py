"""Every slot in the media manifest has a real file, at the size the manifest promises.

`MediaSlot` reserves the manifest's aspect ratio and falls back to its designed
placeholder when a file is missing — quietly, by design, so the site is presentable
before the assets exist. That is the right behaviour and it is also why a missing or
mis-sized asset is invisible in review: the page still looks finished. These tests are
the thing that notices.

They read the dimensions out of the files themselves rather than trusting the build
script that wrote them.
"""

from __future__ import annotations

import json
import re
import struct
import subprocess
from pathlib import Path

import pytest

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
MANIFEST = FRONTEND / "src" / "lib" / "media-manifest.ts"
MEDIA = FRONTEND / "public" / "media"


def _manifest() -> dict[str, dict[str, object]]:
    src = MANIFEST.read_text(encoding="utf-8")
    body = src[src.index("export const MEDIA = {") :]
    out: dict[str, dict[str, object]] = {}
    for entry in re.finditer(r'"([a-z0-9-]+)":\s*\{(.*?)\n  \}', body, re.S):
        name, block = entry.group(1), entry.group(2)

        # Bound as a default so each closure keeps the block it was built for, rather
        # than every one of them reading whatever the loop variable holds at call time.
        def pick(key: str, block: str = block) -> str | None:
            m = re.search(rf'\b{key}:\s*"([^"]*)"', block)
            return m.group(1) if m else None

        def num(key: str, block: str = block) -> int | None:
            m = re.search(rf"\b{key}:\s*([0-9_]+)", block)
            return int(m.group(1).replace("_", "")) if m else None

        out[name] = {
            "kind": pick("kind"),
            "src": pick("src"),
            "poster": pick("poster"),
            "alt": pick("alt"),
            "w": num("w"),
            "h": num("h"),
            "maxBytes": num("maxBytes"),
        }
    return out


ENTRIES = _manifest()


def _png_size(data: bytes) -> tuple[int, int]:
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    w, h = struct.unpack(">II", data[16:24])
    return w, h


def _jpeg_size(data: bytes) -> tuple[int, int]:
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        # SOF0..SOF15, skipping the four that are not frame headers.
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", data[i + 5 : i + 9])
            return w, h
        i += 2 + struct.unpack(">H", data[i + 2 : i + 4])[0]
    raise AssertionError("no JPEG frame header")


def _svg_size(text: str) -> tuple[int, int]:
    w = re.search(r'\bwidth="(\d+)"', text)
    h = re.search(r'\bheight="(\d+)"', text)
    assert w and h, "the SVG does not declare width and height"
    return int(w.group(1)), int(h.group(1))


def _video_size(path: Path) -> tuple[int, int]:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    stream = json.loads(out)["streams"][0]
    return int(stream["width"]), int(stream["height"])


def _paths(entry: dict[str, object]) -> list[str]:
    """The file(s) a slot needs: a video also needs its poster."""
    files = [str(entry["src"])]
    if entry.get("poster"):
        files.append(str(entry["poster"]))
    return files


def test_the_manifest_parses() -> None:
    assert len(ENTRIES) == 15, f"expected 15 slots, read {sorted(ENTRIES)}"


@pytest.mark.parametrize("name", sorted(ENTRIES))
def test_every_slot_has_its_file(name: str) -> None:
    for rel in _paths(ENTRIES[name]):
        path = MEDIA / rel.removeprefix("/media/")
        assert path.is_file(), f"{name}: {path} is missing — MediaSlot would fall back silently"
        assert path.stat().st_size > 0, f"{name}: {path} is empty"


@pytest.mark.parametrize("name", sorted(ENTRIES))
def test_every_asset_is_the_size_the_manifest_reserves(name: str) -> None:
    entry = ENTRIES[name]
    want = (entry["w"], entry["h"])
    for rel in _paths(entry):
        path = MEDIA / rel.removeprefix("/media/")
        suffix = path.suffix.lower()
        if suffix == ".png":
            got = _png_size(path.read_bytes())
        elif suffix in (".jpg", ".jpeg"):
            got = _jpeg_size(path.read_bytes())
        elif suffix == ".svg":
            got = _svg_size(path.read_text(encoding="utf-8"))
        elif suffix == ".mp4":
            got = _video_size(path)
        else:
            raise AssertionError(f"{name}: unexpected asset type {suffix}")
        assert got == want, f"{name}: {path.name} is {got[0]}x{got[1]}, manifest reserves {want[0]}x{want[1]}"


@pytest.mark.parametrize(
    "name", sorted(n for n, e in ENTRIES.items() if e.get("maxBytes"))
)
def test_a_budgeted_asset_is_within_its_budget(name: str) -> None:
    entry = ENTRIES[name]
    path = MEDIA / str(entry["src"]).removeprefix("/media/")
    budget = int(entry["maxBytes"])  # type: ignore[arg-type]
    assert path.stat().st_size <= budget, (
        f"{name}: {path.stat().st_size // 1024} KB over its {budget // 1024} KB budget"
    )


@pytest.mark.parametrize("name", sorted(ENTRIES))
def test_every_slot_has_alt_text_that_describes_the_real_asset(name: str) -> None:
    """Alt text is the asset's only description for a screen reader; it may not be stale.

    Three of these were photographs of people in the original manifest and are segment
    cards now. The text had to move with them, so this asserts the words are there at
    all and that nothing still claims to be a photograph of somebody.
    """
    alt = str(ENTRIES[name]["alt"] or "")
    assert len(alt) > 20, f"{name}: alt text is too short to describe anything"
    for word in ("photograph", "portrait"):
        assert word not in alt.lower(), f"{name}: alt text still says {word!r}"


def test_videos_are_h264_yuv420p_so_they_play_on_a_phone() -> None:
    """Anything else is a black rectangle in Safari, which no unit test would catch."""
    for name, entry in ENTRIES.items():
        if entry["kind"] != "video":
            continue
        path = MEDIA / str(entry["src"]).removeprefix("/media/")
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_name,pix_fmt", "-of", "json", str(path)],
            capture_output=True, text=True, check=True,
        ).stdout
        stream = json.loads(out)["streams"][0]
        assert stream["codec_name"] == "h264", f"{name}: {stream['codec_name']}, not h264"
        assert stream["pix_fmt"] == "yuv420p", f"{name}: {stream['pix_fmt']}, not yuv420p"
