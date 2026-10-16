/**
 * The designed assets — the ones that are graphics rather than screenshots.
 *
 * They are built as HTML and rendered by the real browser against the app's own
 * compiled stylesheet, so the tokens, the type scale and the self-hosted Archivo and
 * Outfit are the same objects the product uses. A hand-made PNG drifts from the brand
 * the first time a token changes; this cannot.
 *
 * Each entry returns markup for a box of exactly its manifest size. `make-media.mjs`
 * screenshots that box at 2x and resizes down.
 */

/** The SAIL ramp, dark theme, from src/styles/tokens.css. Greenless by construction. */
const SAIL = ["#8a95a1", "#a79b93", "#c99a3f", "#dd7f31", "#d4502f", "#b82633"];

const CHAIN = ["iGRC", "GRC", "ARC", "SAIL"];

/** The frameworks the engine actually implements. Regulations, not authority logos. */
const FRAMEWORKS = [
  "Regulation (EU) 2019/947",
  "Regulation (EU) 2019/945",
  "JARUS SORA 2.5",
  "EASA ED Decision 2025/018/R",
  "AMC & GM · Issue 1 Amd 3",
];

const ogDefault = () => `
<div class="asset" data-asset="og-default" style="width:1200px;height:630px">
  <div class="og">
    <div class="og-top">
      <span class="og-mark">SORA Copilot</span>
      <span class="og-eu">EU · specific category</span>
    </div>
    <h1 class="og-promise">From mission to dossier<br>in minutes.</h1>
    <div class="og-chain">
      ${CHAIN.map(
        (step, i) => `
        <span class="og-step${i === CHAIN.length - 1 ? " og-step-last" : ""}">${step}</span>
        ${i === CHAIN.length - 1 ? "" : '<span class="og-arrow"></span>'}`,
      ).join("")}
    </div>
    <div class="og-rule"></div>
    <span class="og-foot">A symbolic rules engine computes the chain. Every line cites its rule.</span>
  </div>
</div>`;

const proofLogos = () => `
<div class="asset" data-asset="proof-logos" style="width:1200px;height:200px">
  <div class="proof">
    ${FRAMEWORKS.map((f) => `<span class="proof-mark">${f}</span>`).join(
      '<span class="proof-sep"></span>',
    )}
  </div>
</div>`;

/**
 * The three segment cards.
 *
 * The manifest originally asked for photographs of people. These are not that, and
 * deliberately: a photograph of a "customer" who does not exist is a fabricated
 * endorsement, and the page's copy describes a segment ("Inspection company, Graz.")
 * rather than quoting a person, so there is nobody to depict.
 *
 * What each segment brings to the product is depictable, though, and is the honest
 * subject: the inputs a roof surveyor types, the inputs a corridor operator types, and
 * the justification a compliance officer reads before the verdict. Plates, hairlines and
 * tabular figures — the product's own language rather than a stock-photo pastiche.
 *
 * Nothing here is a computed class. These are inputs and a trace excerpt, so no card can
 * be read as a determination the engine did not make.
 */
const CARDS = {
  "persona-1": {
    kicker: "Inspection company · Graz",
    title: "Roof survey",
    rows: [
      ["Operation", "VLOS · 42 m AGL"],
      ["Ground environment", "Sparsely populated"],
      ["Population density", "84 ppl/km²"],
      ["Aircraft", "2.3 m · 18 m/s"],
    ],
    foot: "Four minutes of intake.",
  },
  "persona-2": {
    kicker: "Solo operator",
    title: "Powerline corridor",
    rows: [
      ["Operation", "BVLOS · 118 m AGL"],
      ["Flight geography", "12.4 km corridor"],
      ["Airspace", "Class G · near aerodrome"],
      ["Mitigations", "M1 low · strategic air"],
    ],
    foot: "One answer before quoting.",
  },
  "persona-3": {
    kicker: "Compliance officer",
    title: "Reads the trace first",
    trace: [
      ["conclusion", "sail(III)"],
      ["rule", "sora25.sail.lookup"],
      ["premises", "grc(4), arc_residual(b)"],
      ["source", "Main Body · Table 7"],
    ],
    foot: "Signs nothing it cannot defend.",
  },
};

