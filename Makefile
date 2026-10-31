# One command for every gate that runs without a hosted model or a key: `make check` (the local
# embedding model is fetched once by `make model`, then read from its cache).
# CI (.github/workflows/pr-fast.yml) runs the same targets.
SEMGREP_VERSION := 1.179.0
ZIZMOR_VERSION := 1.30.1
PYTEST_OFFLINE := not live and not judged and not guardrails and not perf

# the commits `make privacy-history` checks, as git log revisions (see the target)
RANGE ?= --all

# Advisories `make audit` skips (decision of 2026-10-21, verbatim: "Dependency PR, Pillow exception
# (Recommended)"). Review by 2026-11-21: tests/unit/test_audit_exceptions.py fails after that date,
# so the exception is looked at again, not kept by default.
# Pillow 12.3.0 has forty-one advisories fixed only in Pillow 13, and fastembed 0.9.0, the
# newest, still requires pillow<13; the corpus build also pins pillow==12.3.0, since the scanned
# page is drawn with the font Pillow bundles and tests/unit/test_corpus_build.py checks that a
# rebuild gives the same pixels. Each advisory needs a file an attacker made (a PDF appended to, a
# GIF, APNG, PNG, BMP, MSP, XBM, SPIDER or FlashPix image, a JPEG or JPEG 2000, a PPM or PGM, a
# TIFF, an EPS or its file name, an IPTC or MIC image, a tar file, a broken font, image data
# decoded as P;2L or P;4L), an image saved as TIFF, JPEG or PDF, an image exported to Arrow with
# PILLOW_ALIGNMENT above 1, an image quantized with an empty palette, or a failed allocation; one
# affects Windows builds only. raglab decodes no image it did not make, saves only PNG, quantizes
# none and exports none to Arrow: OCR hands the
# committed PNG's path to Tesseract (pytesseract opens no image for a path), the corpus build
# re-reads only the PNG it rendered, fastembed loads a text model, and the API takes no files.
# The advisories are named by their GitHub ids, which pip-audit matches as aliases. pip-audit
# reported eight on 2026-10-21; GitHub's database has a ninth (GHSA-8g5g-8vmr-9782, JPEG), skipped
# ahead of pip-audit's database; seven more were published the same evening, twenty on 2026-10-22
# and two on 2026-10-23, of the same kinds. Three more, published on 2026-10-21
# (GHSA-4558-3h8r-v8xp, GHSA-rfgq-q3w2-pmv2, GHSA-xvh5-g6gv-559v), are in GitHub's database and not
# yet in the one pip-audit reads, so they are skipped ahead of it too, as the ninth was. The
# DeepEval tool's audit line skips the same: its own lock resolves the same pillow 12.3.0 through
# raglab.
# pypdf 6.19.0 (decision of 2026-10-21, verbatim: "Keep 6.19.0, skip its 4 advisories
# (Recommended)"): advisories fixed in 6.20.0, 6.20.1, 6.21.0, 6.21.1, 6.21.2, 6.21.3 and 6.21.4,
# each an infinite loop, a memory or runtime blow-up or image parsers reached from a PDF an
# attacker made; a fifth was published after the decision, three more on 2026-10-22, three on
# 2026-10-23 (fixed only in 6.21.2) and seven on 2026-10-30 (fixed only in 6.21.3 and 6.21.4, both
# inside Dependabot's 7-day cooldown until 2026-11-03 and 2026-11-04), of the same kinds. raglab
# parses one PDF, the corpus PDF its own build renders and commits. pypdf 6.20.0 to 6.21.2 also
# change plain text extraction: a table cell's wrapped "the account" comes out as "theaccount",
# which fails the corpus build's checks that planted values survive rendering
# (tests/unit/test_answer_key.py); 6.21.2, tried on 2026-10-31 once its cooldown had passed, fails
# them the same way, while the chunk inventory, which reads the PDF by position
# (src/raglab/ingest/pdf.py), came out identical. Same review date; .github/dependabot.yml ignores
# those versions until then.
AUDIT_SKIP := GHSA-462x-pgg6-55fp GHSA-58r4-6rv3-gfh8 GHSA-65qm-jvmh-6pqg GHSA-8g5g-8vmr-9782 \
	GHSA-c6hw-5grf-ff96 GHSA-p4wg-p73j-c528 GHSA-pchr-8j38-3x4p GHSA-q45j-58j2-45rg \
	GHSA-vx6w-vv9f-6gvg \
	GHSA-22hg-r758-rrw9 GHSA-27h8-gf7j-v5hc GHSA-7mwm-ghpf-9vrm GHSA-cp9v-662q-vvx9 \
	GHSA-fc9g-5qg7-mf45 GHSA-j4m9-6w36-pw47 GHSA-w889-685w-c8fh \
	GHSA-24rc-8hj2-v98c GHSA-254f-3936-288h GHSA-332p-7hrc-92wf GHSA-3j72-p6qg-6xp7 \
	GHSA-4rm8-3hmm-39fg GHSA-4rr5-89j8-mwwm GHSA-5xm2-6676-qcp9 GHSA-74r2-7ff9-mjj2 \
	GHSA-78g4-xqwv-q3g8 GHSA-9v9v-9qvf-h2hj GHSA-f2g6-542v-9j58 GHSA-g4qv-2jxx-769h \
	GHSA-g7cr-3p24-7wf7 GHSA-g842-9rc4-69pw GHSA-gg2r-wvfm-q9rx GHSA-jg86-v3jv-hrpm \
	GHSA-mrfp-p49p-3hf2 GHSA-p8hx-v2p6-rp84 GHSA-v9pv-5gc8-w2m6 GHSA-xgh8-jp6q-p5x8 \
	GHSA-5x8w-8jj5-q52h GHSA-654x-cwwv-5j9c \
	GHSA-4558-3h8r-v8xp GHSA-rfgq-q3w2-pmv2 GHSA-xvh5-g6gv-559v \
	GHSA-39mj-jf6j-2qj3 GHSA-5hx5-vpf9-5wcv GHSA-7mh2-4gg2-979f GHSA-9mx8-4j7g-633p \
	GHSA-qfv9-64jg-mh7p \
	GHSA-6vvc-x485-93v7 GHSA-cgf9-327m-v77c GHSA-f54x-cmq8-qg57 \
	GHSA-6c7f-9265-g8fw GHSA-gmh7-3g9r-mjh5 GHSA-jr96-gvgh-j3r4 \
	GHSA-42gh-23hr-vphw GHSA-4vqv-7265-gm2w GHSA-62m5-6wh8-28x7 GHSA-x3rh-gjgm-fmqc \
	GHSA-5849-834g-hvw5 GHSA-cggf-277g-3q54 GHSA-mfr5-77xh-9j7h

