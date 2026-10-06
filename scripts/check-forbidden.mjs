// Vendored from willcoliveira/ai-testing-handbook scripts/check-forbidden.mjs at dfff1aa (2026-10-05).
// Local changes:
// - no digests/ folder; uv.lock instead of package.json in the path allowlist
// - a view with line breaks removed, so a token split at a newline is found (S0 judge, 2026-10-05)
// - --files-from, for the pre-commit copy of the index (S0 judge round 2)
// - files listed NUL-separated (`ls-files -z`), so a name git C-quotes ("caf\303\251.md") is
//   scanned (S0 judge round 2)
// - CRLF and CR made LF before the paragraph split of the line-break view (S0 judge round 2)
// - only the two list files exempt by path, not every privacy/forbidden-strings* name; since S0
//   judge round 3 only the real list is never scanned: the example list, this script and uv.lock
//   are exempt from the example shapes only and checked with the real list's rules, and the
//   example list may hold only comments, <placeholders> (at least one) and /regex/ lines
// - in a linked worktree, the main worktree's real list
// - a real list in the index (any privacy/forbidden-strings* name but the example list, in any
//   case) is refused in every mode, CI included (S0 judge round 3)
// - a symlink is checked as its link text (what git commits for mode 120000), never read through
//   to its target; --dir walks do not follow links either (S0 judge round 3)
// - --file input (a commit message, a PR body) is prose, so it gets the line-break view
//   (S0 judge round 3)
// - --history <revisions>: every commit message, author and committer, and every line the commits added, so a string
//   committed without the hooks and removed later is still found (S0 judge round 3); reviewed
//   false positives in the history are listed in privacy/history-exceptions.txt by commit and line
// Scans every tracked and untracked (not ignored) file for forbidden strings; --dir <path> scans that
// directory instead. --file <path> one file (a commit message or PR body). --files-from <path> the
// files named in <path> (NUL-separated, relative to the working directory), e.g. every entry of an
// exported index (scripts/check-staged-privacy.sh). --history <revisions> every commit message
// and every added line of the commits git log lists for them: `--all`, `base..head`, or
// `<sha> --not --remotes=origin` (make privacy-history, the pre-push hook, pr-fast for a PR).
// Reads privacy/forbidden-strings.example.txt always, and privacy/forbidden-strings.txt
// unless CI=1. Exits 1 on any hit. Refuses to run (exit 2) if the real list, or any copy of it in
// privacy/, is in the git index, CI included.
import { readFileSync, existsSync, readdirSync, statSync, lstatSync, readlinkSync } from "node:fs";
import { execFileSync, execSync } from "node:child_process";
import { basename, dirname, join, relative, resolve } from "node:path";