const card = (id) => {
  const c = CARDS[id];
  const body = c.trace
    ? `<div class="card-trace">${c.trace
        .map(
          ([k, v]) => `<div class="card-trace-row">
            <span class="card-trace-k">${k}</span>
            <span class="card-trace-v">${v}</span>
          </div>`,
        )
        .join("")}</div>`
    : `<div class="card-rows">${c.rows
        .map(
          ([k, v]) => `<div class="card-row">
            <span class="card-k">${k}</span><span class="card-v">${v}</span>
          </div>`,
        )
        .join("")}</div>`;
  return `
<div class="asset" data-asset="${id}" style="width:600px;height:600px">
  <div class="card">
    <div class="card-head">
      <span class="card-kicker">${c.kicker}</span>
      <h2 class="card-title">${c.title}</h2>
    </div>
    ${body}
    <div class="card-foot"><span class="card-tick"></span>${c.foot}</div>
  </div>
</div>`;
};

export const ASSETS = {
  "og-default": { html: ogDefault, w: 1200, h: 630, out: "og-default.png" },
  "proof-logos": { html: proofLogos, w: 1200, h: 200, out: "proof-logos.png" },
  "persona-1": { html: () => card("persona-1"), w: 600, h: 600, out: "persona-1.jpg" },
  "persona-2": { html: () => card("persona-2"), w: 600, h: 600, out: "persona-2.jpg" },
  "persona-3": { html: () => card("persona-3"), w: 600, h: 600, out: "persona-3.jpg" },
};

export const STYLE = `
  html, body { margin: 0; background: #000; }
  .asset { position: relative; overflow: hidden; }
  .og {
    width: 100%; height: 100%; box-sizing: border-box; background: #000;
    padding: 56px 64px; display: flex; flex-direction: column; gap: 0;
    justify-content: space-between;
  }
  .og-top { display: flex; align-items: baseline; justify-content: space-between; }
  .og-mark {
    font-family: var(--font-wordmark), system-ui; font-weight: 300; font-size: 30px;
    letter-spacing: -0.03em; color: #eef1f3;
  }
  .og-eu {
    font-family: var(--font-heading), system-ui; font-weight: 600; font-size: 11px;
    line-height: 1; letter-spacing: .14em;
    text-transform: uppercase; color: #6d7984;
  }
  .og-promise {
    margin: 0; font-family: var(--font-heading), system-ui; font-weight: 600;
    font-size: 76px; line-height: 1.04; letter-spacing: -0.035em; color: #eef1f3;
  }
  .og-chain { display: flex; align-items: center; gap: 14px; }
  .og-step {
    font-family: var(--font-heading), system-ui; font-weight: 600; font-size: 15px;
    line-height: 1; letter-spacing: .1em;
    text-transform: uppercase; color: #9aa6b1; border: 1px solid #262c31;
    background: #121517; padding: 13px 18px; border-radius: 2px;
  }
  .og-step-last { color: #0a0c0d; background: #caff01; border-color: #caff01; }
  .og-arrow { width: 22px; height: 1px; background: #3a4349; }
  .og-rule { height: 1px; background: #1b1f22; }
  .og-foot { font-family: var(--font-heading), system-ui; font-weight: 400; font-size: 17px;
    line-height: 1.5; color: #8a95a1; }

  .proof {
    width: 100%; height: 100%; box-sizing: border-box; background: #0a0c0d;
    display: flex; align-items: center; justify-content: center; gap: 26px;
    padding: 0 40px;
  }
  .proof-mark {
    font-family: var(--font-heading), system-ui; font-weight: 600; font-size: 17px;
    line-height: 1; letter-spacing: .04em;
    color: #8a95a1; white-space: nowrap;
  }
  .proof-sep { width: 1px; height: 28px; background: #262c31; flex: none; }

  .card {
    width: 100%; height: 100%; box-sizing: border-box; background: #0a0c0d;
    display: flex; flex-direction: column; justify-content: space-between;
    padding: 44px 42px; border-top: 2px solid #caff01;
  }
  .card-head { display: flex; flex-direction: column; gap: 14px; }
  .card-kicker {
    font-family: var(--font-heading), system-ui; font-weight: 600; font-size: 11px;
    line-height: 1; letter-spacing: .12em; text-transform: uppercase; color: #6d7984;
  }
  .card-title {
    margin: 0; font-family: var(--font-heading), system-ui; font-weight: 600;
    font-size: 34px; line-height: 1.1; letter-spacing: -0.025em; color: #eef1f3;
  }
  .card-rows { display: flex; flex-direction: column; }
  .card-row {
    display: flex; align-items: baseline; justify-content: space-between; gap: 18px;
    padding: 13px 0; border-bottom: 1px solid #1b1f22;
  }
  .card-k {
    font-family: var(--font-heading), system-ui; font-weight: 600; font-size: 10px;
    line-height: 1; letter-spacing: .1em; text-transform: uppercase; color: #6d7984;
  }
  .card-v {
    font-family: var(--font-heading), system-ui; font-weight: 500; font-size: 15px;
    line-height: 1.3; color: #eef1f3; font-variant-numeric: tabular-nums;
    text-align: right;
  }
  .card-trace { display: flex; flex-direction: column; gap: 2px; }
  .card-trace-row {
    display: flex; align-items: baseline; gap: 14px; background: #121517;
    border-left: 2px solid #262c31; padding: 11px 14px;
  }
  .card-trace-k {
    width: 84px; flex: none; font-family: var(--font-heading), system-ui;
    font-weight: 600; font-size: 10px; line-height: 1.4; letter-spacing: .1em;
    text-transform: uppercase; color: #6d7984;
  }
  .card-trace-v {
    font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; font-size: 14px;
    line-height: 1.4; color: #caff01; word-break: break-all;
  }
  .card-foot {
    display: flex; align-items: center; gap: 10px;
    font-family: var(--font-heading), system-ui; font-weight: 400; font-size: 14px;
    line-height: 1.4; color: #8a95a1;
  }
  .card-tick { width: 14px; height: 2px; background: #caff01; flex: none; }
`;

