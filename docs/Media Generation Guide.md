# Media Generation Guide

Every image, video and illustration the product needs, with a finished prompt for each.

> **All sixteen are built and committed.** `frontend/public/media/` holds the real
> files, and `backend/tests/test_media_assets.py` checks every one against the manifest
> for exact pixel size, byte budget and — for the two videos — H.264 in yuv420p, so a
> drifted or missing asset fails the build instead of silently falling back to a
> placeholder. This guide is now a **replacement** guide: the prompts below are what to
> hand a generator if you want to swap one for something else.
>
> How the shipped ones were made, and why, is in [What is actually in
> `public/media/`](#what-is-actually-in-publicmedia) at the end.

`MediaSlot` reserves the exact aspect ratio from `frontend/src/lib/media-manifest.ts`
and draws a labelled placeholder when a file is missing, so the site stays presentable
either way. Drop a replacement at the path given below and it appears on the next build:
no code change, no manifest edit — but do keep the pixel size, or the test will say so.

**Suggested tools.** Higgsfield for the photographic and cinematic stills, ChatGPT 2.5
for the UI composites and the flat graphics, Seedance 2.5 for the two video loops. Each
prompt below names the one it was written for, but they are all plain descriptive
prompts and will work elsewhere.

---

## Index

| # | File | Type | Pixels | Aspect | Tool | Budget |
|---|---|---|---|---|---|---|
| 1 | `frontend/public/media/hero-loop.mp4` | video | 1440 × 810 | 16:9 | Seedance 2.5 | ≤ 2.5 MB |
| 2 | `frontend/public/media/hero-poster.jpg` | image | 1440 × 810 | 16:9 | ChatGPT 2.5 | ≤ 400 KB |
| 3 | `frontend/public/media/feature-trace.png` | image | 1280 × 960 | 4:3 | ChatGPT 2.5 | ≤ 500 KB |
| 4 | `frontend/public/media/feature-map.png` | image | 1280 × 960 | 4:3 | ChatGPT 2.5 | ≤ 500 KB |
| 5 | `frontend/public/media/feature-dossier.png` | image | 900 × 1200 | 3:4 | ChatGPT 2.5 | ≤ 500 KB |
| 6 | `frontend/public/media/feature-counterfactual.mp4` | video | 900 × 900 | 1:1 | Seedance 2.5 | ≤ 1.2 MB |
| 7 | `frontend/public/media/feature-counterfactual.jpg` | image | 900 × 900 | 1:1 | ChatGPT 2.5 | ≤ 250 KB |
| 8 | `frontend/public/media/proof-logos.png` | image | 1200 × 200 | 6:1 | ChatGPT 2.5 | ≤ 150 KB |
| 9 | `frontend/public/media/persona-1.jpg` | image | 600 × 600 | 1:1 | Higgsfield | ≤ 200 KB |
| 10 | `frontend/public/media/persona-2.jpg` | image | 600 × 600 | 1:1 | Higgsfield | ≤ 200 KB |
| 11 | `frontend/public/media/persona-3.jpg` | image | 600 × 600 | 1:1 | Higgsfield | ≤ 200 KB |
| 12 | `frontend/public/media/dossier-preview.png` | image | 900 × 1200 | 3:4 | ChatGPT 2.5 | ≤ 500 KB |
| 13 | `frontend/public/media/empty-operations.svg` | illustration | 480 × 480 | 1:1 | ChatGPT 2.5 | ≤ 20 KB |
| 14 | `frontend/public/media/empty-dossiers.svg` | illustration | 480 × 480 | 1:1 | ChatGPT 2.5 | ≤ 20 KB |
| 15 | `frontend/public/media/empty-fleet.svg` | illustration | 480 × 480 | 1:1 | ChatGPT 2.5 | ≤ 20 KB |
| 16 | `frontend/public/media/og-default.png` | image | 1200 × 630 | 1.91:1 | ChatGPT 2.5 | ≤ 300 KB |

Retina variants are optional. Where a note says "2× at 1200", generate at double and save
as `<name>@2x.<ext>` alongside; the manifest's intrinsic size is unchanged either way.

---

## The brand, in one block

Paste this with any prompt that needs the product's own look — items 1–8 and 12–16. The
photographic portraits (9–11) deliberately do **not** use it; see their section.

```
BRAND SYSTEM — SORA Copilot (EU drone compliance software)

Ground: pure black #000000. The page ground is black in both light and dark themes;
only the panels change. Panels ("sheets") are near-black graphite: #121517 standard,
#0a0c0d recessed, #191d20 raised. Separation between panels is a 2px black gap, never
a drop shadow. Hairline rules are #262c31, 1px.

Accent: a single acid lime #caff01, used sparingly — one accent per view, on the
primary action or one live value. Never as a fill for large areas. Nothing else is
saturated.

Text: near-white #eef1f3 for primary, #9aa4ad mid, #6b757d low. Typeface Archivo
(grotesque, neutral, slightly condensed) for everything; the wordmark is Outfit Light
300. Numerals are tabular. Micro-labels are uppercase, 10–11px, letter-spaced 0.08em.

Risk colour ramp (SAIL I to VI), deliberately GREENLESS so "low risk" is never read as
"safe to proceed": #8a95a1 slate, #a79b93 warm grey, #c99a3f ochre, #dd7f31 amber,
#d4502f orange-red, #b82633 deep red.

Mood: an instrument, not a dashboard. Precise, quiet, technical, a little severe.
Aerospace documentation and engineering drawings, not consumer SaaS. No gradients,
no glow, no glassmorphism, no rounded cards, no 3D, no floating UI mockups at an
angle, no people in the interface shots, no stock-photo gloss. Flat, square-cornered,
orthogonal. Corner registration marks and graticules are part of the language.
```

---

## 1. Hero loop

**Save as:** `frontend/public/media/hero-loop.mp4`
**Type:** video · **Aspect:** 16:9 · **Pixels:** 1440 × 810 · **Tool:** Seedance 2.5
**Budget:** ≤ 2.5 MB · silent, seamless loop, ~12 s
**Used by:** the landing hero band, full-bleed, below the headline.

```
A 12-second seamless silent screen-capture loop of a dark aerospace-grade software
interface, 1440x810, 16:9.

The entire frame is a map workspace on a pure black #000000 ground. The map is an
abstract vector basemap in near-black graphite #121517 with faint #262c31 hairline
roads and a thin coordinate graticule — no satellite imagery, no labels, no colour.

The motion, in one continuous take with no cuts:
1. (0-3s) A thin #eef1f3 polyline draws itself vertex by vertex across the map,
   closing into a four-sided operational volume. Each vertex lands with a small
   square handle. The enclosed area fills with a very low-opacity pale wash.
2. (3-6s) Two more outlines offset outward from the first, one at a time: a dashed
   contingency boundary, then a solid #dd7f31 amber ground-risk buffer. Each expands
   smoothly from the edge of the previous one, like a tolerance band being applied.
3. (6-9s) In the lower right, a compact instrument panel fades up: five small labelled
   cells reading iGRC, GRC, ARC, RESIDUAL ARC, SAIL. Values populate left to right,
   one cell at a time, in tabular numerals: 5, 4, C, B, then the last cell resolves to
   the Roman numeral III.
4. (9-12s) A small square badge in ochre #c99a3f settles beside the panel showing
   "III" with the word SAIL beneath, and the frame holds steady, returning to the
   first frame's composition for a clean loop.

Camera is perfectly locked — no pan, no zoom, no parallax, no drift. Motion is
mechanical and eased, never bouncy. No cursor, no mouse pointer, no click effects, no
cursor trails, no UI chrome, no browser frame, no window controls, no watermark, no
text captions, no human hands.

Palette strictly: black #000000, graphite #121517 and #0a0c0d, hairline #262c31, text
#eef1f3, one amber #dd7f31, one ochre #c99a3f, and at most one small acid lime #caff01
mark. No other colours. No glow, no bloom, no gradients, no lens flare, no depth of
field.
```

---

## 2. Hero poster

**Save as:** `frontend/public/media/hero-poster.jpg`
**Type:** image · **Aspect:** 16:9 · **Pixels:** 1440 × 810 · **Tool:** ChatGPT 2.5
**Budget:** ≤ 400 KB · also the reduced-motion fallback, so it must stand alone
**Used by:** the hero, before the video loads and whenever motion is reduced.

```
A single still frame of a dark aerospace-grade software interface, 1440x810, 16:9,
flat and perfectly orthogonal — a screenshot, not a rendering.

A map workspace on a pure black #000000 ground. The basemap is abstract vector
cartography in near-black graphite #121517: faint #262c31 hairline roads and a thin
coordinate graticule, no satellite imagery, no place labels, no colour.

Centred slightly left: three concentric four-sided outlines, each offset from the last.
The innermost is a crisp #eef1f3 polygon with small square vertex handles and a very
low-opacity pale fill. Around it, a dashed hairline boundary. Around that, a solid
#dd7f31 amber boundary. A small legend sits beneath them in 10px uppercase letter-
spaced grey: FLIGHT GEOGRAPHY, CONTINGENCY VOLUME, GROUND RISK BUFFER.

Lower right: a compact five-cell instrument strip on a #0a0c0d panel, separated from
the map by a 2px black gap. Cells are divided by 1px #262c31 hairlines, each with a
tiny uppercase grey label above a large tabular numeral: iGRC 5, GRC 4, ARC C,
RESIDUAL ARC B, SAIL III. Beside it, a small square ochre #c99a3f badge containing the
Roman numeral III in near-black, with SAIL in small caps beneath.

Upper right: a thin scale bar reading 500 m, and a small solid north triangle.

Typography is Archivo or a similar neutral grotesque; all numerals tabular; all micro-
labels uppercase and letter-spaced.

No people, no hands, no cursor, no browser chrome, no window controls, no rounded
corners, no drop shadows, no gradients, no glow, no 3D perspective, no angled mockup,
no reflections, no watermark. Flat, square, head-on. Only these colours: #000000,
#121517, #0a0c0d, #262c31, #eef1f3, grey text, #dd7f31, #c99a3f.
```

---

## 3. Feature — the derivation trace

**Save as:** `frontend/public/media/feature-trace.png`
**Type:** image · **Aspect:** 4:3 · **Pixels:** 1280 × 960 · **Tool:** ChatGPT 2.5
**Budget:** ≤ 500 KB · PNG for crisp 1px rules and small type
**Used by:** the landing band "Every line cites its rule".

```
A still screenshot of a node graph in dark aerospace-grade software, 1280x960, 4:3,
flat and perfectly head-on.

A left-to-right directed acyclic graph on a #0a0c0d recessed panel over a pure black
#000000 ground. Roughly twenty small rectangular nodes arranged in six vertical ranks,
connected by thin #3d464c curved bezier edges that enter each node on its left edge and
leave on its right.

Nodes are flat #121517 rectangles with square corners, a 1px #262c31 border, and about
220px wide. Each has a tiny uppercase letter-spaced grey label on its first line and
white #eef1f3 content beneath:
- Left rank, five nodes labelled CONFIRMED FACT: "Maximum characteristic dimension
  1.32 m", "Maximum speed 22 m/s", "Population density 84 ppl/km²", "Ground
  environment sparsely populated", "Airspace class G".
- Second rank, three nodes labelled RULEBASE TABLE, each with a small monospace
  citation chip beneath in dim grey, e.g. "JARUS SORA 2.5 · Table 2".
- Middle ranks, nodes labelled with their conclusion in larger white type and a
  monospace rule identifier beneath in dim grey: "iGRC 5", "GRC 4", "ARC C",
  "RESIDUAL ARC B".
- Rightmost rank, a single larger node containing a square ochre #c99a3f badge with
  the Roman numeral III and SAIL beneath it.

Three of the middle nodes are expanded, showing two extra lines of small grey detail
text inside them. One edge path running the full width is highlighted in acid lime
#caff01, one pixel wide — the only saturated colour in the frame apart from the badge.

Typography Archivo or similar neutral grotesque; identifiers in a monospace face;
numerals tabular.

No cursor, no people, no browser chrome, no rounded cards, no drop shadows, no
gradients, no glow, no 3D, no angled perspective, no watermark, no minimap, no toolbar.
Flat and square. Only: #000000, #0a0c0d, #121517, #262c31, #3d464c, #eef1f3, grey text,
#c99a3f, and a single #caff01 line.
```

---

## 4. Feature — the map step

**Save as:** `frontend/public/media/feature-map.png`
**Type:** image · **Aspect:** 4:3 · **Pixels:** 1280 × 960 · **Tool:** ChatGPT 2.5
**Budget:** ≤ 500 KB
**Used by:** the landing band "Draw the flight geography. The volumes follow."

```
A still screenshot of a map editing step in dark aerospace-grade software, 1280x960,
4:3, flat and perfectly head-on.

Left three-quarters: a map canvas on pure black #000000 with an abstract vector
basemap in graphite #121517 — faint #262c31 hairline roads, a river as a slightly
heavier hairline, a thin coordinate graticule. No satellite imagery, no place labels.

On the map, a long narrow corridor polygon running roughly north-south, as a powerline
inspection route would: a crisp #eef1f3 outline with small square vertex handles and a
very low-opacity pale fill. Offset outward from it, a dashed hairline contingency
boundary, and outside that a solid #dd7f31 amber ground-risk buffer. Outside everything,
a faint dotted adjacent-area boundary. A soft, barely visible population-density
overlay tints two small clusters near the corridor.

Upper left: a solid north triangle with the letter N. Upper right: a scale bar reading
500 m.

Right quarter: a #121517 side panel separated by a 2px black gap, containing a stack of
derived values, each a small uppercase grey label above a white tabular figure, divided
by 1px #262c31 hairlines: FLIGHT GEOGRAPHY 6.75 km², CONTINGENCY VOLUME 7.48 km²,
GROUND RISK BUFFER 8.99 km², ADJACENT AREA 24.1 km². Beneath them, two lines of small
grey explanatory text and one acid lime #caff01 primary button reading CONTINUE.

Typography Archivo or similar neutral grotesque; numerals tabular; micro-labels
uppercase and letter-spaced.

No cursor, no people, no hands, no browser chrome, no rounded corners, no drop shadows,
no gradients, no glow, no 3D, no angled perspective, no watermark. Flat and square.
Only: #000000, #121517, #0a0c0d, #262c31, #eef1f3, grey text, #dd7f31, one #caff01.
```

---

## 5. Feature — the exported dossier

**Save as:** `frontend/public/media/feature-dossier.png`
**Type:** image · **Aspect:** 3:4 · **Pixels:** 900 × 1200 · **Tool:** ChatGPT 2.5
**Budget:** ≤ 500 KB
**Used by:** the landing band "The output looks like it came from an aviation professional."

```
A single page of a printed technical compliance document, photographed flat and
perfectly head-on, 900x1200, 3:4. White paper #ffffff filling the frame edge to edge,
no desk, no background, no perspective, no page curl, no shadow.

The page is set in black and dark grey on white, in a neutral grotesque typeface,
dense and professional — like an aviation authority submission, not a brochure.

Top of the page, a small grey running header in two lines: a disclaimer sentence, then
a version stamp reading "Rulebase 2.5.0-rc1 · determination 58ff96db · dossier v2".
Beneath it, a bold rust-brown warning line in small caps.

Body: a section heading "4. Operational safety objectives", a line of explanatory text,
then a full-width five-column table with thin grey rules and a pale grey header row.
Columns headed OSO, OBJECTIVE, REQUIRED, STATUS, EVIDENCE. About twelve rows of real-
looking content: identifiers like OSO#01, OSO#03, OSO#08, OSO#13, OSO#24; objective
text such as "Operator is competent and/or proven", "UAS maintained by a competent
and/or proven entity", "Operational procedures are defined validated and adhered to";
a REQUIRED column reading low, medium or high; a STATUS column reading documented or
unmet; an EVIDENCE column with filenames like "sheltering-survey.pdf".

Bottom: a small italic grey footnote, and a page number reading "9 / 15" in the lower
right.

Real typography with correct kerning and baseline grid. No lorem ipsum, no blurred or
scribbled placeholder text, no greeked lines. No logos, no signatures, no stamps, no
photographs, no colour beyond the single rust warning line, no shadows, no glossy
paper, no hands, no desk, no 3D, no mockup perspective.
```

---

## 6. Feature — the counterfactual advisor

**Save as:** `frontend/public/media/feature-counterfactual.mp4`
**Type:** video · **Aspect:** 1:1 · **Pixels:** 900 × 900 · **Tool:** Seedance 2.5
**Budget:** ≤ 1.2 MB · silent, seamless loop, ~6 s
**Used by:** the landing band "When the answer is no, the advisor says what would make it yes."

```
A 6-second seamless silent screen-capture loop of a dark aerospace-grade software
panel, 900x900, square.

A single #121517 panel on a pure black #000000 ground. At the top, a small uppercase
letter-spaced grey label: COUNTERFACTUAL ADVISOR. Beneath it a one-line suggestion in
white #eef1f3: "Claim M1 sheltering at medium robustness".

Centre: a horizontal SAIL scale of six small square cells in a row, labelled I through
VI in tabular numerals. The cells run slate #8a95a1, warm grey #a79b93, ochre #c99a3f,
amber #dd7f31, orange-red #d4502f, deep red #b82633. Exactly one cell is active —
filled and bright — while the others are dimmed to about 25 percent.

The motion, one continuous locked take:
1. (0-2s) Cell III is active. Below the scale, a parameter row reads "M1 sheltering —
   none" with a small control at its right.
2. (2-4s) The parameter steps to "M1 sheltering — medium". The active state slides one
   cell to the left, from III to II, in a single crisp mechanical step with a short
   ease — not a fade, not a bounce.
3. (4-6s) A small acid lime #caff01 marker ticks beside the changed row, a line of
   small grey text reads "re-run by the engine", and the frame holds, then returns
   exactly to the opening state for a clean loop.

Camera perfectly locked. No pan, no zoom, no drift, no parallax. No cursor, no mouse
pointer, no click ripples, no browser chrome, no window controls, no watermark, no
captions, no hands.

Palette strictly: #000000, #121517, #0a0c0d, #262c31, #eef1f3, grey text, the six SAIL
ramp colours, and one #caff01 mark. No green anywhere. No glow, no bloom, no gradients,
no depth of field.
```

---

## 7. Counterfactual poster frame

**Save as:** `frontend/public/media/feature-counterfactual.jpg`
**Type:** image · **Aspect:** 1:1 · **Pixels:** 900 × 900 · **Tool:** ChatGPT 2.5
**Budget:** ≤ 250 KB · the poster for item 6, and its reduced-motion fallback
**Note:** this file has no manifest entry of its own — it is referenced as the video's poster, so it must exist alongside it.

```
A single still frame of a dark aerospace-grade software panel, 900x900, square, flat
and perfectly head-on — a screenshot, not a rendering.

One #121517 panel on a pure black #000000 ground. Top: a small uppercase letter-spaced
grey label reading COUNTERFACTUAL ADVISOR, and beneath it a white #eef1f3 line reading
"Claim M1 sheltering at medium robustness".

Centre: a horizontal row of six small square cells labelled I, II, III, IV, V, VI in
tabular numerals, coloured slate #8a95a1, warm grey #a79b93, ochre #c99a3f, amber
#dd7f31, orange-red #d4502f, deep red #b82633. Cell III is fully lit; the other five
are dimmed to about 25 percent opacity.

Below the scale, a parameter row on a 1px #262c31 hairline: "M1 sheltering" on the left
in grey, "none" on the right in white. Beneath it, a second row reading "Resulting
SAIL" and "II". A small line of grey text at the bottom reads "re-run by the engine
before it was offered".

Typography Archivo or similar neutral grotesque; numerals tabular; micro-labels
uppercase and letter-spaced.

No green anywhere. No cursor, no people, no browser chrome, no rounded corners, no drop
shadows, no gradients, no glow, no 3D, no angled perspective, no watermark. Flat and
square.
```

---

## 8. Referenced frameworks row

**Save as:** `frontend/public/media/proof-logos.png`
**Type:** image · **Aspect:** 6:1 · **Pixels:** 1200 × 200 · **Tool:** ChatGPT 2.5
**Budget:** ≤ 150 KB · transparent background preferred
**Used by:** the landing "Referenced frameworks" band, beside the no-endorsement line.

> **Read this before generating.** The site states plainly that these are references and
> that no endorsement is implied. Do **not** reproduce real agency logos, emblems,
> roundels or wordmarks — generate neutral typographic marks only. Using a real
> authority's logo would imply an approval that does not exist, which is exactly what
> this product must never do.

```
A single horizontal strip, 1200x200, 6:1, on a transparent or pure black #000000
background.

Five evenly spaced neutral typographic marks in one row, all in the same flat mid-grey
#6b757d, all optically the same visual weight, separated by thin vertical #262c31
hairline dividers.

Each mark is set type only — no emblems, no crests, no roundels, no shields, no wings,
no globes, no stars, no flags, no pictorial symbols of any kind. Each is a short
abbreviation in an uppercase neutral grotesque, letter-spaced, with a much smaller
uppercase descriptor beneath it in the same grey at about 40 percent of the size:

1. "JARUS" over "SORA 2.5"
2. "EU" over "2019/947"
3. "EASA" over "AMC / GM"
4. "ED-269" over "GEO-ZONES"
5. "ISO" over "21384"

Flat, monochrome, no colour at all, no gradients, no glow, no shadows, no 3D, no
bevels, no rounded badge shapes, no containers or boxes around the marks. Generous even
spacing, optically centred as a group.
```

---

## 9–11. Operator portraits

**Type:** image · **Aspect:** 1:1 · **Pixels:** 600 × 600 · **Tool:** Higgsfield
**Budget:** ≤ 200 KB each · JPEG · optional `@2x` at 1200 × 1200
**Used by:** the landing "Who runs it" band, three across.

These three are the one place the product uses photography, and they deliberately break
the brand block above: real light, real colour, real places. They are documentary
photographs of working people, not stock-photo "drone professionals". The common
direction:

> Documentary editorial photography, natural available light only, Austrian or Alpine
> European setting, candid mid-task — never posed, never looking at the camera, never
> smiling at the lens. Muted natural colour, slightly desaturated, soft contrast.
> Square 1:1 crop, shallow but not extreme depth of field. No studio lighting, no
> flash, no lens flare, no colour grading toward teal-and-orange, no stock-photo gloss,
> no visible brand logos, no text or watermark, no AI-smooth skin.

### 9. Inspection company

**Save as:** `frontend/public/media/persona-1.jpg`

```
Documentary editorial photograph, square 1:1, 600x600.

Two people in their thirties working on a flat rooftop in Graz, Austria, mid-task. One
crouches beside an open hard case with a folded quadcopter inside, checking something
on a rugged tablet; the other stands a few steps away looking out over the parapet at
the roofscape, holding a clipboard at their side. Both wear practical workwear and
high-visibility vests, not branded uniforms.

Overcast midday light, soft and even, no hard shadows. Behind them, the muted terracotta
and grey rooftops of a central European city, hills faintly visible in the distance,
slightly out of focus. Foreground includes a little honest clutter: a cable coil, a
spare battery, a thermos.

Natural muted colour, slightly desaturated, gentle contrast. Candid — neither person
faces the camera, neither is smiling at the lens. Shot at roughly 35mm, modest depth of
field, the standing figure softly out of focus.

No studio lighting, no flash, no lens flare, no HDR, no teal-and-orange grade, no stock-
photo gloss, no visible logos or brand marks, no text, no watermark, no drone in flight,
no over-smoothed skin, nobody posing.
```

### 10. Solo BVLOS operator

**Save as:** `frontend/public/media/persona-2.jpg`

```
Documentary editorial photograph, square 1:1, 600x600.

A single operator in their forties standing in a wide farmland field in rural Austria,
working at a ground control station — a rugged case open on a folding stand with two
screens and a control stick. They are looking down at the screens, one hand on the
stick, concentrating. Practical outdoor clothing, a headset around the neck, no branded
uniform.

Bright but overcast daylight, flat and soft. The field is winter-brown stubble or early
spring grass. In the middle distance, a line of electricity pylons recedes across the
landscape and low hills sit on the horizon. A small white van is parked at the edge of
frame, out of focus.

Natural muted colour, slightly desaturated, gentle contrast. Candid — not facing the
camera, not smiling at the lens. Roughly 50mm, modest depth of field, the pylons softly
out of focus.

No studio lighting, no flash, no golden hour, no lens flare, no HDR, no teal-and-orange
grade, no stock-photo gloss, no visible logos or brand marks, no text, no watermark, no
drone visible in the sky, no over-smoothed skin, nobody posing.
```

### 11. Compliance officer

**Save as:** `frontend/public/media/persona-3.jpg`

```
Documentary editorial photograph, square 1:1, 600x600.

A person in their fifties at a plain office desk, reading a thick printed document — a
stapled technical report held slightly raised in both hands, a pen resting on the desk
beside it. Reading glasses on. Business-casual clothing, nothing corporate or styled.

Daylight from a window to one side, soft and directional, no overhead fluorescent cast,
no screen glow on the face — there is no monitor in the shot, or it is dark and out of
frame. The desk carries a few honest objects: a second printed document with a sticky
tab on it, a coffee cup, a notebook.

Muted natural colour, slightly desaturated, gentle contrast, calm and quiet in mood.
Candid — looking down at the page, not at the camera, not smiling at the lens. Roughly
50mm, shallow depth of field with the background falling away softly.

No studio lighting, no flash, no lens flare, no HDR, no teal-and-orange grade, no stock-
photo gloss, no visible logos or brand marks, no readable text on the document, no
watermark, no over-smoothed skin, nobody posing.
```

---

## 12. Dossier preview

**Save as:** `frontend/public/media/dossier-preview.png`
**Type:** image · **Aspect:** 3:4 · **Pixels:** 900 × 1200 · **Tool:** ChatGPT 2.5
**Budget:** ≤ 500 KB
**Used by:** the in-app dossier builder, as the preview pane beside the section list.

```
A single page of a printed technical compliance document, flat and perfectly head-on,
900x1200, 3:4. White paper #ffffff filling the frame edge to edge — no desk, no
background, no perspective, no shadow, no page curl.

Set in black and dark grey on white in a neutral grotesque typeface, dense and
professional.

Top: a two-line grey running header — a disclaimer sentence, then "Rulebase 2.5.0-rc1 ·
determination 58ff96db · dossier v2" — followed by a bold rust-brown warning line in
small caps.

Body, from the top: a heading "Appendix A — Justification trace" and a short paragraph
of explanatory text. Beneath it, a full-width four-column table with thin grey rules and
a pale grey header row, headed CONCLUSION, RULE, CITATION, FROM. About fourteen rows of
dense real-looking content: conclusions such as "igrc(5)", "grc(4)", "arc(c)",
"sail(iii)"; rule identifiers in monospace such as "sora25.igrc.lookup",
"sora25.arc.aerodrome.uncontrolled"; citations such as "JARUS SORA 2.5 · Table 2, p. 24"
with some marked "[UNVERIFIED]"; and a FROM column listing comma-separated premises.

Bottom: a small italic grey footnote giving a node count and a mission hash, and a page
number reading "12 / 15" lower right.

Real typography with correct kerning and a consistent baseline grid. No lorem ipsum, no
greeked or scribbled placeholder lines. No logos, no signatures, no stamps, no
photographs, no colour beyond the rust warning line, no shadows, no glossy paper, no
hands, no 3D, no mockup perspective.
```

---

## 13–15. Empty-state schematics

**Type:** illustration · **Aspect:** 1:1 · **Pixels:** 480 × 480 · **Tool:** ChatGPT 2.5
**Budget:** ≤ 20 KB each
**Format:** **SVG**. If the tool returns a raster, trace it to clean vector paths before saving — these sit at small sizes on both themes and must stay crisp.

Shared direction: a technical line schematic, not an illustration. Two stroke weights
only (1px hairline and 2px structural), `currentColor` so it inherits the theme's ink,
plus exactly one accent mark in `#caff01`. No fills, no characters, no mascots, no
rounded friendliness.

### 13. No operations

**Save as:** `frontend/public/media/empty-operations.svg`

```
A minimal technical line schematic, square, 480x480, as a clean SVG on a transparent
background.

Centred: an empty four-sided operational-volume outline, drawn as a 2px stroke with a
small square handle at each of its four vertices. It sits over a faint 1px square
graticule that fades out toward the edges of the frame. Just outside the polygon, a
single dashed 1px offset boundary echoes its shape.

In the upper left, a small solid triangle pointing up with a tiny letter N beside it.
In the lower right, a short scale bar: a 1px horizontal line with end ticks.

Exactly one accent: a small solid square in #caff01 at one vertex of the polygon.
Everything else is a single ink colour using currentColor so it adapts to light and dark
themes.

Only two stroke weights: 1px hairline and 2px structural. No fills except the one accent
square and the north triangle. No text beyond the single letter N. No people, no
mascots, no drones, no rounded corners, no gradients, no shadows, no colour other than
the one accent. Geometric, orthogonal, engineering-drawing in feel.
```

### 14. No dossiers

**Save as:** `frontend/public/media/empty-dossiers.svg`

```
A minimal technical line schematic, square, 480x480, as a clean SVG on a transparent
background.

Centred: three stacked rectangular document outlines in portrait proportion, slightly
offset from one another to suggest an unbound stack, drawn as 2px strokes. The topmost
sheet shows its content abstractly: four 1px horizontal rules of varying length near the
top, then a small 1px grid of three columns and four rows in its lower half, standing in
for a table. Its upper right corner is clipped at 45 degrees.

At each of the four corners of the frame, a corner registration mark: two short 2px
strokes meeting at a right angle, not touching the stack.

Exactly one accent: a small solid square in #caff01 beside the first horizontal rule on
the top sheet. Everything else is a single ink colour using currentColor so it adapts to
light and dark themes.

Only two stroke weights: 1px hairline and 2px structural. No fills except the one accent
square. No text, no lettering, no page numbers. No people, no mascots, no folders, no
rounded corners, no gradients, no shadows, no colour other than the one accent.
Geometric, orthogonal, engineering-drawing in feel.
```

### 15. No aircraft

**Save as:** `frontend/public/media/empty-fleet.svg`

```
A minimal technical line schematic, square, 480x480, as a clean SVG on a transparent
background.

Centred: an aircraft record card — a 2px rectangular outline in landscape proportion.
Inside its upper left, a small top-down quadcopter drawn in 1px strokes as pure
geometry: a square central body and four thin arms ending in circles, no propeller
detail, no shading.

Around the quadcopter, three dimension callouts in the manner of an engineering drawing:
a horizontal 1px dimension line with arrowheads at both ends spanning the full width of
the airframe, a vertical one spanning its height, and a short leader line pointing at
one rotor. Each callout terminates in a small empty rectangle where a value would be
written — all three left deliberately blank.

To the right inside the card, four 1px horizontal rules of varying length, each with a
small empty rectangle at its end, standing in for unfilled fields.

Exactly one accent: a small solid square in #caff01 at the end of the horizontal
dimension line. Everything else is a single ink colour using currentColor so it adapts
to light and dark themes.

Only two stroke weights: 1px hairline and 2px structural. No fills except the one accent
square. No text, no numbers, no units. No people, no mascots, no rounded corners, no
gradients, no shadows, no perspective, no colour other than the one accent. Geometric,
orthogonal, engineering-drawing in feel.
```

---

## 16. Social card

**Save as:** `frontend/public/media/og-default.png`
**Type:** image · **Aspect:** 1.91:1 · **Pixels:** 1200 × 630 · **Tool:** ChatGPT 2.5
**Budget:** ≤ 300 KB
**Used by:** `metadataBase` in the root layout — the Open Graph and Twitter card for every
shared link. Text must stay legible at roughly 500px wide.

```
A social share card, 1200x630, flat and perfectly head-on.

Pure black #000000 ground, edge to edge. Generous margins, nothing near the edges.

Upper left: the wordmark "SORA Copilot" in a light-weight geometric sans at around 300
weight, in near-white #eef1f3, preceded by a small solid acid lime #caff01 diamond —
a square rotated 45 degrees, about the height of the lowercase letters.

Centre left, the only large element: the chain, set as five short labels separated by
thin arrows, running horizontally in one line — iGRC → GRC → ARC → RESIDUAL ARC → SAIL.
Labels in small uppercase letter-spaced grey; arrows as thin 1px #3d464c strokes with
small heads. Beneath each of the first four labels, a tabular numeral in near-white:
5, 4, C, B. Beneath the fifth, a small square ochre #c99a3f badge containing the Roman
numeral III in near-black.

Lower left: one line of mid-grey text at a modest size — "From mission to dossier in
minutes."

Nothing else. No photograph, no map, no screenshot, no device frame, no people, no
rounded corners, no gradients, no glow, no shadows, no 3D, no border, no watermark, no
URL, no button. Flat and square. Only: #000000, #eef1f3, grey text, #3d464c, #caff01,
#c99a3f.
```

---

## After you generate them

```bash
# 1. Drop the files into frontend/public/media/ using the exact names above.
# 2. Check nothing is oversized — the budgets are in the table and in the manifest.
ls -la frontend/public/media/

# 3. Rebuild. No code change is needed; MediaSlot swaps each placeholder for its file.
cd frontend && npm run build

# 4. Confirm every slot now paints, at both widths and in both themes.
cd frontend && TOKEN=<a token> npm run smoke
```

`npm run smoke` asserts that **no media slot renders blank** — a file that fails to load
falls back to the designed placeholder rather than leaving a hole, and the check catches
either state. Append `?slots=1` to any page to overlay each slot's id and size budget
while you are placing files.

If a budget is exceeded the asset still works; the budget exists because the hero band
is the first thing a visitor downloads on a free-tier deployment.


---

## What is actually in `public/media/`

The sixteen files in the repository were not generated from the prompts above. They are
built by `frontend/scripts/make-media.mjs`, and most of them are pictures of the product
rather than illustrations of it:

```bash
# with the API on :8000 and `npx serve out -l 3002` running
TOKEN=<jwt> node scripts/make-media.mjs              # all of them
TOKEN=<jwt> node scripts/make-media.mjs --only og-default,feature-trace
```

| Asset | How it was made |
|---|---|
| `feature-trace.png` | Screenshot of the real derivation tree on the worked example, three nodes expanded, citations legible |
| `feature-map.png` | Screenshot of the wizard's map step with all three volumes derived — flight geography, contingency volume, ground risk buffer |
| `hero-poster.jpg` | Screenshot of the verdict at rest |
| `hero-loop.mp4` | Screen recording: the operations list, into a determination, then a slow pass down the trace. 12 s |
| `feature-dossier.png` | The OSO matrix page of the real generated PDF, rasterised at 160 dpi |
| `dossier-preview.png` | The derivation appendix of the same PDF — a different page, so the two slots are not one picture twice |
| `og-default.png`, `proof-logos.png`, `persona-1..3.jpg`, `feature-counterfactual.mp4` + `.jpg` | Built as HTML and rendered against the app's **own compiled stylesheet**, so the tokens, the type scale and the self-hosted Archivo and Outfit are the same objects the product uses |
| `empty-*.svg` | Hand-authored line schematics. Source, not output — `make-media.mjs` does not touch them |

Three of the prompts above were **not** used, and the reason is the same each time:

- **The three segment cards.** The manifest asked for photographs of people. A
  photograph of a "customer" who does not exist is a fabricated endorsement, and the copy
  beside each one describes a segment — "Inspection company, Graz." — rather than quoting
  a person, so there is nobody to depict. They show what each segment brings to the
  product instead: the inputs a roof surveyor types, the inputs a corridor operator
  types, and the trace a compliance officer reads. Inputs and a justification, never a
  computed class, so no card can be read as a determination the engine did not make.
- **The framework row.** Regulation names set as type, never a reproduction of an
  authority's logo — which would read as endorsement directly beside a line saying none
  is implied.
- **The counterfactual loop.** A diagram rather than a screen recording, because the
  advisor is a paid feature that answers 402 on the free plan: a capture would be a
  picture of an upgrade panel. It is drawn with the app's own tokens and the real SAIL
  ramp, and shows the mechanism — one input changes, the engine re-derives, the SAIL
  plate steps.

The prompts stay in this document because they are still the right brief for a
replacement. If you generate one, keep the path and the pixel size and the test will
confirm it landed.
