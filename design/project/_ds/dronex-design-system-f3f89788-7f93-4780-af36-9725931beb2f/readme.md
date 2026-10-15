# Dronex Design System

Dronex is an agri-tech brand selling **precision drone systems to farms** —
survey and mapping, seeding and spreading, variable-rate spraying. The design
language is editorial and industrial: black page ground, off-white paper
sheets butted together with 2px hairline gaps, one acid-lime accent, large
daylight photography of fields and machinery, and a very light geometric
wordmark set against a tight grotesque for everything else.

## Sources

Everything in this system was derived from two flat images supplied by the
user, both credited in-image to **Maryna Vozniuk, "Landing page 2026"**:

- `uploads/r1.jpeg` — desktop landing page (hero stat band, wordmark band,
  full-bleed drone image, black footer).
- `uploads/r2.jpeg` — mobile columns and secondary sections (hero with lime
  arrow badge, editorial card, lime "Performance" band, "Precision" product
  section, carousel).

**No codebase, Figma file, repository, or font binaries were provided.** Every
token, component and screen here is reconstructed from those two 736×920px
JPEGs. Colour values were sampled pixel-exact; type sizes, paddings and
heights are proportional reconstructions, not measured source values. If a
Figma file or front-end codebase exists, wire it up and re-derive — this
system should be replaced by measured values, not extended on top of guesses.

### Substitutions (flagged — please confirm or replace)

| Thing | Source shows | Shipped here |
| --- | --- | --- |
| Headline / UI face | A tight neo-grotesque (Helvetica Now / Aeonik family of shapes) | **Archivo** from Google Fonts |
| Wordmark face | A light geometric sans, near-circular bowls | **Outfit Light (300)** from Google Fonts |
| Icon set | Thin 2px-stroke arrows, hamburger, Instagram / Telegram / Facebook glyphs | **Lucide** (`lucide-static@0.544.0`) via CDN mask |
| Imagery | Full-resolution agricultural photography | Upscaled crops of the 736px mockups |
| Logo | Quadcopter mark with lime crosshair | Extracted from the mockup at 396px (`assets/logo-mark.png`) — a vector original is needed |

Fonts load from the Google Fonts CDN via `tokens/fonts.css`; no binaries are
vendored in this project. Send the real licensed files (or confirm the
substitutes) and the swap is a two-line change.

---

## Index

| Path | What it is |
| --- | --- |
| `styles.css` | The one file consumers link — `@import`s every token file |
| `tokens/` | `fonts.css`, `colors.css`, `typography.css`, `spacing.css`, `radius.css`, `borders.css`, `effects.css`, `motion.css` |
| `components/core/` | `Button`, `Tag`, `IconBadge`, `Icon`, `Logo` |
| `components/content/` | `StatCard`, `MediaFrame`, `ContentCard` |
| `components/forms/` | `Input`, `NewsletterForm` |
| `components/navigation/` | `SiteHeader`, `SiteFooter`, `CarouselNav` |
| `ui_kits/dronex-site/` | Click-through recreation of the marketing site (home, drones, about, mobile) |
| `guidelines/*.card.html` | Foundation specimen cards shown in the Design System tab |
| `assets/` | `logo-mark.png`, `logo-mark-inverse.png`, `logo-lockup.png`, `imagery/` |
| `thumbnail.html` | Project tile |
| `SKILL.md` | Agent-Skills entry point |

### Components

`Button`, `Tag`, `IconBadge`, `Icon`, `Logo`, `StatCard`, `MediaFrame`,
`ContentCard`, `Input`, `NewsletterForm`, `SiteHeader`, `SiteFooter`,
`CarouselNav`. Each has a sibling `.d.ts` (props) and `.prompt.md` (what/when
+ usage), and each directory carries a `*.card.html` specimen.

**Intentional additions** — families the mockups imply but never show as a
discrete part:

- `Icon` — a glyph wrapper, needed because the mockups use icons (arrows,
  hamburger, socials) but ship no icon set.
- `ContentCard` — the tag + headline + copy + CTA sheet appears four times
  across the mockups; factoring it keeps screens honest.
- `Input` — extracted from the newsletter field so forms beyond the newsletter
  have a sanctioned treatment.

Nothing else was invented: there is **no** Toast, Avatar, Tabs, Dialog,
Tooltip, Switch or Select in this system, because the source defines none.
Ask before adding one.

---