.PHONY: check format lint types deps audit sast workflows secrets privacy privacy-history architecture check-dataset model test gate eval-retrieval api-smoke perf-smoke hooks corpus inventory-snapshot playground ollama-up ollama-down ollama-status eval-local gate-local nightly-local release-local judge-contract judge-canaries judge-local position-local cost deepeval-test deepeval-check container container-run zap

check: format lint types deps audit sast workflows secrets privacy architecture check-dataset model test gate api-smoke

format:
	uv run ruff format --check

lint:
	uv run ruff check

types:
	uv run pyright

deps:
	uv run deptry .
	uv run vulture

# S5 (AC10): also the DeepEval tool project's pinned requirements, exported with their hashes from
# its own lock and audited without installing them (the main environment never installs DeepEval)
audit:
	uv run pip-audit --skip-editable $(foreach id,$(AUDIT_SKIP),--ignore-vuln $(id))
	mkdir -p runs/tmp
	uv export --project tools/deepeval-check --locked --no-emit-project --no-emit-local \
		--format requirements-txt --quiet -o runs/tmp/deepeval-check.requirements.txt
	uv run pip-audit -r runs/tmp/deepeval-check.requirements.txt --disable-pip --require-hashes $(foreach id,$(AUDIT_SKIP),--ignore-vuln $(id))

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

