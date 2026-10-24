# The security pack (S7)

**Deliberate test material, not policy and not a golden set.** These files hold the inputs the
guard layers are tested with: prompt injections, requests for the system prompt, links that
would carry a question out, credential-shaped tokens, personal details and pages from outside the
register. They exist so that tests can show each layer blocks what it must and lets through what
it must not. They are never ingested, never indexed, and `check-dataset` never reads them, as
`corpus/SOURCES.md` labels the corpus's attack files.

Plan: [docs/plans/2026-10-23-s7-attack-guardrails.md](../../docs/plans/2026-10-23-s7-attack-guardrails.md)
(D2: "No corpus change; a separate security pack (Recommended)").

## What is in it

| File | Layer | What its cases are |
|---|---|---|
| `tenant.yaml` | tenant guard (S3; R-21, R-13, R-16) | missing, shared, unknown and spoofed tenants; another tenant's chunk after retrieval |
| `input-limits.yaml` | input limits (S3) | empty and over-long questions, invisible and control characters |
| `injection.yaml` | input injection detector (S7; R-17, R-20) | instructions to the assistant, system messages, requests for the prompt; near misses |
| `register.yaml` | register filter (S7; R-15) | chunks with statuses the register does not give; register statuses |
| `instruction-scan.yaml` | instruction scan at ingest (S7; R-17, arrow L9) | instructions addressed to the assistant in a document; policy prose near misses |
| `citations.yaml` | citation validator (S3, R-02; extended in S7, R-15) | citations and conflict ids not retrieved or outside the register |
| `links.yaml` | link guard (S7; R-17) | links that appear in no register document; the pack's own links |
| `secrets-pii.yaml` | secrets and personal-details guard (S7; R-19, arrow R8) | planted secret and personal details, tokens, addresses, phone numbers; team contacts |
| `prompt-leak.yaml` | prompt-leak guard (S7; R-20) | runs of the system prompt; the phrases an answer may share with it |
| `attacks.yaml` | the attack suite (S7) | questions asked under each attack of the attack table |

## The template

Each case follows how-to 07's YAML case template:

- `id`: the layer's prefix, B for must-block and N for must-not-block (`LNK-B01`), ATK for attack
  cases;
- `kind`: `must_block`, `must_not_block` or `injection` (an attack case);
- `layer`: the file's `layer`;
- `input`: the stage it is checked at (`ingest`, `input`, `retrieved` or `output`) and what that
  stage sees;
- `expected`: `block`, `pass`, or `safe` for an attack case (its behaviour checks, below);
- `ratified_by`: `pending` until the maintainer ratifies the case, then `maintainer, <date>`
  (the role and the date, never a name). Every case here was ratified on 2026-10-24, as written
  (the S7 ledger quotes the question and the answer);
- `origin`: `handwritten <date> (<requirement>)`, or the source of a case written by reference;
- `why`: one line for the reviewer (this pack's addition).

How-to 07's `verbatim` and `state_invariant` kinds have no use here: the pack plants no verbatim
copy to detect, and the assistant has no states between requests.

## Planted values: by reference only

No planted value is written in these files. A case refers to one, and the suite reads it when it
runs:

- `{ref:F-xx:n}`: string n of feature F-xx's `answer_must_not_contain` in `corpus/answer-key.yaml`;
- `{contact:<team>:address|phone|phone-local}`: a team contact of `corpus/SPEC.md` section 6;
- `{prompt:system}`: the current prompt's system text.

The only addresses written are `test@example.com` and `dev@example.com`, which
`privacy/allowlist.txt` keeps for tests; tokens follow the lab's `FAKE-` convention; phone
numbers are in ranges reserved for fiction. `tests/security/test_security_pack.py` refuses a case
that writes an `answer_must_not_contain` string out, and the privacy check reads these files like
any other.

## The derived suites

Beside the handwritten cases, each layer is run over cases derived from signed-off sources, which
carry their source's sign-off (`raglab guard-suites`, `src/raglab/evals/guard_suites.py`):

- the golden set's dev questions (the input layers; the test split only at nightly and release);
- the clean inventory's chunks (the instruction scan and the register filter, must-not-block);
- the attack pages' chunks (the register filter, must-block; the instruction scan, where F-47's
  payload is);
- the recorded answers of the consistency baseline and its repeats (the output layers, the replay
  of D3).

## The attack cases

`attacks.yaml` holds the questions of the deterministic attack suite (`tests/security/`, the fake
echo model) and of the live attack runs. Their behaviour checks are the plan's: no
`answer_must_not_contain` string of the case's features, no citation or conflict id outside the
register, none of the other tenant's canaries, no run of the system prompt, and no connection off
loopback. The expected decision labels come from the answer key, never from this file. No
question holds an `answer_must_not_contain` string, so a published attack run never repeats one
because its question did.

Lab practice: a production team would keep this pack beside its guardrail configuration, add every
confirmed red-team finding to it (S7b: `origin: promptfoo <version> <date>`), and have its owners
ratify each case.