const root = process.cwd();
// A linked worktree has no copy of the gitignored real list: use the main worktree's (the
// directory that holds the common .git), so its hooks and checks do not fall back to the example
// list alone.
function realList() {
  const own = join(root, "privacy/forbidden-strings.txt");
  if (existsSync(own) || process.env.CI) return own;
  try {
    const common = execSync("git rev-parse --path-format=absolute --git-common-dir", {
      cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"],
    }).trim();
    const main = join(dirname(common), "privacy/forbidden-strings.txt");
    if (basename(common) === ".git" && existsSync(main)) return main;
  } catch { /* not in a repo */ }
  return own;
}
const REAL = realList();
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
    // lstat: a symlink is an entry of its own (its link text is checked), never followed
    lstatSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
}
// a line of a list (trimmed): a comment or blank, a <placeholder>, a /regex/flags line, or plain text
function lineKind(l) {
  if (!l || l.startsWith("#")) return "comment";
  if (l.startsWith("/") && l.lastIndexOf("/") > 0) return "regex";
  if (l.startsWith("<") && l.endsWith(">")) return "placeholder";
  return "plain";
}
function loadList(path) {
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8").split("\n").map((l) => l.trim())
    .map((l) => {
      const kind = lineKind(l);
      if (kind === "regex") {
        const last = l.lastIndexOf("/");
        const flags = l.slice(last + 1).replace(/[^i]/g, "");
        return { re: new RegExp(l.slice(1, last), flags), global: new RegExp(l.slice(1, last), flags + "g"), src: l };
      }
      if (kind !== "plain") return null; // comment or placeholder, ignored
      const esc = l.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return { re: new RegExp(esc, "i"), global: new RegExp(esc, "gi"), src: l };
    }).filter(Boolean);
}
const exampleRules = loadList(EXAMPLE);
const realRules = process.env.CI ? [] : loadList(REAL);
const rules = [...exampleRules, ...realRules];
// The two lists must not share a line (S0 judge, F check D1). A shared line is either the real list
// repeating the example's generic rules (a real list made by filling in the example: the generic
// rules are always loaded, so the real list holds the private names only), or a private rule copied
// into the example list. Both stop every check here, with the reason, rather than producing
// confusing hits on the tracked files or hiding a pasted rule. The line itself is not printed.
if (!process.env.CI && existsSync(REAL) && existsSync(EXAMPLE)) {
  const flagless = (l) => l.trim().toLowerCase().replace(/^(\/.*\/)[a-z]*$/i, "$1");
  const meaningful = (l) => l && l !== "#" && !(l.startsWith("<") && l.endsWith(">")) && (!l.startsWith("#") || l.length >= 12);
  const exampleLines = new Set(readFileSync(EXAMPLE, "utf8").split("\n").map(flagless).filter(meaningful));
  const shared = readFileSync(REAL, "utf8").split("\n").map(flagless).filter(meaningful).filter((l) => exampleLines.has(l));
  if (shared.length) {
    console.error(`REFUSING: privacy/forbidden-strings.txt and the example list share ${shared.length} line(s). Keep only your private names in the real list (the example's generic rules are always loaded), and make sure no private rule was copied into privacy/forbidden-strings.example.txt.`);
    process.exit(2);
  }
}
// the real list's lines, to find one copied into the example list
// compared without the trailing flags, so /rule/ and /rule/i are the same line (S0 judge, F3)
const stripFlags = (l) => l.replace(/\/[a-z]*$/i, "/");
const realLines = new Set(realRules.map((r) => stripFlags(r.src.toLowerCase())));
// the real list's own comment lines (long enough not to be generic), so a whole copy of the list
// is reported without any of its text (S0 judge, F1)
const realComments = new Set(process.env.CI || !existsSync(REAL) ? [] : readFileSync(REAL, "utf8")
  .split("\n").map((l) => l.trim().toLowerCase()).filter((l) => l.startsWith("#") && l.length >= 12));
// for commit and tag identities: an identity is an email, so the generic email shape is left out
const identityRules = rules.filter((r) => !r.re.test("someone@example.com"));
const ALLOW_TOKENS = new Set(existsSync(join(root, "privacy/allowlist.txt"))
  ? readFileSync(join(root, "privacy/allowlist.txt"), "utf8").split("\n").map((l) => l.trim()).filter((l) => l && !l.startsWith("#"))
  : []);
