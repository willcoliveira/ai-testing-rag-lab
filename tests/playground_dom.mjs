// Runs playground/app.js against a published directory with a minimal stand-in for the DOM and
// fetch (reading the files from disk), and prints what the page built as JSON: the run list, the
// first run's details, the details after clicking the second run, and the status line; then, as
// `every`, what each run shows when clicked in turn, and as `fetchedAll`, every path fetched.
// Usage: node tests/playground_dom.mjs <published dir>
import { readFileSync } from "node:fs";
import { join } from "node:path";

const published = process.argv[2];

class FakeNode {}
class FakeElement extends FakeNode {
  constructor(tag) {
    super();
    this.tagName = tag.toUpperCase();
    this.children = [];
    this.dataset = {};
    this.attributes = {};
    this.listeners = {};
    this.className = "";
    this._text = "";
  }
  set textContent(value) {
    this._text = String(value);
    this.children = [];
  }
  get textContent() {
    return this._text + this.children.map((c) => c.textContent).join("");
  }
  append(...nodes) {
    for (const node of nodes) {
      if (!(node instanceof FakeElement)) throw new Error("append takes elements only here");
      this.children.push(node);
    }
  }
  replaceChildren(...nodes) {
    this.children = [];
    this.append(...nodes);
  }
  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }
  addEventListener(type, fn) {
    this.listeners[type] = fn;
  }
  all(tag) {
    const found = [];
    for (const child of this.children) {
      if (child.tagName === tag) found.push(child);
      found.push(...child.all(tag));
    }
    return found;
  }
  set innerHTML(_) {
    throw new Error("the page must not write HTML");
  }
}

const ids = { runs: new FakeElement("ul"), details: new FakeElement("section"), status: new FakeElement("p") };
globalThis.Node = FakeNode;
globalThis.document = {
  getElementById: (id) => ids[id],
  createElement: (tag) => new FakeElement(tag),
  querySelectorAll: (selector) => (selector === "#runs button" ? ids.runs.all("BUTTON") : []),
};
const fetched = [];
globalThis.fetch = async (path) => {
  fetched.push(path);
  if (!path.startsWith("runs/published/")) return { ok: false, status: 404 };
  try {
    const text = readFileSync(join(published, path.slice("runs/published/".length)), "utf8");
    return { ok: true, status: 200, text: async () => text };
  } catch {
    return { ok: false, status: 404 };
  }
};

const settle = () => new Promise((resolve) => setTimeout(resolve, 50));
await import("../playground/app.js");
await settle();
const view = () => ({
  heading: ids.details.all("H2").map((h) => h.textContent),
  tables: ids.details.all("TABLE").map((t) => t.all("TR").length),
  relevant: ids.details.all("LI").filter((li) => li.className === "relevant").length,
  notes: ids.details.all("P").map((p) => p.textContent),
  meta: ids.details.all("DL").flatMap((dl) => dl.children.map((c) => c.textContent)),
});
const buttons = ids.runs.all("BUTTON");
const first = view();
if (buttons[1]) await buttons[1].listeners.click();
await settle();
const shown = {
  runs: buttons.map((b) => b.textContent),
  pressed: buttons.map((b) => b.attributes["aria-pressed"]),
  first,
  second: view(),
  status: ids.status.textContent,
  fetched: [...fetched],
};
// every run in turn, as a visitor clicking down the list (each click's handler is awaited)
const every = [];
for (const button of buttons) {
  await button.listeners.click();
  every.push({ run: button.dataset.run, ...view(), status: ids.status.textContent });
}
console.log(JSON.stringify({ ...shown, every, fetchedAll: fetched }));
