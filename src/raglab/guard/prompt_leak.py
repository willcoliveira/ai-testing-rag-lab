"""The prompt-leak guard (S7, R-20; OWASP LLM08, Hidden Context Exposure, in
docs/THREAT-MODEL.md): an answer that shares a run of N or more words with the system prompt is
withheld (status blocked, label abstain, no text), apart from the phrase the prompt tells the model
to say.

Words are runs of letters and digits (an apostrophe inside a word kept), in lower case, so case
and punctuation do not hide a copied run. The phrase the prompt tells the model to say ("the
company's documents do not say", rule 3) is taken out of the answer before the runs are counted,
so saying it never counts towards a run.

**N = 8, set from the prompt text alone** (S7 ledger, before the replay): the longest run the
prompt repeats inside itself is 5 words ("a passage with status reference"), so every run of 6 or
more is the prompt's own; and the longest run a correct answer may share with it is the abstain
label's own description, "the passages do not state the answer", 7 words. So a run of 8 words is
the shortest that no correct answer needs. The event names the rule and the run's length, never
the words.

Lab practice: a word-run match catches a copied prompt, not a paraphrase. Production would keep
secrets out of the prompt in the first place and add a canary token to it.
"""

import re
from collections.abc import Sequence

from raglab.core.types import Answer, GuardEvent, ScoredChunk
from raglab.guard.noop import NoopGuardrail

N = 8
WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
# the phrase the prompt tells the model to say (answer-v1 rule 3), never counted
TOLD_TO_SAY = ("the company's documents do not say",)
_GAP = "\x00"


def words(text: str) -> list[str]:
    return WORD.findall(text.replace("\u2019", "'").lower())


class PromptLeakGuard(NoopGuardrail):
    def __init__(self, system: str, n: int = N, told_to_say: Sequence[str] = TOLD_TO_SAY) -> None:
        if n < 2:
            raise ValueError(f"n must be at least 2 words, not {n}")
        self.n = n
        self.system = system
        self.told_to_say = tuple(told_to_say)
        self._prompt = words(system)
        self._at: dict[str, list[int]] = {}
        for position, word in enumerate(self._prompt):
            self._at.setdefault(word, []).append(position)

    @property
    def name(self) -> str:
        return "prompt-leak"

    def rules(self) -> object:
        return {"n": self.n, "system": self.system, "told_to_say": list(self.told_to_say)}

    def _kept(self, text: str) -> list[str]:
        """The text's words, each phrase it is told to say replaced by a gap no run crosses."""
        found = words(text)
        told = [words(p) for p in self.told_to_say]
        kept: list[str] = []
        i = 0
        while i < len(found):
            phrase = next((t for t in told if found[i : i + len(t)] == t), None)
            if phrase:
                kept.append(_GAP)
                i += len(phrase)
            else:
                kept.append(found[i])
                i += 1
        return kept

    def longest_shared(self, text: str) -> int:
        """The longest run of words the text shares with the system prompt, once the phrase it
        is told to say is taken out."""
        kept = self._kept(text)
        best = 0
        for start, word in enumerate(kept):
            for p in self._at.get(word, ()):
                length = 0
                while (
                    start + length < len(kept)
                    and p + length < len(self._prompt)
                    and kept[start + length] == self._prompt[p + length]
                ):
                    length += 1
                best = max(best, length)
        return best

    def check_output(self, answer: Answer, retrieved: Sequence[ScoredChunk]) -> GuardEvent | None:
        for text in (answer.text, answer.conflict.note if answer.conflict else ""):
            if (length := self.longest_shared(text)) >= self.n:
                return GuardEvent(
                    self.name,
                    "output",
                    f"rule prompt-run: the answer shares a run of {length} words with the "
                    f"system prompt (the limit is {self.n})",
                )
        return None