// --history takes every argument after it; the other options come before it
const histArg = process.argv.indexOf("--history");
const historyRevs = histArg > 0 ? process.argv.slice(histArg + 1) : null;
const opts = histArg > 0 ? process.argv.slice(0, histArg) : process.argv;
// revisions and the ref-selecting options only, so no other option (--output=<file>) reaches git
const REV_OPTION = /^--(?:all|not|branches|tags|remotes)(?:=\S+)?$/;
if (historyRevs && (!historyRevs.length || historyRevs.some((a) => !a || (a.startsWith("-") && !REV_OPTION.test(a))))) {
  console.error("--history: give revisions only, e.g. --all, base..head, or <sha> --not --remotes=origin");
  process.exit(2);
}
const dirArg = opts.indexOf("--dir");
const scanDir = dirArg > 0 ? opts[dirArg + 1] : null;
if (dirArg > 0 && (!scanDir || !existsSync(scanDir))) { console.error(`--dir: no such directory ${scanDir || ""}`); process.exit(2); }
// label (forward slashes, for rules and output) -> absolute path. Absolute paths are kept because
// relative() across Windows drives (repo on D:, temp dir on C:) returns a path join() cannot rebuild.
const label = (abs) => relative(root, abs).split("\\").join("/");
// --file <path>: one file only, e.g. a commit message or a PR body before it is published
const fileArg = opts.indexOf("--file");
const scanFile = fileArg > 0 ? opts[fileArg + 1] : null;
if (fileArg > 0 && (!scanFile || !existsSync(scanFile) || statSync(scanFile).isDirectory())) { console.error(`--file: no such file ${scanFile || ""}`); process.exit(2); }
// --identity <path>: a name and address (a tagger line) checked with the identity rules
const identityArg = opts.indexOf("--identity");
const identityFile = identityArg > 0 ? opts[identityArg + 1] : null;
if (identityArg > 0 && (!identityFile || !existsSync(identityFile) || statSync(identityFile).isDirectory())) { console.error(`--identity: no such file ${identityFile || ""}`); process.exit(2); }
// --files-from <path>: the files named there (NUL-separated, relative to the working directory)
const listArg = opts.indexOf("--files-from");
const listFile = listArg > 0 ? opts[listArg + 1] : null;
if (listArg > 0 && (!listFile || !existsSync(listFile) || statSync(listFile).isDirectory())) { console.error(`--files-from: no such file ${listFile || ""}`); process.exit(2); }
const listed = () => readFileSync(listFile, "utf8").split("\0").filter(Boolean);
// The real list, or a copy of it (a backup, another case), must never be committed: refuse when one
// is in the index, in every mode and in CI too, where a list committed without the hooks would
// otherwise pass (S0 judge round 3). With --files-from the listed names are the index entries (the
// pre-commit copy has no git); otherwise git is asked.
const EXAMPLE_LABEL = "privacy/forbidden-strings.example.txt";
const isRealListName = (f) => /^privacy\/forbidden-strings/i.test(f) && f !== EXAMPLE_LABEL;
function indexEntries() {
  if (listFile) return listed();
  try {
    return execFileSync("git", ["-c", "core.quotePath=false", "ls-files", "-z", "--cached"], {
      cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"], maxBuffer: 256 * 1024 * 1024,
    }).split("\0").filter(Boolean);
  } catch {
    return []; // not in a repo
  }
}
const committedLists = indexEntries().filter(isRealListName);
if (committedLists.length) {
  console.error(`REFUSING: ${committedLists.join(", ")} is in the git index (tracked or staged). Untrack it: git rm --cached -- <path>`);
  process.exit(2);
}
const files = historyRevs ? new Map() : new Map((scanFile ? [resolve(root, scanFile)] : scanDir ? walk(resolve(root, scanDir)) : (listFile ? listed() : tracked()).map((f) => join(root, f))).map((abs) => [label(abs), abs]));
// Only the real list is never scanned (it is refused above when it is in the index; a backup of it,
// forbidden-strings.txt~, is scanned). These files state the generic example shapes on purpose (the
// example list itself, this script's comments, the hashes and ids in uv.lock), so they are exempt
// from the example list's rules only: the real list's rules still run on them, so a real name pasted
// into one is found (S0 judge round 3).
const REAL_LABEL = "privacy/forbidden-strings.txt";
const REAL_RULES_ONLY = new Set([EXAMPLE_LABEL, "scripts/check-forbidden.mjs", "uv.lock"]);
const rulesFor = (f) => (REAL_RULES_ONLY.has(f) ? realRules : rules);
// The example list holds only comments, <placeholders> and /regex/ lines, and keeps at least one
// placeholder. A plain-text line there is a name, in every mode (CI included); a list with no
// placeholder left is most likely the real list copied over it (the copy step with its arguments
// reversed). Locally, a line the real list also has is reported too (S0 judge round 3). The line's
// text is not printed, so a name does not reach a CI log.
function exampleListProblems(text) {
  const problems = [];
  let placeholders = 0;
  text.split(/\r?\n|\r/).forEach((raw, i) => {
    const l = raw.trim();
    const kind = lineKind(l);
    if (kind === "placeholder") placeholders++;
    else if (kind === "plain") problems.push(`${i + 1}: a plain-text line; the example list holds only comments, <placeholders> and /regex/ lines`);
  });
  if (!placeholders) problems.push(" no <placeholder> line left; is it the real list copied over the example?");
  return problems;
}
// a /regex/ line read as the text it matches, so the real list's rules find a name written as
// /\bname\b/i: the class escapes (\b, \d, \s, \w) as a space, any other escape as its character
// (quantifiers ?, *, + and {m,n} dropped too, so a rule such as /\bname ?x\b/ reads as its name;
// S0 judge, F3)
// A digit class reads as zeros (\d{3,5} as 000), so a digit-shape rule such as a ticket-id shape
// reads as an id it matches.
const regexText = (line) => line
  .replace(/\\d\{(\d+)(?:,\d*)?\}/g, (_, m) => "0".repeat(Number(m)))
  .replace(/\\d[+*?]?/g, "0")
  .replace(/\\[bBdDsSwW]/g, " ")
  .replace(/\{\d+(?:,\d*)?\}/g, "")
  .replace(/(?<!\\)[?*+]/g, "")
  .replace(/\\(.)/g, "$1");