# S4: the dataset hard stop. Every golden file (golden set v1.1, and v2 from S4b) against its ten
# rules, each by its version (raglab.evals.dataset_check): the answer key, the register and the
# inventory snapshot, no model and no embedder. Every `raglab eval` and `raglab gate` runs the
# same check first on its config's file; pr-fast runs it as its own step.
check-dataset:
	uv run raglab check-dataset

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

# S4b: the three retrieval configurations on their dev split, one after another, offline with the
# cached embedder (no model server), each written to runs/tmp under gate manual: dense (the gate's
# baseline), hybrid and dense-600, the runs a dataset change republishes (S2, S4, S4b GV10), made
# at the stage's frozen commit on a clean tree. Not part of `make check`.
eval-retrieval:
	HF_HUB_OFFLINE=1 uv run raglab eval --suite retrieval --config config/retrieval-dense.toml
	HF_HUB_OFFLINE=1 uv run raglab eval --suite retrieval --config config/retrieval-hybrid.toml
	HF_HUB_OFFLINE=1 uv run raglab eval --suite retrieval --config config/retrieval-dense-600.toml

# S3: `raglab serve` with config/fake.toml (the fake model, the cached embedder) on 127.0.0.1, then
# /healthz, /version, an /ask answer and a no-tenant refusal; offline, the server stopped after
API_SMOKE_PORT ?= 8765
api-smoke:
	HF_HUB_OFFLINE=1 uv run python scripts/api_smoke.py --port $(API_SMOKE_PORT)

# S9: the k6 smoke against the perf stub (docs/OBSERVABILITY.md). The collector (deploy/otel/) and
# `raglab serve --config config/perf.toml` (PERF_TEST_MODE=1, RAGLAB_ENV=ci) on loopback; k6 2.3.0
# and the collector fetched once into ~/.cache/raglab/tools, each archive's sha256 checked on every
# use; the trace files checked; both stopped and the postcheck run, also on Ctrl-C, SIGTERM or
# SIGHUP. Model-free; not in `make check`: pr-fast's perf job runs it.
PERF_PORT ?= 8791
PERF_OTLP_PORT ?= 4391
perf-smoke:
	HF_HUB_OFFLINE=1 uv run python scripts/perf_smoke.py --port $(PERF_PORT) --otlp-port $(PERF_OTLP_PORT)

# S3 AC15: the local model server for one session only, never a resident service
# (docs/LOCAL-MODEL.md). ollama-up and ollama-down are the manual pair; eval-local starts the server,
# runs the live contract test and the generation suite, then stops it and runs the postcheck, also
# on an error, Ctrl-C, SIGTERM or SIGHUP (a SIGKILL leaves it up: run make ollama-down).
# PYTHONUNBUFFERED=1: every line (the session's and its commands') reaches a log as it happens.
LOCAL_CONFIG := config/local-ollama.toml
ollama-up:
	PYTHONUNBUFFERED=1 uv run raglab ollama up --config $(LOCAL_CONFIG)

ollama-down:
	PYTHONUNBUFFERED=1 uv run raglab ollama down --config $(LOCAL_CONFIG)

ollama-status:
	PYTHONUNBUFFERED=1 uv run raglab ollama status --config $(LOCAL_CONFIG)

eval-local:
	PYTHONUNBUFFERED=1 uv run raglab ollama session --config config/local-ollama.toml \
		--run "uv run pytest -m live tests/contract/test_chat_contract.py" \
		--run "uv run raglab eval --suite generation --config config/local-ollama.toml"

# S4 AC7: the consistency gate (Q-05), by hand until keys exist. One session: the live contract
# test, then a dev run of the generation suite x3, written to runs/tmp and gated against the
# published local baseline with the margin of docs/THRESHOLDS.md, in one line. A pull request that
# changes the prompt, the generation code, the chunker, the embedder or the model quotes that line.
gate-local:
	PYTHONUNBUFFERED=1 uv run raglab ollama session --config $(LOCAL_CONFIG) \
		--run "uv run pytest -m live tests/contract/test_chat_contract.py" \
		--run "uv run raglab gate --config $(LOCAL_CONFIG)"

