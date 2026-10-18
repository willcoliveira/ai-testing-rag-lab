"""Prompts are versioned code: each module has a VERSION, its text, the answer schema and a
reviewed snapshot (tests/generation/test_prompt_snapshot.py). A change to the text without a new
VERSION fails that test."""
