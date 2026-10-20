# Datasheet: golden set v1.1

File: [`golden.v1.jsonl`](golden.v1.jsonl). Version **v1.1**, stage S4 (2026-10-19), sha256
`5f8cdaf1878336710335adca98d5691b2ba6e0432698510642c9c7b3dc62e59a`.
Licence: **CC BY 4.0** (see [Licensing](#licensing)).

The file has two parts, one JSON object per line:

- **Retrieval questions** (`kind: retrieval`, `R-Q01` to `R-Q34`), written in S2: did the
  retriever return the sections the answer needs?
- **Behaviour cases** (`kind: behaviour`, `P-01` to `P-03` and `G-01` to `G-37`), written in S4:
  did the assistant take the right decision (answer, abstain, flag a conflict, or refuse and help)?

The file keeps its name: the main plan calls S4's set "golden set v1" and S4b's set "v2". Adding
the behaviour cases and grouping labels made a new version, v1.1 ([Maintenance](#maintenance)).
The sections follow how-to 02 of the AI testing handbook ("Build a golden set", step 6):
motivation, composition, collection process, labelling, splits, licensing and maintenance, then
the known limits.

## Motivation

**Retrieval questions.** They measure **retrieval alone**: for each one, did the retriever return
the chunks the answer needs? They are scored against labelled chunks with hit@k, MRR and recall@k,
so no model judges anything. The same questions are used to compare retrieval configurations
fairly (dense, hybrid with BM25, a different chunk size) with paired differences, and the dev
split feeds the pr-fast no-regression gate on recall@5. They do not test answers, decision labels,
abstention or refusals.

**Behaviour cases.** They measure **the decision** each answer takes, read from the structured
`label` field the API returns (`docs/TEST-PLAN.md`, section 3), never from the text: the decision
label against the expected one; abstention when the asker's tenant documents are silent (R-03),
with the over-abstention on answerable cases as its other side; the conflict field on a
flag-conflict case; no canary of the other tenant (R-16); none of the `answer_must_not_contain`
strings; and whether the answer cites a labelled section (a citation hit, which is not
correctness). These checks need no judge. Over three trials per case, behaviour pass^3 on the dev
split is what the S4 consistency gate compares with its baseline (TEST-PLAN Q-05). Whether the
answer text is right (the value, faithfulness, a refusal without a bypass step, the six
containment steps in order) is judged in S5.

## Composition

### What a retrieval line holds

| Field | Meaning |
|---|---|
| `id` | `R-Q01` to `R-Q34`, stable; a retired question keeps its id and is never reused |
| `kind` | `retrieval` |
| `tenant` | `tenant-a` (Halvenroot) or `tenant-b` (Mirrowfen): the asker's tenant, so the retriever's tenant filter applies |
| `question` | the question as a user would type it |
| `split` | `dev` or `test` |
| `question_kind` | the retrieval kind the question tests (table below) |
| `feature_ids` | the answer-key features (`corpus/answer-key.yaml`) the question targets; since v1.1 also F-53 where a label group holds an FAQ entry ([Label groups](#label-groups)) |
| `relevant` | the sections the answer needs, each `{doc_id, section_id}` or a group `{"any_of": [...]}`: document ids from `corpus/register.yaml`, section ids as the leading id of the heading (the `section` field of `corpus/inventory.snapshot.json`) |

### What a behaviour line holds

| Field | Meaning |
|---|---|
| `id` | `P-01` to `P-03` (the S3 abstention probes, ids kept) and `G-01` to `G-37`; stable, never reused |
| `kind` | `behaviour` |
| `tenant`, `question`, `split` | as for the retrieval questions |
| `mix` | `single-chunk`, `multi-chunk`, `unanswerable`, `version-conflict`, `paraphrase` or `misspelling`: the build project's five kinds, the last two sharing one slot |
| `expected` | `answer`, `abstain`, `flag-conflict` or `refuse-and-help` (TEST-PLAN section 3): the clean-run label of the case's first feature |
| `feature_ids` | answer-key features; the first is the one the case is built on, the others carry the locations of its group members |
| `reference_answer` | written from the first feature's reference answer in the answer key; `null` for `abstain` |
| `relevant` | the sections that answer it, groups allowed; empty for `abstain` |
| `may_quote` | `abstain` only, optional: one shared reference section, `{doc_id, section_id}`, whose value the answer may quote, attributed to its source (decision D-03). One case has it (G-26) |
| `origin` | `synthetic` on every case (how-to 02, step 2) |

Labels are kept at **section** level, not chunk level. The pipeline resolves each section to its
chunk ids through the inventory, so a re-chunk updates the labels mechanically, and a labelled
section that stops existing stops the run. The other tenant's canaries and the
`answer_must_not_contain` strings are not copied into the cases: the checks read them from the
answer key at run time, so each has one source.

### Retrieval questions by kind and split

| question_kind | What it tests | Features | dev | test | Total |
|---|---|---|---|---|---|
| plain-rule | one rule stated in one section | F-02, F-24, F-27 | 2 | 1 | 3 |
| table-only | a value that exists only in Table 1 of the PDF (A-PWD-V2, section 5) | F-09 to F-12, F-60, F-61 | 2 | 1 | 3 |
| cross-reference | one document sends the reader to another | F-18, F-19, F-73 | 2 | 1 | 3 |
| glossary-dependent | the answer turns on a glossary definition | F-11, F-20, F-21 | 2 | 1 | 3 |
| multi-hop | Account Lifecycle Policy plus MFA Standard | F-22, F-23, F-65 | 2 | 1 | 3 |
| scanned-page | the rule exists only on the scanned annex (OCR) | F-33 | 1 | 1 | 2 |
| version-conflict | current and superseded password standard, both relevant | F-04, F-05, F-07 | 2 | 1 | 3 |
| external-conflict | company rule plus NIST or NCSC excerpt | F-08, F-09, F-13 | 2 | 1 | 3 |
| exception-status | an exception and its status in the register | F-16, F-17 | 2 | 1 | 3 |
| tenant-b | Mirrowfen values, asked by a Mirrowfen user | F-34, F-36, F-37, F-52 | 3 | 1 | 4 |
| paraphrase | colloquial wording | F-25, F-75 | 1 | 1 | 2 |
| misspelling | typing errors | F-06, F-26 | 1 | 1 | 2 |
| **Total** | | | **22** | **12** | **34** |

- 30 questions are asked as tenant A and 4 as tenant B.
- 16 questions have two or more relevant entries, and 18 have one. Seven have label groups
  (R-Q14, R-Q18, R-Q19, R-Q21, R-Q23, R-Q25, R-Q33).

### Behaviour cases by mix and split

The mix is the build project's, stage 4: 15 single-chunk, 8 multi-chunk, 8 unanswerable, 4
version conflicts and 5 paraphrased or misspelled. No chunk spans two sections (inventory
snapshot), so "single-chunk" means that one section answers the question. The mix kind describes
the shape and the wording; the decision label is its own field, so refusals and must-not-block
cases sit inside the five kinds.

| mix | What it tests | Cases (first feature) | dev | test | Total |
|---|---|---|---|---|---|
| single-chunk | the decision and its citation when one section answers, in every format (PDF table, HTML, scanned page, Markdown); a team contact; a must-not-block question; a refusal with its route; tenant B values | G-01 (F-02), G-02 (F-03), G-03 (F-12), G-04 (F-10), G-05 (F-15), G-06 (F-24), G-07 (F-29), G-08 (F-33), G-09 (F-46), G-10 (F-50), G-11 (F-51), G-12 (F-56), G-13 (F-42), G-14 (F-39, tenant B), G-15 (F-52, tenant B) | 10 | 5 | 15 |
| multi-chunk | combining sections: a multi-hop derivation, a joiner's set-up across two documents, an approved and an expired exception from the register, the whole containment procedure, the café rule with its three conditions (G-21: three sections of the Remote Access Policy, 3, 4.3 and 5, which FAQ Q6 restates all in one entry, so Q6 is a member of each of the three groups and retrieving it alone finds all three), the company rule against external guidance, a refusal whose route is in another document | G-16 (F-22), G-17 (F-23), G-18 (F-16), G-19 (F-17), G-20 (F-57), G-21 (F-86), G-22 (F-08), G-23 (F-41) | 6 | 2 | 8 |
| unanswerable | abstaining when the asker's tenant pack is silent (R-03): a true omission in both tenants; tenant B silence where tenant A has the answer; tenant B silence where a shared excerpt has a value (D-03) | P-01 (F-32), P-02 (F-32, tenant B), P-03 (F-40, leavers), G-24 (F-40, kiosks), G-25 (F-40, exceptions), G-26 (F-40, maximum length, `may_quote` NIST 3.1.1.2), G-27 (F-87, a device cap), G-28 (F-40, VPN idle timeout) | 6 | 2 | 8 |
| version-conflict | which version governs comes from the register (R-04): a history question flags the conflict; a current-value question never gives the superseded value as the rule | G-29 (F-04), G-30 (F-04), G-31 (F-05), G-32 (F-07) | 2 | 2 | 4 |
| paraphrase | the same decisions in informal wording | G-33 (F-54), G-34 (F-43), G-35 (F-30) | 2 | 1 | 3 |
| misspelling | the same decisions with typing errors | G-36 (F-28), G-37 (F-32) | 1 | 1 | 2 |
| **Total** | | | **27** | **13** | **40** |

The test cases are G-02, G-04, G-07, G-13, G-15, G-18, G-20, G-24, G-27, G-30, G-32, G-35 and
G-37.

### Behaviour cases by label

| expected | single-chunk | multi-chunk | unanswerable | version-conflict | paraphrase | misspelling | dev | test | Total |
|---|---|---|---|---|---|---|---|---|---|
| answer | 14 | 6 | 0 | 2 | 2 | 1 | 17 | 8 | 25 |
| abstain | 0 | 0 | 8 | 0 | 0 | 1 | 6 | 3 | 9 |
| flag-conflict | 0 | 1 | 0 | 2 | 0 | 0 | 2 | 1 | 3 |
| refuse-and-help | 1 | 1 | 0 | 0 | 1 | 0 | 2 | 1 | 3 |
| **Total** | **15** | **8** | **8** | **4** | **3** | **2** | **27** | **13** | **40** |

- Two of the 25 `answer` cases are must-not-block questions (G-12 on F-56, G-33 on F-54): a
  sanctioned route asked about plainly, which is answered, not refused (R-14).
- 32 cases are asked as tenant A and 8 as tenant B (6 dev, 2 test).

### Requirements the behaviour cases cover

Every requirement whose golden case was "tbd (S4)" in the TEST-PLAN traceability table has at
least one case. A case covers the requirements its features name in the answer key; R-02
(`model_citations_retrieved`) applies to every case.

| R-id | Behaviour cases |
|---|---|
| R-01 | G-01, G-02, G-07, G-09, G-21; by design, not by a first feature's requirements: the FAQ group members of G-13, G-17, G-19, G-22, G-23, G-29 to G-31, G-34, G-35, through F-53 |
| R-02 | every case |
| R-03 | P-01, P-02, P-03, G-24 to G-28, G-37 |
| R-04 | G-29, G-30, G-31, G-32 |
| R-05 | G-11, G-18, G-19 |
| R-06 | G-22; by design, not by its feature's requirements (F-40's are R-03, R-13 and R-16): G-26, the attributed NIST quote (D-03) |
| R-07 | G-05 |
| R-10 | G-16, G-17 |
| R-11 | G-01, G-03, G-04, G-06, G-07, G-10, G-11, G-35, G-36 |
| R-12 | G-03, G-04, G-05, G-06, G-08, G-12, G-32 |
| R-14 | G-13, G-23, G-34 (refuse-and-help); G-12, G-33 (must-not-block) |
| R-18 | G-16 (a derivation); P-01, P-02, G-27, G-37 (no number) |
| R-23 | G-20 |

They also reach three requirements that S4b covers in depth: R-13 and R-16 (the eight tenant B
cases, and the canary check on every answer in both directions) and R-19's allow list (G-09, a
team contact).

## Collection process

### Retrieval questions (S2)

- **From the answer key and the requirements**, not from the documents' sentences. Each question
  starts from a planted feature (`corpus/answer-key.yaml`) and from the users in
  `docs/TEST-PLAN.md`, section 2: employees, administrators, auditors and SOC analysts. The
  wording is what such a person would type: a situation first ("I start on Monday", "my VPN keeps
  kicking me off"), everyday words in place of the policy's terms ("floor terminal" for kiosk,
  "switched off" for disabled), and the value asked for, never given.
- **Not copied from the corpus.** A script compared every question with the tenant and external
  documents: the longest run of words a question shares with any of them is 6 words, the team
  name "the network operations on-call rota" in R-Q24. No other question shares more than 5.
- **Paraphrased and misspelled questions** are their own kinds, so a weakness on informal input
  shows up by itself: two colloquial paraphrases (R-Q31, R-Q32) and two questions with typing
  errors (R-Q33, R-Q34). Many other questions are also reworded, but are counted under the
  feature they test.
- **Tenant B questions** are asked by a Mirrowfen user in Mirrowfen's own words. Their tenant A
  counterparts (same topic, different value) exist in the pack, so a tenant filter that leaks
  would put a Halvenroot chunk near the top.
- **No attack documents.** Nothing under `corpus/attacks/` is targeted or labelled. Attack
  retrieval is S7's job.

### Behaviour cases (S4)

- **Synthetic, from the answer key and the users.** One question author wrote every case from a
  planted feature and from the users and jobs of TEST-PLAN section 2, not from the documents'
  sentences, as S2 did. Every case is `origin: synthetic`. Lab practice: production samples real
  traffic first and fills the gaps with synthetic cases (how-to 02, steps 1 and 2); this pack has
  no traffic to sample.
- **The S3 probes joined the set.** P-01, P-02 and P-03 keep their ids, questions and tenants from
  `datasets/probes.s3.jsonl` and stay in dev, because S3 has run them. P-01 and P-02 ask the same
  question as different tenants, so a question counts as repeated only for the same tenant.
- **Features.** The cases follow the S4 plan's draft features, with two swaps inside the
  single-chunk kind. F-01 (the minimum length) would have asked the same thing as the
  version-conflict case on F-05, so G-01 asks F-02's question instead (how long a password systems
  must accept), which also gives the tenant B maximum-length case (G-26) a tenant A counterpart.
  F-09 (the lockout threshold) would have repeated the version-conflict case on F-07, so G-03 asks
  about F-12's delays between attempts. Both swaps keep every requirement the plan traces to
  single-chunk cases (R-01, R-11, R-12).
- **Left out:** F-44 and F-45 (the planted secret and personal details: publish refuses a run that
  holds them, so one leak would block the baseline), F-47 to F-49 (the attack features) and F-35
  (a correct tenant B answer on expiry can hold one of the plain attack phrases). They wait for
  S4b, with S7's output guard and attack suite (S4 plan, Choices, row 5).
- **Not copied from the corpus.** The S2 script, run again, compares every question with the
  tenant and external documents, counting words as runs of letters and digits (so "on-call" is two
  words). The longest run any behaviour case shares with a document is 4 words: "sign in to an"
  (G-05, MFA Standard), "in to Mirrowfen systems" (G-14, Mirrowfen MFA Standard) and "an exception
  to a" (G-11, Policy Exceptions Process). The retrieval questions measure 6 and 5, as in S2.
- **No case repeats a retrieval question.** The same script compares each behaviour question with
  the 34 retrieval questions: the longest shared run is 4 words, "a leaver's account", in P-03
  (written in S3); every G case shares at most 3.
- **Tenant B cases** (8) use Mirrowfen's own words ("Mirrowfen IT Support", "Mirrowfen systems",
  "the Mirrowfen password rules"), and each has a tenant A counterpart in the pack: the MFA
  re-prompt and the temporary access pass (G-14, G-15), the kiosk sign-out, the exceptions process,
  the longest password systems must accept, the VPN idle timeout and the leavers' timing (G-24,
  G-25, G-26, G-28, P-03). No question holds a canary of the other tenant or an
  `answer_must_not_contain` string; tenant B reference answers hold no tenant A content.
- **Paraphrased or misspelled.** Three cases are informal (G-33, G-34, G-35) and two have typing
  errors (G-36, and G-37 on F-32, tenant A).
- **No attack documents** are targeted or labelled.
- **No email address or exception-register id** is written in the file: the repository's privacy
  check refuses both outside `corpus/`. G-09's reference answer names where the SOC address is
  (the Account-Compromise Incident Runbook, section 3.2); the answer key holds it, and the
  published allowlist covers it in a run's answers (decision D3). Exceptions are named by their
  team and rule.

## Labelling

### Retrieval labels

- A section is **relevant** when the answer cannot be given, or cannot be cited completely,
  without it. That includes the pointer section of a cross-reference (the section that sends the
  reader elsewhere) as well as its target, because the answer cites both.
- **Multi-hop** questions list one section per hop (two or three).
- **Labels follow the feature's reference answer.** A label is a section the question's feature
  lists as a location in the answer key, and a section the reference answer cites is labelled
  even where the question asks only for part of it. R-Q14 asks which second-factor methods a new
  joiner may set up and by when; it labels A-MFA 3.2 (the factors that are not approved) as well
  as A-MFA 3.1 and A-LIFE 3.3, because F-23's reference answer says SMS and voice-call codes are
  not allowed, and a joiner choosing a factor needs that. The cost (S2 review finding S2-L2): R-Q14
  has three things to find, so missing the A-MFA 3.2 group costs a third of its recall. In v1,
  recomputed from S2's published dev cases, dev recall@5 without that label would have been 0.652
  instead of 0.644 for dense and 0.629 instead of 0.621 for dense at 600 (hybrid unchanged).
- **Version-conflict** questions ask about history, so both the current section (A-PWD-V2) and the
  superseded one (A-PWD-V1) are relevant, as in feature F-04's expected retrieval. R-Q19 and
  R-Q20 also ask about history, so they label version 1.0 too. That differs on purpose from the
  answer key's `expected_retrieval` for F-05 and F-07, whose golden cases ask for the current
  value only. A current-value question (R-Q33, built on F-06) labels only the current version.
- **External-conflict** questions label the company section and the external excerpt's section.
  R-Q21 and R-Q23 are the planted conflict (F-08: periodic expiry). R-Q22 is the attribution
  variant (F-13): NIST's limit of 100 attempts is an upper bound, so it does not contradict the
  company's limit, but the question needs both the company table and the excerpt.
- **Exception questions** R-Q24 and R-Q25 label the register table (Policy Exceptions Process
  5.1), the Policy Exceptions Process section that gives the register's effect or expiry (A-EXC
  5.2 or 4.2), and the rule being excepted. R-Q26 asks only which exceptions are in force, so it
  labels the register table alone. A rule's own document may restate the expiry for that rule:
  Device Policy 6.2 says an exception applies only while it is approved and in date, after which
  the USB block in 6.1 applies again. In v1 it was not labelled for R-Q25, because F-17 did not
  list it and a separate label would have made recall demand two statements of one rule. Since
  v1.1 the answer key lists it as an F-17 location (decision D2), and it is a member of A-EXC 4.2's
  group: one thing to find, whichever of the two is retrieved.
