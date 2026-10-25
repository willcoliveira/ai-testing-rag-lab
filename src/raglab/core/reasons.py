"""The fixed reason key of a guard's decision (S9): the key the API answers with
(raglab.api.app.REASONS) and the one a trace records. Never a guard's own text, which can carry
what the guard stopped (a refused character, another tenant's chunk id): that goes to the server
log only. Standard library only.

A refusal at input is keyed by the guard that refused it: "tenant" for the tenant guard and for the
pipeline's own fail-closed check, and otherwise "input" unless INPUT_KEYS names another key. A
decision after retrieval or on the output withholds the answer: "blocked". A new guard (S7) adds
its key to REASONS, and to INPUT_KEYS when its refusal at input needs a key of its own;
tests/obs/test_guard_traces.py holds every default guard's key to REASONS.
"""

from raglab.core.types import GuardEvent

INPUT_KEYS = {"tenant": "tenant", "pipeline": "tenant", "input-limits": "input"}
DEFAULT_INPUT_KEY = "input"
WITHHELD_KEY = "blocked"


def reason_key(event: GuardEvent) -> str:
    """The fixed key of one guard decision."""
    if event.stage != "input":
        return WITHHELD_KEY
    return INPUT_KEYS.get(event.guard, DEFAULT_INPUT_KEY)
