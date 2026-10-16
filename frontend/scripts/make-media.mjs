#!/usr/bin/env node
/**
 * Build every asset in the media manifest.
 *
 * Two kinds of asset, one pipeline:
 *
 *   captures  screenshots and screen recordings of the real product, driven through the
 *             real API against the worked example. A screenshot of the thing is truer
 *             than an illustration of it, and it cannot describe a feature the product
 *             does not have.
 *   designed  the social card, the framework row and the three segment cards, built as
 *             HTML and rendered against the app's own compiled stylesheet so the tokens
 *             and the self-hosted typefaces are the same objects the product uses.
 *
 * The three empty-state illustrations are hand-authored SVG in public/media/ and are not
 * built here; they are source, not output.
 *
 *   # with the API on :8000 and `npx serve out -l 3002` running
 *   TOKEN=<jwt> node scripts/make-media.mjs            # everything
 *   TOKEN=<jwt> node scripts/make-media.mjs --only og-default,feature-trace
 *
 * Every output is checked against media-manifest.ts for exact pixel size and its byte
 * budget, and the run fails if one is off, because MediaSlot reserves the manifest's
 * ratio and a mis-sized file is a layout shift nobody notices in review.
 */

import { createRequire } from "node:module";
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, statSync, writeFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { ASSETS as DESIGNED, STYLE, LOOP_HTML, LOOP_STYLE } from "./media/studio.mjs";

function loadPlaywright() {
  const require = createRequire(import.meta.url);
  for (const c of [process.env.PLAYWRIGHT_PATH, "playwright", "/opt/node-tools/node_modules/playwright"].filter(Boolean)) {
    try { return require(c); } catch { /* next */ }
  }
  console.error("Playwright is not installed; see scripts/smoke-ui.mjs for the options.");
  process.exit(2);
}
const { chromium } = loadPlaywright();

const UI = process.env.UI_BASE ?? "http://127.0.0.1:3002";
const API = process.env.API_BASE ?? "http://127.0.0.1:8000";
const TOKEN = process.env.TOKEN ?? "";
const OUT = "public/media";
const EXPORT = "out";
const only = (() => {
  const i = process.argv.indexOf("--only");
  return i === -1 ? null : new Set(process.argv[i + 1].split(",").map((s) => s.trim()));
})();
const wanted = (id) => !only || only.has(id);

mkdirSync(OUT, { recursive: true });
const tmp = mkdtempSync(join(tmpdir(), "media-"));
const log = (...a) => console.log(" ", ...a);
const failures = [];

