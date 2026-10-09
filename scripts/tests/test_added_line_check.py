"""The strong form of rule 64's shared-file duty: is the diff you COMMIT the diff you made?

Rule 64's instrument on `CHANGELOG.md` is a count of added lines beginning `## `. The case that beat it
is `f344a64f`: a foreign edit made INSIDE an existing entry adds no heading, so the count does not move
and the commit carries a peer's uncommitted sentence as its own. These cases build that exact case on a
real repository, show rule 64's instrument reading it as no change, and show the baseline check naming
the surplus line instead.

The last case asserts the limit rather than hiding it: a baseline taken AFTER a peer's line is already
in the file calls that line yours. Confirming the path holds only your change is the reading duty no
instrument here replaces.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

# <repo>/scripts/tests/<this file>: two levels up is where scripts/git-hooks/ lives.
REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK = REPO_ROOT / "scripts" / "git-hooks" / "added_line_check.py"

SEAT = "go-dev@test"
FOREIGN = "- a peer's uncommitted sentence, taken by someone else's commit"
MINE = "## 2026-10-09 - a proof about the shared tree"


def _module():
    spec = importlib.util.spec_from_file_location("added_line_check", CHECK)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", ".")
    _git(repo, "config", "user.email", "check@test.invalid")
    _git(repo, "config", "user.name", "added-line test")
    (repo / "CHANGELOG.md").write_text(
        "# Changelog\n\n## 2026-10-08 - an older entry\n\n- an older line\n", encoding="utf-8"
    )
    _git(repo, "add", "--", "CHANGELOG.md")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


def _run(repo: Path, *args: str) -> tuple[int, str, str]:
    """The tool as a committer runs it: a subprocess, with the seat in the environment."""
    env = {**os.environ, "OPENRIG_SESSION": SEAT}
    proc = subprocess.run(
        [sys.executable, str(CHECK), *args], cwd=repo, capture_output=True, text=True, env=env
    )
    return proc.returncode, proc.stdout, proc.stderr


def _baseline(repo: Path) -> Path:
    root = Path(_git(repo, "rev-parse", "--absolute-git-dir").strip()) / "hunk-baselines"
    runs = sorted(root.glob("*.json"))
    assert len(runs) == 1, "one baseline per snapshot"
    return runs[0]


def _rule_64_instrument(repo: Path) -> int:
    """The shipped heading count: added lines of `git diff HEAD -- CHANGELOG.md` that begin `## `."""
    diff = _git(repo, "diff", "HEAD", "--", "CHANGELOG.md")
    return sum(1 for line in diff.splitlines() if line.startswith("+## "))


def _write_my_entry(repo: Path) -> None:
    """The owner's own entry, appended under the existing older entry."""
    (repo / "CHANGELOG.md").write_text(
        (repo / "CHANGELOG.md").read_text(encoding="utf-8") + MINE + "\n\n",
        encoding="utf-8",
    )


def test_a_foreign_line_inside_an_existing_entry_moves_no_heading_so_rule_64_cannot_see_it(tmp_path: Path) -> None:
    """f344a64f's class: the count reads the mixed diff as YOURS, and the baseline does not."""
    repo = _repo(tmp_path)
    _write_my_entry(repo)
    assert _run(repo, "--snapshot", "--", "CHANGELOG.md")[0] == 0
    before = _rule_64_instrument(repo)
    assert before == 1, "the owner's own heading is the one line rule 64 counts"

    # The peer's line arrives after the snapshot, inside the entry the owner already wrote.
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    (repo / "CHANGELOG.md").write_text(
        text.replace(MINE + "\n\n", MINE + "\n\n" + FOREIGN + "\n"), encoding="utf-8"
    )

    assert _rule_64_instrument(repo) == before, "the heading count cannot see a line inside an entry"

    code, out, err = _run(repo, "--verify", str(_baseline(repo)), "--", "CHANGELOG.md")
    assert code == 3, "the mixing class must stop the commit"
    assert "SURPLUS" in err and FOREIGN in err, f"the surplus line must be named, got: {err!r}"
    assert MINE not in err, "the owner's own line is not surplus"


def test_verify_passes_when_the_path_still_holds_exactly_the_snapshotted_diff(tmp_path: Path) -> None:
    """The green side, so exit 3 means something: snapshot, no intervening write, verify."""
    repo = _repo(tmp_path)
    _write_my_entry(repo)
    assert _run(repo, "--snapshot", "--", "CHANGELOG.md")[0] == 0

    code, out, err = _run(repo, "--verify", str(_baseline(repo)), "--", "CHANGELOG.md")
    assert (code, err) == (0, ""), (code, err)
    assert "equal" in out and "CHANGELOG.md" in out


