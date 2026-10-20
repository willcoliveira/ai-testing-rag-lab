"""`python -m deepeval_check` (S5, AC11): DeepEval's checks against the local judge, in a judge
session (`make deepeval-check`, after the judge's live contract test and the canaries). Telemetry is
switched off and the loopback-only socket guard installed before DeepEval is imported; the
results, the guard's attempts and DeepEval's calls and tokens per check are printed and written to
runs/tmp/deepeval-check/. Exit 1 when a check fails to run or the guard caught an attempt."""

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from deepeval_check import guard


def main(argv: list[str] | None = None) -> int:
    guard.opt_out()  # before DeepEval is imported, below
    imported_before = guard.deepeval_imported()
    sockets = guard.SocketGuard().install()
    from deepeval_check import checks
    from deepeval_check.llm import RaglabJudgeLLM
    from raglab.evals import config as eval_config
    from raglab.judge.build import judge_from_config

    parser = argparse.ArgumentParser(prog="deepeval_check", description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("config/judge-local.toml"))
    parser.add_argument("--judged", type=Path, help="a judged record, for the cross-check")
    args = parser.parse_args(argv)
    root: Path = args.root
    config = eval_config.load_judge(root / args.config, root)
    structured, _, _ = judge_from_config(config)
    plain, _, _ = judge_from_config(config, response_format="none")
    llm = RaglabJudgeLLM(structured.chat, plain.chat, config.judging.seed)
    results: dict[str, object] = {
        "deepeval": version("deepeval"),
        "telemetry_opt_out": os.environ.get(guard.OPT_OUT),
        "opted_out_before_import": not imported_before,
        "judge": structured.describe(),
    }
    failed = False
    for name, run in (
        ("custom_llm_api", lambda: checks.custom_llm_api(llm)),
        ("metric_canary", lambda: checks.metric_canary(llm, root)),
        ("hallucination_direction", lambda: checks.hallucination_direction(llm, root)),
        *(
            [("cross_check", lambda: checks.cross_check(llm, root, root / args.judged))]
            if args.judged
            else []
        ),
    ):
        before = llm.tokens()
        try:
            results[name] = run()
        except Exception as error:  # a check that cannot run is reported, not hidden
            results[name] = {"error": f"{type(error).__name__}: {error}"}
            failed = True
        after = llm.tokens()
        results[f"{name}_tokens"] = {k: after[k] - before[k] for k in after}
        print(json.dumps({name: results[name]}, default=str), flush=True)
    results["guard_attempts"] = sockets.attempts
    sockets.uninstall()
    out = root / "runs" / "tmp" / "deepeval-check"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    path.write_text(json.dumps(results, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"deepeval-check: written {path}; guard attempts: {len(sockets.attempts)}", flush=True)
    return 1 if failed or sockets.attempts else 0


if __name__ == "__main__":
    sys.exit(main())