# S4 AC9: the local nightly, by hand until keys exist. One session: the live contract test, then
# every retrieval question and behaviour case of every split (dev and test) x3, gate nightly. The
# test split runs only here and at a release: raglab eval refuses it under any other gate.
NIGHTLY_CONFIG := config/local-ollama-nightly.toml
nightly-local:
	PYTHONUNBUFFERED=1 uv run raglab ollama session --config $(NIGHTLY_CONFIG) \
		--run "uv run pytest -m live tests/contract/test_chat_contract.py" \
		--run "uv run raglab eval --suite generation --config $(NIGHTLY_CONFIG) --gate nightly"

# The v0.1 release (docs/plans/2026-10-20-v0.1-release.md): the test slice, once per release, by
# hand until keys exist. First the default retrieval configuration on the test split (embedder only),
# then one session: the live contract test and the generation suite on the test split x3, from
# config/local-ollama-release.toml (a generation run uses its config's split). Both run under gate
# release, the only gate besides nightly that may run or publish the test split.
RELEASE_CONFIG := config/local-ollama-release.toml
release-local:
	HF_HUB_OFFLINE=1 uv run raglab eval --suite retrieval --config config/retrieval-dense.toml \
		--split test --gate release
	PYTHONUNBUFFERED=1 uv run raglab ollama session --config $(RELEASE_CONFIG) \
		--run "uv run pytest -m live tests/contract/test_chat_contract.py" \
		--run "uv run raglab eval --suite generation --config $(RELEASE_CONFIG) --gate release"

# S5 AC3: the judge's live contract test in a session of its own. A judge config's session serves
# the judge's pinned model (its size and digest checked by the preflight before the server starts),
# never the generator's: one model per session. It judges hand-written contract items only, never a
# golden answer, probes both response formats, and writes each call's format, seconds and tokens to
# runs/tmp/judge-contract/. The session stops the server and runs the postcheck, as eval-local does.
JUDGE_CONFIG := config/judge-local.toml
judge-contract:
	PYTHONUNBUFFERED=1 uv run raglab ollama session --config $(JUDGE_CONFIG) \
		--run "uv run pytest -m live -s tests/contract/test_judge_contract.py"

# S5: a short judge session: the judge's live contract test, then the canary set alone (raglab
# canaries), which prints each item's verdict, seconds and tokens and writes them to
# runs/tmp/canaries/; it measures the judge's seconds per call before the judged run's cap is set
judge-canaries:
	PYTHONUNBUFFERED=1 uv run raglab ollama session --config $(JUDGE_CONFIG) \
		--run "uv run pytest -m live -s tests/contract/test_judge_contract.py" \
		--run "uv run raglab canaries --config $(JUDGE_CONFIG)"

# S5 AC7, AC8: a judge session on a finished generation run, RUN=<its id or directory>: the judge's
# live contract test, then raglab judge, which runs the canaries first (one off its side stops the
# session before any judged call, and no record is written), then every answer on its criteria and
# the checks on the judge, written to runs/tmp. The judged run's wall-clock cap is the judge
# config's [judging] run_timeout_s.
judge-local:
	@test -n "$(RUN)" || (echo "give the run to judge: make judge-local RUN=<run id>" >&2; exit 2)
	PYTHONUNBUFFERED=1 uv run raglab ollama session --config $(JUDGE_CONFIG) \
		--run "uv run pytest -m live -s tests/contract/test_judge_contract.py" \
		--run "uv run raglab judge --run $(RUN) --config $(JUDGE_CONFIG)"

# S5 AC10: DeepEval 4.3.1 lives in tools/deepeval-check, a uv project with its own lock; the main
# environment never installs it. deepeval-test runs that project's offline tests in its own
# environment (telemetry off, a loopback-only socket guard, DeepEval's pytest plugin not loaded);
# deepeval-check runs its checks (AC11) in a judge session: the judge's live contract test, the
# canaries, then the checks, JUDGED=<a judged run> for the cross-check. Neither is in make check.
DEEPEVAL := tools/deepeval-check
deepeval-test:
	DEEPEVAL_TELEMETRY_OPT_OUT=1 uv run --project $(DEEPEVAL) --locked pytest $(DEEPEVAL)/tests

