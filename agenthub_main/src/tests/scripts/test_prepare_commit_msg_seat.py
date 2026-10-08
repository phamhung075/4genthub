"""The seat-attribution hook: `scripts/git-hooks/prepare-commit-msg` appends `Seat: <OPENRIG_SESSION_NAME>`.

FAILING FIRST: this file was written before the script exists, so every case below is red until it
lands. WHAT IT IS FOR: every commit in this tree carries one machine identity, so git cannot name the
seat that made it - eleven instruments across five seats failed to attribute a file on 2026-10-08.
The trailer's value is not merely that it is unique: `OPENRIG_SESSION_NAME` IS the `rig send` address
(for example `4genthub-min-architect@4genthub-min`), so a reader who finds the trailer can MESSAGE THE
SEAT DIRECTLY, which no other attribution instrument last night could do.

WHAT THE TRAILER DOES NOT FIX: it names the seat that RAN `git commit`, not the author of every line.
`0c8122a9` is the counterexample - go-dev's commit carried the architect's two staged lines, and a
trailer there would read go-dev. This hook and the pre-commit ladder are ONE FIX IN TWO PARTS.

WHERE THE HOOK LIVES IN A TEST: copied into a THROWAWAY repository's own `.git/hooks`, never the
shared repository's hook directory - installing there is the owner's step, and the last case asserts
the script does not install anything itself. Cleanup is pytest's `tmp_path`; no case removes anything
and none uses `rm`.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = (
    Path(__file__).resolve().parents[4]
)  # agenthub_main/src/tests/scripts -> repository root
HOOK = REPO / "scripts" / "git-hooks" / "prepare-commit-msg"
IDENTITY = ["-c", "user.email=probe@local", "-c", "user.name=probe"]

# Self-contained: no seat, daemon or test database is needed.
pytestmark = pytest.mark.unit


def _git(*args, cwd, env=None):
    return subprocess.run(
        ["git", *args], cwd=str(cwd), env=env, capture_output=True, text=True
    )


def _env(session=None):
    env = dict(os.environ)
    env.pop("OPENRIG_SESSION_NAME", None)
    if session is not None:
        env["OPENRIG_SESSION_NAME"] = session
    return env


@pytest.fixture(autouse=True)
def _interpret_trailers_available():
    """A skip is not a pass: if git cannot do this, SAY SO and say why."""
    probe = subprocess.run(
        ["git", "interpret-trailers", "--help"], capture_output=True, text=True
    )
    if probe.returncode != 0:
        pytest.skip(
            "git cannot run interpret-trailers, so this hook cannot be exercised: "
            + (probe.stderr or probe.stdout).strip().splitlines()[0]
        )


def _new_repo(tmp_path):
    repo = tmp_path / "scratch"
    repo.mkdir()
    assert _git("init", "-q", ".", cwd=repo).returncode == 0
    return repo


def _install(repo):
    """Install the hook into the THROWAWAY repo only - never the shared .git/hooks."""
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    target = hooks / "prepare-commit-msg"
    shutil.copy2(HOOK, target)
    os.chmod(target, 0o755)
    return target


def _commit(repo, message, env=None, extra=()):
    (repo / "f.txt").write_text(
        (repo / "f.txt").read_text() + "x" if (repo / "f.txt").exists() else "x"
    )
    _git("add", "--", "f.txt", cwd=repo)
    return _git(*IDENTITY, "commit", *extra, "-m", message, cwd=repo, env=env or _env())


def _body(repo):
    return _git("log", "-1", "--format=%B", cwd=repo).stdout


def test_a_seat_commit_carries_the_seat_trailer(tmp_path):
    repo = _new_repo(tmp_path)
    _install(repo)
    done = _commit(repo, "subject", env=_env("4genthub-min-skills-dev@4genthub-min"))
    assert done.returncode == 0, done.stderr
    assert "Seat: 4genthub-min-skills-dev@4genthub-min" in _body(repo)


def test_without_the_variable_nothing_is_added_and_the_commit_succeeds(tmp_path):
    repo = _new_repo(tmp_path)
    _install(repo)
    done = _commit(repo, "subject", env=_env(None))
    assert done.returncode == 0, done.stderr
    assert "Seat:" not in _body(repo)


def test_a_hand_written_seat_trailer_is_not_duplicated(tmp_path):
    repo = _new_repo(tmp_path)
    _install(repo)
    done = _commit(
        repo,
        "subject\n\nSeat: hand@written",
        env=_env("4genthub-min-skills-dev@4genthub-min"),
    )
    assert done.returncode == 0, done.stderr
    body = _body(repo)
    assert body.count("Seat:") == 1, body
    assert (
        "hand@written" in body
    )  # --if-exists doNothing leaves the hand-written one alone


def test_an_amend_gets_one_trailer_at_most(tmp_path):
    repo = _new_repo(tmp_path)
    _install(repo)
    assert (
        _commit(
            repo, "subject", env=_env("4genthub-min-skills-dev@4genthub-min")
        ).returncode
        == 0
    )
    done = _commit(
        repo,
        "subject amended",
        env=_env("4genthub-min-skills-dev@4genthub-min"),
        extra=("--amend",),
    )
    assert done.returncode == 0, done.stderr
    assert _body(repo).count("Seat:") == 1, _body(repo)


def test_check_reports_a_free_hook_path_and_installs_nothing(tmp_path):
    repo = _new_repo(tmp_path)
    done = subprocess.run(
        [str(HOOK), "--check"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=_env(),
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "free" in (done.stdout + done.stderr).lower()
    assert not (
        repo / ".git" / "hooks" / "prepare-commit-msg"
    ).exists(), "the script must not install"


def test_check_reports_an_occupied_hook_path_and_names_it(tmp_path):
    repo = _new_repo(tmp_path)
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    foreign = hooks / "prepare-commit-msg"
    foreign.write_text("#!/bin/sh\n# somebody else's hook\nexit 0\n")
    done = subprocess.run(
        [str(HOOK), "--check"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        env=_env(),
    )
    assert done.returncode != 0, done.stdout
    out = done.stdout + done.stderr
    assert "prepare-commit-msg" in out and "free" not in out.lower(), out


def test_the_installed_hook_is_the_repositorys_script(tmp_path):
    """The guard's other half: what a seat installs is the versioned file, byte for byte."""
    repo = _new_repo(tmp_path)
    target = _install(repo)
    assert target.read_bytes() == HOOK.read_bytes()
