"""S5 AC12: the cost formula, on hand-computed values. A call costs (prompt x input + completion x
output) / 1,000,000; a case-trial is its generator call and its judge calls; a run is the measured
run's generator and judge tokens and one canary set; a month sums the run types. The committed
price table gives every price its URL and its read date, and the committed assumptions keep the
judge's family apart from the generator's."""

import json
import re
from pathlib import Path

import pytest

from raglab.evals import cost
from tests.conftest import ROOT

pytestmark = pytest.mark.unit
PRICES = ROOT / "config" / "prices.toml"
ASSUMPTIONS = ROOT / "config" / "cost-assumptions.toml"


def price(name: str = "g", inp: float = 1.0, out: float = 2.0, limit: int | None = None):
    return cost.Price(
        name, "p", name, None, inp, out, None, None, limit, "https://x.test/p", "2026-10-20"
    )


def test_a_call_costs_its_prompt_at_the_input_price_and_its_completion_at_the_output_price():
    """AC12's break: the output price applied to prompt tokens fails here."""
    haiku = price("h", 0.10, 0.50)
    assert cost.call_cost(1000, 200, haiku) == pytest.approx(0.0002)  # (100 + 100) / 1e6
    assert cost.call_cost(1_000_000, 0, haiku) == pytest.approx(0.10)
    assert cost.call_cost(0, 1_000_000, haiku) == pytest.approx(0.50)
    assert cost.call_cost(5000, 5000, None) == 0.0  # a local model