/**
 * The counterfactual loop.
 *
 * A diagram, not a screen recording, and deliberately: the advisor is a paid feature
 * that answers 402 on the free plan, so a capture of it would be a picture of an upgrade
 * panel. This shows the mechanism instead — one input changes, the engine re-derives the
 * chain, the SAIL plate steps — in the product's own tokens and its own SAIL ramp.
 *
 * Six seconds, and it loops cleanly: the last frame is the first frame.
 */
export const LOOP_HTML = `
<div class="asset" data-asset="feature-counterfactual" style="width:900px;height:900px">
  <div class="loop">
    <div class="loop-head">
      <span class="loop-kicker">Counterfactual advisor</span>
      <h2 class="loop-title">What would make this<br>one SAIL cheaper?</h2>
    </div>

    <div class="loop-input">
      <span class="loop-k">Maximum altitude</span>
      <span class="loop-vals">
        <span class="loop-v loop-v-before">118 m AGL</span>
        <span class="loop-v loop-v-after">92 m AGL</span>
      </span>
    </div>

    <div class="loop-chain">
      <span class="loop-plate">iGRC 5</span>
      <span class="loop-arrow"></span>
      <span class="loop-plate">GRC 4</span>
      <span class="loop-arrow"></span>
      <span class="loop-plate loop-plate-arc">
        <span class="loop-arc-before">ARC c</span>
        <span class="loop-arc-after">ARC b</span>
      </span>
      <span class="loop-arrow"></span>
      <span class="loop-sail">
        <span class="loop-sail-plate loop-sail-before">SAIL III</span>
        <span class="loop-sail-plate loop-sail-after">SAIL II</span>
      </span>
    </div>

    <div class="loop-foot"><span class="loop-tick"></span>One input changed. The engine re-derived the chain.</div>
  </div>
</div>`;

