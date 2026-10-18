# The lab container (S3, AC10): the API and the page with the FAKE chat model and the real local
# embedder, baked in at build time with every file's sha256 checked (raglab fetch-model). It runs
# as a non-root user and needs no network at run time. Build and run it with `make container` and
# `make container-run` (published on 127.0.0.1 only); `make zap` scans it (deploy/zap/).
# Lab practice: a production image would come from CI with an SBOM and a vulnerability scan, and
# would carry a real model behind a managed endpoint (S3h, S10).

# python 3.13.16 on Debian 13.7: the multi-arch index digest, so amd64 and arm64 build alike
FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

ARG GIT_SHA=unknown
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    RAGLAB_MODEL_DIR=/opt/raglab/models \
    RAGLAB_GIT_SHA=${GIT_SHA}

# Tesseract reads the pack's scanned page when the server ingests the pack at start; pinned, so a
# new package build fails here instead of changing the OCR text silently
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        "tesseract-ocr=5.5.0-1+b1" \
        "tesseract-ocr-eng=1:4.1.0-2" \
        "tesseract-ocr-osd=1:4.1.0-2" \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# uv itself, hash-pinned as in CI
COPY .github/ci-requirements.txt /tmp/uv-requirements.txt
RUN pip install --no-cache-dir --require-hashes --no-deps -r /tmp/uv-requirements.txt \
    && rm /tmp/uv-requirements.txt

# the locked runtime dependencies and raglab itself (no dev tools)
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable && rm -rf /root/.cache

# what the server reads at start: the pack, the configs, the questions and the record schema
COPY corpus ./corpus
COPY config ./config
COPY datasets ./datasets
COPY schemas ./schemas

# the embedder's pinned files, downloaded once here and checked against their sha256
RUN /app/.venv/bin/raglab fetch-model && chmod -R a+rX /opt/raglab

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin raglab
USER 10001
ENV HF_HUB_OFFLINE=1 \
    PATH=/app/.venv/bin:$PATH

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"]
# 0.0.0.0 inside the container's own network namespace only; `make container-run` publishes the
# port on the host's 127.0.0.1
CMD ["raglab", "serve", "--config", "config/fake.toml", "--host", "0.0.0.0", "--port", "8000", "--root", "/app"]
