# SORA Copilot

Decision support for European drone operators: describe the operation, the rules engine computes iGRC → GRC → ARC → residual ARC → SAIL and the OSO set, and every line cites its rule.

> SORA Copilot prepares and verifies your risk assessment. Your national aviation authority grants the authorisation.

## Stack

Next.js 15 (App Router, static export) · Tailwind CSS v4 · Radix primitives (shadcn-style) · Framer Motion · TypeScript.

```bash
npm install
npm run dev     # http://localhost:3000
npm test        # engine tests (node:test)
npm run build   # static export to out/
```

## Layout

| Path | What |
|---|---|
| `src/engine/` | Pure, deterministic SORA 2.5 engine (`engine.ts`), rulebase tables (`rulebase.ts`), category checker, map geometry, tests |
| `src/data/` | Demo workspace fixtures, OSO reference text, map scene |
| `src/styles/tokens.css` | Design tokens — single source of truth; `src/app/globals.css` maps them into Tailwind |
| `src/components/` | SailBadge, MediaSlot, verdict (derivation tree, chain, gap analysis, OSO drawer), wizard, UI primitives |
| `src/app/` | Routes: marketing (`/`, `/pricing`, `/checker`, `/legal`), `/signin`, product under `/app` |
| `design/` | Claude Design handoff bundle (prototype, tokens, component/motion/media specs, chat transcript) |

## Rulebase — verify before production

`src/engine/rulebase.ts` holds the SORA 2.5 tables (iGRC Table 2, mitigations Table 5, ARC tree, SAIL Table 7, OSO Table 14). They were transcribed for this build and **must be checked line by line against the published JARUS SORA 2.5 text and the national annex** by a competent reviewer. Containment (Step 9) is flagged as requiring assessment, not computed.

## Status

Built: marketing site, checker, sign-in, operations dashboard, fleet, verdict (tree, chain, counterfactuals, gap analysis, OSO drawer + evidence).
In progress: intake wizard (map step components exist), conversational intake, dossier builder, settings, system states/overlays, 404/500.

Static export has no backend: workspace changes persist to `localStorage` on the device.
