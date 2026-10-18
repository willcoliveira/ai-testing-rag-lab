#!/bin/sh
# The ZAP baseline scan of the raglab container (S3, AC11), on the Mac: `make zap` (after
# `make container`). It starts the container on 127.0.0.1:8000, waits for /healthz, runs ZAP's
# baseline (passive) scan from its own container against the host ("host.docker.internal") with
# deploy/zap/rules.tsv, and stops the container whatever happens. The reports land in
# runs/tmp/zap/ (gitignored). Exit code: ZAP's (0 pass, 1 FAIL, 2 WARN).
# Lab practice: CI runs the same scan against the deployed host from S3h.
set -eu
IMAGE="${1:-raglab:local}"
# ghcr.io/zaproxy/zaproxy:stable, the multi-arch index digest (2026-10-18; ZAP 2.17.0)
ZAP="ghcr.io/zaproxy/zaproxy:stable@sha256:5ccfff9a411743ab2615136a2edd7416bec9ce41572fa94e935df38c14adb2b6"
OUT="runs/tmp/zap"
NAME="raglab-zap-target"
# Docker Desktop's name for the host, seen from inside a container
TARGET_HOST="host.docker.internal"

mkdir -p "$OUT"
cp deploy/zap/rules.tsv "$OUT/rules.tsv"
# nothing is made world-writable (judge S3-S4): the folder keeps the caller's default mode, and
# Docker Desktop's file sharing lets ZAP's container user write into it. Lab practice: on a Linux
# host, where a bind mount keeps the host's owner, chown the folder to ZAP's uid (1000) instead.
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --rm --name "$NAME" -p 127.0.0.1:8000:8000 "$IMAGE" >/dev/null
trap 'docker stop "$NAME" >/dev/null 2>&1 || true' EXIT INT TERM

i=0
until curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 120 ]; then echo "zap: the container did not answer /healthz" >&2; exit 1; fi
  sleep 1
done

docker run --rm -v "$PWD/$OUT:/zap/wrk:rw" "$ZAP" zap-baseline.py \
  -t "http://${TARGET_HOST}:8000" -c rules.tsv -r report.html -J report.json -w report.md
