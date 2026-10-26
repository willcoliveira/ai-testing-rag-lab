"""The fixed reason key of a guard's decision (S9): the key the API answers with
(raglab.api.app.REASONS), the one a trace records and the one the server log records. Never a
guard's own text, which can carry what the guard stopped (a refused character, another tenant's
chunk id, a credential the secrets and personal-details guard caught): no response, trace or log
line holds it (S7's merge with S9, which reverses S9's "that goes to the server log only"); a run
record keeps it in its guard events. Standard library only.

A refusal at input is keyed by the guard that refused it: "tenant" for the tenant guard and for the
pipeline's own fail-closed check, "injection" for the input injection detector (S7), and otherwise
"input" unless INPUT_KEYS names another key. A decision after retrieval or on the output withholds
the answer: "blocked". A new guard (S7) adds its key to REASONS, and to INPUT_KEYS when its refusal
at input needs a key of its own; tests/obs/test_guard_traces.py holds every default guard's key to
REASONS.

A drop step (S7, the register filter) is the one decision that neither refuses nor withholds: it
leaves chunks out of the prompt and the answer goes on. Its events are an Outcome's `dropped`, never
its `events`, and they take drop_key: "dropped". A GuardEvent carries only its guard and its stage,
and a drop fires at "retrieved", the stage of the withholding events too, so reason_key is called
only for an Outcome's events and drop_key only for its dropped events.
"""

from raglab.core.types import GuardEvent

INPUT_KEYS = {
    "tenant": "tenant",
    "pipeline": "tenant",
    "input-limits": "input",
    "injection": "injection",
}
DEFAULT_INPUT_KEY = "input"
WITHHELD_KEY = "blocked"
DROPPED_KEY = "dropped"


def reason_key(event: GuardEvent) -> str:
    """The fixed key of one decision that refused or withheld (an Outcome's events)."""
    if event.stage != "input":
        return WITHHELD_KEY
    return INPUT_KEYS.get(event.guard, DEFAULT_INPUT_KEY)


def drop_key(event: GuardEvent) -> str:
    """The fixed key of one drop step's decision (an Outcome's dropped events): the answer went
    on without the chunks it left out. Every drop is keyed alike; its text is never read."""
    del event
    return DROPPED_KEY