def test_a_removed_line_is_reported_as_missing_not_as_equal(tmp_path: Path) -> None:
    """Losing your own line is a difference too: the baseline is equality, not a lower bound."""
    repo = _repo(tmp_path)
    _write_my_entry(repo)
    assert _run(repo, "--snapshot", "--", "CHANGELOG.md")[0] == 0

    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    (repo / "CHANGELOG.md").write_text(text.replace(MINE + "\n", ""), encoding="utf-8")

    code, _, err = _run(repo, "--verify", str(_baseline(repo)), "--", "CHANGELOG.md")
    assert code == 3
    assert "MISSING" in err and MINE in err, err


def test_the_baseline_lands_in_the_shared_git_dir_and_carries_the_seat(tmp_path: Path) -> None:
    """A victim can find it: same store the parked-diff captures use, and it names who took it."""
    repo = _repo(tmp_path)
    _write_my_entry(repo)
    assert _run(repo, "--snapshot", "--", "CHANGELOG.md")[0] == 0

    payload = json.loads(_baseline(repo).read_text(encoding="utf-8"))
    assert payload["seat"] == SEAT
    assert MINE in payload["patches"][0]["added"]
    assert str(_baseline(repo)).startswith(str(repo))

    listed = _run(repo, "--list")[1]
    assert _baseline(repo).name in listed and SEAT in listed


def test_a_new_file_is_read_against_dev_null_so_a_peer_line_in_it_is_surplus(tmp_path: Path) -> None:
    """Found by dogfooding: `git diff HEAD` says NOTHING about an untracked path, so `+0/-0` vouched
    for a file the baseline had never read. A new path must be read against /dev/null instead."""
    repo = _repo(tmp_path)
    (repo / "NEW.md").write_text("my new line\n", encoding="utf-8")
    assert _run(repo, "--snapshot", "--", "NEW.md")[0] == 0
    staged = json.loads(_baseline(repo).read_text(encoding="utf-8"))
    assert staged["patches"][0]["added"] == ["my new line"], "a new file's content IS its added set"

    (repo / "NEW.md").write_text("my new line\na peer's line\n", encoding="utf-8")
    code, _, err = _run(repo, "--verify", str(_baseline(repo)), "--", "NEW.md")
    assert code == 3
    assert "SURPLUS" in err and "a peer's line" in err, err


def test_a_removed_line_whose_own_text_starts_with_a_rule_marker_is_counted(tmp_path: Path) -> None:
    """A removed markdown rule is written `----` in the diff; skipping by prefix called it a header."""
    repo = _repo(tmp_path)
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8").replace(
        "## 2026-10-08 - an older entry", "---\n\n## 2026-10-08 - an older entry"
    )
    (repo / "CHANGELOG.md").write_text(text, encoding="utf-8")
    _git(repo, "add", "--", "CHANGELOG.md")
    _git(repo, "commit", "-q", "-m", "a rule marker at HEAD")

    (repo / "CHANGELOG.md").write_text(text.replace("---\n\n", ""), encoding="utf-8")
    assert _run(repo, "--snapshot", "--", "CHANGELOG.md")[0] == 0
    removed = json.loads(_baseline(repo).read_text(encoding="utf-8"))["patches"][0]["removed"]
    assert removed == ["", "---"], removed


def test_a_path_that_was_never_snapshotted_is_refused_rather_than_passed(tmp_path: Path) -> None:
    """Verifying an unlisted path must not read as covered: no baseline, no vouch."""
    repo = _repo(tmp_path)
    (repo / "OTHER.md").write_text("new\n", encoding="utf-8")
    assert _run(repo, "--snapshot", "--", "CHANGELOG.md")[0] == 0

    code, _, err = _run(repo, "--verify", str(_baseline(repo)), "--", "OTHER.md")
    assert code == 3
    assert "MISSING FROM THE BASELINE" in err and "OTHER.md" in err


def test_the_stated_blind_spot_a_snapshot_taken_after_a_peer_edit_calls_their_line_yours(tmp_path: Path) -> None:
    """The limit, asserted so nobody reads this tool as coverage it does not have.

    If the peer's line is already in the file when the owner snapshots, it is in the baseline and the
    check passes. Rule 64's reading duty - the path holds YOUR change and only yours - is not replaced.
    """
    repo = _repo(tmp_path)
    _write_my_entry(repo)
    text = (repo / "CHANGELOG.md").read_text(encoding="utf-8")
    (repo / "CHANGELOG.md").write_text(
        text.replace(MINE + "\n\n", MINE + "\n\n" + FOREIGN + "\n"), encoding="utf-8"
    )
    assert _run(repo, "--snapshot", "--", "CHANGELOG.md")[0] == 0

    code, _, err = _run(repo, "--verify", str(_baseline(repo)), "--", "CHANGELOG.md")
    assert code == 0, "the snapshot is swearing to the mixed diff as it stood - the stated blind spot"
    assert err == ""
