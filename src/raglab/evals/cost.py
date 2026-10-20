"""The cost formula (S5, AC12): tokens measured by a published judged record, prices from
config/prices.toml and the monthly assumptions of config/cost-assumptions.toml, turned into a cost
per call, per case-trial, per run and per month, by role and per provider option (ADR-002).

- **A call** costs (prompt tokens x input price + completion tokens x output price) / 1,000,000,
  in US dollars, the prices per million tokens.
- **A role's tokens** are the judged record's totals: the generator's (from its source run's
  lines), the judge's (one call per verdict), the checks on the judge's and the canaries'. A call
  whose server reported no tokens is unreported: it is counted, never priced or estimated, and the
  report says how many there were.
- **A case-trial** is its generator call and its judge calls: each role's cost over the record's
  case-trials.
- **A run** of an option is the measured run's generator and judge tokens and one canary set at
  the option's prices; the checks on the judge (repeatability, order) are S5's measurements, not
  part of a routine run, and are reported apart.
- **A month** is the sum over the run types of runs per month x (case-trials x the cost of a
  generator call, and of a case-trial's judge calls when the run type is judged, plus one canary
  set per judged run).

A local model costs nothing here: electricity and the Mac's time are not priced. Tokens measured
on local models are a proxy for hosted ones (another tokenizer counts the same text differently,
and hosted answers differ in length); ADR-002 says so beside the numbers.
"""

import json
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

type Json = dict[str, object]

LOCAL = "local"
ROLES = ("generator", "judge", "judge_checks", "canaries")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL = re.compile(r"^https://[^\s]+$")
PRICE_KEYS = {
    "id": str,
    "provider": str,
    "model": str,
    "model_id": str,
    "input": (float, int),
    "output": (float, int),
    "batch_input": (float, int),
    "batch_output": (float, int),
    "max_prompt_tokens": int,
    "source": str,
    "read": str,
    "note": str,
}
PRICE_OPTIONAL = {"model_id", "batch_input", "batch_output", "max_prompt_tokens", "note"}
RUN_TYPE_KEYS = {"runs_per_month": int, "cases": int, "trials": int, "judged": bool}
OPTION_KEYS = {"name": str, "generator": str, "judge": str}


class CostError(ValueError):
    """A price table or assumptions file that is not valid, or a record that cannot be priced."""


@dataclass(frozen=True)
class Price:
    id: str
    provider: str
    model: str
    model_id: str | None
    input: float
    output: float
    batch_input: float | None
    batch_output: float | None
    max_prompt_tokens: int | None
    source: str
    read: str


@dataclass(frozen=True)
class PriceTable:
    path: str
    date: str
    prices: dict[str, Price]


@dataclass(frozen=True)
class RunType:
    name: str
    runs_per_month: int
    cases: int
    trials: int
    judged: bool

    @property
    def case_trials(self) -> int:
        return self.cases * self.trials


@dataclass(frozen=True)
class Option:
    name: str
    generator: str
    judge: str


@dataclass(frozen=True)
class Assumptions:
    path: str
    run_types: tuple[RunType, ...]
    options: tuple[Option, ...]


def _checked(table: Mapping[str, object], keys: Mapping[str, object], where: str) -> None:
    for key, value in table.items():
        if key not in keys:
            raise CostError(f"{where}: unknown key {key}")
        kind = cast(type | tuple[type, ...], keys[key])
        if (isinstance(value, bool) and kind is not bool) or not isinstance(value, kind):
            raise CostError(f"{where}: {key} has the wrong type ({type(value).__name__})")


def _read_toml(path: Path) -> dict[str, object]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise CostError(f"{path}: cannot be read ({error})") from error


def load_prices(path: Path) -> PriceTable:
    """The price table, strictly: every price has its URL and its read date; the table's date is
    its latest read date."""
    data = _read_toml(path)
    if set(data) != {"date", "price"}:
        raise CostError(f"{path}: a price table has date and [[price]] rows only")
    date = data["date"]
    if not isinstance(date, str) or not DATE.match(date):
        raise CostError(f"{path}: date must be YYYY-MM-DD")
    prices: dict[str, Price] = {}
    for number, raw in enumerate(cast(list[object], data["price"]), start=1):
        if not isinstance(raw, dict):
            raise CostError(f"{path}: price {number} is not a table")
        row = {str(k): v for k, v in cast(dict[object, object], raw).items()}
        where = f"{path}: price {number} ({row.get('id', '?')})"
        _checked(row, PRICE_KEYS, where)
        if missing := sorted(set(PRICE_KEYS) - PRICE_OPTIONAL - set(row)):
            raise CostError(f"{where}: missing {missing}")
        if not URL.match(str(row["source"])):
            raise CostError(f"{where}: source must be the https URL the price was read from")
        if not DATE.match(str(row["read"])):
            raise CostError(f"{where}: read must be the date it was read, YYYY-MM-DD")
        figures = [row[k] for k in ("input", "output", "batch_input", "batch_output") if k in row]
        if any(cast(float, f) < 0 for f in figures):
            raise CostError(f"{where}: a price is never negative")
        price_id = str(row["id"])
        if price_id in prices or price_id == LOCAL:
            raise CostError(f"{where}: id {price_id} is used twice or reserved")
        batch_in, batch_out = row.get("batch_input"), row.get("batch_output")
        limit = row.get("max_prompt_tokens")
        prices[price_id] = Price(
            price_id,
            str(row["provider"]),
            str(row["model"]),
            cast(str | None, row.get("model_id")),
            float(cast(float, row["input"])),
            float(cast(float, row["output"])),
            None if batch_in is None else float(cast(float, batch_in)),
            None if batch_out is None else float(cast(float, batch_out)),
            None if limit is None else cast(int, limit),
            str(row["source"]),
            str(row["read"]),
        )
    if not prices:
        raise CostError(f"{path}: no prices")
    if date != max(p.read for p in prices.values()):
        raise CostError(f"{path}: the table's date is its latest read date, not {date}")
    return PriceTable(path.as_posix(), date, prices)


