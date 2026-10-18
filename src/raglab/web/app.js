// The page's only script: it posts the question to /ask and writes the reply as text.
// Nothing is written as HTML (textContent only), so an answer can never inject markup.
const DEMO_TOKEN = "demo"; // lab: a public demo token, not a secret (config [api] tokens)

const byId = (id) => document.getElementById(id);

function show(reply) {
  byId("label").textContent = reply.label ?? "";
  byId("answer").textContent = reply.answer || reply.reason || "";
  const list = byId("citations");
  list.replaceChildren();
  for (const c of reply.citations ?? []) {
    const item = document.createElement("li");
    const page = c.page === null ? "" : `, page ${c.page}`;
    item.textContent = `${c.document} ${c.version}, section ${c.section}${page} (${c.chunk_id})`;
    list.append(item);
  }
}

async function ask(event) {
  event.preventDefault();
  const status = byId("status");
  status.textContent = "Asking...";
  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${DEMO_TOKEN}` },
      body: JSON.stringify({ tenant: byId("tenant").value, question: byId("question").value }),
    });
    const reply = await response.json();
    show(reply);
    status.textContent = `${response.status}: ${reply.status}`;
  } catch (error) {
    status.textContent = `The request failed: ${error}`;
  }
}

byId("ask").addEventListener("submit", ask);