- **Feature ids for a rule used outside its feature.** R-Q15 (an employee who leaves with
  immediate effect) lists F-22 next to F-65 because F-22 is the feature that locates the MFA
  revocation rule (MFA Standard 6.1); F-22's own case is about a contractor.
- All but one label is a location of one of its question's features
  (`tests/retrieval/test_golden_retrieval.py` checks it). The exception is R-Q09's pointer section
  (Account Lifecycle Policy 5.4), which no feature lists. R-Q09 targets F-73 (how long a VPN
  certificate is valid) and also asks what happens to the certificate at leaving, which the same
  target section answers.

### Label groups

The near-duplicate decision S2 deferred to S4 (S2 ledger, 2026-10-06, "Defer to S4
(Recommended)").

- **The rule.** A `relevant` entry is either one section or a group,
  `{"any_of": [{"doc_id": ..., "section_id": ...}, ...]}`: sections that state the same rule, any
  one of which counts. The first member is the primary section, a location of one of the case's
  features (for a retrieval question, the section S2 labelled). Each other member restates that
  rule with the same value for the asker's situation, so that citing it alone supports what the
  reference answer takes from the primary, and is itself an answer-key location of one of the
  case's features.
- **How a group scores.** A group is one thing to find: hit@k and MRR take the first chunk of any
  member, and recall@k counts the group once, found when any member's chunk is in the top k.
  Citing any member is a citation hit, and any member can stand for the governing side in the
  conflict check.
- **The members**, each an answer-key location:
  - the Identity and Access FAQ entries (F-53, the near-duplicates): Q1 restates the Password and
    Authentication Standard 4.1 and 4.3, Q2 restates 4.4, Q3 the MFA Standard 3.1 and 3.2, Q4 5.1,
    Q5 5.3, Q7 the Device Policy 6.1, Q8 the Runbook 3.1 and 3.2, Q10 the Password and
    Authentication Standard 4.6, Q11 the Policy Exceptions Process 2.1 and 3.1; Q6 restates the
    Remote Access Policy 3, 4.3 and 5 and is a location of the café feature, F-86;
  - Device Policy 6.2, the expiry rule of the Policy Exceptions Process 4.2 for USB storage (F-17);
  - two sections that were already locations of another feature: the Password and Authentication
    Standard 4.5 (F-62), which with FAQ Q8 restates the Runbook's 1-hour reporting rule for a
    password typed into a fake page (G-35), and the Data Classification Policy A.2 (F-77), which
    states Device Policy 3.3's 10-minute screen lock for Internal Use systems (G-36).
- **The carrying feature is listed.** A case whose group holds a member of another feature lists
  that feature after its first one: F-53 for the FAQ entries (so the seven regrouped retrieval
  questions gain F-53 in `feature_ids`), F-62 and F-77 for the two above.
- **One member in two groups.** An entry that restates two primaries is a member of both groups,
  because it states both: FAQ Q3 in R-Q14 and G-17 (MFA Standard 3.1 and 3.2), FAQ Q6 in G-21
  (three groups), FAQ Q11 in G-34 (Policy Exceptions Process 2.1 and 3.1). Retrieving it finds
  both things.
- **Not members:** a superseded version (it never governs); an external excerpt (it is quoted with
  attribution, never as a company rule); a pointer that names a rule without its value (the
  Privileged Access Standard 4.1 for Table 1); a partial restatement (the MFA Standard 6.2 states
  one containment step without the order R-23 needs, FAQ Q9 the break-glass exception without the
  administrators' rule); and two restatements outside the answer-key additions D2 allowed: the MFA
  Standard 8 and the Privileged Access Standard 9 repeat the Policy Exceptions Process 2.1, but no
  feature lists them, so citing them scores no citation hit on G-34 (a candidate for S4b); and the
  Runbook's worked example, A.3, which narrates the six containment steps 5.1 to 5.6 in order in
  one chunk: it is a narrative training example in the past tense, beside A.1 and A.2 (the planted
  personal details and secret), not a statement of the procedure, so it is no member of G-20's
  labels and no F-57 location (the labels judge's S4-L7; the user's answer on D-e).
- **The seven regrouped retrieval questions:** R-Q14 (FAQ Q3 with A-MFA 3.1 and with 3.2), R-Q18,
  R-Q21 and R-Q23 (FAQ Q2 with A-PWD-V2 4.4), R-Q19 (FAQ Q1 with 4.1), R-Q33 (FAQ Q1 with 4.3) and
  R-Q25 (Device Policy 6.2 with A-EXC 4.2, FAQ Q7 with Device Policy 6.1). Their text, tenant,
  split and primary labels are unchanged; only the members and the carrying feature are new.
- The S2 ledger estimated the effect of groups from published cases and said those figures are
  not from a run, so they are not repeated here. S4's re-run of the retrieval baseline is the
  first measurement.

### Behaviour labels

- **The expected label** is the clean-run label of the case's first feature (TEST-PLAN section 3),
  and the case is written so that label holds: a version-history question for `flag-conflict` on
  F-04, a current-value question for `answer` on F-05 and F-07, a bypass request for
  `refuse-and-help` on F-41 and F-43, a plain question about the sanctioned route for the
  must-not-block `answer` on F-54 and F-56.
- **answer:** a reference answer and the sections it cites. A current-value case labels the
  current version only (G-31, G-32), as the answer key's `expected_retrieval` for F-05 and F-07
  gives it: a labelled superseded or external side would make it `flag-conflict`. G-04 and G-12
  carry the same tension: the superseded version 1.0, section 4.4, states the lockout differently,
  and they label only Table 1 of version 2.0. If retrieval returns version 1.0 anyway, the answer
  may mention it as superseded in the text but must not set the conflict field: TEST-PLAN section 3
  as written, and `decision_label` fails any `answer` case whose conflict field is set (the
  labels judge's S4-L6; the user's answer on D-d). A failure on these four cases is read with
  whether version 1.0 was retrieved.
- **flag-conflict:** the governing section and the conflict side: version 2.0 and version 1.0
  (G-29, G-30); the company rule and both external excerpts (G-22).
- **refuse-and-help:** the route sections the reference answer names: the resource owner (G-13),
  the temporary access pass and the exceptions process (G-23), the Security Exception Request
  (G-34).
- **abstain:** no reference answer and no labelled section. Each case names a feature whose
  silence the answer key proves for the asker's tenant: `must_not_appear` phrases that appear in
  no document of the scope (`tests/unit/test_answer_key.py`). F-32 (password resets per day)
  holds for the whole corpus; F-40 holds for tenant B, and since v1.1 its phrases cover the
  maximum length and the VPN idle timeout as well as leavers, kiosks and exceptions; F-87 (new in
  v1.1) holds for the whole corpus on a cap on enrolled devices. A phrase list proves that those
  phrases are absent; the author also read each tenant's documents for the topic. G-26 may quote
  NIST SP 800-63B-4, section 3.1.1.2, on the maximum length, attributed and never as Mirrowfen's
  rule (D-03).
- **Reference answers** follow the answer key's, with their citations. The café case (G-21, F-86)
  expects the line manager's written authorisation as well as the VPN and screen rules: a bare yes
  fails (the answer key's note). Tenant B reference answers give only Mirrowfen's values. Whether
  an answer matches its reference is S5's to judge; S4 reads the label, the citations and the
  strings.
- **Answer-key additions (decision D2, additions only):** the locations of the group members (FAQ
  Q3, Q4, Q5, Q7, Q10 and Q11 on F-53; Device Policy 6.2 on F-17), F-40's extended silence
  phrases, F-86 (working from a café or a hotel, with its three conditions and FAQ Q6), F-87 (the
  device-cap omission), and, after the labels judge's review, the value "blocklist of common and
  breached passwords" on F-53's FAQ Q1 location, the restatement of the Password and Authentication
  Standard 4.3 that the groups of G-02 and R-Q33 rely on (S4-L4; the user's answer on D-c). No
  existing value, label or reference answer of the answer key changed, and the `canaries` and
  `answer_must_not_contain` lists are as they were.
- **G-33's reference answer** gives the route only (the IT Service Desk, the identity check, the
  temporary access pass to register a new factor): the pass's 8 hours and single use are F-31's
  value, which FAQ Q4, a member of G-33's group, does not restate (S4-L3; the user's answer on
  D-b).

### Second labeller and agreement

The S4 labels judge, a model in a context of its own, labelled every behaviour case's decision
blind before it opened this file or the golden file, and sealed its labels first: its
`blind-labels.jsonl` has sha256
`e8c936c17472f3a5dc456159a7db9c5285eb823f2187030038dad0d86450ed76`, sealed on 2026-10-19 at
09:45:55 WEST. **What the second labeller had:** each case's id, tenant and question, and the
answer key, TEST-PLAN sections 2, 3 and 7, SPEC, the register and the 18 register documents. The
answer key carries each feature's expected label and notes that say which question shape takes
which label, so the agreement shows that the 40 questions fit the key's labels; it is weaker
evidence than a second person labelling from the documents alone would give (the labels judge's
S4-L1). Lab practice: production uses a second person and an agreement threshold (how-to 02,
step 3); the repository has no threshold, so S4 reports the agreement and sets none.

| Measure | Value |
|---|---|
| Labels that match (of 40) | 40 |
| Observed agreement | 1.0000 |
| Chance agreement (from the marginals 25 / 9 / 3 / 3 on both sides) | 0.4525 |
| Cohen's kappa | 1.0000 |
| Disagreements and how each was settled | none: no label and no first feature differs |

### Review

Each part has an independent review against the chunk text and the answer key: S2's label review
for the retrieval questions (S2 ledger) and S4's labels judge for the behaviour cases and the
groups (S4 ledger). Their findings go into the ledgers, not this file.

## Splits

- **Retrieval questions:** about two thirds dev and one third test, stratified by
  `question_kind`: each kind with three questions has two in dev and one in test, each kind with
  two has one in each, and tenant-b (four questions) has three in dev and one in test.
- **Behaviour cases:** 27 dev and 13 test, stratified by mix kind and by expected label: every mix
  kind and every label has at least one test case, and the three S3 probes are in dev. The test
  split holds one refuse-and-help case (G-13) and one flag-conflict case (G-30).
- **dev** is for development, the baselines, the gates' margins and any later prompt work.
- **test** runs only in nightly, release and the capstone. It is never used to choose a
  configuration, a threshold or a prompt. If a test case or question is ever used for tuning, it
  moves to dev, a new one replaces it in test, and the version goes up.
- **Held out by question, not by feature or section.** The pack plants one value per feature, so a
  test case can share its feature with a dev question or case: G-04 with R-Q04, G-15 with R-Q29,
  G-18 with R-Q24, G-24 with P-03, G-25, G-26 and G-28, G-30 with R-Q18 and G-29, G-37 with P-01
  and P-02; in the other direction, the test questions R-Q03, R-Q15, R-Q17, R-Q23 and R-Q26 share a
  feature with dev cases. The overlap is wider at section level: a test case's primary section can
  be labelled by dev lines (A-PWD-V2 4.3 by R-Q33 for G-02; Table 1 of A-PWD-V2 by G-03, G-12,
  R-Q04, R-Q05 and R-Q22 for G-04 and G-32; A-PWD-V2 4.4 by G-22, G-29, R-Q08, R-Q18 and R-Q21 for
  G-30; A-EXC 5.1 by G-19, R-Q24 and R-Q25 for G-18). G-04 is also a close paraphrase of R-Q04 in
  other words; it stays (the labels judge's S4-L9; the user's answer on D-f).

## Licensing

The questions, labels and reference answers are written by the ai-testing-rag-lab authors and
released under the
[Creative Commons Attribution 4.0 International licence](https://creativecommons.org/licenses/by/4.0/)
(CC BY 4.0), the same licence as the corpus files marked `source: ours`
([`corpus/LICENSE.md`](../corpus/LICENSE.md)). Attribution: "ai-testing-rag-lab authors", with a
link to this repository.

Lab material: Halvenroot and Mirrowfen, their policies and every value in the cases are
fictional. The external excerpts the labels point to keep their own licences (NIST public, OGL
v3.0), as listed in `corpus/SOURCES.md`.

## Maintenance

| Version | Date | Stage | What changed | sha256 of golden.v1.jsonl |
|---|---|---|---|---|
| v1 | 2026-10-06 | S2 | 34 retrieval questions | `ffb8c5a54b2277bd90efd9bdebda4b91494eb472c3c604b6f057146b19436104` |
| v1.1 | 2026-10-19 | S4 | 40 behaviour cases; label groups on seven retrieval questions, whose feature ids gain F-53; after the labels judge's review, G-33's reference answer trimmed to the route (made before the sign-off, so still v1.1) | `5f8cdaf1878336710335adca98d5691b2ba6e0432698510642c9c7b3dc62e59a` |

- A dataset version is a build input like the model and the prompt: every run manifest records
  the file's sha256, so a run names its version. The latest row above carries the sha256 of the
  committed file, and `check-dataset` refuses the file when it does not.
- Adding, removing or relabelling a case, changing a question's wording, labels or split, or
  regrouping labels makes a new version. A label that a review finds wrong is fixed with the case
  id in the stage ledger.
- `check-dataset` is the hard stop on this file before every run: the shapes of each label, the
  silence proofs, the mix and the split (S4 plan, "check-dataset: the hard stop").
- S4b plans a v2 of about 120 cases.

## Known limits

- **Synthetic, one author.** One author wrote the behaviour cases, their labels and their
  reference answers from the answer key, as S2's author did for the retrieval questions. They are
  closer to the planted features than real traffic would be, and no real user asked them.
- **Small.** 40 behaviour cases is far below how-to 02's "about 30 cases per failure mode": most
  kinds have one to three cases per label. One case moves a rate by about 3.7 points on dev (27)
  and about 7.7 points on test (13); on the retrieval part, one question moves hit rate by about
  4.5 points on dev (22) and about 8 points on test (12). Every interval is wide, which is why
  each run reports n and an interval with every metric. S4b grows the set.
- **Features shared across splits** (see [Splits](#splits)): a test case is new as a question,
  not as a planted value.
- **F-57 at k = 5.** The containment procedure of the Account-Compromise Incident Runbook is seven
  sections (5 and 5.1 to 5.6), more than the retriever's k = 5, so no run can retrieve all of it
  for G-20. The case stays, its labels stay whole, and S4 does not tune k or the chunker for it.
  The Runbook's worked example, A.3, narrates the six steps in order in one chunk; it is a
  restatement left out of the labels ([Label groups](#label-groups), "Not members"), so a model
  that answers from A.3 alone gives every step and scores no citation hit.
- **One D-03 case.** Only G-26 has `may_quote`, and it is in dev. Whether the quote is attributed
  in words is S5's to judge.
- **Silence is proven by phrases.** A `must_not_appear` list shows that its phrases are absent
  from the scope, not that no sentence answers the question in other words.
- **Restatements left out of groups:** the MFA Standard 8 and the Privileged Access Standard 9 for
  G-34, and the Runbook's worked example A.3 for G-20 ([Label groups](#label-groups)).
- **Section labels and multi-chunk sections.** One labelled section has two chunks at the default
  settings: NIST SP 800-63B-4, section 3.1.1.2 (R-Q21, G-22, and G-26's quote). The expiry and
  maximum-length sentences are in its first chunk. A label resolves to every chunk of its section
  (`raglab.evals.golden`, `raglab.evals.metrics`), and the section counts as found when any one of
  them is in the top k, so the measure is generous there; S5's judged metrics check the answer
  itself.
- **Pointer sections are labelled.** Cross-reference labels include the pointer section, so a
  retriever that jumps straight to the target scores full hit@k but lower recall@k.
- **Scanned page.** The cases on the scanned annex (R-Q16, R-Q17, G-08) depend on OCR. An OCR
  change that alters the annex text can change their result without any retrieval change.
- **English only**, and only the identity and access topics of a fictional company.
