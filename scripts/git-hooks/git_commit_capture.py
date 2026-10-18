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
`<git-dir>/parked-diffs/<UTC stamp>-<seat>-<pid>/NN-<name>.patch`, ONE patch per path, plus a
`MANIFEST.txt` naming each path with its byte count and sha1. `<git-dir>` is the SHARED repository, so
any seat finds the capture by `git rev-parse --absolute-git-dir` - not by knowing whose commit it was.
It then runs the real `git commit` and, after it returns, VERIFIES every captured path: the content is
back in the worktree (the framework restored it), or it is in HEAD (this commit landed it), or neither
holds - and then the capture is the only copy, which the wrapper says LOUDLY with the exact command that
puts it back (`git apply <patch>`), exiting 3.

RETENTION. A run directory is swept only when it is BOTH older than `--keep-days` (default 7) AND every
verdict its own manifest records PROVES nothing is at risk - every path either `landed` or `restored`. The
rule requires proof, not the absence of the word `at-risk`: an `unverified` run (the wrapper died inside
the window, before `verify` could write anything, which is exactly the case this tool exists for), a run
with no readable manifest, and any verdict this file does not recognise all KEEP their capture. A capture
that might hold the only copy is never removed; `--list` names what it keeps and why. This mirrors the
scan's rule in `stash_patch_scan.py`: never prune what might be the only copy.

LIMIT, STATED SO IT IS NOT MISTAKEN FOR COVERAGE. The framework never touches UNTRACKED files, so the
window cannot lose them either; they are not captured here because capturing their contents on every
commit is its own cost. Untracked work is therefore out of scope, not covered.

AND THE MIRROR LIMIT, which no wrapper can close: `git commit -- <path>` takes the WORKTREE content of
the path it names, so an UNCOMMITTED edit by another seat to that path rides the committer's commit, with the
committer's message as its only attribution (measured: `f344a64f`, CHANGELOG.md numstat 15/1 - the committer's
14-line entry plus a peer's 1 line). This file preserves the BYTES of such an edit; it cannot stop the
attribution moving and it cannot tell the victim. A seat whose `git diff HEAD -- <path>` goes EMPTY while it
still expects an edit has had that edit taken; `git log -1 --numstat -S'<the line>' -- <path>` names the commit.

DOCS-ONLY CHECK (owner's rule: seats build, fix and improve; docs, CHANGELOG and TEST-CHANGELOG change
ONCE, in the code commit of a finished task). It lives HERE and nowhere else, because this is the one
place that sees the PATH SET the commit will carry. A seat commits by pathspec (AGENTS.md rule 4), and
`git commit -- <paths>` takes those files' worktree content without touching the index, so a hook reading
`git diff --cached` answers "not docs" on exactly the commits the rule is about - measured 2026-10-17: the
retired `docs-only-guard` probe exited 0 for a docs-only pathspec commit and 1 only when docs happened to
be staged. This wrapper expands the pathspecs and refuses when every path the commit carries is
documentation. The owner's host (no AGENTHUB_SESSION_NAME) and the owner's flag `OWNER_DOCS_COMMIT=1` are
exempt.

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
SEAT_ENV = "AGENTHUB_SEAT"
#: Exported to every seat and unset on the owner's host: the docs-only check is a seat's check.
SEAT_SESSION_ENV = "AGENTHUB_SESSION_NAME"
#: The owner's one-commit exemption, for a document the owner asked for.
OWNER_DOCS_ENV = "OWNER_DOCS_COMMIT"

DOCS_ONLY_REFUSAL = """\
docs-only commit refused: every path this commit carries is documentation.
The owner's rule: seats build, fix and improve. A plan, finding, ruling, status or recount goes through the
queue (one short row), not into a commit. Docs, CHANGELOG and TEST-CHANGELOG change ONCE, in the code commit
of the finished task. Put these files in that commit, or drop them.
Only if the owner asked for this document: OWNER_DOCS_COMMIT=1 python3 scripts/git-hooks/git_commit_capture.py -- ...
"""


def git(*args: str, repo: Path | None = None) -> subprocess.CompletedProcess:
    """`--no-optional-locks` on every read: a plain git call rewrites the index stat cache."""
    return subprocess.run(
        ["git", "--no-optional-locks", *args], cwd=repo, capture_output=True, text=True
    )


def is_document(path: str) -> bool:
    """The doc globs in one statement: a `.md` anywhere, `ai_docs/`, any `CHANGELOG/`, the plan files.

    `TEST-CHANGELOG.md` needs no clause of its own: it is a `.md`.
    """
    p = path.replace(os.sep, "/")
    return (
        p.endswith(".md")
        or p.startswith("ai_docs/")
        or p.startswith("CHANGELOG/")
        or "/CHANGELOG/" in p
        or p.startswith("NEXT-GEN")
    )


