# One command for every gate that runs without a model or a key: `make check`.
# CI (.github/workflows/pr-fast.yml) runs the same targets.
SEMGREP_VERSION := 1.179.0
ZIZMOR_VERSION := 1.30.1
PYTEST_OFFLINE := not live and not judged and not guardrails and not perf

# the commits `make privacy-history` checks, as git log revisions (see the target)
RANGE ?= --all

.PHONY: check format lint types deps audit sast workflows secrets privacy privacy-history architecture test hooks

check: format lint types deps audit sast workflows secrets privacy architecture test

format:
	uv run ruff format --check

lint:
	uv run ruff check

types:
	uv run pyright

deps:
	uv run deptry .
	uv run vulture

audit:
	uv run pip-audit --skip-editable

sast:
	uv run bandit -q -r src scripts
	uvx semgrep@$(SEMGREP_VERSION) scan --config p/python --metrics=off --error --quiet src scripts

workflows:
	uvx zizmor@$(ZIZMOR_VERSION) --offline .github/

secrets:
	gitleaks dir . --redact --no-banner
	gitleaks git . --redact --no-banner

privacy:
	node scripts/check-forbidden.mjs

# Every commit message and every line added in a range of commits: a string committed without the
# hooks and removed later is still in the history a push publishes. RANGE is git log revisions:
# --all (default), base..head, or <sha> --not --remotes=origin. CI runs it on a PR's commits with
# the example list, the pre-push hook on the commits being pushed, GO-PUBLIC.md step 1 over --all.
privacy-history:
	node scripts/check-forbidden.mjs --history $(RANGE)

architecture:
	uv run python scripts/check_architecture.py

test:
	uv run pytest -m "$(PYTEST_OFFLINE)"

# required once in every clone: commit-msg, pre-commit and pre-push
hooks:
	git config core.hooksPath .githooks
