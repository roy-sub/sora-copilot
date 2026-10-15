# # SORA Copilot Design System

**Three clarifying questions:**

1. **SAIL badge visual language**: Should the SAIL I

_Started 2026-10-14 19:11 UTC_

---

## User

You are the design lead for SORA Copilot, a European aviation-compliance web app for
professional drone operators. The full brief is in the attached SORA Design Brief.md.
Read it completely before you make a single visual decision.

WHAT I NEED FROM YOU

A complete, opinionated visual system plus high-fidelity screens, built so that an
engineer can implement it in Next.js + Tailwind + shadcn/ui + Framer Motion without
guessing at a single value.

Work in two passes.

PASS 1 — the plan. Before designing anything, write me a compact design plan:
  - Palette: 6-8 named hex values with the role of each. Dark-first; a light theme is a
    derived secondary, not an afterthought.
  - Typography: one or two families only, from Google Fonts, with a full type scale
    (size / weight / line-height / tracking per role). Justify why these faces belong to
    this subject matter specifically.
  - Layout: the page/app grid, spacing scale, radius scale, elevation model, and how
    the marketing site and the authenticated product relate to each other visually.
  - Motion: the easing curves, durations, and the ONE orchestrated moment per screen
    that is allowed to be showy. Everything else is functional feedback.
  - Principles: 5 lines on what makes this look like a flight-deck instrument and not a
    generic SaaS dashboard.
Then critique your own plan against the brief and revise anything that reads like a
default you would have produced for any B2B SaaS. Tell me what you changed and why.
Stop there and show me the plan. I will approve it before you build.

PASS 2 — the screens. After I approve, produce every screen listed in section 6 of the
brief at desktop (1440) and mobile (390), in both dark and light theme, in a real
interactive form (working HTML/CSS, not flat mockups) so I can click through it.

NON-NEGOTIABLE CONSTRAINTS

1. Implementable. Every color, size, radius, shadow and duration must come from a named
   token. Output the tokens as (a) a CSS custom-property block on :root and
   [data-theme="light"], and (b) a tailwind.config.ts theme extension. Both must agree.
2. No invented data patterns. Use the exact domain vocabulary from the brief — iGRC, GRC,
   ARC, SAIL I-VI, OSO, TMPR, containment. Never simplify it to "score" or "level".
   The SAIL badge and the derivation tree are the identity of this product.
3. Media is deferred. I will add real photos and video myself, later. Wherever media
   belongs, design a MediaSlot: correct aspect ratio, a designed placeholder state that
   looks intentional (not a grey box with a camera icon), and a note of the exact asset
   spec. List every slot in a manifest table at the end: slot id, page, aspect ratio,
   intrinsic size, whether it is image or video, and what the asset should depict.
4. Accessibility floor, unannounced: AA contrast everywhere, visible keyboard focus
   rings on every interactive element, prefers-reduced-motion honoured, 44px minimum
   touch targets, and never colour alone to carry meaning (the SAIL scale needs a shape
   or label difference too).
5. Copy is yours to write. The brief gives voice and a few fixed strings; write the rest.
   Sentence case, active voice, no filler, no exclamation marks. This audience is
   professional pilots and compliance officers — they want precision, not enthusiasm.

DELIVERABLES, in this order
  A. design-plan.md — the approved pass-1 plan.
  B. tokens.css and tailwind.theme.ts — the token system, both representations.
  C. The interactive screens.
  D. components.md — every component you invented, with its variants, states
     (default / hover / focus / active / disabled / loading / empty / error), and the
     props an engineer would need.
  E. media-manifest.md — the MediaSlot table from constraint 3.
  F. motion.md — named animation presets with duration, easing, and trigger.

Ask me at most three clarifying questions before Pass 1. If something is genuinely
ambiguous, choose the more opinionated option and note the choice rather than stalling.

## Assistant



## Assistant

I'll read the brief first.

_[tool: read_file]_

Brief read. The project has the **Dronex** system attached (black/paper sheets, acid lime, Archivo) — which collides head-on with your brief's explicit "no near-black-plus-one-acid-accent" and its instrument direction. I've resolved that in the plan and made it question 1.

_[tool: set_project_title]_

_[tool: write_file]_

_[tool: show_to_user]_

_[tool: ask_user]_

Plan's up in `design-plan.md` — palette (greenless SAIL ramp designed first), IBM Plex superfamily with a mono-means-machine-derived rule, four-level ink material logic, motion budget per screen, and a self-critique section listing the six SaaS defaults I killed and why.

Waiting on your three answers before I build tokens and screens.

## User

Answered — dronex: Full inheritance — lime accent and all; the brief's palette direction yields; map: Designed vector chart surface drawn in-page — no tiles, no network, full control of the ED-269 / density / volume layers (my recommendation); sequence: All screens in one delivery at uniform fidelity

## Assistant

Full Dronex inheritance changes the palette and type foundations — revising the plan, then building everything in one delivery.

_[tool: list_files]_

_[tool: read_file]_

_[tool: read_file]_

_[tool: write_file]_

_[tool: write_file]_

_[tool: write_file]_

Now the build. Shell + landing first.

_[tool: dc_write]_

_[tool: dc_write]_

_[tool: dc_write]_

_[tool: dc_html_str_replace]_

