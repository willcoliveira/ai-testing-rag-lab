"""Prompts are versioned code: each module has a VERSION, its text, the answer schema and a
reviewed snapshot (tests/generation/test_prompt_snapshot.py). A change to the text without a new
VERSION fails that test.

`CURRENT` is the one current prompt, chosen here in code and never in a config (S4: the prompt is
code, not config, and the consistency gate checks its fingerprint on its own). The pipeline, the
generation suite, the position suite and, through the pipeline, the API read it, so a run record
always names the prompt it was made with. Every version stays importable for its records.
"""

from raglab.generate.prompts import answer_v2

CURRENT = answer_v2
