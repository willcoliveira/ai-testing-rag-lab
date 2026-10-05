# One command for every gate that runs without a model or a key: `make check`.
# CI (.github/workflows/pr-fast.yml) runs the same targets.
SEMGREP_VERSION := 1.179.0
ZIZMOR_VERSION := 1.30.1
PYTEST_OFFLINE := not live and not judged and not guardrails and not perf

.PHONY: check format lint types deps audit sast workflows secrets privacy architecture test hooks

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

architecture:
	uv run python scripts/check_architecture.py

test:
	uv run pytest -m "$(PYTEST_OFFLINE)"

# once per clone
hooks:
	git config core.hooksPath .githooks
