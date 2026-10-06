// The playground's data model: pure functions from the published files to rows of text. No DOM,
// no network: app.js fetches and renders, and tests/playground_smoke.mjs runs these in Node.

export const INDEX = "runs/published/index.json";

const fixed = (value) => (typeof value === "number" ? value.toFixed(3) : "n/a");

// "0.773 (0.591 to 0.909, n 22)"
export function formatInterval(metric) {
  if (!metric) return "n/a";
  return `${fixed(metric.value)} (${fixed(metric.ci_low)} to ${fixed(metric.ci_high)}, n ${metric.n})`;
}

// The index's runs, newest first, as rows for the run list.
export function runRows(index) {
  if (!index || index.schema_version !== "published-index.v1" || !Array.isArray(index.runs)) {
    throw new Error("not a published index (published-index.v1)");
  }
  const baselines = new Set(Object.values(index.baselines || {}));
  return index.runs.map((run) => ({
    runId: String(run.run_id),
    path: String(run.path),
    created: String(run.created_at),
    config: String(run.config),
    split: String(run.split),
    retriever: `${run.retriever}, k ${run.k}`,
    chunkSize: String(run.chunk_size),
    embedder: String(run.embedder),
    provenance: String(run.provenance),
    gitSha: String(run.git_sha).slice(0, 7),
    n: String(run.n),
    baseline: baselines.has(run.run_id),
    metrics: Object.entries(run.metrics || {}).map(([name, m]) => ({
      name,
      text: formatInterval(m),
    })),
  }));
}

// A run's files are only ever read from below runs/published: a path from the index that leaves
// it (an absolute URL, "..", a scheme) is refused.
export function runFile(path, name) {
  if (!/^[A-Za-z0-9._-]+\/$/.test(path) || path.startsWith(".")) {
    throw new Error(`refusing a run path outside runs/published: ${path}`);
  }
  return `runs/published/${path}${name}`;
}

export function parseCases(text) {
  return text
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line));
}

// One row per question: whether a labelled section was in the top k, the scores, and the
// retrieved chunk ids with the labelled ones marked.
export function caseRows(cases) {
  return cases.map((c) => ({
    caseId: String(c.case_id),
    split: String(c.split),
    tenant: String(c.tenant),
    kind: c.question_kind ? String(c.question_kind) : "",
    question: String(c.question),
    hit: c.hit === 1,
    rr: fixed(c.reciprocal_rank),
    recall: fixed(c.recall),
    labels: c.labels.map((l) => `${l.doc_id} ${l.section_id}${l.found ? "" : " (missed)"}`),
    retrieved: c.retrieved.map((r) => ({ id: String(r.chunk_id), relevant: r.relevant === true })),
  }));
}

// The manifest lines shown above a run's questions.
export function manifestRows(manifest) {
  const e = manifest.embedder;
  return [
    ["Run", manifest.run_id],
    ["Provenance", manifest.provenance],
    ["Git", `${manifest.git_sha}${manifest.git_dirty ? " (dirty)" : ""}`],
    ["Config", `${manifest.config.name} (${manifest.config.path})`],
    ["Embedder", `${e.model} at ${String(e.revision).slice(0, 12)}`],
    ["Chunker", `${manifest.chunker.chunk_size} characters, overlap ${manifest.chunker.overlap}`],
    ["Dataset", `${manifest.dataset.path}, ${manifest.dataset.questions} questions`],
    [
      "Bootstrap",
      `${manifest.bootstrap.resamples} resamples, seed ${manifest.bootstrap.seed}, ${Math.round(manifest.bootstrap.level * 100)}%`,
    ],
  ].map(([label, value]) => ({ label, value: String(value) }));
}