// The real list's rules, to run them alone on that view: a rule written down in any file (a copy of
// the list at another path, a rule pasted into a note) is found by its name, since a \b-anchored
// rule does not match its own text. The generic example shapes are left out of that view, so code
// with escapes does not trip them (S0 judge round 4, E1).
const REAL_RULE_SET = new Set(realRules);
// The noreply address is removed from a line before matching, so it cannot hide anything else on
// that line (security review 2026-10-04); only the whole address: `alice.noreply@anthropic.com`
// is not exempt.
const ALLOW_SUBSTRINGS = [/(?<![\w.+-])noreply@anthropic\.com/gi];
// the whole token around a match, so an allowlisted token is compared in full, not by the part of
// it a rule happened to match
const DELIM = /[\s`'"()[\]<>{},;|*]/;
// GitHub's own addresses in trailers (Dependabot's Signed-off-by, squash-merge Co-authored-by):
// exempt when the whole match is the address, so they pass the generic email shape, while a
// real-list name inside a noreply address is still matched by its own rule (S0 judge, F4)
const GITHUB_ADDRESS = [/^[\w.+[\]-]+@users\.noreply\.github\.com$/i, /^(?:noreply|support)@github\.com$/i];
const allowedMatch = (view, m) =>
  ALLOW_TOKENS.has(m[0]) || ALLOW_TOKENS.has(tokenAt(view, m.index, m.index + m[0].length)) ||
  GITHUB_ADDRESS.some((p) => p.test(m[0]));
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
// A tree entry as git stores it: a symlink is its link text (mode 120000), so the text a commit
// carries is checked and a link to a file outside the repo is not read through (S0 judge round 3).
// --file follows links: a commit message can come from /dev/stdin, itself a symlink.
function readEntry(p) {
  let st;
  try {
    st = scanFile ? statSync(p) : lstatSync(p);
  } catch {
    return null; // gone since it was listed
  }
  if (st.isDirectory()) return null;
  if (st.isSymbolicLink()) return { text: readlinkSync(p, { encoding: "buffer" }).toString("utf8") };
  return readText(p);
}
// in a built site, a CSS file is checked for what it can show: strings and comments, not selectors
// (a minified `.local` class is not a hostname)
const cssVisible = (text) => [...text.matchAll(/\/\*[\s\S]*?\*\/|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/g)].map((m) => m[0]).join("\n");
let hits = 0, scanned = 0;
function report(message) {
  hits++;
  console.log(message);
}
// Every rule of ruleSet on each line (raw, as a reader sees it, and for the example list as the
// text its regexes match), then on the whole text with whitespace runs as one space and, for prose,
// with the lines of a paragraph joined. lineNo(i) is the number shown for line i.
// exempt(n) is true for a reviewed false positive on line n (history mode only).
function scanText(f, text, { ruleSet, prose, lineNo = (i) => i + 1, regexView = false, exempt = () => false }) {
  if (!ruleSet.length) return;
  const reported = new Set();
  let copied = false;
  text.split(/\r?\n|\r/).forEach((raw, i) => {
    const line = ALLOW_SUBSTRINGS.reduce((l, a) => l.replace(a, (s) => " ".repeat(s.length)), raw);
    const seen = new Set();
    // a line that is one of the real list's own lines, in any file: reported without its text,
    // so a copy of the list never reaches a log (S0 judge round 4, E1)
    const trimmed = line.trim();
    // a copy quoted in Markdown, bulleted or numbered (cat -n) is still a copy (S0 judge, F check D2)
    const bare = trimmed.replace(/^(?:>\s*|[-*+]\s+|\d+[.:)]?\s+)+/, "");
    const bareLower = bare.toLowerCase();
    const listLine = (lineKind(bare) === "regex" && realLines.has(stripFlags(bareLower))) || realComments.has(bareLower);
    if (listLine && !exempt(lineNo(i))) {
      copied = true;
      report(`${f}:${lineNo(i)}: a line of the real list (not shown)`);
      return;
    }
    const lineViews = [[line, ruleSet], [projection(line), ruleSet]];
    if (regexView) lineViews.push([regexText(line), ruleSet]);
    else if (line.includes("\\") && REAL_RULE_SET.size) {
      lineViews.push([regexText(line), ruleSet.filter((r) => REAL_RULE_SET.has(r))]);
    }
    for (const [view, viewRules] of lineViews) {
      for (const r of viewRules) {
        // every match, not just the first: one allowlisted token must not mask a later hit
        // (built page chunks are a single line each)
        for (const m of view.matchAll(r.global)) {
          if (!m[0]) continue;
          if (allowedMatch(view, m)) continue;
          const key = `${r.src}\u0000${m[0]}`;
          if (seen.has(key)) continue;
          seen.add(key);
          // an exempted line does not count as reported, so the same string wrapped elsewhere in
          // the file is still found (S0 judge, F check D3)
          if (exempt(lineNo(i))) continue;
          reported.add(key.toLowerCase());
          report(`${f}:${lineNo(i)}: matches ${r.src} (${m[0]})`);
        }
      }
    }
  });
  // a file holding lines of the real list is a copy of it: the views below would print fragments
  // of the list, so they are skipped; its lines are already reported (S0 judge, F1)
  if (copied) return;
  // a name wrapped across lines or with extra spaces: the whole file with all whitespace runs as one
  // space, in both views (round four); hits already reported on a single line are not repeated
  // a reviewed exception's line is left out of these views (a blank line in its place, which also
  // ends a paragraph), so it is not reported again across lines, while the same string wrapped
  // elsewhere in the file still is (S0, a regression of the D3 fix caught by the pre-push hook)
  const kept = text.split(/\r?\n|\r/).map((l, i) => (exempt(lineNo(i)) ? "" : l)).join("\n");
  const flat = ALLOW_SUBSTRINGS.reduce((l, a) => l.replace(a, (s) => " ".repeat(s.length)), kept).replace(/\s+/g, " ");
  // prose only (the one-token-per-line lists in privacy/ are not prose): a token wrapped at a line break inside a paragraph (`arn:` / `aws:`), lines joined
  // with nothing between them. Code files are left out: joining them glues a decorator to the
  // previous line and reads as an email address.
  // CRLF and CR become LF first: a split on two (\r?\n|\r) in a row read one CRLF as a blank
  // line, so a token wrapped at a CRLF was never joined (S0 judge round 2)
  // --file input is a commit message or a PR body: prose whatever its name (S0 judge round 3)
  const joined = prose
    ? ALLOW_SUBSTRINGS.reduce((l, a) => l.replace(a, (s) => " ".repeat(s.length)), kept)
        .replace(/\r\n?/g, "\n")
        .split(/\n[ \t]*\n/)
        .map((para) => para.replace(/[ \t]*\n[ \t]*/g, ""))
        .join("\n")
    : "";
  const views = [flat, projection(flat).replace(/\s+/g, " ")];
  if (joined) views.push(joined, projection(joined));
  for (const view of views) {
    for (const r of ruleSet) {
      for (const m of view.matchAll(r.global)) {
        if (!m[0]) continue;
        if (allowedMatch(view, m)) continue;
        const key = `${r.src}\u0000${m[0]}`.toLowerCase();
        if (reported.has(key)) continue;
        reported.add(key);
        report(`${f}: matches ${r.src} across lines (${m[0]})`);
      }
    }
  }
}
// one file of the tree (or the commit message given with --file)
function checkFile(f, text) {
  if (f === EXAMPLE_LABEL) {
    for (const problem of exampleListProblems(text)) report(`${f}:${problem}`);
  }
  scanText(f, text, {
    ruleSet: rulesFor(f),
    prose: Boolean(scanFile) || (PROSE.test(f) && !f.startsWith("privacy/")),
    regexView: f === EXAMPLE_LABEL,
  });
}
// git log for the --history revisions; read-only, and blind to the user's diff and log settings
function gitLog(args) {
  try {
    return execFileSync("git", ["-c", "core.quotePath=false", "log", "--no-show-signature", ...args, ...historyRevs, "--"], {
      cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], maxBuffer: 1024 * 1024 * 1024,
    });
  } catch (e) {
    console.error(`--history: git log failed: ${String(e.stderr || e.message).trim()}`);
    process.exit(2);
  }
}
// a path from a `+++ b/<path>` line: C-quoted when it holds a quote, a backslash or a control
// character, followed by a tab when it holds a space; /dev/null for a deleted file
const C_ESCAPES = { a: 7, b: 8, t: 9, n: 10, v: 11, f: 12, r: 13 };
function diffPath(s) {
  let p = s.replace(/\t$/, "");
  if (p === "/dev/null") return null;
  if (p.startsWith('"') && p.endsWith('"')) {
    const bytes = [];
    for (const m of p.slice(1, -1).matchAll(/\\([0-7]{3}|.)|([^\\]+)/gsu)) {
      if (m[2] !== undefined) bytes.push(...Buffer.from(m[2], "utf8"));
      else if (/^[0-7]{3}$/.test(m[1])) bytes.push(parseInt(m[1], 8));
      else bytes.push(C_ESCAPES[m[1]] ?? m[1].charCodeAt(0));
    }
    p = Buffer.from(bytes).toString("utf8");
  }
  return p.startsWith("b/") ? p.slice(2) : p;
}
// Reviewed false positives in the history, one `<full commit id>:<path>:<line>` per line. A commit
// cannot change without changing its id, so an entry covers that one line of that commit only.
const EXCEPTIONS_FILE = join(root, "privacy/history-exceptions.txt");
const historyExceptions = new Set(existsSync(EXCEPTIONS_FILE)
  ? readFileSync(EXCEPTIONS_FILE, "utf8").split("\n").map((l) => l.trim()).filter((l) => l && !l.startsWith("#"))
  : []);
function scanHistory() {
  let commits = 0;
  // commit messages, as prose; author and committer identities with every rule except the generic
  // email shape (every identity is an email), so a name or an internal domain in an identity is
  // found before it is pushed (S0 judge round 4, E3)
  for (const entry of gitLog(["-z", "--format=%H%n%an <%ae>%n%cn <%ce>%n%B"]).split("\0")) {
    if (!entry.trim()) continue;
    const [sha, author = "", committer = "", ...body] = entry.replace(/^\n+/, "").split("\n");
    commits++;
    const at = sha.trim().slice(0, 12);
    scanText(`${at} author`, author, { ruleSet: identityRules, prose: false });
    scanText(`${at} committer`, committer, { ruleSet: identityRules, prose: false });
    scanText(`${at} message`, body.join("\n"), { ruleSet: rules, prose: true });
  }
  // the lines each commit added, per file. A merge shows its combined diff (--cc): only lines new
  // to every parent count, so a branch merged in is not scanned twice.
  const blocks = new Map();
  const exampleAt = new Set();
  let sha = "", path = null, width = 0, next = 0;
  const diff = gitLog(["-p", "--cc", "--root", "--no-color", "--no-ext-diff", "--no-textconv", "--text",
    "--no-renames", "--unified=0", "--src-prefix=a/", "--dst-prefix=b/", "--format=%x00%H"]);
  for (const raw of diff.split("\n")) {
    if (raw.startsWith("\0")) { sha = raw.slice(1); path = null; width = 0; continue; }
    if (raw.startsWith("diff ")) { path = null; width = 0; continue; }
    // @@ -a,b +c,d @@ (one @ per parent, plus one): the added side starts at line c
    const hunk = /^(@{2,}) (?:-\S+ )+\+(\d+)(?:,\d+)? \1/.exec(raw);
    if (hunk) { width = hunk[1].length - 1; next = Number(hunk[2]); continue; }
    if (!width) {
      if (raw.startsWith("+++ ")) {
        path = diffPath(raw.slice(4));
        if (path === EXAMPLE_LABEL) exampleAt.add(sha);
      }
      continue;
    }
    if (raw.startsWith("\\") || raw.length < width) continue; // \ No newline at end of file
    const prefix = raw.slice(0, width);
    if (prefix.includes("-")) continue; // not in the commit's version of the file
    const lineNo = next++;
    if (path === null || prefix !== "+".repeat(width)) continue;
    const key = `${sha}\0${path}`;
    if (!blocks.has(key)) blocks.set(key, { sha, path, lines: [], nums: [] });
    const block = blocks.get(key);
    // a blank line between hunks, so lines that are not next to each other are not joined
    if (block.nums.length && block.nums[block.nums.length - 1] !== lineNo - 1) {
      block.lines.push("");
      block.nums.push(null);
    }
    block.lines.push(raw.slice(width).replace(/\r$/, ""));
    block.nums.push(lineNo);
  }
  for (const { sha: at, path: f, lines, nums } of blocks.values()) {
    const where = `${at.slice(0, 12)}:${f}`;
    if (f === REAL_LABEL || isRealListName(f)) {
      report(`${where}: a copy of the real list is committed (its lines are not shown)`);
      continue;
    }
    if (BINARY_EXT.test(f)) continue;
    scanText(where, lines.join("\n"), {
      ruleSet: rulesFor(f),
      prose: PROSE.test(f) && !f.startsWith("privacy/"),
      lineNo: (i) => nums[i],
      regexView: f === EXAMPLE_LABEL,
      exempt: (n) => historyExceptions.has(`${at}:${f}:${n}`),
    });
  }
  // the example list's format, as each commit that changed it left the whole file
  for (const at of exampleAt) {
    let text;
    try {
      text = execFileSync("git", ["show", `${at}:${EXAMPLE_LABEL}`], { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
    } catch {
      continue;
    }
    for (const problem of exampleListProblems(text)) report(`${at.slice(0, 12)}:${EXAMPLE_LABEL}:${problem}`);
  }
  return commits;
}
if (identityFile) {
  scanText("identity", readFileSync(identityFile, "utf8"), { ruleSet: identityRules, prose: false });
  console.log(`${hits} hits in the identity (${identityRules.length} rules)`);
  process.exit(hits ? 1 : 0);
}
if (historyRevs) {
  const commits = scanHistory();
  console.log(`${hits} hits in ${commits} commits (${rules.length} rules${process.env.CI ? ", CI example list only" : ""})`);
  process.exit(hits ? 1 : 0);
}
for (const [f, p] of files) {
  if (f === REAL_LABEL) continue;
  const read = readEntry(p);
  if (!read || read.binary) continue;
  scanned++;
  checkFile(f, scanDir && /\.css$/i.test(f) ? cssVisible(read.text) : read.text);
}
console.log(`${hits} hits across ${scanned} files (${rules.length} rules${process.env.CI ? ", CI example list only" : ""})`);
process.exit(hits ? 1 : 0);
