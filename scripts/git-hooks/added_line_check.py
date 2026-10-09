#!/usr/bin/env python3
"""Prove the diff you COMMIT is the diff you made - the strong form of rule 64's shared-file duty.

WHY THIS EXISTS. Rule 64 protects a commit from the tree every seat shares, and its instrument on
`CHANGELOG.md` is a count of added lines beginning `## `. That count cannot see the failing case
(`f344a64f`): a FOREIGN edit made INSIDE an existing entry adds lines under a heading that already
exists, so the count does not move and the commit carries a peer's uncommitted sentence as its own.
Nothing protects the victim of that either - the correction is post-hoc, in someone else's CHANGELOG
entry, after the fact. The heading count is a smoke alarm; this is the strong form the lead recorded
for whoever generalized it: ADDED-LINE SET EQUALITY.

WHAT THE COMMITTER DOES. Immediately AFTER your own edit, take a snapshot:
    python3 scripts/git-hooks/added_line_check.py --snapshot -- <paths>
It writes `<git-dir>/hunk-baselines/<UTC stamp>-<seat>.json`: for each PATCH, the added-line and
removed-line SETS and their sha1s. `<git-dir>` is the SHARED repository, so the baseline is findable
the way the parked-diff captures are. Immediately BEFORE the commit, verify:
    python3 scripts/git-hooks/added_line_check.py --verify <baseline> -- <paths>
It re-computes the same two sets, requires them to be EQUAL, names any SURPLUS line (a line present now
and not in your snapshot - the mixing class) and any line that has gone MISSING, and exits 3 on any
difference so a commit can be gated on it. A path that is NEW (untracked at HEAD) is diffed against
/dev/null, so its whole content is its added set; without that, a baseline over a new file would say
`+0/-0` and vouch for content it never read. Nothing is written to the repository; the diff is read,
never staged.

WHAT IT DOES NOT DO, STATED SO IT IS NOT MISTAKEN FOR COVERAGE. It cannot tell whether the SNAPSHOT
ITSELF was already mixed: if a peer's line was in the file before you took the snapshot, it is in your
baseline and this tool will call it yours. Confirming the path holds YOUR change and only yours at
snapshot time is rule 64's reading duty, and no instrument here replaces it. It also does not stage,
commit, or touch the index - `git diff HEAD -- <path>` compares the WORKTREE with HEAD, which is the
content `git add -- <path>` then `git commit -- <path>` will carry.

USAGE. python3 scripts/git-hooks/added_line_check.py --snapshot -- <paths>
        python3 scripts/git-hooks/added_line_check.py --verify <baseline.json> -- <paths>
        python3 scripts/git-hooks/added_line_check.py --show <baseline.json>
        python3 scripts/git-hooks/added_line_check.py --list
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SEAT_ENV = "OPENRIG_SESSION"
BASELINE_DIRNAME = "hunk-baselines"
EXIT_MISMATCH = 3


def git(*args: str, repo: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=False
    )


def repo_root(start: Path) -> Path | None:
    proc = git("rev-parse", "--show-toplevel", repo=start)
    return Path(proc.stdout.strip()) if proc.returncode == 0 and proc.stdout.strip() else None


def baseline_root(repo: Path) -> Path:
    proc = git("rev-parse", "--absolute-git-dir", repo=repo)
    if proc.returncode != 0:
        raise SystemExit(f"not a git repository: {repo}")
    return Path(proc.stdout.strip()) / BASELINE_DIRNAME


def seat() -> str:
    return re.sub(r"[^A-Za-z0-9._@-]", "_", os.environ.get(SEAT_ENV) or "seat")


def label() -> str:
    """Stamp + seat + pid: the same lesson the parked-diff label learned - two runs in one second."""
    return f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{seat()}-{os.getpid()}"


def is_untracked(repo: Path, path: str) -> bool:
    """A path untracked at HEAD has no `git diff HEAD` at all - its whole content is its added set."""
    status = git("status", "--porcelain", "--", path, repo=repo).stdout
    return status.startswith("??")


def change_sets(repo: Path, path: str) -> dict:
    """The added and removed lines of `git diff HEAD -- <path>`, as sets, with their sha1s.

    A path untracked at HEAD is diffed against /dev/null instead, because `git diff HEAD` reports
    nothing for it: without this, a baseline over a NEW file said `+0/-0` and would vouch for content
    it had never read.
    """
    if is_untracked(repo, path):
        diff = git("diff", "--no-index", "--", os.devnull, path, repo=repo).stdout
    else:
        diff = git("diff", "HEAD", "--", path, repo=repo).stdout
    added: list[str] = []
    removed: list[str] = []
    in_hunk = False
    for line in diff.splitlines():
        # Only the hunk BODY is content: the file header and the "\ No newline" marker are machinery.
        # Skipping by prefix alone would swallow a removed line whose own text begins with `---`.
        if line.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk or line.startswith("\\"):
            continue
        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            removed.append(line[1:])
    return {
        "patch": path,
        "added": sorted(added),
        "removed": sorted(removed),
        "added_sha1": sha1_of(added),
        "removed_sha1": sha1_of(removed),
        "unchanged": not added and not removed,
    }


def sha1_of(lines: list[str]) -> str:
    return hashlib.sha1("\n".join(sorted(lines)).encode("utf-8")).hexdigest()


def snapshot(repo: Path, paths: list[str]) -> int:
    root = baseline_root(repo)
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "run": label(),
        "seat": seat(),
        "head": git("rev-parse", "HEAD", repo=repo).stdout.strip(),
        "repo": str(repo),
        "taken": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "patches": [change_sets(repo, p) for p in paths],
    }
    target = root / f"{payload['run']}.json"
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"baseline {target}")
    for row in payload["patches"]:
        print(
            f"  {row['patch']}  +{len(row['added'])}/-{len(row['removed'])}  "
            f"added_sha1={row['added_sha1'][:12]} removed_sha1={row['removed_sha1'][:12]}"
        )
    return 0


def verify(repo: Path, baseline_path: Path, paths: list[str]) -> int:
    if not baseline_path.exists():
        print(f"no such baseline: {baseline_path}", file=sys.stderr)
        return 2
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    recorded = {row["patch"]: row for row in payload["patches"]}

    checked = paths or sorted(recorded)
    bad = 0
    for path in checked:
        if path not in recorded:
            print(f"MISSING FROM THE BASELINE: {path} - it was not snapshotted, so nothing vouches for it", file=sys.stderr)
            bad += 1
            continue
        now = change_sets(repo, path)
        was = recorded[path]
        surplus = sorted(set(now["added"]) - set(was["added"]))
        lost = sorted(set(was["added"]) - set(now["added"]))
        surplus_removed = sorted(set(now["removed"]) - set(was["removed"]))
        lost_removed = sorted(set(was["removed"]) - set(now["removed"]))

        if not (surplus or lost or surplus_removed or lost_removed):
            print(f"equal  {path}  +{len(now['added'])}/-{len(now['removed'])}  added_sha1={now['added_sha1'][:12]}")
            continue

        bad += 1
        print(f"SURPLUS {path}: the diff is NOT the one you snapshotted.", file=sys.stderr)
        for line in surplus:
            print(f"  + SURPLUS  {line}", file=sys.stderr)
        for line in surplus_removed:
            print(f"  - SURPLUS  {line}", file=sys.stderr)
        for line in lost:
            print(f"  + MISSING  {line}", file=sys.stderr)
        for line in lost_removed:
            print(f"  - MISSING  {line}", file=sys.stderr)

    if bad:
        print(
            f"{bad} path(s) differ from the baseline taken {payload.get('taken')} by seat "
            f"{payload.get('seat')}. Do NOT commit over this: re-read the path, keep your own lines, "
            "and leave the rest to its author.",
            file=sys.stderr,
        )
        return EXIT_MISMATCH
    print(f"every patch equals the baseline {baseline_path.name} taken {payload.get('taken')}")
    return 0


def show(baseline_path: Path) -> int:
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    print(f"run {payload['run']}  seat {payload['seat']}  head {payload.get('head', '-')[:12]}  taken {payload['taken']}")
    for row in payload["patches"]:
        print(f"  {row['patch']}  +{len(row['added'])}/-{len(row['removed'])}  added_sha1={row['added_sha1'][:12]}")
        for line in row["added"]:
            print(f"    + {line}")
        for line in row["removed"]:
            print(f"    - {line}")
    return 0


def list_baselines(repo: Path) -> int:
    root = baseline_root(repo)
    runs = sorted((p for p in root.glob("*.json")), reverse=True) if root.exists() else []
    if not runs:
        print(f"no baseline under {root}")
        return 0
    for path in runs:
        payload = json.loads(path.read_text(encoding="utf-8"))
        patches = ", ".join(row["patch"] for row in payload["patches"]) or "(none)"
        print(f"{path.name}  seat {payload.get('seat')}  taken {payload.get('taken')}  {patches}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--snapshot", action="store_true", help="record the current diff of the paths")
    group.add_argument("--verify", metavar="BASELINE", help="re-compute the diff and require equality")
    group.add_argument("--show", metavar="BASELINE", help="print what a baseline recorded")
    group.add_argument("--list", action="store_true", help="name every baseline in the repository")
    parser.add_argument("--repo", default=None, help="the repository to act on (default: cwd)")
    parser.add_argument("paths", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    start = Path(args.repo).resolve() if args.repo else Path.cwd()
    repo = repo_root(start)
    if repo is None:
        print("not a git repository (pass --repo)", file=sys.stderr)
        return 2

    paths = [p for p in args.paths if p != "--"]
    if args.list:
        return list_baselines(repo)
    if args.show:
        return show(Path(args.show))
    if args.verify:
        return verify(repo, Path(args.verify), paths)
    if not paths:
        print("nothing to snapshot: name the paths after `--`", file=sys.stderr)
        return 2
    return snapshot(repo, paths)


if __name__ == "__main__":
    raise SystemExit(main())