def load_assumptions(path: Path, prices: PriceTable) -> Assumptions:
    """The monthly assumptions, strictly; every option names local or a price of the table."""
    data = _read_toml(path)
    if set(data) != {"run_types", "option"}:
        raise CostError(f"{path}: assumptions have [run_types.<name>] and [[option]] only")
    run_types: list[RunType] = []
    for name, raw in cast(dict[str, object], data["run_types"]).items():
        where = f"{path}: run type {name}"
        if not isinstance(raw, dict):
            raise CostError(f"{where} is not a table")
        row = {str(k): v for k, v in cast(dict[object, object], raw).items()}
        _checked(row, RUN_TYPE_KEYS, where)
        if missing := sorted(set(RUN_TYPE_KEYS) - set(row)):
            raise CostError(f"{where}: missing {missing}")
        runs, cases, trials = (cast(int, row[k]) for k in ("runs_per_month", "cases", "trials"))
        if min(runs, cases, trials) < 0:
            raise CostError(f"{where}: counts are never negative")
        run_types.append(RunType(name, runs, cases, trials, bool(row["judged"])))
    options: list[Option] = []
    for number, raw in enumerate(cast(list[object], data["option"]), start=1):
        if not isinstance(raw, dict):
            raise CostError(f"{path}: option {number} is not a table")
        row = {str(k): v for k, v in cast(dict[object, object], raw).items()}
        where = f"{path}: option {number}"
        _checked(row, OPTION_KEYS, where)
        if missing := sorted(set(OPTION_KEYS) - set(row)):
            raise CostError(f"{where}: missing {missing}")
        for part in ("generator", "judge"):
            if row[part] != LOCAL and row[part] not in prices.prices:
                raise CostError(f"{where}: {part} {row[part]} is not local or a price id")
        options.append(Option(str(row["name"]), str(row["generator"]), str(row["judge"])))
    return Assumptions(path.as_posix(), tuple(run_types), tuple(options))


def call_cost(prompt: int | float, completion: int | float, price: Price | None) -> float:
    """What a call costs at a price, in US dollars: (prompt x input + completion x output) /
    1,000,000. A local model (price None) costs nothing."""
    if price is None:
        return 0.0
    return (prompt * price.input + completion * price.output) / 1_000_000


@dataclass(frozen=True)
class Role:
    """A role's calls and the tokens their servers reported."""

    calls: int
    prompt: int
    completion: int
    unreported: int
    max_prompt: int

    @property
    def reported(self) -> int:
        return self.calls - self.unreported


@dataclass(frozen=True)
class Measured:
    run_id: str
    source: str
    case_trials: int
    roles: dict[str, Role]


def _obj(value: object) -> Json:
    return {str(k): v for k, v in cast(dict[object, object], value).items()}


def _list(value: object) -> list[object]:
    return list(cast(list[object], value)) if isinstance(value, list) else []