export const LOOP_STYLE = `
  .loop {
    width: 100%; height: 100%; box-sizing: border-box; background: #0a0c0d;
    display: flex; flex-direction: column; justify-content: space-between;
    padding: 56px 52px; border-top: 2px solid #caff01;
  }
  .loop-head { display: flex; flex-direction: column; gap: 16px; }
  .loop-kicker {
    font-family: var(--font-heading), system-ui; font-weight: 600; font-size: 11px;
    line-height: 1; letter-spacing: .12em; text-transform: uppercase; color: #6d7984;
  }
  .loop-title {
    margin: 0; font-family: var(--font-heading), system-ui; font-weight: 600;
    font-size: 40px; line-height: 1.12; letter-spacing: -0.028em; color: #eef1f3;
  }
  .loop-input {
    display: flex; align-items: baseline; justify-content: space-between; gap: 20px;
    padding: 18px 0; border-top: 1px solid #1b1f22; border-bottom: 1px solid #1b1f22;
  }
  .loop-k {
    font-family: var(--font-heading), system-ui; font-weight: 600; font-size: 10px;
    line-height: 1; letter-spacing: .1em; text-transform: uppercase; color: #6d7984;
  }
  .loop-vals { position: relative; display: inline-block; min-width: 150px; height: 24px; }
  .loop-v {
    position: absolute; right: 0; top: 0; white-space: nowrap;
    font-family: var(--font-heading), system-ui; font-weight: 500; font-size: 20px;
    line-height: 1.2; color: #eef1f3; font-variant-numeric: tabular-nums;
  }
  .loop-v-before { animation: cf-out 6s infinite; }
  .loop-v-after  { color: #caff01; animation: cf-in 6s infinite; }

  .loop-chain { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .loop-plate {
    font-family: var(--font-heading), system-ui; font-weight: 600; font-size: 13px;
    line-height: 1; letter-spacing: .08em; text-transform: uppercase; color: #9aa6b1;
    background: #121517; border: 1px solid #262c31; padding: 14px 15px; border-radius: 2px;
    animation: cf-settle 6s infinite;
  }
  .loop-arrow { width: 16px; height: 1px; background: #3a4349; flex: none; }
  .loop-plate-arc { position: relative; min-width: 86px; text-align: center; }
  .loop-arc-before { animation: cf-out 6s infinite; }
  .loop-arc-after {
    position: absolute; left: 0; right: 0; top: 14px; color: #caff01;
    animation: cf-in 6s infinite;
  }
  .loop-sail { position: relative; display: inline-block; min-width: 116px; height: 44px; }
  .loop-sail-plate {
    position: absolute; left: 0; top: 0; padding: 14px 18px; border-radius: 2px;
    font-family: var(--font-heading), system-ui; font-weight: 600; font-size: 13px;
    line-height: 1; letter-spacing: .08em; text-transform: uppercase; color: #0a0c0d;
  }
  /* The SAIL ramp, from src/styles/tokens.css: III is #c99a3f, II is #a79b93. */
  .loop-sail-before { background: #c99a3f; animation: cf-out 6s infinite; }
  .loop-sail-after  { background: #a79b93; animation: cf-in 6s infinite; }

  .loop-foot {
    display: flex; align-items: center; gap: 10px;
    font-family: var(--font-heading), system-ui; font-weight: 400; font-size: 15px;
    line-height: 1.4; color: #8a95a1;
  }
  .loop-tick { width: 14px; height: 2px; background: #caff01; flex: none; }

  /* 0-25% before · 25-35% the swap · 35-88% after · 88-100% back, so the last frame
     is the first frame and the loop has no seam. */
  @keyframes cf-out {
    0%, 25% { opacity: 1; } 33%, 88% { opacity: 0; } 96%, 100% { opacity: 1; }
  }
  @keyframes cf-in {
    0%, 25% { opacity: 0; } 33%, 88% { opacity: 1; } 96%, 100% { opacity: 0; }
  }
  @keyframes cf-settle {
    0%, 30% { border-color: #262c31; }
    38% { border-color: #4a5560; }
    52%, 100% { border-color: #262c31; }
  }
`;
