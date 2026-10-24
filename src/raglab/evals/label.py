"""The blind label CLI (S6, `raglab label`): each item of a calibration's sample shown exactly as
the judge saw it, and the maintainer's label recorded in the judge's schema
(docs/plans/2026-10-23-s6-judge-calibration.md, JC5; the guide is datasets/calibration/README.md).

**What it shows.** Each item is rebuilt with `raglab.evals.judged.judge_item` from the source
generation run and the corpus, through `judged.inputs`, the same code the judged run builds its
calls with (the corpus and dataset sha256 checked against the source first): the judge prompt's
user message for that call, so the criterion's pass and fail rules in the judge prompt's words
(which tests/unit/test_criteria.py holds equal to docs/CRITERIA.md), the question, each passage
with its id, document, version, section and status, and the answer, as the judge read them.

**What it never shows, and never opens.** It reads the sample, the bar, the source run and the
corpus, and never the judged record's lines (`cases.jsonl`): the sample holds no verdict and no
stratum, so nothing the judge said about an item (its verdict, quote, passage ids or reason) can
reach the screen. A re-label shows neither the first labels nor the judge's verdicts.

**What it records** (raglab.evals.calibration.LABEL_FIELDS), after each item: the verdict (pass or
fail; ambiguity is a flag on a binary label, never a third class), a quote that is a span of the
answer (whitespace runs read as one space, as the judge's quote check reads it), the passage ids
among those shown (by number or id), a one-sentence reason, the ambiguous flag, the shown answer's
sha256, the time, and the seconds spent on the item. It resumes at the first item without a label;
`redo` labels one item again; `seal` writes the file's sha256 and time once every item is labelled,
and after the seal it refuses any change, as `raglab calibrate` refuses labels that differ from
their seal. The re-label (D3) opens only `relabel.min_gap_hours` after the labels' seal.

It needs no model, no Ollama and no network.
"""

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from raglab.core.types import JudgeItem, Status
from raglab.evals import calibration, judged, judged_record
from raglab.evals.calibration import CalibrationError, Item, Json, Sample
from raglab.ingest import pipeline

type Ask = Callable[[str], str]
type Say = Callable[[str], None]

QUIT = "q"


@dataclass(frozen=True)
class Shown:
    """One item and the judge call it was: the inputs the judge saw, and the answer."""

    item: Item
    judge_item: JudgeItem
    answer: str

    @property
    def ids(self) -> tuple[str, ...]:
        return self.judge_item.shown_ids()


def shown_items(
    root: Path,
    sample: Sample,
    items: Sequence[Item],
    inventory: pipeline.Inventory | None = None,
) -> list[Shown]:
    """Each item rebuilt as the judge saw it, from the source run the sample pins and the corpus;
    never from the judged record."""
    run_id = str(sample.pins["source_run"])
    source_dir = root / calibration.PUBLISHED / run_id
    if not source_dir.is_dir():
        raise CalibrationError(f"the source run {run_id} is not published")
    built = judged.inputs(source_dir, root, inventory)
    by_answer = {(str(s["case_id"]), cast(int, s["trial"])): s for s in built.sources}
    seed = cast(int, sample.pins["judge_seed"])
    out: list[Shown] = []
    for item in items:
        source = by_answer.get((item.case_id, item.trial))
        if source is None:
            raise CalibrationError(
                f"item {item.order}: {item.case_id} trial {item.trial} is not in {run_id}"
            )
        if source["status"] != Status.OK.value:
            raise CalibrationError(f"item {item.order}: the answer was withheld, so never judged")
        reference = judged_record.reference_of(source, built.refs)
        judge_item = judged.judge_item(item.criterion, source, built.passages, reference, seed)
        out.append(Shown(item, judge_item, str(source["answer"])))
    return out


def render(shown: Shown, total: int, prompt: str, title: str = "Item") -> str:
    """The item as the judge saw it: its prompt's user message for the call (the criterion's rules,
    then each input the criterion sees), and the shown passages by number."""
    _, user = judged_record.PROMPTS[prompt].build(shown.judge_item)
    lines = [f"===== {title} {shown.item.order} of {total}: {shown.item.criterion} =====", "", user]
    if shown.ids:
        lines += ["", "Passages shown, by number:"]
        lines += [f"  {n}. {chunk_id}" for n, chunk_id in enumerate(shown.ids, start=1)]
    return "\n".join(lines) + "\n"


def _ask(ask: Ask, question: str) -> str | None:
    """One answer, stripped; None at the end of input."""
    try:
        return ask(question).strip()
    except EOFError:
        return None


def passage_ids(text: str, shown: Sequence[str]) -> list[str]:
    """The passages a label names, by number (1 for the first shown) or by id; [] for none.
    ValueError for one not shown, or one named twice."""
    if text.strip().lower() in ("", "none", "-"):
        return []
    found: list[str] = []
    for token in (t.strip() for t in text.replace(";", ",").split(",")):
        if token.isdigit() and 1 <= int(token) <= len(shown):
            chunk_id = shown[int(token) - 1]
        elif token in shown:
            chunk_id = token
        else:
            raise ValueError(f"{token!r} is not a passage shown (1 to {len(shown)}, or its id)")
        if chunk_id in found:
            raise ValueError(f"{chunk_id} is named twice")
        found.append(chunk_id)
    return found