def judged_dir(tmp_path: Path) -> Path:
    """A judged record's files, as much as raglab.evals.cost reads: 4 case-trials, each a
    generator call of 1,000 and 100 tokens and two judge calls of 1,000 and 100; one line with a
    repeat and a reversal; two canaries of 500 and 50."""
    run = tmp_path / "judged"
    run.mkdir()
    verdict = {"prompt_tokens": 1000, "completion_tokens": 100}
    lines = [
        {
            "source_tokens": {"prompt": 1000, "completion": 100},
            "verdicts": {"grounded": verdict, "relevant": verdict},
            **(
                {"repeat": {"grounded": verdict}, "reversed": {"grounded": verdict}}
                if n == 0
                else {}
            ),
        }
        for n in range(4)
    ]
    tokens = {
        "generator": {"calls": 4, "prompt": 4000, "completion": 400, "unreported": 0},
        "judge": {"calls": 8, "prompt": 8000, "completion": 800, "unreported": 0},
        "judge_checks": {"calls": 2, "prompt": 2000, "completion": 200, "unreported": 0},
        "canaries": {"calls": 2, "prompt": 1000, "completion": 100, "unreported": 0},
    }
    manifest = {
        "run_id": "R",
        "suite": "judged",
        "source": {"run_id": "S"},
        "results": {"judged": {"tokens": tokens}},
        "canaries": {"results": [{"prompt_tokens": 500}, {"prompt_tokens": 500}]},
    }
    (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (run / "cases.jsonl").write_text("".join(json.dumps(x) + "\n" for x in lines))
    return run


def test_the_estimate_by_hand(tmp_path):
    table = cost.PriceTable(
        "p.toml", "2026-10-20", {"G": price("G", 1.0, 2.0), "J": price("J", 0.5, 4.0)}
    )
    assumptions = cost.Assumptions(
        "a.toml",
        (cost.RunType("a", 10, 2, 3, True), cost.RunType("b", 30, 1, 2, False)),
        (
            cost.Option("hosted", "G", "J"),
            cost.Option("local judge only", "local", "J"),
            cost.Option("local", "local", "local"),
        ),
    )
    found = cost.measured(judged_dir(tmp_path))
    assert found.case_trials == 4
    assert found.roles["judge"].max_prompt == 1000
    assert found.roles["canaries"].max_prompt == 500
    hosted, judge_only, local = cost.estimate(found, table, assumptions)
    # generator per call (1,000 x 1.0 + 100 x 2.0) / 1e6;
    # judge per call (1,000 x 0.5 + 100 x 4.0) / 1e6
    assert hosted.generator_per_call == pytest.approx(0.0012)
    assert hosted.judge_per_call == pytest.approx(0.0009)
    # per case-trial: the generator's 4,800 / 1e6 and the judge's 7,200 / 1e6, over 4 case-trials
    assert hosted.per_case_trial == pytest.approx(0.0012 + 0.0018)
    # a run: generator 0.0048 + judge 0.0072 + one canary set 0.0009; the checks apart, 0.0018
    assert hosted.per_run == pytest.approx(0.0129)
    assert hosted.checks_per_run == pytest.approx(0.0018)
    # a month: 10 judged runs of 6 case-trials (each 0.0030) and a canary set, and 30 unjudged runs
    # of 2 case-trials (each 0.0012): 10 x 0.0189 + 30 x 0.0024
    assert hosted.per_month == pytest.approx(0.189 + 0.072)
    assert judge_only.per_month == pytest.approx(10 * (6 * 0.0018 + 0.0009))
    assert (judge_only.generator_per_call, judge_only.per_run) == (0.0, pytest.approx(0.0081))
    assert (local.per_case_trial, local.per_run, local.per_month) == (0.0, 0.0, 0.0)
    text = cost.render(found, table, assumptions, [hosted, judge_only, local])
    assert "price_table_date 2026-10-20" in text
    assert "| hosted | $0.0012 | $0.0009 | $0.0030 | $0.0129 | $0.0018 | $0.2610 |" in text


def test_a_prompt_above_a_prices_tier_is_refused(tmp_path):
    table = cost.PriceTable("p.toml", "2026-10-20", {"J": price("J", 0.5, 4.0, limit=900)})
    assumptions = cost.Assumptions("a.toml", (), (cost.Option("o", "local", "J"),))
    with pytest.raises(cost.CostError, match="a judge prompt of 1000 tokens is above J's 900"):
        cost.estimate(cost.measured(judged_dir(tmp_path)), table, assumptions)


def test_the_committed_price_table_gives_every_price_its_url_and_read_date():
    table = cost.load_prices(PRICES)
    assert table.date == "2026-10-21"
    for item in table.prices.values():
        assert item.source.startswith("https://"), item.id
        assert item.read == "2026-10-21", item.id
    # the rows the plan saw while planning, read again by the developer on 2026-10-20 and 2026-10-21
    expected = {
        "anthropic-haiku-5.5": (0.10, 0.50, 0.05, 0.25),
        "anthropic-sonnet-5.5": (2.0, 10.0, 1.0, 5.0),
        "anthropic-opus-5.5": (4.0, 20.0, 2.0, 10.0),
        "anthropic-haiku-4.5": (1.0, 5.0, 0.50, 2.50),
        "openai-gpt-5-nano": (0.05, 0.40, 0.025, 0.20),
        "openai-gpt-5-mini": (0.25, 2.00, 0.125, 1.00),
        "openai-gpt-6-luna": (0.10, 0.50, 0.05, 0.25),
    }
    found = {k: (p.input, p.output, p.batch_input, p.batch_output) for k, p in table.prices.items()}
    assert found == expected
    assert table.prices["anthropic-haiku-5.5"].model_id == "claude-haiku-5-5"
    assert table.prices["anthropic-haiku-5.5"].max_prompt_tokens == 100000


ANTHROPIC = 'source = "https://platform.claude.com/docs/en/about-claude/pricing"\n'
EXTRA = (
    '\n[[price]]\nid = "x"\nprovider = "p"\nmodel = "m"\ninput = 1\noutput = 1\n'
    'source = "https://a.b"\nread = "2026-10-20"\ncolour = "red"\n'
)
WRONG_TABLES = [
    (lambda t: t.replace(ANTHROPIC, "", 1), "missing \\['source'\\]"),
    (lambda t: t.replace('read = "2026-10-21"\n', "", 1), "missing \\['read'\\]"),
    (lambda t: t.replace("https://developers", "developers", 1), "https URL"),
    (lambda t: t.replace('read = "2026-10-21"', 'read = "20 October"', 1), "YYYY-MM-DD"),
    (lambda t: t.replace('date = "2026-10-21"', 'date = "2026-10-20"', 1), "latest read date"),
    (lambda t: t.replace("input = 0.10", "input = -0.10", 1), "never negative"),
    (lambda t: t.replace("output = 0.50", 'output = "0.50"', 1), "wrong type"),
    (lambda t: t + EXTRA, "unknown key colour"),
]


@pytest.mark.parametrize(("edit", "match"), WRONG_TABLES)
def test_a_price_without_its_url_or_read_date_or_otherwise_wrong_is_refused(tmp_path, edit, match):
    """AC12's break: a price without a URL or a date fails."""
    path = tmp_path / "prices.toml"
    path.write_text(edit(PRICES.read_text(encoding="utf-8")), encoding="utf-8")
    with pytest.raises(cost.CostError, match=match):
        cost.load_prices(path)


def test_the_committed_assumptions_price_options_whose_judge_is_of_another_family():
    table = cost.load_prices(PRICES)
    assumptions = cost.load_assumptions(ASSUMPTIONS, table)
    names = {t.name for t in assumptions.run_types}
    assert names == {"eval-on-change", "nightly", "weekly", "release"}  # the main plan's gate map
    providers = {"local": None, **{k: p.provider for k, p in table.prices.items()}}
    for option in assumptions.options:
        if option.generator != "local":
            assert providers[option.generator] != providers[option.judge], option.name
    assert any(o.generator == o.judge == "local" for o in assumptions.options)


def test_an_option_that_names_no_price_is_refused(tmp_path):
    table = cost.load_prices(PRICES)
    path = tmp_path / "a.toml"
    text = ASSUMPTIONS.read_text(encoding="utf-8").replace(
        'judge = "openai-gpt-5-mini"', 'judge = "openai-gpt-9"', 1
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(cost.CostError, match="judge openai-gpt-9 is not local or a price id"):
        cost.load_assumptions(path, table)


def test_the_cli_prices_a_judged_record(tmp_path, capsys):
    """raglab cost on a judged run of the small pack, with the committed table and assumptions."""
    from raglab.__main__ import main
    from tests.judge_support import judged_root, local_judge, run_judged

    root, source = judged_root(tmp_path)
    judge, description, provenance = local_judge()
    run_dir = run_judged(root, source, judge, description, provenance)
    argv = ["cost", "--judged", str(run_dir), "--root", str(root)]
    argv += ["--prices", str(PRICES), "--assumptions", str(ASSUMPTIONS)]
    assert main(argv) == 0
    out = capsys.readouterr().out
    assert "price_table_date 2026-10-21" in out
    assert "| local only | $0.0000 | $0.0000 | $0.0000 | $0.0000 | $0.0000 | $0.0000 |" in out
    # per case-trial: the generator's one call per case-trial; the canaries, once per run: "-"
    assert "| generator | 14 | 1400 | 280 | 0 | 100.0 | 20.0 | 100 | 100.0 | 20.0 |" in out
    assert re.search(
        r"^\| canaries \| (\d+ \| ){4}[\d.]+ \| [\d.]+ \| \d+ \| - \| - \|$", out, re.M
    )
    assert main(["cost", "--judged", str(source), "--root", str(root)]) == 1  # not a judged run


def test_the_output_names_its_inputs_relative_to_the_root_so_it_is_the_same_anywhere():
    """raglab cost's output (cost.report) over the published judged baseline names the price table
    and the assumptions as repository paths, never this machine's, so ADR-002 can quote it word
    for word (AC13)."""
    run_dir = ROOT / "runs" / "published" / "20261021T081852Z-judge-local-dev-5aa0ec5"
    out = cost.report(ROOT, run_dir, Path("config/prices.toml"), ASSUMPTIONS)
    assert "Prices: config/prices.toml, price_table_date 2026-10-21." in out
    assert "Assumptions: config/cost-assumptions.toml." in out
    assert str(ROOT) not in out
    assert out == cost.report(ROOT, run_dir, PRICES, Path("config/cost-assumptions.toml"))