def commit_paths(repo: Path, commit_args: list[str]) -> list[str]:
    """The paths THIS commit carries: the pathspec rule 4 prescribes, or the index when there is none.

    `git commit -- <paths>` takes each named file's WORKTREE content and records nothing in the index, so
    for exactly the commits rule 4 describes the index cannot answer what the commit carries. The pathspec
    is expanded against HEAD - the changed tracked files those arguments will carry - which is also what
    makes a directory or glob pathspec judgeable. A pathspec that matches no change expands to nothing and
    the commit itself reports that, so it is not this check's refusal to make.
    """
    if "--" in commit_args:
        pathspec = commit_args[commit_args.index("--") + 1 :]
        if pathspec:
            proc = git(
                "diff", "--name-only", "--no-renames", "--diff-filter=ACMR", "HEAD", "--", *pathspec, repo=repo
            )
            return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    proc = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", repo=repo)
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def docs_only_refusal(repo: Path, commit_args: list[str]) -> str | None:
    """The refusal when a seat's commit carries only documentation; None when it may run."""
    if not os.environ.get(SEAT_SESSION_ENV) or os.environ.get(OWNER_DOCS_ENV) == "1":
        return None
    paths = commit_paths(repo, commit_args)
    if not paths or any(not is_document(path) for path in paths):
        return None
    return DOCS_ONLY_REFUSAL


def repo_root(start: Path) -> Path | None:
    proc = git("rev-parse", "--show-toplevel", repo=start)
    return Path(proc.stdout.strip()) if proc.returncode == 0 and proc.stdout.strip() else None


def parked_root(repo: Path) -> Path:
    proc = git("rev-parse", "--absolute-git-dir", repo=repo)
    if proc.returncode != 0:
        raise SystemExit(f"not a git repository: {repo}")
    return Path(proc.stdout.strip()) / PARKED_DIRNAME


def run_label() -> str:
    """Stamp + seat + pid: without the pid, two runs by one seat in the same SECOND share a run directory.

    They would then overwrite each other's patches (same `NN-<name>.patch` slugs) and manifests, and a
    second run with nothing to park would `rmtree` the first run's capture - a silent-loss path inside the
    module whose whole purpose is that nothing is lost.
    """
    seat = os.environ.get(SEAT_ENV) or "seat"
    return (
        f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
        f"-{re.sub(r'[^A-Za-z0-9._@-]', '_', seat)}-{os.getpid()}"
    )


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


SAFE_VERDICTS = frozenset({"landed", "restored"})


def retention_of(run_dir: Path) -> tuple[bool, str]:
    """Keep unless EVERY recorded verdict is PROVEN safe: proof, never the absence of a word.

    An `unverified` manifest is the mid-window-death case this tool exists for - the wrapper died before
    `verify` could write anything, so nothing recorded that the capture is safe to drop. A manifest that
    cannot be read records nothing either, and a verdict this file does not recognise is not proof. All
    three KEEP the capture; only a run whose every path is `landed` or `restored` may be swept.
    """
    verdicts = manifest_verdicts(run_dir)
    if not verdicts:
        return True, "no verdict it can read: its verification never recorded anything"
    unsafe = sorted({v for v in verdicts if v not in SAFE_VERDICTS})
    if unsafe:
        return True, f"unproven verdict(s): {', '.join(unsafe)}"
    return False, "every path verified landed or restored"


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
        keep, why = retention_of(run_dir)
        if at_risk:
            mark = f"AT RISK ({at_risk}) - never swept, the capture is the only copy"
        elif keep:
            mark = f"KEEP - {why}"
        else:
            mark = "safe to sweep once old (every path verified landed or restored)"
        print(f"{run_dir.name}  patches {len(patches):>3}  age {age_days:>6.1f}d  {mark}")
        for patch in patches:
            print(f"    {patch.name}")
    return 0


def sweep(parked: Path, keep_days: float) -> int:
    """Retention: an old run goes only when EVERY recorded verdict proves nothing is at risk."""
    removed = kept = 0
    for run_dir in stored_runs(parked):
        age_days = (time.time() - run_dir.stat().st_mtime) / 86400
        if age_days < keep_days:
            kept += 1
            continue
        hold, why = retention_of(run_dir)
        if hold:
            print(f"kept {run_dir.name}: {why}")
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
    # Before anything is parked: a refused commit runs nothing, so it has nothing to capture.
    refusal = docs_only_refusal(repo, commit_args)
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return 1

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
    # It runs with no rows too, so a seat that expected a capture learns it had none instead of silence.
    code = report(run_dir, rows, verdicts)
    return code if code else proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
