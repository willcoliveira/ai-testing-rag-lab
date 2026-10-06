"""Serve the playground locally (`make playground`), laid out as Pages will publish it.

A site directory under runs/tmp/ links the playground's files and runs/published/ side by side,
so the page's relative paths (runs/published/index.json) work as they will on Pages, and nothing
else of the repo is served. The server listens on 127.0.0.1 only. The playground stays local until
the repo goes public (S2 decision; Pages is a step in docs/GO-PUBLIC.md).

Usage: uv run python scripts/serve_playground.py [--port 8000]
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


def build_site(root: Path, site: Path) -> Path:
    """The site directory: a link to each playground file and to runs/published."""
    if site.exists():
        shutil.rmtree(site)
    (site / "runs").mkdir(parents=True)
    for path in sorted((root / "playground").iterdir()):
        (site / path.name).symlink_to(path)
    published = root / "runs" / "published"
    published.mkdir(parents=True, exist_ok=True)
    (site / "runs" / "published").symlink_to(published, target_is_directory=True)
    return site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    site = build_site(ROOT, SITE)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site))
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"playground: http://127.0.0.1:{args.port}/ (Ctrl-C stops it)")
        with contextlib.suppress(KeyboardInterrupt):
            server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
