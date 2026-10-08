"""The Seat trailer hook: what it writes, what it refuses, and what it leaves alone.

Instrument note, and it is the point of several cases below: EVERY ASSERTION READS THE TRAILER
THROUGH GIT'S PARSER (`git log --format=%(trailers:key=Seat,valueonly)`), never through a
`^Key:` grep. A grep for a capitalised word and a colon counts prose: this repository's commit
bodies contain mid-paragraph lines like "Gates: ..." and "UserTaskController: ...", and a census
that grepped for them counted trailers that were not there. The parser, unlike the grep, reads
only the final trailer block.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

# <repo>/agenthub_main/src/tests/scripts/<this file>: the repository root is four levels up, and that
# is where scripts/git-hooks/ lives - the same relative path the pre-commit config's `entry` names.
REPO_ROOT = Path(__file__).resolve().parents[4]
HOOK = REPO_ROOT / "scripts" / "git-hooks" / "prepare-commit-msg"

ADDRESS = "4genthub-min-skills-dev@4genthub-min"


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    full = dict(os.environ)
    full.update(env or {})
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=full,
    ).stdout


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Test Seat")
    _git(repo, "config", "user.email", "seat@example.invalid")
    (repo / "a.txt").write_text("one\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo


def _install(repo: Path, src: Path | None = None) -> Path:
    """Install the script the way git finds a prepare-commit-msg hook."""
    dest = repo / ".git" / "hooks" / "prepare-commit-msg"
    dest.write_text((src or HOOK).read_text())
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR)
    return dest


def _commit(repo: Path, message: str, env: dict[str, str]) -> None:
    _git(repo, "commit", "-q", "--allow-empty", "-m", message, env=env)


def _seats(repo: Path) -> list[str]:
    """Every Seat value git's own trailer parser finds on HEAD, in order."""
    out = _git(repo, "log", "-1", "--format=%(trailers:key=Seat,valueonly)")
    return [line.strip() for line in out.splitlines() if line.strip()]


def test_a_seat_commit_carries_the_send_address(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _install(repo)
    _commit(repo, "feat: something", {"OPENRIG_SESSION_NAME": ADDRESS})
    assert _seats(repo) == [ADDRESS]


def test_the_case_can_fail_a_do_nothing_hook(tmp_path: Path) -> None:
    """Control: with a hook that writes nothing, the positive case is red."""
    repo = _repo(tmp_path)
    noop = tmp_path / "noop"
    noop.write_text("#!/bin/sh\nexit 0\n")
    _install(repo, src=noop)
    _commit(repo, "feat: something", {"OPENRIG_SESSION_NAME": ADDRESS})
    assert _seats(repo) == []


def test_no_seat_identity_writes_nothing_and_still_commits(tmp_path: Path) -> None:
    """The owner commits from the host, where the variable is unset."""
    repo = _repo(tmp_path)
    _install(repo)
    _commit(repo, "docs: from the host", {"OPENRIG_SESSION_NAME": ""})
    assert _seats(repo) == []
    assert _git(repo, "log", "-1", "--format=%s").strip() == "docs: from the host"


def test_a_hand_written_trailer_is_left_alone(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _install(repo)
    _commit(
        repo,
        "fix: hand written\n\nSeat: someone-else@rig\n",
        {"OPENRIG_SESSION_NAME": ADDRESS},
    )
    assert _seats(repo) == ["someone-else@rig"]


def test_prose_that_looks_like_a_trailer_is_not_one(tmp_path: Path) -> None:
    """The census's error, as a case: a body line reading `Gates: ...` is prose, not a trailer.

    Git parses only the final trailer block, so the Seat line must still be the single value the
    parser returns - which a `^Key:` grep would have got wrong.
    """
    repo = _repo(tmp_path)
    _install(repo)
    body = "feat: something\n\nGates: the rung that watches for it\nSeat: not-a-trailer-here\n\nSeat is written at the end.\n"
    _commit(repo, body, {"OPENRIG_SESSION_NAME": ADDRESS})
    assert _seats(repo) == [ADDRESS]


def test_no_message_file_is_not_a_failure(tmp_path: Path) -> None:
    """The framework's own `run` mode passes no message file: nothing to write, and no refusal."""
    repo = _repo(tmp_path)
    hook = _install(repo)
    result = subprocess.run(
        [str(hook)],
        capture_output=True,
        text=True,
        env={**os.environ, "OPENRIG_SESSION_NAME": ADDRESS},
    )
    assert result.returncode == 0
    assert _seats(repo) == []