## CONTENT FUNDAMENTALS

**Voice.** Plain agricultural-trade English, written for a farm operator, not
a venture audience. Claims are operational ("consistent coverage and accurate
delivery"), not visionary. No exclamation marks anywhere in the source.

**Person.** "We" for the company, "farmers"/"your fields" for the reader —
third-person plural for the audience in body copy ("give farmers full control
over their fields"), second person only when addressing them directly in a
form or CTA ("Your email"). Never "I".

**Casing.** Three registers, strictly separated:
- Headlines — sentence case, with a colon as the one permitted bit of
  punctuation flourish: *"Seed and Spread Smarter: Precision Drones for Field
  Operations"*. Note the title-case drift in that headline; both appear in
  the source, sentence case dominates: *"Driving the evolution of agriculture
  with advanced drone systems"*.
- Labels, nav, buttons, tags, field placeholders — ALL CAPS, 0.1em tracked:
  `HOME`, `DRONES`, `ABOUT US`, `DASHBOARD`, `SEED SMARTER`, `GROW MORE`,
  `DISCOVER DRONEX`, `PRECISION`, `PERFORMANCE`, `YOUR EMAIL`, `SUBSCRIBE`.
- Body — sentence case, 2–5 lines, one idea per paragraph.

**Headline construction.** Two-beat compound statements, often a period
mid-line for rhythm: *"Smarter spreading. Better yields"*. Comparatives do the
work ("smarter", "better", "measurable"). Length runs 3–10 words for heroes,
up to 11 for section headers that wrap to 3–4 tight lines.

**Body construction.** Opens with what the product does, ends with the
operational payoff: *"From real-time crop monitoring to precision spraying,
our solutions increase productivity while reducing resource waste and
operational costs."* Em-dashes appear as tight `—` joins in product copy
("accurate delivery—built for modern, high-efficiency farming").

**Numbers.** Figures are stated bare and large with a plain noun label
underneath: `10+` / "Years of Expertise", `85%` / "Client Satisfaction". The
supporting sentence always says *why the number is credible* ("Trusted by
farmers for reliable performance…"), never restates it.

**Emoji: never.** Not in UI, not in copy. The brand's only expressive mark is
the lime crosshair in the logo.

**Vibe.** Confident, unhurried, slightly cold — a machinery catalogue with an
art director. Avoid startup vocabulary (no "revolutionary", "AI-powered",
"game-changing"), avoid hedging, avoid questions as headlines.

---

## VISUAL FOUNDATIONS

**Ground and sheets.** The page itself is black (`--black`). Content sits on
off-white **sheets** (`--paper`, #F5F5F5) that butt against each other with a
**2px gap** (`--gap-sheet`), so the black ground reads as hairline rules
between panels. This is the system's structural signature — not cards
floating in space, but a grid of sheets with the ground showing through.

**Colour.** Four values total: black `#000000`, paper `#F5F5F5`, concrete grey
`#D9D9D9`, acid lime `#CAFF01`. Lime is an accent of last resort — **one lime
element per view** (one stat column, or one CTA, or one band). Type on lime is
always black; type on black is paper (headings) and 45% paper (secondary).
There are no brand gradients, no secondary hues, no tinted neutrals.

**Type.** Geometric light wordmark (Outfit 300, −0.035em, 112px at hero scale)
versus tight grotesque for everything else (Archivo 600 headlines at leading
1.02 and −0.025em tracking; Archivo 400 body at 16/1.5 in 64% ink; 11px caps
at 0.1em for every label). Headlines wrap to 3–4 lines on purpose — do not
balance them to one line. Figures are Archivo 700 at 56px.

**Spacing.** 4px base; the live values are 2 (sheet gaps), 24–32 (card
padding), 48 (page margins), 64–96 (section rhythm). Stat columns hold a
deliberate empty middle: figure and label at the top, body copy pinned to the
bottom edge.

**Backgrounds.** Flat colour only. No patterns, no textures, no noise, no
illustration, no hand-drawn marks, no gradient fills. Photography is used
full-bleed (hero) or sheet-contained, never as a tinted or blurred backdrop
behind text.

**Imagery.** Real daylight agricultural photography — fields, crops, a combine
harvester, hands on a controller, drones in flight. Warm golden-hour crop
tones against cool blue-grey sky; natural contrast, no filter, no grain, no
duotone, no b&w. People are shown working, mid-task, never posed to camera.
Filter in code is a near-neutral `saturate(.95) contrast(1.02)`.

**Crop marks.** The house motif: short 18×2px dashes inset 12px at the corners
of an image frame (top two corners on sheet images, all four on full-bleed
heroes). Paper-coloured over photography, ink over light images. They are the
one decorative element in the system — use them instead of borders on media.

**Corner radii.** Only three: `0` for sheets, stat columns and the lime block
CTA; `10px` for contained media and mobile cards; full pill (999px) for
buttons, tags, fields and circular badges. Nothing uses 4/6/8px.

**Cards.** A card is a square-cornered paper or concrete sheet with 24–32px
padding, **no border and no shadow**. Mobile cards soften to 10px. Separation
comes from the 2px black gap, never from elevation.

**Shadows.** None. `--shadow-card: none` is a real token, stated so nobody
adds one. The only sanctioned non-flat effect is `--shadow-float`, reserved
for a chip that must float over photography — currently unused.

**Transparency and blur.** Used almost nowhere. Ink and paper tints
(`--ink-64`, `--paper-45`) handle text hierarchy; `--blur-chip` exists for a
glass chip over imagery but the source never does it. Don't introduce frosted
panels.

**Protection.** Type over photography gets a gradient scrim
(`--scrim-bottom` / `--scrim-left`) rather than a capsule — except where the
photo is already bright and the type is black, as in "Smarter spreading.
Better yields", which sits unprotected on open sky. Capsules (pill buttons on
photos) are white, fully opaque.

**Buttons and states.** Hairline outline pills (12% ink) for secondary
actions; a white pill with a black circular mark badge for "DISCOVER DRONEX";
solid lime pill for submit; square lime block for the one primary CTA under a
headline. Hover = value shift only (lime darkens to `#B2E200`, outline gains a
6% ink wash and a 20% border); press = `scale(0.98)`. No lift, no glow, no
colour change on press. Disabled drops to 35% opacity.

**Animation.** Restrained: 120ms for control states, 200ms for UI, 420ms for a
media zoom (`scale(1.03)` on hover), all on
`cubic-bezier(.22,.61,.36,1)` / `cubic-bezier(.16,1,.3,1)`. No bounce, no
spring, no entrance choreography, no parallax.

**Layout rules.** Max content width 1240px. Desktop hero is a 3-column sheet
band (photo ≈1.5fr, two stat columns 1fr each) about 430px tall; the wordmark
band below it is a full-width paper sheet ~184px tall with the lockup left and
two outline pills right. The black footer always closes the page. Mobile is a
single 390px column of stacked full-width sheets with 20px side margins; the
lime arrow badge is the only element allowed to break a frame edge
(overlapping the top-right corner of the mobile hero).

---

## ICONOGRAPHY

The source ships **no icon font, no sprite sheet and no SVG set** — the
mockups contain exactly five glyph shapes: a diagonal arrow (↘) in the lime
badge, left/right carousel arrows, a hamburger (two rules), and the three
social marks in the footer (Instagram, Telegram, Facebook).

- **Substitute set (flagged): Lucide** `lucide-static@0.544.0`, loaded from
  unpkg as a CSS `mask-image` so glyphs inherit `currentColor`. Lucide's 2px
  stroke and square-ish caps are the closest free match to the thin arrows in
  the mockups. Wrapped by `components/core/Icon.jsx`.
- **Sizes.** 14px inside buttons, 18–22px in nav and social chips, 21px in a
  46–56px lime badge (glyph ≈45% of the circle).
- **Colour.** Monochrome always — black on paper/lime, paper on black. Icons
  are never lime themselves; the lime is the circle behind them.
- **Shape.** Icons appear either bare (nav hamburger, inline button arrows) or
  centred in a circular badge (`IconBadge`): lime for the hero arrow, white for
  footer socials, hairline outline for carousel arrows.
- **Brand marks.** The only non-Lucide glyph is the Dronex quadcopter mark
  (`assets/logo-mark.png` / `-inverse.png`), used at 13–18px beside the
  wordmark, 22–28px in headers, 58px+ in hero lockups, and inside the black
  badge on "DISCOVER DRONEX" buttons.
- **Emoji and unicode glyphs: never used.** The arrows in the source are drawn
  icons, not `→` characters; keep them as icons.

If the real brand owns an icon set, replace Lucide and this section — the
substitution is the largest single approximation in this system after the
fonts.