// ---------------------------------------------------------------- the manifest is law
/** Parsed straight out of the TypeScript, so there is one registry and not two. */
function manifest() {
  const src = readFileSync("src/lib/media-manifest.ts", "utf8");
  const body = src.slice(src.indexOf("export const MEDIA = {"));
  const out = {};
  const re = /"([a-z0-9-]+)":\s*\{([^}]*?)\}/gs;
  let m;
  while ((m = re.exec(body))) {
    const [, id, block] = m;
    const pick = (k) => block.match(new RegExp(`\\b${k}:\\s*([^,\\n]+)`))?.[1]?.trim();
    const num = (k) => {
      const v = pick(k);
      return v ? Number(v.replace(/_/g, "")) : undefined;
    };
    out[id] = {
      kind: pick("kind")?.replace(/"/g, ""),
      src: pick("src")?.replace(/"/g, ""),
      w: num("w"), h: num("h"), maxBytes: num("maxBytes"),
    };
  }
  return out;
}
const MEDIA = manifest();

function im(args) { execFileSync("convert", args, { stdio: ["ignore", "ignore", "pipe"] }); }

/** Resize a 2x grab down to the manifest's exact intrinsic size, then write it. */
function finish(id, grab) {
  const e = MEDIA[id];
  const dest = join(OUT, e.src.replace("/media/", ""));
  const jpg = dest.endsWith(".jpg");
  im([
    grab, "-filter", "Lanczos", "-resize", `${e.w}x${e.h}!`, "-strip",
    ...(jpg ? ["-quality", "88", "-sampling-factor", "4:2:0", "-colorspace", "sRGB"] : []),
    dest,
  ]);
  check(id, dest);
}

function check(id, dest) {
  const e = MEDIA[id];
  const size = statSync(dest).size;
  const dim = execFileSync("identify", ["-format", "%wx%h", dest]).toString();
  const want = `${e.w}x${e.h}`;
  const kb = (size / 1024).toFixed(0);
  if (dim !== want) failures.push(`${id}: ${dim}, manifest says ${want}`);
  else if (e.maxBytes && size > e.maxBytes)
    failures.push(`${id}: ${kb} KB over its ${(e.maxBytes / 1024).toFixed(0)} KB budget`);
  else log(`ok    ${id.padEnd(24)} ${dim.padEnd(10)} ${kb.padStart(5)} KB`);
}

// ---------------------------------------------------------------- designed assets
async function buildDesigned(browser) {
  const ids = Object.keys(DESIGNED).filter(wanted);
  if (!ids.length) return;
  // The app's compiled stylesheet carries the tokens, the type scale and the @font-face
  // rules for the self-hosted Archivo and Outfit. Taking it from the built export rather
  // than restating any of it is what keeps these assets from drifting.
  const index = readFileSync(join(EXPORT, "index.html"), "utf8");
  const css = [...index.matchAll(/href="(\/_next\/static\/css\/[^"]+\.css)"/g)].map((m) => m[1]);
  if (!css.length) throw new Error("no stylesheet found in the export; run npm run build first");
  // The <html> tag carries the next/font classes that DEFINE --font-archivo and
  // --font-outfit. Without them the tokens resolve to nothing, and a `font:` shorthand
  // naming an empty custom property is invalid CSS — the whole declaration is dropped
  // and the text silently renders at the inherited 16px. Reuse the real tag.
  const htmlTag = index.match(/<html[^>]*>/)?.[0] ?? '<html lang="en" data-theme="dark">';

  const studio = join(EXPORT, "__studio.html");
  writeFileSync(studio, `<!doctype html>${htmlTag}<head><meta charset="utf-8">
${css.map((h) => `<link rel="stylesheet" href="${h}">`).join("\n")}
<style>${STYLE}</style></head><body>
${ids.map((id) => DESIGNED[id].html()).join("\n")}
</body></html>`);
  try {
    const page = await browser.newPage({ viewport: { width: 1400, height: 900 }, deviceScaleFactor: 2 });
    await page.goto(`${UI}/__studio.html`, { waitUntil: "networkidle" });
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(400);
    for (const id of ids) {
      const grab = join(tmp, `${id}.png`);
      await page.locator(`[data-asset="${id}"]`).screenshot({ path: grab });
      finish(id, grab);
    }
    await page.close();
  } finally {
    rmSync(studio, { force: true });
  }
}

// ---------------------------------------------------------------- the worked example
async function authed(browser, opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1100 }, deviceScaleFactor: 2, ...opts });
  await ctx.route("**/api/v1/**", (route) =>
    route.continue({ headers: { ...route.request().headers(), authorization: `Bearer ${TOKEN}` } }));
  return ctx;
}

/** The demo operation's id: seeded through the real endpoint, never hand-built. */
async function exampleId(page) {
  const res = await page.request.post(`${API}/api/v1/demo/example`, {
    headers: { authorization: `Bearer ${TOKEN}` },
  });
  if (!res.ok()) throw new Error(`demo seed failed: ${res.status()} ${await res.text()}`);
  return (await res.json()).id;
}

