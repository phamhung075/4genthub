#!/usr/bin/env python3
"""Classify — and optionally prune — the stash patches the pre-commit framework leaves behind.

WHY THIS EXISTS. The repository's pre-commit framework rewinds the WHOLE worktree to the index on every
commit (`staged_files_only` in `pre_commit/commands/run.py`), and it does that by writing the tree's
unstaged diff into `$PRE_COMMIT_HOME` as `patch<epoch>-<pid>` first. Every seat has its own store, so the
parked set is scattered across a dozen directories and nothing ever removes it. Two things then go wrong:

  * a seat (or a human) can re-apply a parked patch whose content is ALREADY in the tree, which duplicates
    or breaks content that was fine; and
  * a patch left by an interrupted commit is indistinguishable, by name, from a live one — and that is not
    hypothetical: the 2026-10-08 23:28 interruption on this box left a 0-byte patch behind.

So the scan answers exactly one question per patch — is its content in the tree RIGHT NOW — and prints the
COUNT of each answer rather than a pass. A summary that says "ok" after scanning zero patches is the failure
mode this script refuses: it exits 2 and says so.

WHAT IT WILL NOT DO. It never prunes `carried` (content absent — a live parked diff), `drifted` (neither
direction applies — needs an eye) or `empty` (0 bytes — an interrupted write, and the incident artifact is
one). Those are named instead. `--prune` moves only patches that are BOTH already-applied and at least
`--max-age-hours` old, into `<store>/pruned/`, and records them in `<store>/pruned-manifest.log` first.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PATCH_NAME = re.compile(r"^patch(?P<epoch>\d+)-(?P<pid>\d+)$")

# The layout this exists for: one store per seat under the OpenRig state dir, plus the framework's
# historical default, which still holds the largest pile.
#
# NOTE, AND IT COST A FALSE GREEN: `~` IS NOT THE HUMAN'S HOME INSIDE A SEAT. A seat's $HOME points at its
# own state directory, so `~/.cache/pre-commit` resolves to that SEAT'S store and `~/.openrig/state/…` to a
# path that does not exist — the first run of this scan reported "1 store, 99 patches" and quietly ignored
# the other 653. The human's home is therefore read from the passwd database, never from $HOME.
# THAT LESSON WAS IN THE COMMENT BUT NOT IN THE CODE: the first version of `default_stores` kept `{home}`
# inside the strings and called `expanduser`, which substitutes `~` and NOTHING ELSE. Both patterns stayed
# literal, `is_dir()` was false for both, and the scan reported "no patch store exists" on a box holding 764
# patches — a vacuous scan that LOOKED like an empty problem. The home is now composed from the passwd
# database; `~` is used only for the seat's own store, where it is the right answer.

APPLIED = "applied"  # content is already in the tree; the patch is spent
CARRIED = "carried"  # content is NOT in the tree; this is a live parked diff
DRIFTED = "drifted"  # neither direction applies; a human has to look
EMPTY = "empty"  # 0 bytes: an interrupted write, not a patch

CLASSES = (APPLIED, CARRIED, DRIFTED, EMPTY)


def human_home() -> Path:
    """The HUMAN's home. Inside a seat `~` is the seat's own state dir, so it is never used here."""
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def default_stores(
    home: Path | None = None, environ: dict[str, str] | None = None
) -> list[Path]:
    """Every store that HOLDS a patch: $PRE_COMMIT_HOME, this seat's own, the human's, and one per seat.

    A store with no `patch*` in it is not evidence either way, and this box carries ~170 empty
    `<state>/<kind>/<name>.json/.cache/pre-commit` directories; printing those beside the ten that matter
    is how a real count gets read as noise.

    `home` and `environ` are seams: the discovery has to be testable without depending on this machine's
    passwd entry or environment.
    """
    human = Path(home) if home is not None else human_home()
    env = os.environ if environ is None else environ
    candidates: list[Path] = []
    env_home = env.get("PRE_COMMIT_HOME")
    if env_home:
        candidates.append(Path(env_home).expanduser())
    candidates.append(Path("~/.cache/pre-commit").expanduser())  # THIS seat's own store
    candidates.append(human / ".cache" / "pre-commit")
    candidates.extend(
        sorted((human / ".openrig" / "state").glob("*/*/.cache/pre-commit"))
    )
    seen: set[Path] = set()
    stores: list[Path] = []
    for cand in candidates:
        real = cand.resolve()
        if real in seen:
            continue
        seen.add(real)
        if not real.is_dir() or not any(real.glob("patch*")):
            continue
        stores.append(real)
    return stores


def git_repo_root(start: Path) -> Path | None:
    """`--no-optional-locks` on the read: a plain git call rewrites the index stat cache."""
    proc = subprocess.run(
        ["git", "--no-optional-locks", "rev-parse", "--show-toplevel"],
        cwd=start,
        capture_output=True,
        text=True,
    )
    return Path(proc.stdout.strip()) if proc.returncode == 0 and proc.stdout.strip() else None


def applies(repo: Path, patch: Path, *, reverse: bool) -> bool:
    """Would this patch apply cleanly? `--check` is a dry run; it writes nothing, index included."""
    args = ["git", "--no-optional-locks", "apply", "--check"]
    if reverse:
        args.append("--reverse")
    args.append(str(patch))
    return subprocess.run(args, cwd=repo, capture_output=True, text=True).returncode == 0


def classify(repo: Path, patch: Path) -> str:
    if patch.stat().st_size == 0:
        return EMPTY
    # Reverse first: a patch whose content is present is the one that must not be re-applied.
    if applies(repo, patch, reverse=True):
        return APPLIED
    if applies(repo, patch, reverse=False):
        return CARRIED
    return DRIFTED


def patch_epoch(patch: Path) -> int:
    """The framework puts the epoch in the name; the mtime is only a fallback."""
    match = PATCH_NAME.match(patch.name)
    return int(match.group("epoch")) if match else int(patch.stat().st_mtime)


def scan(repo: Path, stores: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for store in stores:
        for patch in sorted(store.glob("patch*")):
            if not patch.is_file():
                continue
            rows.append(
                {
                    "store": str(store),
                    "path": str(patch),
                    "name": patch.name,
                    "bytes": patch.stat().st_size,
                    "epoch": patch_epoch(patch),
                    "age_hours": round((time.time() - patch_epoch(patch)) / 3600, 1),
                    "class": classify(repo, patch),
                }
            )
    return rows


def prune(repo: Path, rows: list[dict], max_age_hours: float) -> list[dict]:
    """Move applied-and-old patches out of the live set. Nothing else is ever touched."""
    moved: list[dict] = []
    for row in rows:
        if row["class"] != APPLIED or row["age_hours"] < max_age_hours:
            continue
        src = Path(row["path"])
        dest_dir = Path(row["store"]) / "pruned"
        dest_dir.mkdir(exist_ok=True)
        digest = hashlib.sha1(src.read_bytes()).hexdigest()
        with (Path(row["store"]) / "pruned-manifest.log").open("a", encoding="utf-8") as log:
            log.write(
                f"{int(time.time())} moved {row['name']} bytes={row['bytes']} epoch={row['epoch']} "
                f"age_hours={row['age_hours']} sha1={digest} class={row['class']}\n"
            )
        shutil.move(str(src), str(dest_dir / row["name"]))
        moved.append(row)
    return moved


def summarise(rows: list[dict], stores: list[Path]) -> dict:
    counts = {name: sum(1 for r in rows if r["class"] == name) for name in CLASSES}
    per_store = {}
    for store in stores:
        store_rows = [r for r in rows if r["store"] == str(store)]
        per_store[str(store)] = {
            "patches": len(store_rows),
            **{name: sum(1 for r in store_rows if r["class"] == name) for name in CLASSES},
        }
    epochs = [r["epoch"] for r in rows]
    return {
        "stores": len(stores),
        "patches": len(rows),
        "counts": counts,
        "per_store": per_store,
        "oldest_epoch": min(epochs) if epochs else None,
        "newest_epoch": max(epochs) if epochs else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--store", action="append", default=[], help="a patch store; repeatable")
    parser.add_argument("--repo", default=None, help="the git repo the patches were made against")
    parser.add_argument("--prune", action="store_true", help="move applied+old patches to <store>/pruned/")
    parser.add_argument("--max-age-hours", type=float, default=24.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve() if args.repo else git_repo_root(Path.cwd())
    if repo is None:
        print("not a git repository (pass --repo)", file=sys.stderr)
        return 2

    stores = [Path(s).expanduser().resolve() for s in args.store]
    stores = [s for s in stores if s.is_dir()] if args.store else default_stores()
    if not stores:
        print(
            "SCANNED NOTHING: no store holds a patch — a scan with nothing in it proves nothing",
            file=sys.stderr,
        )
        return 2

    rows = scan(repo, stores)
    if not rows:
        print(
            f"SCANNED 0 PATCHES across {len(stores)} store(s) — the scan is vacuous, not a pass",
            file=sys.stderr,
        )
        return 2

    summary = summarise(rows, stores)
    moved = prune(repo, rows, args.max_age_hours) if args.prune else []

    if args.json:
        print(json.dumps({**summary, "moved": [m["name"] for m in moved]}, indent=2))
        return 0

    print(f"stores scanned: {summary['stores']}   patches scanned: {summary['patches']}")
    print(f"  {APPLIED:<8} {summary['counts'][APPLIED]:>4}  content already in the tree; safe to prune once old")
    print(f"  {CARRIED:<8} {summary['counts'][CARRIED]:>4}  content NOT in the tree — a live parked diff, never pruned")
    print(f"  {DRIFTED:<8} {summary['counts'][DRIFTED]:>4}  applies neither way — named below, needs an eye")
    print(f"  {EMPTY:<8} {summary['counts'][EMPTY]:>4}  0 bytes — an interrupted write, not a patch")
    for row in rows:
        if row["class"] in (DRIFTED, EMPTY):
            print(f"    {row['class']:<8} {row['age_hours']:>7}h  {row['path']}")
    if args.prune:
        print(f"pruned: {len(moved)} moved to <store>/pruned/ (manifest: <store>/pruned-manifest.log)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
