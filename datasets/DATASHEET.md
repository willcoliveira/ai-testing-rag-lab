# Datasheet: golden set v1, retrieval questions

File: [`golden.v1.jsonl`](golden.v1.jsonl). Version **v1**, stage S2 (2026-10-06).
Licence: **CC BY 4.0** (see [Licence](#licence)).

This datasheet describes only the retrieval part of the golden set (`kind: retrieval`). S4 adds
the behaviour cases (`kind: behaviour`) to the same file and extends this datasheet.

## Purpose

The questions measure **retrieval alone**: for each one, did the retriever return the chunks the
answer needs? They are scored against labelled chunks with hit@k, MRR and recall@k, so no model
judges anything. The same questions are used to compare retrieval configurations fairly (dense,
hybrid with BM25, a different chunk size) with paired differences, and the dev split feeds the
pr-fast no-regression gate on recall@5.

The questions do not test answers, decision labels, abstention or refusals. Those are S3 and S4.

## What a line holds

| Field | Meaning |
|---|---|
| `id` | `R-Q01` to `R-Q34`, stable; a retired question keeps its id and is never reused |
| `kind` | always `retrieval` in this part |
| `tenant` | `tenant-a` (Halvenroot) or `tenant-b` (Mirrowfen): the asker's tenant, so the retriever's tenant filter applies |
| `question` | the question as a user would type it |
| `split` | `dev` or `test` |
| `question_kind` | the retrieval kind the question tests (table below) |
| `feature_ids` | the answer-key features (`corpus/answer-key.yaml`) the question targets |
| `relevant` | the sections the answer needs, as `{doc_id, section_id}`: document ids from `corpus/register.yaml`, section ids as the leading id of the heading (the `section` field of `corpus/inventory.snapshot.json`) |

Labels are kept at **section** level, not chunk level. The pipeline resolves each section to its
chunk ids through the inventory, so a re-chunk updates the labels mechanically, and a test fails if
a labelled section stops existing.

## How the questions were written

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

## How the labels were made

- A section is **relevant** when the answer cannot be given, or cannot be cited completely,
  without it. That includes the pointer section of a cross-reference (the section that sends the
  reader elsewhere) as well as its target, because the answer cites both.
- **Multi-hop** questions list one section per hop (two or three).
- **Version-conflict** questions ask about history, so both the current section (A-PWD-V2) and the
  superseded one (A-PWD-V1) are relevant, as in feature F-04's expected retrieval. R-Q19 and
  R-Q20 also ask about history, so they label version 1.0 too. That differs on purpose from the
  answer key's `expected_retrieval` for F-05 and F-07, whose golden cases ask for the current
  value only. A current-value question (R-Q33, built on F-06) labels only the current version.
- **External-conflict** questions label the company section and the external excerpt's section.
  R-Q21 and R-Q23 are the planted conflict (F-08: periodic expiry). R-Q22 is the attribution
  variant (F-13): NIST's limit of 100 attempts is an upper bound, so it does not contradict the
  company's limit, but the question needs both the company table and the excerpt.
- **Exception questions** R-Q24 and R-Q25 label the register table (Policy Exceptions Process 5.1),
  the section that gives the register's effect or expiry (5.2 or 4.2), and the rule being
  excepted. R-Q26 asks only which exceptions are in force, so it labels the register table alone.
- **Feature ids for a rule used outside its feature.** R-Q15 (an employee who leaves with
  immediate effect) lists F-22 next to F-65 because F-22 is the feature that locates the MFA
  revocation rule (MFA Standard 6.1); F-22's own case is about a contractor.
- Every label was checked by script: the document is in the register, the section exists in the
  inventory, a tenant B question labels only tenant B documents, a tenant A question labels only
  tenant A or shared documents, and every feature id exists in the answer key. All but one label
  is a location of one of its question's features. The exception is R-Q09's pointer section
  (Account Lifecycle Policy 5.4), which no feature lists. R-Q09 targets F-73 (how long a VPN
  certificate is valid) and also asks what happens to the certificate at leaving, which the same
  target section answers.
- **Review.** S2's plan has an independent reviewer check every label against the chunk text.
  The result of that review goes into the S2 ledger, not this file.

## Mix by kind and split

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
- 16 questions have two or more relevant sections, and 18 have one.

## Split

- About two thirds dev and one third test, stratified by `question_kind`: each kind with three
  questions has two in dev and one in test, each kind with two has one in each, and tenant-b
  (four questions) has three in dev and one in test.
- **dev** is used for development, for comparing configurations and for the pr-fast recall@5
  gate.
- **test** runs only in nightly, release and the capstone. It is never used to choose a
  configuration, a threshold or a prompt. If a test-split question is ever used for tuning, it
  moves to dev, a new question replaces it in test, and the version goes up.

## Versioning

- **v1** (this file): 34 retrieval questions, written in S2.
- Changing a question's wording, labels or split makes a new version. Fixing a label that the
  review finds wrong is recorded in the stage ledger, with the question id.
- S4 adds the behaviour cases to `golden.v1.jsonl`. S4b plans a v2 of about 120 cases.

## Known limits

- **Small.** At 22 dev and 12 test questions, one question moves hit rate by about 4.5 points on
  dev and about 8 points on test. Intervals are wide, which is why each run reports a bootstrap
  interval and n with every metric.
- **One author.** The same author wrote the questions and the labels, from the answer key. They
  are closer to the planted features than real user traffic would be.
- **Near-duplicate FAQ chunks are not labelled.** The Identity and Access FAQ repeats some primary
  values (feature F-53). When a question's answer also appears in a FAQ entry, only the primary
  section is labelled, so a retriever that returns only the FAQ chunk scores a miss. This affects
  R-Q14 (FAQ Q3), R-Q18, R-Q21 and R-Q23 (FAQ Q2), R-Q19 and R-Q33 (FAQ Q1), and R-Q25 (FAQ Q7).
  Adding the FAQ sections to `relevant` would be wrong, because recall would then demand both
  copies. The fix is a schema choice that is still open: groups of labels where any one member
  counts.
- **Section labels and multi-chunk sections.** One labelled section has two chunks at the default
  settings: NIST SP 800-63B-4, section 3.1.1.2 (R-Q21). The expiry sentence that R-Q21 needs is
  in its first chunk. How a section with several chunks counts towards recall is decided where
  labels are resolved, and stated there.
- **Pointer sections are labelled.** Cross-reference labels include the pointer section, so a
  retriever that jumps straight to the target scores full hit@k but lower recall@k.
- **Scanned page.** The two scanned-page questions depend on OCR. An OCR change that alters the
  annex text can change their result without any retrieval change.
- **English only**, and only the identity and access topics of a fictional company.

## Licence

The questions and labels are written by the ai-testing-rag-lab authors and released under the
[Creative Commons Attribution 4.0 International licence](https://creativecommons.org/licenses/by/4.0/)
(CC BY 4.0), the same licence as the corpus files marked `source: ours`
([`corpus/LICENSE.md`](../corpus/LICENSE.md)). Attribution: "ai-testing-rag-lab authors", with a
link to this repository.

Lab material: Halvenroot and Mirrowfen, their policies and every value in the questions are
fictional. The external excerpts the labels point to keep their own licences (NIST public, OGL
v3.0), as listed in `corpus/SOURCES.md`.
