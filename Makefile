# One command for every gate that runs without a hosted model or a key: `make check` (the local
# embedding model is fetched once by `make model`, then read from its cache).
# CI (.github/workflows/pr-fast.yml) runs the same targets.
SEMGREP_VERSION := 1.179.0
ZIZMOR_VERSION := 1.30.1
PYTEST_OFFLINE := not live and not judged and not guardrails and not perf

# the commits `make privacy-history` checks, as git log revisions (see the target)
RANGE ?= --all

.PHONY: check format lint types deps audit sast workflows secrets privacy privacy-history architecture model test gate api-smoke hooks corpus inventory-snapshot playground ollama-up ollama-down ollama-status eval-local container container-run zap

check: format lint types deps audit sast workflows secrets privacy architecture model test gate api-smoke

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

# the pinned embedding model (BAAI/bge-small-en-v1.5, ONNX) into $RAGLAB_MODEL_DIR (default
# ~/.cache/raglab/models): downloads only what is missing or fails its sha256, so it is offline once
# the cache is filled. The tests never download; they load from this cache.
model:
	uv run raglab fetch-model

test:
	HF_HUB_OFFLINE=1 uv run pytest -m "$(PYTEST_OFFLINE)"

# the retrieval no-regression gate (docs/THRESHOLDS.md): a fresh run of the default configuration
# on the dev split, offline with the cached model, must keep recall@5 within one question of the
# published baseline in runs/published/index.json
gate:
	HF_HUB_OFFLINE=1 uv run raglab gate --config config/retrieval-dense.toml

# S3: `raglab serve` with config/fake.toml (the fake model, the cached embedder) on 127.0.0.1, then
# /healthz, /version, an /ask answer and a no-tenant refusal; offline, the server stopped after
API_SMOKE_PORT ?= 8765
api-smoke:
	HF_HUB_OFFLINE=1 uv run python scripts/api_smoke.py --port $(API_SMOKE_PORT)

# S3 AC15: the local model server for one session only, never a resident service
# (docs/LOCAL-MODEL.md). ollama-up and ollama-down are the manual pair; eval-local starts the server,
# runs the live contract test and the generation suite, then stops it and runs the postcheck, also
# on an error, Ctrl-C, SIGTERM or SIGHUP (a SIGKILL leaves it up: run make ollama-down).
LOCAL_CONFIG := config/local-ollama.toml
ollama-up:
	uv run raglab ollama up --config $(LOCAL_CONFIG)

ollama-down:
	uv run raglab ollama down --config $(LOCAL_CONFIG)

ollama-status:
	uv run raglab ollama status --config $(LOCAL_CONFIG)

eval-local:
	uv run raglab ollama session --config config/local-ollama.toml \
		--run "uv run pytest -m live tests/contract/test_chat_contract.py" \
		--run "uv run raglab eval --suite generation --config config/local-ollama.toml"

# S3 AC10, AC11: the container with the fake model and the baked-in embedder (deploy/Dockerfile),
# run on 127.0.0.1 only, and the ZAP baseline scan against it (deploy/zap/)
IMAGE := raglab:local
container:
	docker build -f deploy/Dockerfile --build-arg GIT_SHA=$$(git rev-parse HEAD) -t $(IMAGE) .

container-run:
	docker run --rm --name raglab -p 127.0.0.1:8000:8000 $(IMAGE)

zap:
	sh deploy/zap/scan.sh $(IMAGE)

# required once in every clone: commit-msg, pre-commit and pre-push
hooks:
	git config core.hooksPath .githooks

# re-render the corpus PDF, HTML export and scanned page after a corpus Markdown change
# (tests/unit/test_corpus_build.py fails until the committed files match a fresh build)
corpus:
	uv run python scripts/build_corpus.py

# regenerate the committed chunk inventory snapshot on purpose, after a parser, chunker or corpus
# change, and review its diff in the PR (tests/ingestion/test_inventory_snapshot.py fails until the
# committed file matches a fresh run at the default settings)
inventory-snapshot:
	uv run raglab ingest --snapshot corpus/inventory.snapshot.json

# the static playground, served on 127.0.0.1 as Pages will lay it out (playground/ next to
# runs/published/); it reads the published runs and never calls a model
playground:
	uv run python scripts/serve_playground.py
