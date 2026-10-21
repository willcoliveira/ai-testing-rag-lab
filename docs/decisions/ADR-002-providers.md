# ADR-002: Providers for the generator and the judge

**Status:** accepted: local only for now (D6, 2026-10-21). **Date:** 2026-10-21. **Stage:** S5.

## Context

Until S5 every model ran on the maintainer's Mac: the generator (NVIDIA's Nemotron 3.5 Lightning,
`config/local-ollama.toml`) and, since S5, an own LLM judge (Mistral's Ministral 3 14B,
`config/judge-local.toml`, prompt judge-v2, criteria in docs/CRITERIA.md). No provider key exists.
S5 measured every call's tokens, so this record turns them into a monthly cost per option from a
dated price table, for the user to choose what, if anything, to sign up for (D6). The hosted half
of S5 (AC16 to AC21) follows that choice.

What S5 showed about the local judge (S5 ledger): it ran all 592 calls of the judged baseline
with every token count reported and all 19 canaries on their side, at a p50 of 5,522.768 ms a
call, and the judged run of the dev slice took 3,380.41 s of the Mac's awake time. Its judged
numbers are uncalibrated until S6, so nothing judged is gated yet. S5's judge sessions run on the
maintainer's Mac only; a judged gate in CI needs a judge that CI can call.

**Lab practice.** Costs here come from local token counts and a price table read by hand.
Production reads the providers' own usage and billing exports.

## Options

The six options of `config/cost-assumptions.toml`, in three kinds:

1. **Local only:** the local generator and the local judge; no key, no spend, no judged gate in
   CI.
2. **The local generator with a hosted judge:** Claude Haiku 5.5, gpt-5-mini or Claude Sonnet 5.5
   as the judge.
3. **A hosted generator with a hosted judge of another family:** Claude Haiku 5.5 with a
   gpt-5-mini judge, or gpt-5-mini with a Claude Haiku 5.5 judge.

In every option the judge's family differs from the generator's.

## The estimate

`make cost JUDGED=20261021T081852Z-judge-local-dev-5aa0ec5`, that is `raglab cost` over the
published judged baseline (judge-v2), the price table and the assumptions. Its output, word for
word (`tests/unit/test_adr.py` renders it again from the committed record and table, and fails if
a number here differs):

Tokens: 20261021T081852Z-judge-local-dev-5aa0ec5 (judged; the generator's from its source 20261019T172035Z-generation-local-ollama-dev-97011a7), 147 case-trials.
Prices: config/prices.toml, price_table_date 2026-10-21. Assumptions: config/cost-assumptions.toml.

| Role | Calls | Prompt | Completion | Unreported | Prompt per call | Completion per call | Largest prompt | Prompt per case-trial | Completion per case-trial |
|---|---|---|---|---|---|---|---|---|---|
| generator | 147 | 153210 | 16138 | 0 | 1042.2 | 109.8 | 1304 | 1042.2 | 109.8 |
| judge | 433 | 316158 | 51092 | 0 | 730.2 | 118.0 | 1431 | 2150.7 | 347.6 |
| judge_checks | 140 | 115988 | 16691 | 0 | 828.5 | 119.2 | 1309 | 789.0 | 113.5 |
| canaries | 19 | 14224 | 1688 | 0 | 748.6 | 88.8 | 1174 | - | - |

Per case-trial: the role's tokens over the run's case-trials (none when a call reported none); the canaries run once per run.

| Run type | Runs a month | Cases | Trials | Judged |
|---|---|---|---|---|
| eval-on-change | 10 | 49 | 3 | yes |
| nightly | 30 | 20 | 3 | no |
| weekly | 4 | 74 | 5 | yes |
| release | 1 | 25 | 3 | yes |

| Option | Generator per call | Judge per call | Per case-trial | Per run | Checks per run | Per month |
|---|---|---|---|---|---|---|
| local only | $0.0000 | $0.0000 | $0.0000 | $0.0000 | $0.0000 | $0.0000 |
| local generator, Claude Haiku 5.5 judge | $0.0000 | $0.0001 | $0.0004 | $0.0594 | $0.0199 | $1.21 |
| local generator, gpt-5-mini judge | $0.0000 | $0.0004 | $0.0012 | $0.1882 | $0.0624 | $3.83 |
| local generator, Claude Sonnet 5.5 judge | $0.0000 | $0.0026 | $0.0078 | $1.19 | $0.3989 | $24.21 |
| Claude Haiku 5.5 generator, gpt-5-mini judge | $0.0002 | $0.0004 | $0.0014 | $0.2115 | $0.0624 | $4.60 |
| gpt-5-mini generator, Claude Haiku 5.5 judge | $0.0005 | $0.0001 | $0.0009 | $0.1300 | $0.0199 | $3.53 |

How to read it: a call costs (prompt tokens × the input price + completion tokens × the output
price) / 1,000,000; a case-trial is its generator call and its judge calls; a run is its
case-trials and one canary set; "Checks per run" is the judge's repeatability and order checks,
priced apart and **not counted in the month total**: they are S5's measurements of the judge, not
part of a routine run; a month sums the run types' runs, each its generator calls, its judge calls
when the run type is judged and one canary set (`src/raglab/evals/cost.py`, tested on
hand-computed values). The runs a month are assumptions, the main plan's gate map and its budget
scenario B, and the user's to change.

## The prices

From `config/prices.toml`, US dollars per million tokens, at the tier every S5 prompt falls in
(each far below Claude Haiku 5.5's 100,000-token threshold and gpt-6-luna's 272,000). Read on
2026-10-20 and again on 2026-10-21 for this record: no row changed.

| Model | Input | Output | Batch input / output | Source |
|---|---|---|---|---|
| Claude Haiku 5.5 (`claude-haiku-5-5`) | $0.10 | $0.50 | $0.05 / $0.25 | [A1], [A2] |
| Claude Sonnet 5.5 | $2 | $10 | $1 / $5 | [A1] |
| Claude Opus 5.5 | $4 | $20 | $2 / $10 | [A1] |
| Claude Haiku 4.5 (the main plan's row) | $1 | $5 | $0.50 / $2.50 | [A1] |
| gpt-5-nano | $0.05 | $0.40 | $0.025 / $0.20 | [O1] |
| gpt-5-mini | $0.25 | $2.00 | $0.125 / $1.00 | [O1] |
| gpt-6-luna | $0.10 | $0.50 | $0.05 / $0.25 | [O1] |

The estimate uses the standard prices; the batch prices are half the standard ones in every row.

## What the estimate cannot know

- **Tokenizers differ.** The tokens are the local models' counts. Each provider counts the same
  text its own way; Claude Haiku 5.5's page says it "uses the same newer tokenizer as Claude 4.7
  and later models, so the same text counts as approximately 30% more tokens than on Claude Haiku
  4.5" [A2]. The estimate is a proxy until a hosted run measures the provider's own usage (AC17,
  AC20).
- **Hosted answers and verdicts differ in length** from the local models', and so do their
  tokens.
- **A hosted judge's settings differ.** The local judge runs at temperature 0 with a seed; its 92
  repeated verdicts agreed in every pair. Claude Haiku 5.5's page says to omit `temperature`,
  `top_p` and `top_k` (values that return a 400 error) [A2], so a Haiku 5.5 judge's repeatability
  is measured again, not assumed.
- **DeepEval-style metrics cost more calls.** DeepEval 4.3.1's `FaithfulnessMetric` made 4 calls
  per evaluation against the local judge (16 calls for 4 evaluations: 16,856 prompt and 1,974
  completion tokens), and `HallucinationMetric` 2 (4 calls for 2 evaluations: 3,802 and 288),
  where the own judge makes one call per criterion; those scores were not usable in S5 (S5
  ledger), and this estimate prices the own judge only.
- **The runs a month are assumptions,** and the prices change: the table names its read date, and
  a decision reads the pages again.

## Recommendation

**The local generator with a Claude Haiku 5.5 judge** (the second row: $1.21 a month at the
assumed volume), keeping the local judge for offline work and as the fallback:

- it is the cheapest hosted judge priced here, and a judge of another family than the generator;
- it gives S6 a judge that can run in CI, where its calibration on human labels can turn the
  judged criteria into gates;
- the local judge's caveats in S5 (`relevant` failing short right answers, `grounded` failing
  some "the documents don't say" answers; S5 ledger) are what S6 measures, and if Haiku 5.5's
  agreement with the human labels is too low, Claude Sonnet 5.5 is the next judge to price
  ($24.21 a month in the same table);