_[tool: dc_js_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: show_html]_

_[tool: get_webview_logs]_

_[tool: show_html]_

_[tool: eval_js]_

_[tool: dc_js_str_replace]_

_[tool: dc_js_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_js_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: get_webview_logs]_

_[tool: dc_js_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: get_webview_logs]_

_[tool: multi_screenshot]_

_[tool: eval_js]_

_[tool: grep]_

_[tool: eval_js]_

_[tool: run_script]_

_[tool: eval_js]_

_[tool: run_script]_

_[tool: eval_js]_

_[tool: eval_js]_

_[tool: eval_js]_

_[tool: dc_html_str_replace]_

_[tool: eval_js]_

_[tool: read_file]_

_[tool: show_html]_

_[tool: sleep]_

_[tool: eval_js]_

_[tool: dc_html_str_replace]_

Now the remaining documentation deliverables.

_[tool: write_file]_

_[tool: write_file]_

_[tool: write_file]_

_[tool: ready_for_verification]_

Pass 2 is in, all sixteen screen areas in one clickable file. Use the toolbar to switch screen, 1440/390, dark/light, and slot ids.

**Deliverables:** `design-plan.md` (revised for full Dronex inheritance) · `tokens.css` + `tailwind.theme.ts` · `SORA Copilot.dc.html` (+ `SailBadge.dc.html`, `MediaSlot.dc.html`) · `components.md` · `media-manifest.md` · `motion.md`.

Three things worth your judgement:

- **Lime now carries interactive affordance**, held to one primary action per view. The brief warned against near-black-plus-acid; if it reads that way to you, swapping `--accent` to a cold cyan is a two-line change and the system holds.
- **No monospace.** Dronex ships none and the brief forbids decorative mono, so the machine-derived register is marked structurally — recessed well, caps micro-label, Archivo 500 `tnum`.
- **The ground is black in both themes**; only the sheets flip. Light theme is literally Dronex as shipped.

## User

Found issues — fixing…

## User

Found issues — fixing…

## User

Found issues — fixing…

## User

Found issues — fixing…

## Assistant

Let me look at the actual render and find what's broken.

_[tool: show_html]_

_[tool: get_webview_logs]_

_[tool: show_html]_

_[tool: sleep]_

_[tool: save_screenshot]_

_[tool: save_screenshot]_

Rendering is sound; the defects are text wrapping in narrow chrome, the verdict column split, and the screen `<select>` not reflecting state. Checking that last one:

_[tool: eval_js]_

Select is correctly bound — that was a screenshot artifact. Fixing the real defects: text wrapping in the chrome, the overlapping area readout, and the verdict column split starving the derivation tree.

_[tool: dc_html_str_replace]_

_[tool: run_script]_

_[tool: save_screenshot]_

Preview is stale — reloading to pick up the edits.

_[tool: show_html]_

_[tool: save_screenshot]_

_[tool: eval_js]_

_[tool: eval_js]_

All layers are present — the missing outlines were a screenshot-renderer artifact. Two real fixes left:

_[tool: run_script]_

_[tool: show_html]_

_[tool: save_screenshot]_

Desktop is clean now, but the mobile breakpoint has a real break — the operations table keeps its 6-column grid at 390 and the cells collide. Fixing the mobile layouts:

_[tool: dc_js_str_replace]_

_[tool: dc_js_str_replace]_

_[tool: dc_js_str_replace]_

Now rewiring the markup to use those computed layouts:

_[tool: run_script]_

_[tool: show_html]_

_[tool: save_screenshot]_

Mobile layouts are correct now. One last thing — the marketing nav wraps awkwardly at 390:

_[tool: run_script]_

_[tool: grep]_

The landing CTA is now a Dronex `Button` via `x-import` — a direct edit I need to keep working. Checking the bundle is actually loaded:

_[tool: list_files]_

_[tool: eval_js]_

Global is loaded and the import resolved. Reloading to confirm the landing header renders at both widths:

_[tool: show_html]_

_[tool: save_screenshot]_

Two refinements: the mobile hero should drop to the 36px display size from the plan, and the scrolling nav shouldn't show a track.

_[tool: dc_js_str_replace]_

_[tool: run_script]_

_[tool: show_html]_

_[tool: save_screenshot]_

Fixed and verified across breakpoints and themes. Handing off:

_[tool: ready_for_verification]_

Fixed what the review turned up:

**Desktop** — wordmarks, rail nav labels and the toolbar stamp no longer wrap; the verdict split is now fluid-left / 420px-right so the derivation tree gets real width instead of a 50/50 squeeze; area readout values hold one line.

**Mobile (390)** — the genuine break. The operations table was keeping its six-column grid and collapsing cells on top of each other; it's now a stacked card per row (name, site, SAIL badge + status, rulebase/run line) with the header row dropped. Also: risk chain goes 2-up, gap analysis to single column, the wizard stepper scrolls instead of stacking into three rows, the marketing nav scrolls on one line, and the hero drops to the 36px display size the plan specified.

Two things that looked like bugs and weren't: the screen `<select>` showing "1 · Landing" and the map's buffer outlines vanishing are both artifacts of the screenshot renderer — I probed the DOM and the binding and all five map layers are correct.

Your edit swapping the landing CTA to the Dronex `Button` is preserved and resolving against the loaded bundle.

