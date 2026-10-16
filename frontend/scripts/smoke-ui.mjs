#!/usr/bin/env node
/**
 * Drive the built frontend in a real browser and assert the screens actually render.
 *
 * This exists because of a bug it would have caught. `@xyflow/react`'s structural
 * stylesheet was never imported, so the derivation tree — the product's central claim —
 * laid itself out below its own container and the panel rendered blank. Every unit test
 * passed. The component mounted, the nodes existed in the DOM, the API returned a
 * 27-node trace. Nothing was wrong except what you could see.
 *
 * So the assertions here are deliberately about *pixels and geometry*, not about
 * components existing: a node is only counted if its box actually intersects the panel
 * that is supposed to contain it.
 *
 *   # with the API on :8000 and `npx serve out -l 3002` running
 *   SUPABASE_JWT_SECRET=... node scripts/smoke-ui.mjs
 *
 * Exits non-zero on the first failure, so it is usable as a release gate.
 */

import { createRequire } from "node:module";

/**
 * Playwright is not a dependency of this package.
 *
 * It is a 300 MB browser download that nobody installing the frontend to *build* it
 * needs, so it is resolved at run time from wherever it happens to be — the repo, a
 * global install, or `PLAYWRIGHT_PATH`.
 */
function loadPlaywright() {
  const require = createRequire(import.meta.url);
  const candidates = [
    process.env.PLAYWRIGHT_PATH,
    "playwright",
    "/opt/node-tools/node_modules/playwright",
  ].filter(Boolean);
  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch {
      /* try the next one */
    }
  }
  console.error(
    "Playwright is not installed. Either:\n" +
      "    npm i -D playwright && npx playwright install chromium\n" +
      "  or point PLAYWRIGHT_PATH at an existing install.",
  );
  process.exit(2);
}

const { chromium } = loadPlaywright();

const BASE = process.env.UI_BASE ?? "http://127.0.0.1:3002";
const API = process.env.API_BASE ?? "http://127.0.0.1:8000";
const TOKEN = process.env.TOKEN ?? "";

const failures = [];
const ok = (label) => console.log(`  ok    ${label}`);
const check = (condition, label, detail = "") => {
  if (condition) return ok(label);
  failures.push(label);
  console.error(`  FAIL  ${label}${detail ? ` — ${detail}` : ""}`);
};
const step = (label) => console.log(`\n== ${label} ==`);

if (!TOKEN) {
  console.error("TOKEN is not set. Mint one with the API's JWT secret; see smoke.sh.");
  process.exit(2);
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await ctx.newPage();
const pageErrors = [];
page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 160)));
await page.route("**/api/v1/**", (route) =>
  route.continue({
    headers: { ...route.request().headers(), authorization: `Bearer ${TOKEN}` },
  }),
);

const text = async () => (await page.innerText("body")).trim();
const noOverflow = async () =>
  page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);

try {
  // ---------------------------------------------------------------- marketing
  step("the landing page");
  await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
  const landing = await text();
  check(landing.includes("From mission to dossier"), "the promise is on the page");
  check(landing.includes("iGRC"), "the chain is named");
  check(await noOverflow(), "no horizontal overflow");

  // Every media slot is either a real asset or the designed placeholder — never blank.
  const slots = await page.evaluate(() =>
    [...document.querySelectorAll("[data-slot]")].map((el) => ({
      id: el.getAttribute("data-slot"),
      painted: el.getBoundingClientRect().height > 40 && el.innerText.trim().length > 0,
    })),
  );
  check(slots.length > 0, `media slots present (${slots.length})`);
  const blank = slots.filter((s) => !s.painted).map((s) => s.id);
  check(blank.length === 0, "no media slot renders blank", blank.join(", "));

  // ---------------------------------------------------------------- the example
  step("the worked example");
  await page.goto(`${BASE}/app/`, { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  const button = page.locator("text=Show me a worked example").first();
  if (await button.count()) {
    await button.click();
  } else {
    // Already seeded in this organisation: open the newest determination instead.
    await page.locator("a[href*='/app/operations/view/']").first().click();
  }
  await page.waitForURL("**/app/operations/view/**", { timeout: 60_000 });
  await page.waitForTimeout(3500);

  const verdict = await text();
  for (const phrase of ["SAIL", "iGRC", "Derivation", "Gap analysis"]) {
    check(verdict.includes(phrase), `the verdict shows "${phrase}"`);
  }

  // ---------------------------------------------------------------- the tree
  step("the derivation tree actually renders");
  const tree = await page.evaluate(() => {
    const flow = document.querySelector(".react-flow");
    if (!flow) return { error: "no .react-flow on the page" };
    const panel = flow.getBoundingClientRect();
    const nodes = [...document.querySelectorAll(".react-flow__node")];
    const inside = nodes.filter((n) => {
      const b = n.getBoundingClientRect();
      return (
        b.width > 0 &&
        b.height > 0 &&
        b.right > panel.left &&
        b.left < panel.right &&
        b.bottom > panel.top &&
        b.top < panel.bottom
      );
    });
    const withText = inside.filter((n) => (n.innerText || "").trim().length > 0);
    return {
      panel: [Math.round(panel.width), Math.round(panel.height)],
      total: nodes.length,
      inside: inside.length,
      withText: withText.length,
      edges: document.querySelectorAll(".react-flow__edge").length,
      sample: withText[0]?.innerText?.replace(/\s+/g, " ").slice(0, 50) ?? null,
    };
  });
  check(!tree.error, "the graph is mounted", tree.error);
  check(tree.total > 10, `the trace has nodes (${tree.total})`);
  check(
    tree.inside === tree.total,
    `every node is inside the panel (${tree.inside}/${tree.total})`,
    "the layout escaped its container — is the xyflow stylesheet imported?",
  );
  check(tree.withText === tree.total, `every node has rendered text (${tree.withText})`);
  check(tree.edges > 5, `the nodes are connected (${tree.edges} edges)`);
  if (tree.sample) ok(`a node reads: "${tree.sample}"`);

  // ---------------------------------------------------------------- the rest
  step("the other screens");
  for (const [path, phrase] of [
    ["/app/authority/", "Austro Control"],
    ["/app/dossiers/", "Sections"],
    ["/app/settings/", "Plan"],
    ["/app/fleet/", "fleet"],
    ["/checker/", "category"],
    ["/pricing/", "€89"],
  ]) {
    await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(900);
    const body = await text();
    check(body.toLowerCase().includes(phrase.toLowerCase()), `${path} shows "${phrase}"`);
    check(await noOverflow(), `${path} has no horizontal overflow`);
  }

  step("nothing threw");
  check(pageErrors.length === 0, "no uncaught errors", pageErrors.slice(0, 3).join(" | "));
} finally {
  await browser.close();
}

if (failures.length) {
  console.error(`\n${failures.length} check(s) failed:\n  - ${failures.join("\n  - ")}`);
  process.exit(1);
}
console.log(`\nAll UI checks passed against ${BASE} (API ${API}).`);
