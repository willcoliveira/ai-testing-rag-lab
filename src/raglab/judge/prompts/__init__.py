"""Judge prompts are versioned code, as the answer prompts are: each module has a VERSION, its
texts, the criteria's pass and fail rules, the verdict schema and a reviewed snapshot
(tests/judge/test_judge_prompt.py). A change to the text without a new VERSION fails that test."""
