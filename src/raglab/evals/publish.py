"""Publish a run: validate it, run the privacy check on its files, copy it to
runs/published/<run_id>/ and rebuild runs/published/index.json, which the playground reads.

A run is refused when it is not a valid run record, when it was made from a dirty work tree
(git_dirty: its commit would not reproduce it), when its provenance is fake or any model field
says fake (provider, revision or digest), when it is partial, when it holds the test cases (split
test or all) under a gate other than nightly or release (S4), when one of its files holds a string
the answer key says no answer may repeat (the planted secret, personal details and attack
canaries: `answer_must_not_contain`, R-19; since S4's D3 the plain attack phrases only in attack
runs), when it is a judged run (S5) whose source run is not published, or that was made under
another docs/CRITERIA.md or canary set than the tree's (stale), when it is an attack run (S7) made
with the defences off (a measured result, reported by counts only) or whose egress guard saw an
attempt off loopback, or when the privacy check finds anything in its files. The privacy check
reads the files at their published path (runs/published/<run_id>/), where
privacy/allowlist-published.txt applies
(the planted exception ids and, since D3, the team contact addresses); a refused run's copy is
removed again. An already published run is replaced only by identical files. `--baseline` makes
the run the baseline of its suite, config and split, which the no-regression gate compares
against.
"""

import json
import re
import shutil
import subprocess  # nosec B404
from collections.abc import Callable
from pathlib import Path
from typing import cast

from raglab.evals import judged_record, record
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


# D3 (the user's decision of 2026-10-19, "Narrow both (Recommended)"). The suites whose runs read
# the register's documents only, so no attack page is indexed and no answer repeats one. In their
# runs the plain attack phrases (words only, such as F-48's "never expire") do not block, because
# a correct answer on an expiry rule can hold them; every other string blocks every run: the
# planted secret (F-44), the personal details (F-45), the canary token and the planted links and
# address. A run of any other suite (S7's attack suite) is held to every string.
CLEAN_SUITES = frozenset({"retrieval", "generation"})
PLAIN_PHRASE = re.compile(r"[A-Za-z0-9]+(?: [A-Za-z0-9]+)*")


def blocks_clean_runs(kind: str, string: str) -> bool:
    """Whether an answer_must_not_contain string blocks a clean run: every string but a plain
    phrase (letters and digits between single spaces) of an attack feature."""
    return not (kind.startswith("attack-") and PLAIN_PHRASE.fullmatch(string))


def banned_strings(root: Path, suite: str) -> dict[str, list[str]]:
    """The answer_must_not_contain strings a run of this suite may not hold, by feature."""
    banned: dict[str, list[str]] = {}
    for feature in answer_key.features(root).values():
        strings = [
            s
            for s in feature.must_not_contain
            if suite not in CLEAN_SUITES or blocks_clean_runs(feature.kind, s)
        ]
        if strings:
            banned[feature.id] = strings
    return banned


def planted_strings(run_dir: Path, root: Path) -> list[str]:
    """Each run file line that holds an answer_must_not_contain string the run's suite may not
    hold (D3: the plain attack phrases only in attack runs; the rest in every run). A judged run
    (S5) is held to its source's suite: it quotes its source's answers and adds the judge's
    reasons."""
    try:
        manifest = as_json(json.loads((run_dir / record.MANIFEST).read_text("utf-8")))
        suite = str(manifest["suite"])
        if suite == judged_record.JUDGED:
            suite = str(as_json(manifest["source"])["suite"])
    except (OSError, ValueError, KeyError):  # an unreadable suite is held to every string
        suite = ""
    try:
        banned = banned_strings(root, suite)
    except (OSError, ValueError, KeyError) as error:  # fails closed: no check, no publish
        return [f"the answer key cannot be read ({error})"]
    found: list[str] = []
    for name in FILES:
        lines = (run_dir / name).read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, start=1):
            folded = line.casefold()  # in any letter case (S4 judge, S4-J3)
            for feature, strings in sorted(banned.items()):
                found += [
                    f"{name}:{number}: {feature}'s {s!r}" for s in strings if s.casefold() in folded
                ]
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
    if "judge" in manifest:  # a judged run (S5): the judge, its prompt and the run it judged
        judge = as_json(manifest["judge"])
        entry["judge"] = f"{judge['model']}@{str(judge['digest'])[:12]}"
        entry["prompt"] = as_json(manifest["judge_prompt"])["version"]
        entry["source"] = as_json(manifest["source"])["run_id"]
    return entry


def judged_problems(manifest: Json, root: Path) -> list[str]:
    """Why a judged run may not be published (S5): its source is not published with the manifest
    it names, or it was made under another docs/CRITERIA.md or another canary set than the ones
    in the tree now (stale, as a changed prompt fingerprint makes a baseline stale)."""
    problems: list[str] = []
    source = as_json(manifest["source"])
    published = root / PUBLISHED / str(source["run_id"])
    try:
        raw = (published / record.MANIFEST).read_bytes()
    except OSError:
        problems.append(f"its source run {source['run_id']} is not published")
    else:
        if record.sha256_bytes(raw) != source["manifest_sha256"]:
            problems.append(f"its source run {source['run_id']} is published with another manifest")
    for part, what in (("criteria", "docs/CRITERIA.md"), ("canaries", "the canary set")):
        block = as_json(manifest[part])
        try:
            current = record.sha256_bytes((root / str(block["path"])).read_bytes())
        except OSError:
            current = ""
        if current != block["sha256"]:
            now = current[:12] or "none"
            problems.append(
                f"it is stale: it was made under another version of {what} "
                f"({block['path']}, sha256 {str(block['sha256'])[:12]}, now {now})"
            )
    return problems


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
    if manifest["suite"] == judged_record.JUDGED and (found := judged_problems(manifest, root)):
        raise PublishError(f"{manifest['run_id']}: " + "; ".join(found))
    if manifest["suite"] == "attack":  # S7: the defences-on run only, with nothing sent out
        block = as_json(manifest["attack"])
        if block["configuration"] != "defences-on":
            raise PublishError(
                f"{manifest['run_id']} was made with the defences off: a measured result, "
                "reported by counts in the ledger and never published"
            )
        if block["egress"] != "none":
            raise PublishError(f"{manifest['run_id']}: its egress guard saw {block['egress']}")
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
