"""notify-seats' behind-note: WHOSE tree does it read?

THE DEFECT (measured 2026-10-15). A post-commit hook in a linked worktree receives
`GIT_DIR=<main>/.git/worktrees/<wt>`, and `git -C <path>` does NOT override an exported `GIT_DIR`. The
note's three reads - the "is this a git tree" guard, the short sha and the `HEAD..main` count - therefore
answered for the COMMITTER's checkout: at 17:49Z all five seats were told
`/home/daihu/__projects__/4genthub at ea72e6ad ... 3 commit(s) behind main`, one value for the whole room,
while each pane's own tree was main's tip. The same leak defeated the guard, so a path that is not a
repository got a warning instead of the plain notice.

These cases drive the real script with a stubbed `tmux` (which answers the pane path) and a stubbed
`4genteam` (one running seat, and the outgoing message captured to a file), under exactly the environment
a post-commit hook receives. The seat's tree is one commit behind ITS OWN `main`; the committer's
repository is at another revision, so a read of the wrong repository is visible in the assertion.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import gitfixture

# <repo>/scripts/tests/<this file>: the repository root is two levels up, and that is where
# scripts/git-hooks/ lives - the same relative path the pre-commit config's `entry` names.
REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "scripts" / "git-hooks" / "notify-seats"

ROOM = "4genthub-min"
SESSION = "agenthub--4genthub-min--lead"


def _repo(path: Path, *messages: str) -> Path:
    """A repository whose `main` carries the messages, committed with an identity of its own."""
    path.mkdir(parents=True)
    gitfixture.git(path, "init", "-q", "-b", "main")
    gitfixture.git(path, "config", "user.email", "fixture@test.invalid")
    gitfixture.git(path, "config", "user.name", "fixture")
    for message in messages:
        gitfixture.git(path, "commit", "-q", "--allow-empty", "-m", message)
    return path


def _stubs(tmp_path: Path, seats: list[tuple[str, str]]) -> tuple[Path, Path, Path]:
    """The `bin` a hook call gets, the message file, and the seat-key file its `4genteam send` writes."""
    bin_dir = tmp_path / "bin"
    sent = tmp_path / "sent.txt"
    sent_seats = tmp_path / "sent_seats.txt"
    bin_dir.mkdir()
    (bin_dir / "tmux").write_text('#!/usr/bin/env bash\nprintf "%s" "$FAKE_PANE_PATH"\n')
    running = " ".join(f"'{seat} omp running {session}'" for seat, session in seats)
    (bin_dir / "4genteam").write_text(
        "#!/usr/bin/env bash\n"
        'case "${1:-} ${2:-}" in\n'
        f'  "room status") printf "%s\\n" {running} ;;\n'
        f'  "send"*) printf "%s\\n" "${{7}}" >> "{sent_seats}"; printf "%s\\n" "${{@: -1}}" >> "{sent}" ;;\n'
        "esac\n"
    )
    for name in ("tmux", "4genteam"):
        (bin_dir / name).chmod(0o755)
    return bin_dir, sent, sent_seats


def _run_hook(
    tmp_path: Path,
    *,
    pane: Path,
    committer: Path,
    committer_session: str | None = None,
) -> str:
    """Run the hook as git runs it: GIT_DIR exported, the pane's cwd reachable only through tmux.

    `committer_session` sets `AGENTHUB_SESSION_NAME`, which is what the hook reads to know which seat
    the commit came from; it is left unset in the cases that do not care.
    """
    bin_dir, sent, _ = _stubs(
        tmp_path,
        [("lead", SESSION), ("go-dev", "agenthub--4genthub-min--go-dev")],
    )
    state = tmp_path / "state"
    (state / "rooms" / ROOM).mkdir(parents=True)
    overrides = {
        "GIT_DIR": str(committer / ".git"),
        "AGENTHUB_STATE_DIR": str(state),
        "FAKE_PANE_PATH": str(pane),
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
    }
    if committer_session is not None:
        overrides["AGENTHUB_SESSION_NAME"] = committer_session
    subprocess.run(["bash", str(HOOK)], capture_output=True, text=True, env=gitfixture.environment(**overrides), check=True)
    return sent.read_text() if sent.exists() else ""


def _told(tmp_path: Path) -> list[str]:
    """The seat keys the hook sent to, in order - the stub appends one line per `4genteam send`."""
    path = tmp_path / "sent_seats.txt"
    return path.read_text().split() if path.exists() else []


def _short(repo: Path, env: dict[str, str] | None = None, *args: str) -> str:
    return gitfixture.git(repo, "rev-parse", "--short", *(args or ("HEAD",)), env=env).stdout.strip()


def test_the_hook_run_receives_a_git_dir_that_beats_its_cwd(tmp_path: Path) -> None:
    """Control and cause in one: the leak is real, so a read of the wrong repository is possible."""
    committer = _repo(tmp_path / "committer", "committer commit")
    seat = _repo(tmp_path / "seat", "seat first", "seat second")
    gitfixture.git(seat, "checkout", "-q", "-b", "seat", "main~1")
    inherited = {"GIT_DIR": str(committer / ".git")}

    assert _short(seat) != _short(committer)
    assert _short(seat, inherited) == _short(committer)
    assert _short(seat) != _short(seat, inherited)


def test_the_warning_names_the_panes_own_tree_not_the_committers(tmp_path: Path) -> None:
    """The defect itself: a seat one commit behind ITS main must be told its OWN revision."""
    committer = _repo(tmp_path / "committer", "committer commit")
    seat = _repo(tmp_path / "seat", "seat first", "seat second")
    gitfixture.git(seat, "checkout", "-q", "-b", "seat", "main~1")
    assert _short(seat) != _short(committer)

    message = _run_hook(tmp_path, pane=seat, committer=committer)

    assert f"New commit {_short(committer)} on" in message  # the hook still describes its own commit
    assert "WARNING" in message
    assert f"your tree ({seat} at {_short(seat)}) is 1 commit(s) behind main" in message


def test_a_pane_at_its_own_main_tip_is_silent(tmp_path: Path) -> None:
    """The committer's own tree is what the old code read for everyone: it has nothing to be told."""
    committer = _repo(tmp_path / "committer", "committer commit")

    message = _run_hook(tmp_path, pane=committer, committer=committer)

    assert message.startswith(f"New commit {_short(committer)} on")
    assert "WARNING" not in message


