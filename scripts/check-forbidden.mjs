// Vendored from willcoliveira/ai-testing-handbook scripts/check-forbidden.mjs at dfff1aa (2026-10-05).
// Local changes:
// - no digests/ folder; uv.lock instead of package.json in the path allowlist
// - a view with line breaks removed, so a token split at a newline is found (S0 judge, 2026-10-05)
// - --files-from, for the pre-commit copy of the index (S0 judge round 2)
// - files listed NUL-separated (`ls-files -z`), so a name git C-quotes ("caf\303\251.md") is
//   scanned (S0 judge round 2)
// - CRLF and CR made LF before the paragraph split of the line-break view (S0 judge round 2)
// - only the two list files exempt by path, not every privacy/forbidden-strings* name
// Scans every tracked and untracked (not ignored) file for forbidden strings; --dir <path> scans that
// directory instead. --file <path> one file (a commit message or PR body). --files-from <path> the
// files named in <path> (NUL-separated, relative to the working directory), e.g. every entry of an
// exported index (scripts/check-staged-privacy.sh)
// Reads privacy/forbidden-strings.example.txt always, and privacy/forbidden-strings.txt
// unless CI=1. Exits 1 on any hit. Refuses to run if the real list is tracked by git.
import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { execSync } from "node:child_process";
import { join, relative, resolve } from "node:path";

const root = process.cwd();
const REAL = join(root, "privacy/forbidden-strings.txt");
const EXAMPLE = join(root, "privacy/forbidden-strings.example.txt");

function tracked() {
  try {
    // -z: names verbatim, NUL-separated (without it git C-quotes "caf\303\251.md" and the file is
    // never found); stderr silent so a directory outside a repo walks without git's "fatal" line
    return execSync("git -c core.quotePath=false ls-files -z --cached --others --exclude-standard", {
      cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], maxBuffer: 256 * 1024 * 1024,
    }).split("\0").filter(Boolean);
  } catch {
    return walk(root).map((p) => relative(root, p));
  }
}
function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name === ".git") continue;
    const p = join(dir, name);
    statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
}
if (!process.env.CI && existsSync(REAL)) {
  try {
    execSync("git ls-files --error-unmatch privacy/forbidden-strings.txt", { cwd: root, stdio: "ignore" });
    console.error("REFUSING: privacy/forbidden-strings.txt is tracked by git. Untrack it first.");
    process.exit(2);
  } catch { /* not tracked, good */ }
}
function loadList(path) {
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8").split("\n").map((l) => l.trim())
    .filter((l) => l && !l.startsWith("#"))
    .map((l) => {
      if (l.startsWith("/") && l.lastIndexOf("/") > 0) {
        const last = l.lastIndexOf("/");
        const flags = l.slice(last + 1).replace(/[^i]/g, "");
        return { re: new RegExp(l.slice(1, last), flags), global: new RegExp(l.slice(1, last), flags + "g"), src: l };
      }
      if (l.startsWith("<") && l.endsWith(">")) return null; // placeholder, ignored
      const esc = l.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return { re: new RegExp(esc, "i"), global: new RegExp(esc, "gi"), src: l };
    }).filter(Boolean);
}
const rules = [...loadList(EXAMPLE), ...(process.env.CI ? [] : loadList(REAL))];
const ALLOW_TOKENS = new Set(existsSync(join(root, "privacy/allowlist.txt"))
  ? readFileSync(join(root, "privacy/allowlist.txt"), "utf8").split("\n").map((l) => l.trim()).filter((l) => l && !l.startsWith("#"))
  : []);