def measured(run_dir: Path) -> Measured:
    """The tokens by role a judged record measured, with each role's largest prompt (from its
    lines: the generator's from the source tokens they copy)."""
    manifest = _obj(json.loads((run_dir / "manifest.json").read_text(encoding="utf-8")))
    if manifest.get("suite") != "judged":
        raise CostError(f"{run_dir.name} is not a judged run: its tokens hold no judge calls")
    lines = [
        _obj(json.loads(line))
        for line in (run_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    tokens = _obj(_obj(_obj(manifest["results"])["judged"])["tokens"])
    largest: dict[str, int] = dict.fromkeys(ROLES, 0)
    for line in lines:
        source = _obj(line["source_tokens"])
        largest["generator"] = max(largest["generator"], cast(int | None, source["prompt"]) or 0)
        for field, role in (
            ("verdicts", "judge"),
            ("repeat", "judge_checks"),
            ("reversed", "judge_checks"),
        ):
            for verdict in _obj(line.get(field) or {}).values():
                prompt = cast(int | None, _obj(verdict)["prompt_tokens"]) or 0
                largest[role] = max(largest[role], prompt)
    for row in _list(_obj(manifest["canaries"])["results"]):
        prompt = cast(int | None, _obj(row)["prompt_tokens"]) or 0
        largest["canaries"] = max(largest["canaries"], prompt)
    roles = {
        role: Role(
            cast(int, _obj(tokens[role])["calls"]),
            cast(int, _obj(tokens[role])["prompt"]),
            cast(int, _obj(tokens[role])["completion"]),
            cast(int, _obj(tokens[role])["unreported"]),
            largest[role],
        )
        for role in ROLES
    }
    return Measured(
        str(manifest["run_id"]), str(_obj(manifest["source"])["run_id"]), len(lines), roles
    )


@dataclass(frozen=True)
class OptionCost:
    option: Option
    generator_per_call: float
    judge_per_call: float
    per_case_trial: float
    per_run: float
    checks_per_run: float
    per_month: float


def _price(key: str, table: PriceTable) -> Price | None:
    return None if key == LOCAL else table.prices[key]


def _per_call(role: Role, price: Price | None) -> float:
    if role.reported == 0:
        return 0.0
    return call_cost(role.prompt / role.reported, role.completion / role.reported, price)


def estimate(found: Measured, table: PriceTable, assumptions: Assumptions) -> list[OptionCost]:
    """Each option's cost per call (generator, judge), per case-trial, per run, per month."""
    roles = found.roles
    costs: list[OptionCost] = []
    for option in assumptions.options:
        generator, judge = _price(option.generator, table), _price(option.judge, table)
        for role, price in (("generator", generator), ("judge", judge), ("canaries", judge)):
            if price is None or price.max_prompt_tokens is None:
                continue
            if roles[role].max_prompt > price.max_prompt_tokens:
                raise CostError(
                    f"{option.name}: a {role} prompt of {roles[role].max_prompt} tokens is above "
                    f"{price.id}'s {price.max_prompt_tokens}-token tier"
                )
        generator_run = call_cost(
            roles["generator"].prompt, roles["generator"].completion, generator
        )
        judge_run = call_cost(roles["judge"].prompt, roles["judge"].completion, judge)
        canary_run = call_cost(roles["canaries"].prompt, roles["canaries"].completion, judge)
        checks_run = call_cost(
            roles["judge_checks"].prompt, roles["judge_checks"].completion, judge
        )
        generator_trial = generator_run / found.case_trials
        judge_trial = judge_run / found.case_trials
        month = sum(
            t.runs_per_month
            * (
                t.case_trials * (generator_trial + (judge_trial if t.judged else 0.0))
                + (canary_run if t.judged else 0.0)
            )
            for t in assumptions.run_types
        )
        costs.append(
            OptionCost(
                option,
                _per_call(roles["generator"], generator),
                _per_call(roles["judge"], judge),
                generator_trial + judge_trial,
                generator_run + judge_run + canary_run,
                checks_run,
                month,
            )
        )
    return costs


def _usd(value: float) -> str:
    return f"${value:,.4f}" if value < 1 else f"${value:,.2f}"


def render(
    found: Measured, table: PriceTable, assumptions: Assumptions, costs: Sequence[OptionCost]
) -> str:
    """The estimate as Markdown, with its inputs: the record, the price table and its date, the
    assumptions, the tokens by role and each option's costs."""
    lines = [
        f"Tokens: {found.run_id} (judged; the generator's from its source {found.source}), "
        f"{found.case_trials} case-trials.",
        f"Prices: {table.path}, price_table_date {table.date}. Assumptions: {assumptions.path}.",
        "",
        "| Role | Calls | Prompt | Completion | Unreported | Prompt per call | "
        "Completion per call | Largest prompt |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name in ROLES:
        role = found.roles[name]
        per = (
            (role.prompt / role.reported, role.completion / role.reported)
            if role.reported
            else (0, 0)
        )
        lines.append(
            f"| {name} | {role.calls} | {role.prompt} | {role.completion} | {role.unreported} | "
            f"{per[0]:.1f} | {per[1]:.1f} | {role.max_prompt} |"
        )
    lines += [
        "",
        "| Run type | Runs a month | Cases | Trials | Judged |",
        "|---|---|---|---|---|",
        *(
            f"| {t.name} | {t.runs_per_month} | {t.cases} | {t.trials} | "
            f"{'yes' if t.judged else 'no'} |"
            for t in assumptions.run_types
        ),
        "",
        "| Option | Generator per call | Judge per call | Per case-trial | Per run | "
        "Checks per run | Per month |",
        "|---|---|---|---|---|---|---|",
    ]
    for cost in costs:
        lines.append(
            f"| {cost.option.name} | {_usd(cost.generator_per_call)} | "
            f"{_usd(cost.judge_per_call)} | {_usd(cost.per_case_trial)} | {_usd(cost.per_run)} | "
            f"{_usd(cost.checks_per_run)} | {_usd(cost.per_month)} |"
        )
    unreported = sum(r.unreported for r in found.roles.values())
    if unreported:
        lines += ["", f"{unreported} call(s) reported no tokens: counted, never priced."]
    return "\n".join(lines) + "\n"
