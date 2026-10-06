// Smoke check of the playground's data model (AC9): reads a runs/published directory the way the
// page does, through playground/model.js, and prints what the page would render as JSON.
// Usage: node tests/playground_smoke.mjs <published dir>
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { caseRows, manifestRows, parseCases, runFile, runRows } from "../playground/model.js";

const published = process.argv[2];
const read = (rel) => readFileSync(join(published, rel.replace(/^runs\/published\//, "")), "utf8");
const runs = runRows(JSON.parse(read("runs/published/index.json")));
const out = runs.map((run) => ({
  run,
  manifest: manifestRows(JSON.parse(read(runFile(run.path, "manifest.json")))),
  cases: caseRows(parseCases(read(runFile(run.path, "cases.jsonl")))),
}));
let refused = [];
for (const bad of ["../x/", "https://example.org/", "/etc/", ".hidden/"]) {
  try {
    runFile(bad, "manifest.json");
  } catch {
    refused.push(bad);
  }
}
console.log(JSON.stringify({ runs: out, refused }));
