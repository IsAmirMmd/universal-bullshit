"""Build the static file-manager site into _site/.

Copies every tracked file of the repo (except tooling folders) into _site/,
writes _site/files.json with name/size/last-commit date for each file, and
puts the file-manager page at _site/index.html.

Usage:  python site/build.py [out_dir]
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "_site"
EXCLUDE_PREFIXES = (".github/", ".claude/", "site/", "_site/")
EXCLUDE_FILES = {".gitignore", ".gitattributes"}


def git(*args):
    return subprocess.run(
        ["git", "-c", "core.quotepath=off", *args],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout.decode("utf-8")


def tracked_files():
    out = git("ls-files", "-z")
    files = [p for p in out.split("\0") if p]
    return [
        p for p in files
        if not p.startswith(EXCLUDE_PREFIXES)
        and p not in EXCLUDE_FILES
        and (ROOT / p).is_file()
    ]


def last_commit_dates():
    """Map path -> ISO date of the last commit that touched it (one git call)."""
    dates = {}
    out = git("log", "--format=\x01%cI", "--name-only", "-z", "HEAD")
    for block in out.split("\x01"):
        if not block.strip("\0\n"):
            continue
        tokens = [t.strip("\n") for t in block.replace("\n", "\0").split("\0")]
        tokens = [t for t in tokens if t]
        if not tokens:
            continue
        date, paths = tokens[0], tokens[1:]
        for p in paths:
            if p not in dates:
                dates[p] = date
    return dates


def main():
    files = tracked_files()
    dates = last_commit_dates()

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    entries = []
    for p in files:
        src = ROOT / p
        dst = OUT / p
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        entries.append({"path": p, "size": src.stat().st_size, "mtime": dates.get(p)})

    entries.sort(key=lambda e: e["path"].lower())
    (OUT / "files.json").write_text(
        json.dumps({"generated": git("log", "-1", "--format=%cI").strip(), "files": entries},
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    shutil.copy2(ROOT / "site" / "index.html", OUT / "index.html")
    (OUT / ".nojekyll").write_text("")
    print(f"built {len(entries)} files into {OUT}")


if __name__ == "__main__":
    main()