def test_a_pane_that_is_not_a_repository_gets_the_notice_and_no_warning(tmp_path: Path) -> None:
    """The guard the same leak defeated: a path that is not a tree is skipped, not warned about."""
    committer = _repo(tmp_path / "committer", "committer commit")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    message = _run_hook(tmp_path, pane=elsewhere, committer=committer)

    assert f"New commit {_short(committer)} on" in message
    assert "WARNING" not in message


def test_the_committing_seat_is_not_told_about_its_own_commit(tmp_path: Path) -> None:
    """A notice to yourself is refused as a self message, so the hook does not send it at all."""
    committer = _repo(tmp_path / "committer", "committer commit")

    _run_hook(tmp_path, pane=committer, committer=committer, committer_session=SESSION)

    assert _told(tmp_path) == ["go-dev"]


def test_an_identity_outside_this_room_tells_every_seat(tmp_path: Path) -> None:
    """Control for the case above: a commit that is not one of this room's seats skips nobody.

    The committer's identity is read from the environment, and a commit made by a session this room
    does not run (the shared checkout's own Claude Code session, for instance) must still tell every
    running seat - otherwise the skip would silence the notice for the one commit nobody was told about.
    """
    committer = _repo(tmp_path / "committer", "committer commit")

    _run_hook(
        tmp_path,
        pane=committer,
        committer=committer,
        committer_session="agenthub--some-other-room--lead",
    )

    assert _told(tmp_path) == ["lead", "go-dev"]