def label_one(
    shown: Shown,
    total: int,
    prompt: str,
    ask: Ask,
    say: Say,
    clock: Callable[[], datetime],
    monotonic: Callable[[], float],
    title: str = "Item",
) -> Json | None:
    """Show one item and ask for its label in the judge's schema; None when the labeller stops."""
    say(render(shown, total, prompt, title))
    started = monotonic()
    while True:
        answer = _ask(ask, "Verdict: p (pass) or f (fail), or q to stop for now: ")
        if answer is None or answer.lower() == QUIT:
            return None
        chosen = [s for s in calibration.SIDES if answer.lower() in (s, s[0])]
        if chosen:
            verdict = chosen[0]
            break
        say("Answer p or f (or q).")
    quote_found = judged_record.PROMPTS[prompt].quote_found
    while True:
        quote = _ask(ask, "Quote: the words of the answer your verdict rests on, copied exactly: ")
        if quote is None:
            return None
        if quote_found(quote, shown.answer) is True:
            break
        say("That quote is not in the answer: copy the answer's words exactly.")
    while True:
        text = _ask(
            ask, "Passages your verdict rests on (numbers or ids, commas; empty for none): "
        )
        if text is None:
            return None
        try:
            ids = passage_ids(text, shown.ids)
        except ValueError as error:
            say(f"{error}.")
            continue
        break
    while True:
        reason = _ask(ask, "Reason, one sentence: ")
        if reason is None:
            return None
        if reason:
            break
        say("Give one sentence.")
    while True:
        flag = _ask(ask, "Ambiguous? y or n (y: your reason gives both readings) [n]: ")
        if flag is None:
            return None
        if flag.lower() in ("", "n", "no", "y", "yes"):
            break
        say("Answer y or n.")
    item = shown.item
    return {
        **item.as_json(),
        "verdict": verdict,
        "answer_quote": quote,
        "passage_ids": ids,
        "reason": reason,
        "ambiguous": flag.lower() in ("y", "yes"),
        "answer_sha256": judged_record.sha256_text(shown.answer),
        "labelled_at": calibration.stamp(clock()),
        "seconds": round(monotonic() - started, 1),
    }


def _write(path: Path, rows: dict[int, Json]) -> None:
    path.write_text(calibration.jsonl_text([rows[n] for n in sorted(rows)]), encoding="utf-8")


def run(
    root: Path,
    folder: Path,
    relabel: bool = False,
    redo: int | None = None,
    seal: bool = False,
    ask: Ask = input,
    say: Say = print,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    monotonic: Callable[[], float] = time.monotonic,
    inventory: pipeline.Inventory | None = None,
) -> int:
    """`raglab label`: label the sample's items (or, `relabel`, D3's 12) blind, one at a time;
    `redo` one item again before the seal; `seal` the file once every item is labelled. Exit 0,
    or CalibrationError naming the refusal."""
    bar = calibration.load_bar(folder)
    sample = calibration.read_sample(folder)
    if bar.sha256 != sample.pins["bar_sha256"]:
        raise CalibrationError(f"the bar ({calibration.BAR}) changed since the sample pinned it")
    name, seal_name = (
        (calibration.RELABELS, calibration.RELABELS_SEAL)
        if relabel
        else (calibration.LABELS, calibration.LABELS_SEAL)
    )
    if (folder / seal_name).exists():
        sealed = calibration.read_seal(folder, name, seal_name)  # refuses a file changed since
        raise CalibrationError(
            f"{name} is sealed ({seal_name}, {sealed['sealed_at']}): nothing changes after the seal"
        )
    if relabel:
        first = calibration.read_seal(folder, calibration.LABELS, calibration.LABELS_SEAL)
        opens = calibration.parse_time(str(first["sealed_at"]), calibration.LABELS_SEAL)
        opens += timedelta(hours=bar.relabel_gap_hours)
        if clock() < opens:
            raise CalibrationError(
                f"the re-label opens {bar.relabel_gap_hours:g} hours after the labels' seal, at "
                f"{calibration.stamp(opens)}"
            )
        items = calibration.relabel_items(sample, bar)
        title = "Re-label item"
    else:
        items = list(sample.items)
        title = "Item"
    prompt = str(sample.pins["judge_prompt"])
    shown = shown_items(root, sample, items, inventory)
    by_order = {s.item.order: s for s in shown}
    path = folder / name
    rows: dict[int, Json] = {}
    if path.exists():
        for row in calibration.read_jsonl(path):
            order = row.get("order")
            if not isinstance(order, int) or order not in by_order or order in rows:
                raise CalibrationError(f"{name}: a line names no item of the sample, or one twice")
            s = by_order[order]
            if problems := calibration.label_problems(row, s.item, s.answer, s.ids, prompt):
                raise CalibrationError(f"{name}: " + "; ".join(problems))
            rows[order] = row
    total = len(shown)
    if seal:
        if missing := [n for n in by_order if n not in rows]:
            raise CalibrationError(f"items {missing} have no label yet: the seal needs every item")
        body = calibration.seal(folder, name, seal_name, clock)
        say(
            f"sealed {name}: {body['lines']} labels, sha256 {body['sha256']}, at "
            f"{body['sealed_at']} ({seal_name}). Nothing changes after the seal."
        )
        return 0
    if redo is not None:
        if redo not in by_order:
            raise CalibrationError(f"there is no item {redo} (1 to {total})")
        done = label_one(by_order[redo], total, prompt, ask, say, clock, monotonic, title)
        if done is not None:
            rows[redo] = done
            _write(path, rows)
            say(f"item {redo} labelled again.")
        return 0
    for order in sorted(by_order):
        if order in rows:
            continue
        done = label_one(by_order[order], total, prompt, ask, say, clock, monotonic, title)
        if done is None:
            say(f"stopped at item {order}: {len(rows)} of {total} labelled; run again to resume.")
            return 0
        rows[order] = done
        _write(path, rows)
    say(
        f"all {total} items labelled ({name}). Redo one with REDO=<n>; seal with SEAL=1 when you "
        "are done: nothing changes after the seal."
    )
    return 0
