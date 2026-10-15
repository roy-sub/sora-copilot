import type { Config } from "tailwindcss";

/**
 * SORA Copilot — Tailwind theme extension.
 *
 * Mirrors tokens.css exactly. Every value references the CSS custom property so
 * the two representations cannot drift: tokens.css is the single source of truth,
 * this file is the Tailwind surface over it. Raw hexes appear only in `brand`,
 * which is theme-invariant by definition.
 *
 * Theme switch: `data-theme` on <html>. Dark is default (:root), light is the
 * derived override. The page ground is black in BOTH themes — only the sheets flip.
 */
const config: Partial<Config> = {
  darkMode: ["variant", '&:where([data-theme="dark"], [data-theme="dark"] *)'],
  theme: {
    extend: {
      colors: {
        // theme-invariant brand base (Dronex, inherited in full)
        brand: {
          black: "#000000",
          paper: "#f5f5f5",
          concrete: "#d9d9d9",
          lime: "#caff01",
          "lime-press": "#b2e200",
          "lime-tint": "#eaffa3",
        },
        // structural surfaces — flip with data-theme
        ground: "var(--ground)",
        sheet: {
          DEFAULT: "var(--sheet)",
          raised: "var(--sheet-raised)",
          well: "var(--sheet-well)",
          alt: "var(--sheet-alt)",
        },
        hairline: {
          DEFAULT: "var(--hairline)",
          strong: "var(--hairline-strong)",
        },
        ink: {
          hi: "var(--text-hi)",
          mid: "var(--text-mid)",
          low: "var(--text-low)",
          "on-accent": "var(--text-on-accent)",
        },
        field: {
          DEFAULT: "var(--field-bg)",
          border: "var(--field-border)",
          "border-hover": "var(--field-border-hover)",
        },
        accent: {
          DEFAULT: "var(--accent)",
          press: "var(--accent-press)",
          ink: "var(--accent-ink)",
          wash: "var(--accent-wash)",
          line: "var(--accent-line)",
        },
        // SAIL risk ramp I-VI. Never used as colour alone — see SailBadge.
        sail: {
          1: "var(--sail-1)",
          2: "var(--sail-2)",
          3: "var(--sail-3)",
          4: "var(--sail-4)",
          5: "var(--sail-5)",
          6: "var(--sail-6)",
          "1-ink": "var(--sail-1-ink)",
          "2-ink": "var(--sail-2-ink)",
          "3-ink": "var(--sail-3-ink)",
          "4-ink": "var(--sail-4-ink)",
          "5-ink": "var(--sail-5-ink)",
          "6-ink": "var(--sail-6-ink)",
        },
        // ARC band a-d. A different axis from SAIL, so a different ramp.
        arc: {
          a: "var(--arc-a)",
          b: "var(--arc-b)",
          c: "var(--arc-c)",
          d: "var(--arc-d)",
        },
        warn: "var(--warn)",
        fail: "var(--fail)",
        scrim: "var(--scrim)",
      },

      spacing: {
        sheet: "var(--gap-sheet)", // 2px — the ground showing through
        1: "var(--space-1)",
        2: "var(--space-2)",
        3: "var(--space-3)",
        4: "var(--space-4)",
        5: "var(--space-5)",
        6: "var(--space-6)",
        8: "var(--space-8)",
        10: "var(--space-10)",
        12: "var(--space-12)",
        16: "var(--space-16)",
        24: "var(--space-24)",
        touch: "var(--touch-min)",
        rail: "var(--rail-w)",
        "rail-collapsed": "var(--rail-w-collapsed)",
      },

      borderRadius: {
        none: "var(--radius-0)",
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        pill: "var(--radius-pill)",
      },

      boxShadow: {
        card: "var(--shadow-card)", // none, on purpose
        overlay: "var(--shadow-overlay)",
      },

      maxWidth: {
        content: "var(--content-max)",
        measure: "var(--measure)",
      },

      fontFamily: {
        sans: ["Archivo", "Helvetica Neue", "Arial", "sans-serif"],
        wordmark: ["Outfit", "Archivo", "sans-serif"],
      },

      // [size, { lineHeight, letterSpacing, fontWeight }]
      fontSize: {
        display: ["60px", { lineHeight: "1.04", letterSpacing: "-0.025em", fontWeight: "600" }],
        "display-sm": ["36px", { lineHeight: "1.08", letterSpacing: "-0.02em", fontWeight: "600" }],
        h1: ["32px", { lineHeight: "1.12", letterSpacing: "-0.02em", fontWeight: "600" }],
        h2: ["24px", { lineHeight: "1.2", letterSpacing: "-0.015em", fontWeight: "600" }],
        h3: ["18px", { lineHeight: "1.3", letterSpacing: "-0.01em", fontWeight: "600" }],
        h4: ["15px", { lineHeight: "1.35", letterSpacing: "0em", fontWeight: "600" }],
        "body-lg": ["18px", { lineHeight: "1.6" }],
        body: ["15px", { lineHeight: "1.55" }],
        "body-sm": ["13px", { lineHeight: "1.5" }],
        label: ["12px", { lineHeight: "1.3", letterSpacing: "0.1em", fontWeight: "600" }],
        micro: ["11px", { lineHeight: "1.25", letterSpacing: "0.1em", fontWeight: "600" }],
        data: ["14px", { lineHeight: "1.4", fontWeight: "500" }],
        "data-sm": ["12px", { lineHeight: "1.4", fontWeight: "500" }],
        figure: ["72px", { lineHeight: "1", letterSpacing: "-0.03em", fontWeight: "700" }],
        wordmark: ["112px", { lineHeight: "0.9", letterSpacing: "-0.035em", fontWeight: "300" }],
      },

      transitionTimingFunction: {
        ui: "cubic-bezier(0.22,0.61,0.36,1)",
        exit: "cubic-bezier(0.4,0,1,1)",
        instrument: "cubic-bezier(0.16,1,0.3,1)",
      },

      transitionDuration: {
        tap: "90ms",
        ui: "160ms",
        panel: "240ms",
        media: "420ms",
        compute: "1200ms",
      },

      keyframes: {
        "edge-draw": {
          from: { strokeDashoffset: "var(--edge-len, 240)" },
          to: { strokeDashoffset: "0" },
        },
        "node-settle": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "none" },
        },
        "volume-extrude": {
          from: { transform: "scale(0.82)", opacity: "0" },
          to: { transform: "scale(1)", opacity: "1" },
        },
        "chain-link": {
          from: { opacity: "0", transform: "translateX(-6px)" },
          to: { opacity: "1", transform: "none" },
        },
        "stage-tick": {
          from: { opacity: "0.35" },
          to: { opacity: "1" },
        },
      },

      animation: {
        "edge-draw": "edge-draw var(--t-compute) var(--ease-instrument) both",
        "node-settle": "node-settle var(--t-panel) var(--ease-ui) both",
        "volume-extrude": "volume-extrude var(--t-media) var(--ease-instrument) both",
        "chain-link": "chain-link var(--t-panel) var(--ease-ui) both",
        "stage-tick": "stage-tick var(--t-ui) var(--ease-ui) both",
      },
    },
  },
};

export default config;