async function buildCaptures(browser) {
  const ctx = await authed(browser);
  const page = await ctx.newPage();
  const id = await exampleId(page);
  const verdict = `${UI}/app/operations/view/?id=${encodeURIComponent(id)}`;

  // ---- feature-trace: the derivation tree, nodes expanded, citations legible
  if (wanted("feature-trace")) {
    await page.goto(verdict, { waitUntil: "networkidle" });
    await page.waitForSelector(".react-flow__node", { timeout: 60_000 });
    await page.waitForTimeout(2500);
    const nodes = page.locator(".react-flow__node");
    const n = await nodes.count();
    for (const i of [0, Math.floor(n / 3), Math.floor((2 * n) / 3)]) {
      try { await nodes.nth(i).click({ timeout: 2000 }); await page.waitForTimeout(250); } catch { /* not expandable */ }
    }
    await page.waitForTimeout(600);
    const grab = join(tmp, "feature-trace.png");
    await page.locator(".react-flow").screenshot({ path: grab });
    im([grab, "-gravity", "center", "-resize", "1280x960^", "-extent", "1280x960", join(tmp, "ft.png")]);
    finish("feature-trace", join(tmp, "ft.png"));
  }

  // ---- hero-poster: the verdict at rest — the chain and the SAIL plate
  if (wanted("hero-poster")) {
    await page.goto(verdict, { waitUntil: "networkidle" });
    await page.waitForTimeout(3000);
    const grab = join(tmp, "hero.png");
    await page.screenshot({ path: grab, clip: { x: 0, y: 0, width: 1600, height: 900 } });
    im([grab, "-gravity", "north", "-resize", "1440x810^", "-extent", "1440x810", join(tmp, "hero2.png")]);
    finish("hero-poster", join(tmp, "hero2.png"));
  }

  // ---- feature-map: the wizard's map step, volumes extruded, density overlay on
  if (wanted("feature-map")) {
    // A wide window on purpose: the wizard gives the chart whatever the window spares.
    await page.setViewportSize({ width: 1700, height: 1150 });
    await page.goto(`${UI}/app/new/?id=${encodeURIComponent(id)}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1200);
    // The stepper gates on how far the draft has been taken, so walk forward rather
    // than jumping: a disabled jump would silently capture the aircraft step instead.
    for (let i = 0; i < 6; i++) {
      if (await page.getByText("Flight geography").first().isVisible().catch(() => false)) break;
      const jump = page.getByRole("button", { name: "Map", exact: true });
      if (await jump.isEnabled().catch(() => false)) { await jump.click(); }
      else { await page.getByRole("button", { name: /^(Next|Continue)/ }).first().click().catch(() => {}); }
      await page.waitForTimeout(900);
    }
    const panel = page.locator('[data-media="map"]');
    await panel.waitFor({ timeout: 30_000 });
    await page.waitForTimeout(2500);
    // The contingency volume and the ground risk buffer are derived on commit, so the
    // picture of "all three volumes" needs an edit to have happened. Adding a vertex is
    // what a user does; it commits the outline and the server derives the rest.
    // One committed edit, because committing is what makes the server derive the
    // contingency volume and the ground risk buffer — without it the chart shows the
    // flight geography alone. It does leave a vertex behind, so this build wants a
    // fresh TOKEN: a new organisation gets a new worked example.
    await page.getByRole("button", { name: /add vertex/i }).click().catch(() => {});
    await page.waitForTimeout(3500);
    // The camera fit the geography once, before the buffer existed and before the edit,
    // so centre the volumes again: one step out for the buffer, then drag what the edit
    // pushed below the fold back into frame.
    await page.getByRole("button", { name: /zoom out/i }).click().catch(() => {});
    await page.waitForTimeout(700);
    const box = await panel.boundingBox();
    if (box) {
      await page.mouse.move(box.x + box.width / 2, box.y + box.height * 0.75);
      await page.mouse.down();
      await page.mouse.move(box.x + box.width / 2, box.y + box.height * 0.45, { steps: 12 });
      await page.mouse.up();
    }
    await page.waitForTimeout(1500);
    const grab = join(tmp, "map.png");
    await panel.screenshot({ path: grab });
    // Fit by width and keep the top-left: the readout overlay lives there, and a
    // centre crop of a wide panel cuts it in half.
    // Fill the frame: match the height first, then trim the width. The wizard's map
    // column is wider than 4:3, and letterboxing it would ship a small picture inside a
    // large black rectangle.
    im([grab, "-resize", "1280x", "-background", "#0a0c0d", "-gravity", "north",
        "-extent", "1280x960", join(tmp, "map2.png")]);
    finish("feature-map", join(tmp, "map2.png"));
  }

  // ---- the dossier pages: the real PDF the product emits, rasterised. Not a mock —
  //      a mock of your own output is the one illustration you never need.
  //
  //      Rendered through backend/scripts/sample_dossier.py rather than the HTTP export,
  //      because the export is a paid feature and correctly answers 402 on the free plan.
  //      A screenshot source is not an export: nothing is stored and no credit is spent.
  if (wanted("feature-dossier") || wanted("dossier-preview")) {
    const pdf = join(tmp, "dossier.pdf");
    execFileSync("../backend/.venv/bin/python", ["scripts/sample_dossier.py", pdf], {
      cwd: "../backend", stdio: ["ignore", "ignore", "inherit"],
    });
    execFileSync("pdftoppm", ["-png", "-r", "160", pdf, join(tmp, "pg")]);
    // Page numbers move as the document grows, so find the OSO matrix by its content.
    const pages = execFileSync("pdftotext", [pdf, "-"]).toString().split("\f");
    const find = (re) => pages.findIndex((t) => re.test(t)) + 1;
    // Two slots, two different pages: the same image twice would say the document has
    // one page worth looking at.
    const want = {
      "feature-dossier": find(/OSO#01[\s\S]*OSO#03/) || 1,        // the OSO matrix
      "dossier-preview": find(/Derivation|because\(|sora25\./) || 1, // the trace appendix
    };
    log(`      dossier: ${pages.length} pages · OSO matrix ${want["feature-dossier"]} · trace ${want["dossier-preview"]}`);
    for (const [idn, nth] of Object.entries(want)) {
      if (!wanted(idn)) continue;
      const pick = join(tmp, `pg-${String(nth).padStart(2, "0")}.png`);
      im([pick, "-gravity", "north", "-resize", "900x1200^", "-extent", "900x1200",
          join(tmp, `${idn}.png`)]);
      finish(idn, join(tmp, `${idn}.png`));
    }
  }

  await ctx.close();
  return id;
}

// ---------------------------------------------------------------- video
/**
 * Playwright writes webm; the manifest asks for mp4. Encode for a loop that autoplays
 * on a phone: H.264 with yuv420p (anything else is a black rectangle on Safari), no
 * audio track, and the moov atom at the front so it starts before it has finished
 * downloading.
 */
function encode(webm, id) {
  const e = MEDIA[id];
  const dest = join(OUT, e.src.replace("/media/", ""));
  const crfs = [30, 33, 36, 40];
  for (const crf of crfs) {
    execFileSync("ffmpeg", [
      "-y", "-loglevel", "error", "-i", webm,
      "-vf", `scale=${e.w}:${e.h}:force_original_aspect_ratio=increase,crop=${e.w}:${e.h},fps=24`,
      "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p",
      "-crf", String(crf), "-preset", "slow", "-movflags", "+faststart", "-an", dest,
    ]);
    if (!e.maxBytes || statSync(dest).size <= e.maxBytes) break;
  }
  const size = statSync(dest).size;
  const probe = execFileSync("ffprobe", [
    "-v", "error", "-select_streams", "v:0",
    "-show_entries", "stream=width,height,duration", "-of", "csv=p=0", dest,
  ]).toString().trim();
  const [w, h] = probe.split(",");
  if (Number(w) !== e.w || Number(h) !== e.h) failures.push(`${id}: ${w}x${h}, manifest says ${e.w}x${e.h}`);
  else if (e.maxBytes && size > e.maxBytes)
    failures.push(`${id}: ${(size / 1024).toFixed(0)} KB over its ${(e.maxBytes / 1024).toFixed(0)} KB budget`);
  else log(`ok    ${id.padEnd(24)} ${w}x${h}`.padEnd(42) + `${(size / 1024).toFixed(0).padStart(5)} KB · ${probe.split(",")[2]?.slice(0, 4)}s`);
}

/** The one webm a recording context just wrote. */
async function recorded(ctx, page) {
  const video = page.video();
  await ctx.close();
  return video.path();
}

async function buildVideos(browser, id) {
  const verdict = `${UI}/app/operations/view/?id=${encodeURIComponent(id)}`;

  // ---- hero-loop: arriving at a determination. The entrance animations are the point,
  //      so the recording starts on the list and clicks through rather than deep-linking.
  if (wanted("hero-loop")) {
    const ctx = await authed(browser, {
      viewport: { width: 1440, height: 810 }, deviceScaleFactor: 1,
      recordVideo: { dir: join(tmp, "v1"), size: { width: 1440, height: 810 } },
    });
    const page = await ctx.newPage();
    await page.goto(`${UI}/app/`, { waitUntil: "networkidle" });
    await page.waitForTimeout(1400);
    await page.locator("a[href*='/app/operations/view/']").first().click();
    await page.waitForURL("**/app/operations/view/**", { timeout: 60_000 });
    await page.waitForTimeout(4200);
    // A slow pass down the verdict: the chain, then the tree. Small steps so the
    // encoder sees motion it can predict instead of one hard cut.
    for (let i = 0; i < 26; i++) {
      await page.mouse.wheel(0, 90);
      await page.waitForTimeout(115);
    }
    await page.waitForTimeout(1600);
    encode(await recorded(ctx, page), "hero-loop");
  }

  // ---- feature-counterfactual: the advisor's mechanism, as a diagram.
  //      Not a screen recording: the advisor is a paid feature and answers 402 on the
  //      free plan, so a capture would show an upgrade panel rather than the thing. The
  //      loop is built from the app's own tokens and SAIL ramp and is plainly a diagram.
  if (wanted("feature-counterfactual")) {
    const studio = join(EXPORT, "__loop.html");
    const index = readFileSync(join(EXPORT, "index.html"), "utf8");
    const css = [...index.matchAll(/href="(\/_next\/static\/css\/[^"]+\.css)"/g)].map((m) => m[1]);
    const htmlTag = index.match(/<html[^>]*>/)?.[0] ?? '<html lang="en" data-theme="dark">';
    writeFileSync(studio, `<!doctype html>${htmlTag}<head><meta charset="utf-8">
${css.map((h) => `<link rel="stylesheet" href="${h}">`).join("\n")}
<style>${STYLE}${LOOP_STYLE}</style></head><body>${LOOP_HTML}</body></html>`);
    try {
      const ctx = await browser.newContext({
        viewport: { width: 900, height: 900 }, deviceScaleFactor: 1,
        recordVideo: { dir: join(tmp, "v2"), size: { width: 900, height: 900 } },
      });
      const page = await ctx.newPage();
      await page.goto(`${UI}/__loop.html`, { waitUntil: "networkidle" });
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(6400);
      // The poster is the loop's own first frame, so the still and the motion agree.
      const grab = join(tmp, "cf.png");
      await page.locator('[data-asset="feature-counterfactual"]').screenshot({ path: grab });
      const posterDest = join(OUT, "feature-counterfactual.jpg");
      im([grab, "-filter", "Lanczos", "-resize", "900x900!", "-strip", "-quality", "88",
          "-sampling-factor", "4:2:0", posterDest]);
      log(`ok    feature-counterfactual.jpg  900x900 ${(statSync(posterDest).size / 1024).toFixed(0)} KB`);
      encode(await recorded(ctx, page), "feature-counterfactual");
    } finally {
      rmSync(studio, { force: true });
    }
  }
}

// ---------------------------------------------------------------- go
// SwiftShader: headless Chromium has no GPU, MapLibre needs WebGL, and without it the
// map step renders its designed graticule and nothing else — which is exactly what the
// first run of this script shipped.
const browser = await chromium.launch({
  args: ["--use-gl=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"],
});
try {
  await buildDesigned(browser);
  if (TOKEN) {
    const id = await buildCaptures(browser);
    await buildVideos(browser, id);
  } else log("skip  product captures: TOKEN is not set");
} finally {
  await browser.close();
  rmSync(tmp, { recursive: true, force: true });
}
if (failures.length) {
  console.error(`\n${failures.length} asset(s) wrong:`);
  for (const f of failures) console.error(`  FAIL  ${f}`);
  process.exit(1);
}
console.log("\nAll requested assets built into public/media/.");
