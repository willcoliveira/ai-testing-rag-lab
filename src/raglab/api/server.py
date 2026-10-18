"""`raglab serve`: the API built from a generation config, run by uvicorn.

It listens on 127.0.0.1 unless told otherwise (the container passes --host 0.0.0.0 inside its
own network namespace), without the server header. /version reports the commit from the
RAGLAB_GIT_SHA environment variable (the container's build argument) or from git.
"""

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from raglab import __version__
from raglab.api.app import VersionInfo, create_app
from raglab.evals import config as eval_config
from raglab.evals import retrieval
from raglab.generate import assemble
from raglab.generate.pipeline import PROMPT_VERSION

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


def build_app(config_path: Path, root: Path) -> FastAPI:
    config = eval_config.load_generation(config_path, root)
    if not config.tokens:
        raise eval_config.ConfigError(f"{config_path}: serving needs [api] tokens")
    built = assemble.assemble(config, root)
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
    return create_app(built.pipeline, info, config.tokens, config.generation.seed)


def serve(config_path: Path, root: Path, host: str, port: int) -> int:
    app = build_app(config_path, root)
    print(f"raglab serve: http://{host}:{port}/ ({config_path})", flush=True)
    uvicorn.run(app, host=host, port=port, server_header=False, proxy_headers=False)
    return 0
