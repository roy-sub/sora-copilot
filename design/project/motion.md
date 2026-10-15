# SORA Copilot — motion

Two rules govern everything here.

1. **One orchestrated moment per screen.** Everything else is functional feedback on an
   action the operator took.
2. **`prefers-reduced-motion: reduce` collapses all durations to 1ms** and renders every
   animated element in its final state. No information exists only in motion. This is
   enforced globally in `tokens.css`, not per component.

## Easing

| Token | Curve | Use |
|---|---|---|
| `--ease-ui` | `cubic-bezier(.22,.61,.36,1)` | Entry and state change. Inherited from Dronex. |
| `--ease-exit` | `cubic-bezier(.4,0,1,1)` | Anything leaving the screen. |
| `--ease-instrument` | `cubic-bezier(.16,1,.3,1)` | Computation and physical volume only. Long tail, no overshoot — it reads as something settling into a measured position. |

Nothing in this system bounces, springs or overshoots.

## Duration

| Token | ms | Use |
|---|---|---|
| `--t-tap` | 90 | Press, checkbox, radio, toggle, segmented control |
| `--t-ui` | 160 | Hover, focus, colour and border transitions |
| `--t-panel` | 240 | Accordion, drawer, step change, chip state |
| `--t-media` | 420 | Map volume extrude, media zoom |
| `--t-compute` | 1200 | Derivation tree, total staged budget |

## Named presets

| Preset | Duration · easing | Trigger | Notes |
|---|---|---|---|
| `tap-press` | 90 · `--ease-ui` | `:active` on any control | `scale(.98)`. No lift, no glow, no colour change. |
| `state-shift` | 160 · `--ease-ui` | hover / focus | Value shift only: `--accent` → `--accent-press`, or a `--sheet-raised` wash. |
| `panel-expand` | 240 · `--ease-ui` | accordion, derivation node, FAQ | `max-height` + `opacity` + `padding`. Chevron rotates in the same tick. |
| `step-advance` | 240 · `--ease-ui` | wizard Continue / Back | Outgoing step translates 12px in the travel direction and fades; stepper tick fills. |
| `drawer-in` / `drawer-out` | 240 · `--ease-ui` / `--ease-exit` | OSO drawer, mobile map sheet | X on desktop, Y on mobile. Scrim cross-fades at 160. |
| `toast-in` | 240 · `--ease-ui` | toast enqueued | Translate 8px up + fade. Exit on `--ease-exit`. Auto-dismiss 6000ms, paused on hover or focus, never for failures. |
| `chain-link` | 240 · `--ease-ui`, 90ms stagger | landing hero on load; verdict chain on first paint | Five cells assemble left→right. Once per page load. |
| `volume-extrude` | 420 · `--ease-instrument`, 120ms stagger | map step derive | Flight geography, then contingency, then ground risk buffer scale `.8 → 1` outward from the drawn geometry. |
| `media-zoom` | 420 · `--ease-instrument` | hover on a loaded MediaSlot | `scale(1.03)`, overflow clipped. Marketing only. |
| `edge-draw` | 520 · `--ease-instrument`, 60ms stagger | verdict mount, REPLAY, counterfactual re-run | `stroke-dashoffset` from the edge length to 0, leaves → root. |
| `node-settle` | 240 · `--ease-ui`, 40ms behind its incoming edge | same | `translateY(4px)` + fade. |
| `figure-count` | 900 · `--ease-instrument` | verdict only, once | The SAIL numeral and the chain figures count up a single time per determination. Never repeated, never on a list. |
| `sail-step` | 180 per level · `--ease-ui` | counterfactual applied | The badge steps one plate at a time (IV → III → II): fill, segments and plate geometry change together at each step so the shape encoding stays in sync. |
| `stage-tick` | 160 · `--ease-ui`, sequential | ComputationProgress | A stage resolves from 35% to full opacity as it completes. The running stage's accent band does not pulse. |

## The verdict sequence, in full

This is the only showy moment in the product, and it is a computation completing rather
than a decoration animating. Total 1200ms.

```
  0ms   canvas present, nodes at opacity 0
  0ms   edge-draw begins at the five fact leaves        (60ms stagger)
 60ms   fact nodes settle, each 40ms behind its edge
420ms   edges to iGRC and ARC draw
460ms   iGRC and ARC nodes settle, values already final
640ms   edges to GRC and residual ARC draw
700ms   those nodes settle
760ms   the two accent edges to SAIL draw               (60ms apart)
1020ms  the root plate settles; the SailBadge resolves
1020ms  figure-count runs, once
```

Replay is an explicit control, not a scroll trigger. Re-running after a counterfactual
replays the sequence with the changed branch marked by a 2px accent left band on the
affected nodes.

## Forbidden

Parallax · spring and bounce curves · entrance choreography on scroll · skeleton shimmer
(use static stepped-opacity blocks) · spinners where a staged progress is possible ·
looping ambient motion · animated page transitions between app routes.
