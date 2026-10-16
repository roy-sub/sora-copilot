"""A static chart of the operational volumes, for the dossier.

The build spec asks the dossier to carry "operational volume description with a static
map render". This draws one: the flight geography, the contingency volume, the ground
risk buffer and the adjacent area as nested outlines, with a scale bar and a north mark.

Deliberately not a basemap. A dossier is printed and archived, and a tile from a third
party would be a dead reference in a year and a licensing question today. What matters in
the document is the **relationship** between the volumes and their scale, both of which
this shows exactly, from the same geometry the engine read.

Pure drawing: no network, no database.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from itertools import pairwise
from math import cos, radians
from typing import Any

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1600
HEIGHT = 1000
MARGIN = 96

# Print-oriented ink: dark on paper, since the dossier is a document rather than a screen.
PAPER = (255, 255, 255)
GRID = (226, 228, 230)
HAIRLINE = (150, 155, 160)
INK = (26, 26, 26)
MUTED = (90, 96, 102)
FG_LINE = (40, 40, 40)
FG_FILL = (236, 240, 214)
CV_LINE = (110, 116, 122)
GRB_LINE = (176, 98, 26)
ADJACENT = (170, 174, 178)

EARTH_RADIUS_M = 6_378_137.0

Ring = list[tuple[float, float]]

#: Bundled with the backend (``app/assets/fonts``), not taken from the host: there is no
#: Dockerfile installing ``fonts-dejavu-core`` any more, and PIL's bitmap default is
#: unreadable at print size.
_FONT_PATHS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


@dataclass(frozen=True, slots=True)
class Layer:
    ring: Ring
    label: str
    colour: tuple[int, int, int]
    dash: bool = False
    fill: tuple[int, int, int] | None = None
    width: int = 3


def _ring_of(polygon: dict[str, Any] | None) -> Ring:
    if not polygon:
        return []
    coords = (polygon.get("coordinates") or [[]])[0]
    return [(float(lon), float(lat)) for lon, lat in coords]


def _project(rings: list[Ring]) -> tuple[list[Ring], float]:
    """Local metres from lon/lat, and the metres-per-pixel scale that fits the canvas."""
    points = [p for ring in rings for p in ring]
    if not points:
        return [], 1.0
    lat0 = sum(p[1] for p in points) / len(points)
    lon0 = sum(p[0] for p in points) / len(points)
    mx = EARTH_RADIUS_M * radians(1.0) * cos(radians(lat0))
    my = EARTH_RADIUS_M * radians(1.0)

    metres = [[((lon - lon0) * mx, (lat - lat0) * my) for lon, lat in ring] for ring in rings]
    flat = [p for ring in metres for p in ring]
    span_x = max(p[0] for p in flat) - min(p[0] for p in flat)
    span_y = max(p[1] for p in flat) - min(p[1] for p in flat)
    usable_x = WIDTH - 2 * MARGIN
    usable_y = HEIGHT - 2 * MARGIN
    scale = max(span_x / usable_x if usable_x else 1, span_y / usable_y if usable_y else 1, 1e-6)

    min_x = min(p[0] for p in flat)
    max_y = max(p[1] for p in flat)
    pixels = [
        [
            (
                MARGIN + (x - min_x) / scale + (usable_x - span_x / scale) / 2,
                MARGIN + (max_y - y) / scale + (usable_y - span_y / scale) / 2,
            )
            for x, y in ring
        ]
        for ring in metres
    ]
    return pixels, scale


def _dashed(draw: ImageDraw.ImageDraw, ring: Ring, colour: tuple[int, int, int], width: int) -> None:
    """A dashed outline, drawn segment by segment so it reads in print."""
    dash, gap = 14, 9
    closed = [*ring, ring[0]]
    for (x1, y1), (x2, y2) in pairwise(closed):
        length = max(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5, 1e-6)
        steps = int(length // (dash + gap)) + 1
        for i in range(steps):
            t0 = min(1.0, (i * (dash + gap)) / length)
            t1 = min(1.0, (i * (dash + gap) + dash) / length)
            draw.line(
                [
                    (x1 + (x2 - x1) * t0, y1 + (y2 - y1) * t0),
                    (x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1),
                ],
                fill=colour,
                width=width,
            )


def render(
    *,
    flight_geography: dict[str, Any] | None,
    contingency_volume: dict[str, Any] | None = None,
    ground_risk_buffer: dict[str, Any] | None = None,
    adjacent_area: dict[str, Any] | None = None,
) -> bytes | None:
    """The chart as PNG bytes, or None when there is no geometry to draw."""
    layers_in = [
        (adjacent_area, "Adjacent area", ADJACENT, True, None, 2),
        (ground_risk_buffer, "Ground risk buffer", GRB_LINE, False, None, 3),
        (contingency_volume, "Contingency volume", CV_LINE, True, None, 3),
        (flight_geography, "Flight geography", FG_LINE, False, FG_FILL, 3),
    ]
    layers = [
        Layer(ring=_ring_of(polygon), label=label, colour=colour, dash=dash, fill=fill, width=width)
        for polygon, label, colour, dash, fill, width in layers_in
        if _ring_of(polygon)
    ]
    if not layers:
        return None

    pixels, scale = _project([layer.ring for layer in layers])

    image = Image.new("RGB", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    label_font = _font(22)
    small_font = _font(20)

    # A 500 m graticule, so distance is readable without measuring the scale bar.
    step_m = _nice_step(scale)
    step_px = step_m / scale
    gx = float(MARGIN)
    while gx <= WIDTH - MARGIN:
        draw.line([(gx, MARGIN), (gx, HEIGHT - MARGIN)], fill=GRID, width=1)
        gx += step_px
    gy = float(MARGIN)
    while gy <= HEIGHT - MARGIN:
        draw.line([(MARGIN, gy), (WIDTH - MARGIN, gy)], fill=GRID, width=1)
        gy += step_px
    draw.rectangle([MARGIN, MARGIN, WIDTH - MARGIN, HEIGHT - MARGIN], outline=HAIRLINE, width=1)

    for layer, ring in zip(layers, pixels, strict=False):
        if layer.fill:
            draw.polygon(ring, fill=layer.fill)
        if layer.dash:
            _dashed(draw, ring, layer.colour, layer.width)
        else:
            draw.polygon(ring, outline=layer.colour, width=layer.width)

    # Legend, bottom left, inside the frame.
    ly = HEIGHT - MARGIN + 22
    lx = MARGIN
    for layer in reversed(layers):
        draw.rectangle([lx, ly + 8, lx + 26, ly + 13], fill=layer.colour)
        draw.text((lx + 36, ly), layer.label, fill=MUTED, font=label_font)
        lx += 300

    # Scale bar and north mark.
    bar_px = step_px
    bx, by = WIDTH - MARGIN - bar_px, MARGIN - 26
    draw.line([(bx, by), (bx + bar_px, by)], fill=INK, width=3)
    draw.line([(bx, by - 7), (bx, by + 7)], fill=INK, width=3)
    draw.line([(bx + bar_px, by - 7), (bx + bar_px, by + 7)], fill=INK, width=3)
    draw.text((bx, by - 34), _step_label(step_m), fill=INK, font=small_font)

    # North: a drawn triangle rather than an arrow glyph, which not every font carries.
    nx, ny = MARGIN + 8, MARGIN - 42
    draw.polygon([(nx, ny), (nx - 7, ny + 18), (nx + 7, ny + 18)], fill=INK)
    draw.text((nx + 16, ny), "N", fill=INK, font=small_font)

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _nice_step(scale: float) -> float:
    """A round grid step — 100 m to 10 km — that lands between 80 and 220 px."""
    for candidate in (100, 250, 500, 1000, 2000, 5000, 10000):
        if 80 <= candidate / scale <= 220:
            return float(candidate)
    return 1000.0


def _step_label(step_m: float) -> str:
    return f"{step_m / 1000:g} km" if step_m >= 1000 else f"{step_m:g} m"
