#!/usr/bin/env node
/**
 * Put MapLibre's worker where the app can serve it.
 *
 * MapLibre 6 loads its worker from `new URL("./maplibre-gl-worker.mjs", base)` with the
 * base taken from `import.meta.url`. Webpack cannot analyse that call, so it emits no
 * worker chunk, the URL resolves to a file the build does not contain, and the map
 * silently renders nothing — no error a user would see, just an empty chart. The
 * component calls `setWorkerUrl("/maplibre-gl-worker.mjs")`; this puts the file there.
 *
 * Copied at build time rather than committed, so it can never be a stale version of a
 * dependency that has since moved.
 */
import { copyFileSync, mkdirSync, statSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const src = join(dirname(require.resolve("maplibre-gl/package.json")), "dist", "maplibre-gl-worker.mjs");
const dest = join("public", "maplibre-gl-worker.mjs");

mkdirSync("public", { recursive: true });
copyFileSync(src, dest);
console.log(`maplibre worker → ${dest} (${(statSync(dest).size / 1024).toFixed(0)} KB)`);