const dirArg = process.argv.indexOf("--dir");
const scanDir = dirArg > 0 ? process.argv[dirArg + 1] : null;
if (dirArg > 0 && (!scanDir || !existsSync(scanDir))) { console.error(`--dir: no such directory ${scanDir || ""}`); process.exit(2); }
// label (forward slashes, for rules and output) -> absolute path. Absolute paths are kept because
// relative() across Windows drives (repo on D:, temp dir on C:) returns a path join() cannot rebuild.
const label = (abs) => relative(root, abs).split("\\").join("/");
// --file <path>: one file only, e.g. a commit message or a PR body before it is published
const fileArg = process.argv.indexOf("--file");
const scanFile = fileArg > 0 ? process.argv[fileArg + 1] : null;
if (fileArg > 0 && (!scanFile || !existsSync(scanFile) || statSync(scanFile).isDirectory())) { console.error(`--file: no such file ${scanFile || ""}`); process.exit(2); }
// --files-from <path>: the files named there (NUL-separated, relative to the working directory)
const listArg = process.argv.indexOf("--files-from");
const listFile = listArg > 0 ? process.argv[listArg + 1] : null;
if (listArg > 0 && (!listFile || !existsSync(listFile) || statSync(listFile).isDirectory())) { console.error(`--files-from: no such file ${listFile || ""}`); process.exit(2); }
const listed = () => readFileSync(listFile, "utf8").split("\0").filter(Boolean);
const files = new Map((scanFile ? [resolve(root, scanFile)] : scanDir ? walk(resolve(root, scanDir)) : (listFile ? listed() : tracked()).map((f) => join(root, f))).map((abs) => [label(abs), abs]));
// files never scanned (by path only). The noreply address is removed from a line before matching,
// so it cannot hide anything else on that line (security review 2026-10-04).
// the two list files by exact name: a backup of the real list (forbidden-strings.txt~) is scanned
const ALLOW_PATHS = [/^privacy\/forbidden-strings(?:\.example)?\.txt$/, /^scripts\/check-forbidden\.mjs$/, /^uv\.lock$/];
// only the whole address: `alice.noreply@anthropic.com` is not exempt
const ALLOW_SUBSTRINGS = [/(?<![\w.+-])noreply@anthropic\.com/gi];
// the whole token around a match, so an allowlisted id (BUG-123) is compared in full, not by the
// prefix a rule happened to match (BUG-1)
const DELIM = /[\s`'"()[\]<>{},;|*]/;
function tokenAt(line, start, end) {
  let a = start, b = end;
  while (a > 0 && !DELIM.test(line[a - 1])) a--;
  while (b < line.length && !DELIM.test(line[b])) b++;
  return line.slice(a, b).replace(/[.:!?]+$/, "");
}
// Text a reader would see, as well as the raw line, so a name split by markup or disguised with
// lookalike characters is still found (adversarial re-test, 2026-10-04): tags removed (inline tags
// join, block tags separate), the common entities decoded, Markdown emphasis and code markers
// removed, NFKC, zero-width characters dropped, Unicode hyphens and dashes made `-`.
const INLINE_TAGS = "a|abbr|b|bdi|bdo|cite|code|del|dfn|em|i|ins|kbd|mark|q|s|samp|small|span|strong|sub|sup|u|var|wbr";
const ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " ", "#39": "'" };
function projection(line) {
  return line
    .replace(new RegExp(`</?(?:${INLINE_TAGS})\\b[^>]*>`, "gi"), "")
    .replace(/<[^>]+>/g, " ")
    .replace(/&(#x[0-9a-f]+|#\d+|[a-z]+\d*);/gi, (m, e) => {
      if (ENTITIES[e.toLowerCase()]) return ENTITIES[e.toLowerCase()];
      if (e[0] === "#") { const n = e[1].toLowerCase() === "x" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10); return Number.isFinite(n) ? String.fromCodePoint(n) : m; }
      return m;
    })
    .normalize("NFKC")
    .replace(/[\u200B-\u200D\u2060\uFEFF\u00AD]/g, "")
    .replace(/[\u2010-\u2015\u2212\uFE58\uFE63\uFF0D]/g, "-")
    .replace(/\*\*|__|~~|[*_`]/g, "");
}
// binary by content, not by name: a NUL byte in the first 8 KB (UTF-16 text is decoded instead)
// A NUL byte makes a file binary only for real binary formats; any other file with a NUL is read as
// text with the NULs removed (round four: a NUL hid a whole text file)
const PROSE = /\.(md|markdown|txt|rst|html?)$/i;
const BINARY_EXT = /\.(png|jpe?g|gif|webp|ico|pdf|zip|gz|woff2?|ttf|otf)$/i;
function readText(p) {
  const buf = readFileSync(p);
  if (buf[0] === 0xff && buf[1] === 0xfe) return { text: buf.subarray(2).toString("utf16le") };
  if (buf[0] === 0xfe && buf[1] === 0xff) return { text: Buffer.from(buf.subarray(2)).swap16().toString("utf16le") };
  if (buf.subarray(0, 8192).includes(0)) return BINARY_EXT.test(p) ? { binary: true } : { text: buf.toString("utf8").replace(/\0/g, "") };
  return { text: buf.toString("utf8") };
}
// in a built site, a CSS file is checked for what it can show: strings and comments, not selectors
// (a minified `.local` class is not a hostname)
const cssVisible = (text) => [...text.matchAll(/\/\*[\s\S]*?\*\/|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/g)].map((m) => m[0]).join("\n");
let hits = 0, scanned = 0;
for (const [f, p] of files) {
  if (ALLOW_PATHS.some((a) => a.test(f))) continue;
  if (!existsSync(p) || statSync(p).isDirectory()) continue;
  const read = readText(p);
  if (read.binary) continue;
  const text = scanDir && /\.css$/i.test(f) ? cssVisible(read.text) : read.text;
  scanned++;
  const reported = new Set();
  text.split(/\r?\n|\r/).forEach((raw, i) => {
    const line = ALLOW_SUBSTRINGS.reduce((l, a) => l.replace(a, (s) => " ".repeat(s.length)), raw);
    const seen = new Set();
    for (const view of [line, projection(line)]) {
      for (const r of rules) {
        // every match, not just the first: one allowlisted token must not mask a later hit
        // (built page chunks are a single line each)
        for (const m of view.matchAll(r.global)) {
          if (!m[0]) continue;
          if (ALLOW_TOKENS.has(m[0]) || ALLOW_TOKENS.has(tokenAt(view, m.index, m.index + m[0].length))) continue;
          const key = `${r.src}\u0000${m[0]}`;
          if (seen.has(key)) continue;
          seen.add(key);
          reported.add(key.toLowerCase());
          hits++; console.log(`${f}:${i + 1}: matches ${r.src} (${m[0]})`);
        }
      }
    }
  });
  // a name wrapped across lines or with extra spaces: the whole file with all whitespace runs as one
  // space, in both views (round four); hits already reported on a single line are not repeated
  const flat = ALLOW_SUBSTRINGS.reduce((l, a) => l.replace(a, (s) => " ".repeat(s.length)), text).replace(/\s+/g, " ");
  // prose only (the one-token-per-line lists in privacy/ are not prose): a token wrapped at a line break inside a paragraph (`arn:` / `aws:`), lines joined
  // with nothing between them. Code files are left out: joining them glues a decorator to the
  // previous line and reads as an email address.
  // CRLF and CR become LF first: a split on two (\r?\n|\r) in a row read one CRLF as a blank
  // line, so a token wrapped at a CRLF was never joined (S0 judge round 2)
  const joined = PROSE.test(f) && !f.startsWith("privacy/")
    ? ALLOW_SUBSTRINGS.reduce((l, a) => l.replace(a, (s) => " ".repeat(s.length)), text)
        .replace(/\r\n?/g, "\n")
        .split(/\n[ \t]*\n/)
        .map((para) => para.replace(/[ \t]*\n[ \t]*/g, ""))
        .join("\n")
    : "";
  const views = [flat, projection(flat).replace(/\s+/g, " ")];
  if (joined) views.push(joined, projection(joined));
  for (const view of views) {
    for (const r of rules) {
      for (const m of view.matchAll(r.global)) {
        if (!m[0]) continue;
        if (ALLOW_TOKENS.has(m[0]) || ALLOW_TOKENS.has(tokenAt(view, m.index, m.index + m[0].length))) continue;
        const key = `${r.src}\u0000${m[0]}`.toLowerCase();
        if (reported.has(key)) continue;
        reported.add(key);
        hits++; console.log(`${f}: matches ${r.src} across lines (${m[0]})`);
      }
    }
  }
}
console.log(`${hits} hits across ${scanned} files (${rules.length} rules${process.env.CI ? ", CI example list only" : ""})`);
process.exit(hits ? 1 : 0);
