"""Publish a run: validate it, run the privacy check on its files, copy it to
runs/published/<run_id>/ and rebuild runs/published/index.json, which the playground reads.

A run is refused when it is not a valid run record, when it was made from a dirty work tree
(git_dirty: its commit would not reproduce it), when its provenance is fake or any model field
says fake (provider, revision or digest), when it is partial, when it holds the test cases
(split test or all) under a gate other than nightly or release (S4), when one of its files holds a
string the answer key says no answer may repeat (the planted secret,
personal details and attack canaries: `answer_must_not_contain`, R-19), or when the privacy check
finds anything in its files. The privacy check reads the files at their published path
(runs/published/<run_id>/), where privacy/allowlist-published.txt applies; a refused run's copy is
removed again. An already published run is replaced only
by identical files. `--baseline` makes the run the baseline of its suite, config and split, which
the no-regression gate compares against.
"""

import json
import shutil
import subprocess  # nosec B404
from collections.abc import Callable
from pathlib import Path
from typing import cast

from raglab.evals import record
from raglab.evals.config import held_out_problem
from raglab.evals.record import Json, as_json
from raglab.ingest import answer_key

PUBLISHED = "runs/published"
INDEX = "index.json"
INDEX_VERSION = "published-index.v1"
FILES = (record.MANIFEST, record.CASES, record.REPORT)

type PrivacyCheck = Callable[[Path, Path], list[str]]


class PublishError(ValueError):
    pass


def node_privacy_check(run_dir: Path, root: Path) -> list[str]:
    """scripts/check-forbidden.mjs over the run's directory; its output lines when it finds
    anything (or cannot run)."""
    node = shutil.which("node")
    if node is None:
        return ["node is not on PATH: the privacy check cannot run"]
    # our own script with fixed arguments, no shell
    command = [node, "scripts/check-forbidden.mjs", "--dir", str(run_dir.resolve())]
    done = subprocess.run(  # noqa: S603  # nosec B603
        command, cwd=root, capture_output=True, text=True, check=False
    )
    if done.returncode == 0:
        return []
    return [line for line in (done.stdout + done.stderr).splitlines() if line.strip()] or [
        f"the privacy check exited {done.returncode}"
    ]


def planted_strings(run_dir: Path, root: Path) -> list[str]:
    """Each run file line that holds one of the answer key's answer_must_not_contain strings."""
    try:
        banned = answer_key.must_not_contain(root)
    except (OSError, ValueError) as error:  # fails closed: no check, no publish
        return [f"the answer key cannot be read ({error})"]
    found: list[str] = []
    for name in FILES:
        lines = (run_dir / name).read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            for feature, strings in sorted(banned.items()):
                found += [f"{name}:{number}: {feature}'s {s!r}" for s in strings if s in line]
    return found


def baseline_key(manifest: Json) -> str:
    return f"{manifest['suite']}/{as_json(manifest['config'])['name']}/{manifest['split']}"


def index_entry(manifest: Json) -> Json:
    embedder = as_json(manifest["embedder"])
    retriever = as_json(manifest["retriever"])
    entry: Json = {
        "run_id": manifest["run_id"],
        "path": f"{manifest['run_id']}/",
        "created_at": manifest["created_at"],
        "suite": manifest["suite"],
        "split": manifest["split"],
        "config": as_json(manifest["config"])["name"],
        "provenance": manifest["provenance"],
        "git_sha": manifest["git_sha"],
        "embedder": f"{embedder['model']}@{str(embedder['revision'])[:7]}",
        "retriever": retriever["kind"],
        "k": retriever["k"],
        "chunk_size": as_json(manifest["chunker"])["chunk_size"],
        "n": as_json(manifest["totals"])["cases"],
        "metrics": as_json(manifest["results"])["metrics"],
    }
    if "generator" in manifest:  # a generation run (S3): the model and its pinned digest
        generator = as_json(manifest["generator"])
        entry["generator"] = f"{generator['model']}@{str(generator['digest'])[:12]}"
        entry["prompt"] = as_json(manifest["prompt"])["version"]
    return entry


def read_index(published: Path) -> Json:
    path = published / INDEX
    if not path.is_file():
        return {"schema_version": INDEX_VERSION, "runs": [], "baselines": {}}
    return as_json(json.loads(path.read_text(encoding="utf-8")))


def build_index(published: Path, baselines: dict[str, str]) -> Json:
    """The index of every run directory under published, newest first, with the baselines."""
    runs: list[Json] = []
    for manifest_path in sorted(published.glob(f"*/{record.MANIFEST}")):
        runs.append(index_entry(as_json(json.loads(manifest_path.read_text(encoding="utf-8")))))
    runs.sort(key=lambda r: (str(r["created_at"]), str(r["run_id"])), reverse=True)
    known = {str(r["run_id"]) for r in runs}
    missing = {key: run for key, run in baselines.items() if run not in known}
    if missing:
        raise PublishError(f"baselines name runs that are not published: {missing}")
    return {
        "schema_version": INDEX_VERSION,
        "runs": runs,
        "baselines": dict(sorted(baselines.items())),
    }


def write_index(published: Path, index: Json) -> None:
    (published / INDEX).write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def publish(
    run_dir: Path, root: Path, baseline: bool = False, privacy: PrivacyCheck = node_privacy_check
) -> Path:
    if problems := record.validate(run_dir, root):
        raise PublishError("not a valid run record: " + "; ".join(problems))
    manifest, _ = record.read(run_dir)
    if manifest["git_dirty"]:
        raise PublishError(
            f"{manifest['run_id']} was made from a dirty work tree: commit, then run it again"
        )
    fake = record.fake_models(manifest)
    if manifest["provenance"] == "fake" or fake:
        raise PublishError(
            f"{manifest['run_id']} has fake provenance or a fake model "
            f"({', '.join(fake) or 'provenance fake'}): fake runs are never published"
        )
    if manifest["partial"]:
        raise PublishError(f"{manifest['run_id']} is partial")
    if held_out := held_out_problem(str(manifest["split"]), str(manifest["gate"])):
        raise PublishError(f"{manifest['run_id']}: {held_out}")
    if found := planted_strings(run_dir, root):
        raise PublishError("the run repeats strings no answer may hold:\n" + "\n".join(found))
    published = root / PUBLISHED
    dest = published / str(manifest["run_id"])
    new_folder = not published.exists()
    created = False
    if dest.exists():
        for name in FILES:
            if (dest / name).read_bytes() != (run_dir / name).read_bytes():
                raise PublishError(f"{dest} is already published with different files")
    elif dest.resolve() != run_dir.resolve():
        dest.mkdir(parents=True)
        created = True
        for name in FILES:
            shutil.copyfile(run_dir / name, dest / name)
    if found := privacy(dest if dest.exists() else run_dir, root):
        if created:
            shutil.rmtree(dest)
            if new_folder:
                published.rmdir()
        raise PublishError("the privacy check found:\n" + "\n".join(found))
    baselines = {
        str(k): str(v) for k, v in as_json(read_index(published).get("baselines", {})).items()
    }
    if baseline:
        baselines[baseline_key(manifest)] = str(manifest["run_id"])
    write_index(published, build_index(published, baselines))
    return dest


def baseline_run(root: Path, key: str) -> Path | None:
    """The published run that is the baseline for key (suite/config/split), if any."""
    published = root / PUBLISHED
    run = as_json(read_index(published).get("baselines", {})).get(key)
    return published / cast(str, run) if run else None
