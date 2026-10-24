"""`raglab serve`: the API built from a generation config, run by uvicorn.

It listens on 127.0.0.1 unless told otherwise (the container passes --host 0.0.0.0 inside its
own network namespace), without the server header. /version reports the commit from the
RAGLAB_GIT_SHA environment variable (the container's build argument) or from git.

S9 (docs/OBSERVABILITY.md): before anything is built or any port is bound, the environment is
checked (raglab.api.environment: RAGLAB_ENV, PERF_TEST_MODE and the content opt-in) and so is the
trace endpoint (raglab.obs.otel.endpoint: RAGLAB_OTLP_ENDPOINT, loopback only). A refusal ends
`raglab serve` with one line and exit 1. With an endpoint, this is the only place a tracer provider
is built: FastAPI's request span and the pipeline's spans go to it, and the batch is flushed when
the server stops gracefully. Without one nothing is traced.
"""

import os
from collections.abc import Mapping
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from raglab import __version__
from raglab.api import environment
from raglab.api.app import VersionInfo, create_app
from raglab.evals import config as eval_config
from raglab.evals import retrieval
from raglab.generate import assemble
from raglab.generate.pipeline import PROMPT_VERSION
from raglab.obs import otel

GIT_SHA_ENV = "RAGLAB_GIT_SHA"


def git_sha(root: Path) -> str:
    configured = os.environ.get(GIT_SHA_ENV)
    if configured:
        return configured
    try:
        state = retrieval.git_state(root)
    except (RuntimeError, OSError, ValueError):
        return "unknown"
    return state.sha + ("-dirty" if state.dirty else "")


def build_app(config_path: Path, root: Path, environ: Mapping[str, str] | None = None) -> FastAPI:
    environ = os.environ if environ is None else environ
    config = eval_config.load_generation(config_path, root, perf_stub=True)
    if not config.tokens:
        raise eval_config.ConfigError(f"{config_path}: serving needs [api] tokens")
    switches = environment.switches(environ, config.generator.provider)
    try:
        endpoint = otel.endpoint(environ)
    except otel.TracingError as error:
        raise environment.EnvironmentRefused(str(error)) from error
    tracing = None if endpoint is None else otel.for_endpoint(endpoint, switches.capture_content)
    built = assemble.assemble(config, root, tracer=None if tracing is None else tracing.tracer)
    chat = built.chat_description
    info = VersionInfo(
        raglab=__version__,
        git_sha=git_sha(root),
        prompt_version=PROMPT_VERSION,
        provider=str(chat["provider"]),
        model=str(chat["model"]),
        digest=str(chat["digest"]),
        provenance=built.provenance,
    )
    return create_app(
        built.pipeline,
        info,
        config.tokens,
        config.generation.seed,
        tracer_provider=None if tracing is None else tracing.provider,
        on_shutdown=None if tracing is None else tracing.shutdown,
        environ=environ,
    )


def serve(config_path: Path, root: Path, host: str, port: int) -> int:
    app = build_app(config_path, root)
    print(f"raglab serve: http://{host}:{port}/ ({config_path})", flush=True)
    uvicorn.run(app, host=host, port=port, server_header=False, proxy_headers=False)
    return 0