deepeval-check:
	@test -n "$(JUDGED)" || (echo "give a judged run: make deepeval-check JUDGED=<run id>" >&2; exit 2)
	DEEPEVAL_TELEMETRY_OPT_OUT=1 PYTHONUNBUFFERED=1 uv run raglab ollama session --config $(JUDGE_CONFIG) \
		--run "uv run pytest -m live -s tests/contract/test_judge_contract.py" \
		--run "uv run raglab canaries --config $(JUDGE_CONFIG)" \
		--run "uv run --project $(DEEPEVAL) --locked python -m deepeval_check --judged runs/published/$(JUDGED)"

# S5 AC12: a published judged record's measured tokens priced with config/prices.toml per call,
# case-trial, run and month for each option of config/cost-assumptions.toml (no model, no network)
cost:
	@test -n "$(JUDGED)" || (echo "give a judged run: make cost JUDGED=<run id>" >&2; exit 2)
	uv run raglab cost --judged $(JUDGED)

# S5 AC9: the position test, one generator session: the generator's live contract test, then each
# position case with its answering chunk first, in the middle and last of a long context, written
# to runs/tmp; its judge's correct comes after, in a judge session (make judge-local RUN=<it>).
POSITION_CONFIG := config/position-local.toml
position-local:
	PYTHONUNBUFFERED=1 uv run raglab ollama session --config $(POSITION_CONFIG) \
		--run "uv run pytest -m live tests/contract/test_chat_contract.py" \
		--run "uv run raglab position --config $(POSITION_CONFIG)"

# S7 (AG6): every guard layer over its must-block and must-not-block cases (datasets/security/ and
# the derived suites: the golden set's dev questions, the clean inventory, the attack pages and
# the consistency baseline's recorded answers), no model; per layer the miss and false-block rates
# with their Wilson intervals and the added latency, written to runs/guard-suites/. make test
# already decides every case binary per build (tests/security/); this is the measured record.
.PHONY: guard-suites replay attack-local
guard-suites:
	HF_HUB_OFFLINE=1 uv run raglab guard-suites

# S7 (AG10, D3): today's default guards replayed over the consistency baseline and its repeats, no
# model. Zero events writes runs/replays/<baseline>--<guard set sha256>.json, which keeps the
# baseline current for the new guard set; any event is printed and nothing is written.
replay:
	HF_HUB_OFFLINE=1 uv run raglab replay

# S7 (AG9): the live attack runs, one generator session (docs/LOCAL-MODEL.md), by hand and only
# with the maintainer's go: the live contract test, then the attack suite on
# config/attack-local.toml (the security pack's attack cases, three trials, the consistency gate's
# pipeline and seed) in two
# configurations, each inside the loopback-only egress guard: defences off (S3's guard set, no
# instruction scan; a measured result, kept in runs/tmp, reported by counts, never published) and
# defences on (S7a's guard set and the scan; the command exits 1 if any safety check of any case
# and trial fails, or anything left loopback). The session stops the server and runs the
# postcheck, as eval-local does.
ATTACK_CONFIG := config/attack-local.toml
attack-local:
	PYTHONUNBUFFERED=1 uv run raglab ollama session --config $(ATTACK_CONFIG) \
		--run "uv run pytest -m live tests/contract/test_chat_contract.py" \
		--run "uv run raglab eval --suite attack --config $(ATTACK_CONFIG) --defences off" \
		--run "uv run raglab eval --suite attack --config $(ATTACK_CONFIG) --defences on"

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

# the static playground, served on 127.0.0.1 as Pages lays it out (playground/ next to
# runs/published/; .github/workflows/pages.yml publishes the same layout, as plain files); it
# reads the published runs and never calls a model
playground:
	uv run python scripts/serve_playground.py