- the generator stays local: hosting it is not needed to judge, and every hosted generator option
  costs more a month than this one.

Local only remains a sound choice if S6 should calibrate the local judge first; then no key is
needed in S5, and AC16 to AC21 become "not applicable, by D6".

## Decision (D6)

On 2026-10-21, at about 11:02 WEST, asked through the orchestrator's prompt "D6: what should S5
sign up for (ADR-002's options above)?", the user wrote, in their own words rather than a listed
option, verbatim:

> let's use a local model for now and then we need to identify all the signups and everything that
> I need to do

**Local only for now.** No provider is signed up for in S5, and no key exists: the generator and
the judge stay on the maintainer's Mac. The recommendation above is not taken now; it stays here
for when the hosted judge is revisited.

## Consequences

- **In S5:** nothing hosted is built or signed up for; AC16 to AC21 are "not applicable, by D6",
  and the pull request does not wait for a sign-up. The judged numbers stay local and reported.
- **Later:** "for now" defers the hosted half; it does not cancel it. The hosted judge is
  revisited after the list of sign-ups and tasks the user asked for, which the orchestrator
  compiles with the user; this record is the starting point then, with its estimate re-run from
  the records and prices of that day.
- **When a provider is chosen then:**
  - **keys** only in a local `.env` (gitignored) or a GitHub Environment secret, never in the
    repo or a config file;
  - **a hard spend limit at the provider, set before the first call:** an Anthropic workspace
    other than the default one, or an OpenAI project, with its own limit. Neither page offers a
    limit per key, and OpenAI's says enforcement "is not instantaneous" [A3], [O2] (as the S5 plan
    read them on 2026-10-20). A per-run budget abort from the price table backs it (AC18);
  - **CI:** the hosted judge's contract tests run with the key (marker `live`, skipped without
    it); judged gates move to CI only after S6 calibrates the judge.

## Sources

- [A1] Anthropic, pricing: https://platform.claude.com/docs/en/about-claude/pricing (read
  2026-10-20 and 2026-10-21)
- [A2] Anthropic, Claude Haiku 5.5 overview:
  https://platform.claude.com/docs/en/models/haiku-5-5/overview (read 2026-10-20 and 2026-10-21)
- [A3] Anthropic, rate limits and spend limits: https://platform.claude.com/docs/en/api/rate-limits
  (read 2026-10-20, S5 plan)
- [O1] OpenAI, pricing: https://developers.openai.com/api/docs/pricing (read 2026-10-20 and
  2026-10-21)
- [O2] OpenAI, spend limits: https://developers.openai.com/api/docs/guides/spend-limits (read
  2026-10-20, S5 plan)
