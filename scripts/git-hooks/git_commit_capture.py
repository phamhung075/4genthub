#!/usr/bin/env python3
"""Commit through the pre-commit stash window without losing a seat's uncommitted work.

WHY THIS EXISTS. The pre-commit framework runs `staged_files_only` on EVERY commit: it writes the
worktree's unstaged diff of every TRACKED file into a patch, rewinds the whole tree to the index, runs
the hooks, and re-applies the patch in a `finally:`. A hook that merely REFUSES is therefore safe. The
loss needs the process to DIE inside that window, and that trigger has already fired on this box: the
2026-10-08 23:28 interruption left a 0-byte pre-commit patch behind. Two properties make the loss hard
to recover from. The framework's patch lands in the COMMITTING seat's store, which is derived from that
seat's $HOME - so a victim looking in their own cache finds nothing - and nothing ever removes it.

WHAT THIS DOES. Before the hooks can take anything, it records the unstaged diff to
`<git-dir>/parked-diffs/<UTC stamp>-<seat or pid>/NN-<name>.patch`, ONE patch per path, plus a
`MANIFEST.txt` naming each path with its byte count and sha1. `<git-dir>` is the SHARED repository, so
any seat finds the capture by `git rev-parse --absolute-git-dir` - not by knowing whose commit it was.
It then runs the real `git commit` and, after it returns, VERIFIES every captured path: the content is
back in the worktree (the framework restored it), or it is in HEAD (this commit landed it), or neither
holds - and then the capture is the only copy, which the wrapper says LOUDLY with the exact command that
puts it back (`git apply <patch>`), exiting 3.

RETENTION. A run directory is swept only when it is BOTH older than `--keep-days` (default 7) and holds
nothing at risk, as recorded by its own verification in `MANIFEST.txt`. A capture that holds the only
copy of anything is never removed; `--list` names it instead. This mirrors the scan's rule in
`stash_patch_scan.py`: never prune what might be the only copy.

LIMIT, STATED SO IT IS NOT MISTAKEN FOR COVERAGE. The framework never touches UNTRACKED files, so the
window cannot lose them either; they are not captured here because capturing their contents on every
commit is its own cost. Untracked work is therefore out of scope, not covered.

USAGE. python3 scripts/git-hooks/git_commit_capture.py -- <the arguments you would give git commit>
        python3 scripts/git-hooks/git_commit_capture.py --list
        python3 scripts/git-hooks/git_commit_capture.py --sweep [--keep-days 7]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

PARKED_DIRNAME = "parked-diffs"
MANIFEST_NAME = "MANIFEST.txt"
DEFAULT_KEEP_DAYS = 7.0
#: The seam a test replaces to stage the death without killing a real process.
COMMIT_COMMAND: list[str] = ["git", "commit"]
SEAT_ENV = "OPENRIG_SEAT"


def git(*args: str, repo: Path | None = None) -> subprocess.CompletedProcess:
    """`--no-optional-locks` on every read: a plain git call rewrites the index stat cache."""
    return subprocess.run(
        ["git", "--no-optional-locks", *args], cwd=repo, capture_output=True, text=True
    )


def repo_root(start: Path) -> Path | None:
    proc = git("rev-parse", "--show-toplevel", repo=start)
    return Path(proc.stdout.strip()) if proc.returncode == 0 and proc.stdout.strip() else None


def parked_root(repo: Path) -> Path:
    proc = git("rev-parse", "--absolute-git-dir", repo=repo)
    if proc.returncode != 0:
        raise SystemExit(f"not a git repository: {repo}")
    return Path(proc.stdout.strip()) / PARKED_DIRNAME


def run_label() -> str:
    seat = os.environ.get(SEAT_ENV) or f"pid{os.getpid()}"
    return f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{re.sub(r'[^A-Za-z0-9._@-]', '_', seat)}"


def slug(index: int, path: str) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]", "_", Path(path).name)[:60] or "path"
    return f"{index:02d}-{name}.patch"


def unstaged_paths(repo: Path) -> list[str]:
    proc = git("diff", "--name-only", repo=repo)
    return [line for line in proc.stdout.splitlines() if line.strip()]


def capture(repo: Path, run_dir: Path) -> list[dict]:
    """One patch per path. Per path is the point: verification has to be decidable per path."""
    rows: list[dict] = []
    for index, path in enumerate(unstaged_paths(repo), start=1):
        diff = git("diff", "--", path, repo=repo).stdout
        if not diff.strip():
            continue
        patch = run_dir / slug(index, path)
        patch.write_text(diff, encoding="utf-8")
        rows.append(
            {
                "path": path,
                "patch": patch,
                "bytes": len(diff.encode("utf-8")),
                "sha1": hashlib.sha1(diff.encode("utf-8")).hexdigest(),
            }
        )
    return rows


def holds_the_content(repo: Path, patch: Path) -> bool:
    """Reverse-applies to the WORKTREE: the captured change is in front of us right now."""
    if not patch.exists() or patch.stat().st_size == 0:
        return False
    return git("apply", "--check", "--reverse", str(patch), repo=repo).returncode == 0


def committed_paths(repo: Path) -> set[str]:
    proc = git("show", "--name-only", "--format=", "HEAD", repo=repo)
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def head(repo: Path) -> str | None:
    proc = git("rev-parse", "HEAD", repo=repo)
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None


def verify(repo: Path, rows: list[dict], head_before: str | None) -> list[dict]:
    """restored (the framework put it back) / landed (THIS commit carries it) / at-risk (only copy).

    `landed` is decided from HEAD MOVING and then naming the path. Asking the current HEAD alone would
    call a path landed just because some EARLIER commit touched it - and a commit that died inside the
    window leaves HEAD exactly where it was.
    """
    moved = head(repo) != head_before
    landed = committed_paths(repo) if moved else set()
    verdicts: list[dict] = []
    for row in rows:
        if moved and row["path"] in landed:
            verdict = "landed"  # this commit carries it
        elif holds_the_content(repo, row["patch"]):
            verdict = "restored"  # back in the worktree, still uncommitted
        else:
            verdict = "at-risk"  # in no worktree and in no commit: the capture is the only copy
        verdicts.append({**row, "verdict": verdict})
    return verdicts


def write_manifest(run_dir: Path, rows: list[dict], commit_args: list[str], verdicts: list[dict] | None) -> None:
    lines = [
        f"run {run_dir.name}",
        f"seat {os.environ.get(SEAT_ENV) or '-'} home {os.environ.get('HOME') or '-'} pid {os.getpid()}",
        f"args {' '.join(commit_args)}",
    ]
    by_path = {v["path"]: v for v in verdicts or []}
    for row in rows:
        verdict = by_path.get(row["path"], {}).get("verdict", "unverified")
        lines.append(
            f"{row['path']} bytes={row['bytes']} sha1={row['sha1']} "
            f"patch={row['patch'].name} verdict={verdict}"
        )
    (run_dir / MANIFEST_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def report(run_dir: Path, rows: list[dict], verdicts: list[dict]) -> int:
    at_risk = [v for v in verdicts if v["verdict"] == "at-risk"]
    restored = sum(1 for v in verdicts if v["verdict"] == "restored")
    landed = sum(1 for v in verdicts if v["verdict"] == "landed")
    if not rows:
        print("nothing was parked: the worktree had no unstaged change before this commit")
        return 0
    print(f"parked {len(rows)} path(s) at {run_dir}  (restored {restored}, landed {landed})")
    if at_risk:
        print(
            f"AT RISK: {len(at_risk)} path(s) are in NO worktree and in NO commit - the capture is the "
            "only copy. Recover with:",
            file=sys.stderr,
        )
        for row in at_risk:
            print(f"  git apply {row['patch']}    # {row['path']} sha1={row['sha1']}", file=sys.stderr)
        return 3
    return 0


def stored_runs(parked: Path) -> list[Path]:
    return sorted((d for d in parked.glob("*") if d.is_dir()), reverse=True)


def manifest_verdicts(run_dir: Path) -> list[str]:
    manifest = run_dir / MANIFEST_NAME
    if not manifest.exists():
        return []
    return re.findall(r"verdict=(\S+)", manifest.read_text(encoding="utf-8"))


def list_runs(parked: Path) -> int:
    runs = stored_runs(parked)
    if not runs:
        print(f"no capture under {parked}")
        return 0
    for run_dir in runs:
        verdicts = manifest_verdicts(run_dir)
        patches = sorted(run_dir.glob("*.patch"))
        at_risk = verdicts.count("at-risk")
        age_days = (time.time() - run_dir.stat().st_mtime) / 86400
        mark = "AT RISK" if at_risk else "safe to sweep once old"
        print(f"{run_dir.name}  patches {len(patches):>3}  age {age_days:>6.1f}d  {mark}")
        for patch in patches:
            print(f"    {patch.name}")
    return 0


def sweep(parked: Path, keep_days: float) -> int:
    """Retention: an old run goes only when its own verification recorded nothing at risk."""
    removed = kept = 0
    for run_dir in stored_runs(parked):
        age_days = (time.time() - run_dir.stat().st_mtime) / 86400
        if age_days < keep_days:
            kept += 1
            continue
        if "at-risk" in manifest_verdicts(run_dir):
            print(f"kept {run_dir.name}: it holds the only copy of something")
            kept += 1
            continue
        shutil.rmtree(run_dir)
        removed += 1
    print(f"swept {removed} run(s) older than {keep_days}d, kept {kept}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--list", action="store_true", help="name every capture and its verdict")
    parser.add_argument("--sweep", action="store_true", help="apply the retention rule")
    parser.add_argument("--keep-days", type=float, default=DEFAULT_KEEP_DAYS)
    parser.add_argument("--repo", default=None, help="the repository to act on (default: cwd)")
    parser.add_argument("commit_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    start = Path(args.repo).resolve() if args.repo else Path.cwd()
    repo = repo_root(start)
    if repo is None:
        print("not a git repository (pass --repo)", file=sys.stderr)
        return 2
    parked = parked_root(repo)
    parked.mkdir(parents=True, exist_ok=True)

    if args.list:
        return list_runs(parked)
    if args.sweep:
        return sweep(parked, args.keep_days)

    commit_args = list(args.commit_args)
    if commit_args[:1] == ["--"]:
        commit_args = commit_args[1:]  # only the wrapper's own separator; a later `--` is git's
    if not commit_args:
        print("nothing to commit: pass the arguments you would give `git commit` after `--`", file=sys.stderr)
        return 2

    run_dir = parked / run_label()
    run_dir.mkdir(parents=True, exist_ok=True)
    rows = capture(repo, run_dir)
    head_before = head(repo)
    write_manifest(run_dir, rows, commit_args, None)
    if not rows:
        shutil.rmtree(run_dir)

    proc = subprocess.run([*COMMIT_COMMAND, *commit_args], cwd=repo)
    verdicts = verify(repo, rows, head_before) if rows else []
    if rows:
        write_manifest(run_dir, rows, commit_args, verdicts)
    if proc.returncode != 0:
        print(f"git commit exited {proc.returncode}", file=sys.stderr)
    # The report runs whatever the commit did: a commit that died is exactly when the verdict matters.
    code = report(run_dir, rows, verdicts) if rows else 0
    return code if code else proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
