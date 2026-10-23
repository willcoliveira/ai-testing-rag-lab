"""Serve the playground locally (`make playground`), laid out as Pages publishes it.

A site directory under runs/tmp/ links the playground's files and runs/published/ side by side,
so the page's relative paths (runs/published/index.json) work as they do on Pages, below the
project path, and nothing else of the repo is served. The server listens on 127.0.0.1 only.
With --out, the same layout is written as plain files to a new directory and nothing is served:
the Pages workflow (.github/workflows/pages.yml, docs/GO-PUBLIC.md step 9) uploads that directory.

Usage: uv run python scripts/serve_playground.py [--port 8000]
       python3 scripts/serve_playground.py --out _site
"""

import argparse
import contextlib
import functools
import http.server
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "runs" / "tmp" / "playground-site"


def build_site(root: Path, site: Path, *, copy: bool = False) -> Path:
    """The site directory: each playground file and runs/published, side by side. Linked for
    `make playground`, so an edit shows on a reload; copied as plain files for Pages (`copy`),
    whose artifact holds the files themselves."""
    if site.exists():
        shutil.rmtree(site)
    (site / "runs").mkdir(parents=True)
    place = copy_into if copy else link_into
    for path in sorted((root / "playground").iterdir()):
        place(path, site / path.name)
    published = root / "runs" / "published"
    published.mkdir(parents=True, exist_ok=True)
    place(published, site / "runs" / "published")
    return site


def link_into(source: Path, target: Path) -> None:
    target.symlink_to(source, target_is_directory=source.is_dir())


def copy_into(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--out",
        type=Path,
        help="write the site as plain files to this new directory and exit (the Pages build)",
    )
    args = parser.parse_args(argv)
    if args.out is not None:
        # a new directory only: build_site empties an existing one first
        if args.out.exists():
            parser.error(f"--out {args.out} exists; give a new directory")
        site = build_site(ROOT, args.out, copy=True)
        files = sum(1 for path in site.rglob("*") if path.is_file())
        print(f"pages site: {files} files in {site}")
        return 0
    site = build_site(ROOT, SITE)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"playground: http://127.0.0.1:{args.port}/ (Ctrl-C stops it)")
        with contextlib.suppress(KeyboardInterrupt):
            server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
