// Renders the published runs. Reads only files below runs/published (same origin), calls no model
// and no other site, and writes text with textContent, never as HTML.
import { INDEX, caseRows, manifestRows, parseCases, runFile, runRows } from "./model.js";

const $ = (id) => document.getElementById(id);

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function row(cells, header = false) {
  const tr = el("tr");
  for (const cell of cells) {
    const td = el(header ? "th" : "td");
    if (cell instanceof Node) td.append(cell);
    else td.textContent = cell;
    tr.append(td);
  }
  return tr;
}

async function fetchText(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return response.text();
}

function status(message) {
  $("status").textContent = message;
}

async function showRun(run) {
  status(`Loading ${run.runId}...`);
  for (const button of document.querySelectorAll("#runs button")) {
    button.setAttribute("aria-pressed", String(button.dataset.run === run.runId));
  }
  const manifest = JSON.parse(await fetchText(runFile(run.path, "manifest.json")));
  const cases = parseCases(await fetchText(runFile(run.path, "cases.jsonl")));
  const details = $("details");
  details.replaceChildren();
  details.append(el("h2", run.config));
  const meta = el("dl", undefined, "meta");
  for (const { label, value } of manifestRows(manifest)) meta.append(el("dt", label), el("dd", value));
  details.append(meta);

  details.append(el("h3", "Metrics"));
  const metrics = el("table");
  metrics.append(row(["Metric", "Value (95% interval, n)"], true));
  for (const m of run.metrics) metrics.append(row([m.name, m.text]));
  details.append(metrics);

  details.append(el("h3", "Questions"));
  const table = el("table", undefined, "cases");
  table.append(row(["Case", "Question", "Hit", "RR", "Recall", "Labelled sections", "Retrieved"], true));
  for (const c of caseRows(cases)) {
    const retrieved = el("ol");
    for (const r of c.retrieved) retrieved.append(el("li", r.id, r.relevant ? "relevant" : ""));
    const question = el("div");
    question.append(el("div", c.question), el("div", [c.split, c.tenant, c.kind].filter(Boolean).join(", "), "muted"));
    table.append(
      row([c.caseId, question, el("span", c.hit ? "yes" : "no", c.hit ? "yes" : "no"), c.rr, c.recall, c.labels.join("; "), retrieved]),
    );
  }
  details.append(table);
  status("");
}

async function start() {
  let rows;
  try {
    rows = runRows(JSON.parse(await fetchText(INDEX)));
  } catch (error) {
    status(`No published runs to show (${error.message}).`);
    return;
  }
  const list = $("runs");
  list.replaceChildren();
  for (const run of rows) {
    const button = el("button");
    button.type = "button";
    button.dataset.run = run.runId;
    button.append(
      el("strong", run.config + (run.baseline ? " (baseline)" : "")),
      el("span", `${run.created}, ${run.retriever}, chunk ${run.chunkSize}`, "muted"),
      el("span", `${run.provenance}, ${run.embedder}, git ${run.gitSha}, n ${run.n}`, "muted"),
    );
    for (const m of run.metrics) button.append(el("span", `${m.name} ${m.text}`));
    button.addEventListener("click", () => showRun(run).catch((e) => status(e.message)));
    const item = el("li");
    item.append(button);
    list.append(item);
  }
  if (rows.length) await showRun(rows[0]);
  else status("No published runs yet.");
}

start().catch((error) => status(error.message));
