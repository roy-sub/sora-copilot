"""Where the typeface comes from, for everything that renders a document or an image.

Bundled rather than found on the system. The backend has no Dockerfile any more, so
there is no `apt-get install fonts-dejavu-core` guaranteeing a usable face — and a host
without one does not fail loudly, it renders a dossier full of blank boxes or an
unreadable bitmap chart. A font in the repository is the only version of this that works
the same on a laptop, on Render and in CI.

DejaVu Sans, under the Bitstream Vera licence (``assets/fonts/LICENSE.DejaVu.txt``),
which permits redistribution. It is here for its coverage: the dossier contains ``—``,
``×``, ``²``, ``·`` and German umlauts, none of which survive a Latin-1 core font.
"""

from __future__ import annotations

from pathlib import Path

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

REGULAR = FONT_DIR / "DejaVuSans.ttf"
BOLD = FONT_DIR / "DejaVuSans-Bold.ttf"

#: Checked only if the bundled file is somehow missing — a partial checkout, or a
#: packaging step that dropped the data files.
_SYSTEM_FALLBACKS = {
    REGULAR.name: (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ),
    BOLD.name: (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ),
}


class FontMissing(RuntimeError):
    """No usable typeface. Fatal: a dossier of blank boxes is worse than no dossier."""


def _resolve(path: Path) -> Path:
    if path.is_file():
        return path
    for candidate in _SYSTEM_FALLBACKS.get(path.name, ()):
        if Path(candidate).is_file():
            return Path(candidate)
    raise FontMissing(
        f"{path.name} is not in {FONT_DIR} and no system copy was found. It ships with "
        "the repository; a checkout that is missing it cannot render documents."
    )


def regular() -> Path:
    return _resolve(REGULAR)


def bold() -> Path:
    return _resolve(BOLD)
