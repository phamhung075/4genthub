"""The stash-patch scan: the four classes it separates, and the one rule that protects live work.

The scan exists because a parked pre-commit patch is indistinguishable by name from a live one, so the
question it has to answer is "is this content in the tree RIGHT NOW". These cases build each class for real
— with real `git diff` output applied against a real repository — because the classifier is the whole point
and a fixture would only test the fixture.

Each patch targets its OWN file. That is not tidiness: a patch's class is a property of the tree at scan
time, so rewriting the file one patch targets changes another patch's class (it becomes `drifted`). Keeping
them apart is what makes each assertion mean what it says.

The load-bearing case is `test_prune_takes_applied_and_old_patches_and_nothing_else`: a `carried` patch is a
seat's uncommitted work, and a scan that prunes it destroys exactly what this whole row is about.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# <repo>/scripts/tests/<this file>: the repository root is two levels up, and that is where
# scripts/git-hooks/ lives — the same relative path the pre-commit config's `entry` names.
REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN = REPO_ROOT / "scripts" / "git-hooks" / "stash_patch_scan.py"

NOW = int(time.time())
OLD = NOW - 48 * 3600  # past any sane retention
FRESH = NOW - 3600  # inside the default 24h window


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", ".")
    _git(repo, "config", "user.email", "scan@test.invalid")
    _git(repo, "config", "user.name", "scan test")
    (repo / "f.txt").write_text("one\n", encoding="utf-8")  # applied-old
    (repo / "g.txt").write_text("alpha\n", encoding="utf-8")  # drifted
    (repo / "h.txt").write_text("uno\n", encoding="utf-8")  # carried
    (repo / "i.txt").write_text("un\n", encoding="utf-8")  # applied-fresh
    _git(repo, "add", "--", "f.txt", "g.txt", "h.txt", "i.txt")
    _git(repo, "commit", "-q", "-m", "base")
    return repo


def _capture(repo: Path, path: str, content: str, dest: Path) -> None:
    """Write a REAL git patch for `content` at `path`, captured while it is dirty."""
    (repo / path).write_text(content, encoding="utf-8")
    diff = subprocess.run(
        ["git", "diff", "--", path], cwd=repo, check=True, capture_output=True, text=True
    ).stdout
    assert diff, f"the fixture produced an empty patch for {path}"
    dest.write_text(diff, encoding="utf-8")


def _commit(repo: Path, path: str) -> None:
    _git(repo, "add", "--", path)
    _git(repo, "commit", "-q", "-m", f"land {path}")


def _store(tmp_path: Path) -> Path:
    store = tmp_path / "store"
    store.mkdir()
    return store


def _scan(store: Path, repo: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCAN), "--store", str(store), "--repo", str(repo), *extra],
        capture_output=True,
        text=True,
        env={**os.environ, "PRE_COMMIT_HOME": str(store)},
    )


def _counts(store: Path, repo: Path) -> dict:
    proc = _scan(store, repo, "--json")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["counts"]


def _build_all_four(tmp_path: Path) -> tuple[Path, Path]:
    """One repo, one store, and one patch of each class — the classifier's whole input space."""
    repo = _repo(tmp_path)
    store = _store(tmp_path)

    # applied: the patch's content is IN the tree, because the change was committed after capture.
    _capture(repo, "f.txt", "one\ntwo\n", store / f"patch{OLD}-1")
    _commit(repo, "f.txt")

    # carried: captured here, then the tree was put back, so the content is NOT in the tree.
    _capture(repo, "h.txt", "uno\ndos\n", store / f"patch{OLD}-2")
    (repo / "h.txt").write_text("uno\n", encoding="utf-8")

    # drifted: a patch whose context is gone in both directions, because the file moved on entirely.
    _capture(repo, "g.txt", "alpha\nbeta\ngamma\n", store / f"patch{OLD}-3")
    (repo / "g.txt").write_text("totally different\n", encoding="utf-8")

    # empty: 0 bytes, the shape an interrupted write leaves behind.
    (store / f"patch{OLD}-4").write_bytes(b"")
    return repo, store


def test_each_class_is_separated_and_counted(tmp_path: Path) -> None:
    """The deliverable is the COUNT of each class, not a pass: assert the four numbers."""
    repo, store = _build_all_four(tmp_path)
    assert _counts(store, repo) == {"applied": 1, "carried": 1, "drifted": 1, "empty": 1}


def test_prune_takes_applied_and_old_patches_and_nothing_else(tmp_path: Path) -> None:
    """A `carried` patch is a seat's uncommitted work. Pruning it is the harm this row is about."""
    repo, store = _build_all_four(tmp_path)
    # A second applied patch that is FRESH: spent content, but too new to sweep.
    _capture(repo, "i.txt", "un\ndos\n", store / f"patch{FRESH}-5")
    _commit(repo, "i.txt")

    proc = _scan(store, repo, "--prune")
    assert proc.returncode == 0, proc.stderr

    pruned = sorted(p.name for p in (store / "pruned").glob("patch*"))
    assert pruned == [f"patch{OLD}-1"], "only the applied+old patch may leave the live set"
    live = sorted(p.name for p in store.glob("patch*"))
    assert live == [f"patch{OLD}-2", f"patch{OLD}-3", f"patch{OLD}-4", f"patch{FRESH}-5"]
    assert (store / "pruned-manifest.log").read_text(encoding="utf-8").count("moved") == 1
    # The pruned patch is MOVED, not deleted: its bytes are still there to inspect.
    assert (store / "pruned" / f"patch{OLD}-1").stat().st_size > 0


def test_a_vacuous_scan_is_not_a_pass(tmp_path: Path) -> None:
    """Green after scanning nothing is the false-green class; the count has to be stated."""
    repo = _repo(tmp_path)
    store = _store(tmp_path)
    proc = _scan(store, repo)
    assert proc.returncode == 2
    assert "SCANNED 0 PATCHES" in proc.stderr
    assert "vacuous" in proc.stderr


def test_a_missing_store_is_not_a_pass(tmp_path: Path) -> None:
    """No store means no evidence, which is not the same as no problem."""
    repo = _repo(tmp_path)
    proc = _scan(tmp_path / "does-not-exist", repo)
    assert proc.returncode == 2
    assert "SCANNED NOTHING" in proc.stderr


def test_the_counts_are_printed_with_the_class_that_needs_a_human(tmp_path: Path) -> None:
    """`drifted` and `empty` are named, because neither may be pruned and both need an eye."""
    repo, store = _build_all_four(tmp_path)
    proc = _scan(store, repo)
    assert proc.returncode == 0
    assert "patches scanned: 4" in proc.stdout
    assert f"patch{OLD}-3" in proc.stdout  # drifted
    assert f"patch{OLD}-4" in proc.stdout  # empty
    assert f"patch{OLD}-2" not in proc.stdout  # carried: a live diff, not a finding to report back


def _module():
    """The scan as a module, so the discovery seam can be handed a fixture home."""
    spec = importlib.util.spec_from_file_location("stash_patch_scan", SCAN)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_the_seat_stores_are_found_and_a_store_with_no_patch_is_not(tmp_path: Path) -> None:
    """Inside a seat `~` is the SEAT's state dir, so the human's home can never come from it.

    This is the case that was missing when the scan reported "no patch store exists" on a box holding
    764 of them: discovery was never called with a home at all, and the two patterns kept the literal
    `{home}` because `expanduser` substitutes `~` and nothing else.
    """
    module = _module()
    human = tmp_path / "human"  # what the passwd database says, NOT what $HOME says in a seat
    legacy = human / ".cache" / "pre-commit"
    seat_store = human / ".openrig" / "state" / "omp" / "seat-a@rig" / ".cache" / "pre-commit"
    empty_store = human / ".openrig" / "state" / "omp" / "seat-b@rig" / ".cache" / "pre-commit"
    for directory in (legacy, seat_store, empty_store):
        directory.mkdir(parents=True)
    (legacy / f"patch{OLD}-1").write_bytes(b"a real patch")
    (seat_store / f"patch{OLD}-2").write_bytes(b"a real patch")

    found = module.default_stores(home=human, environ={})

    assert legacy.resolve() in found, "the human's historical default holds the largest pile"
    assert seat_store.resolve() in found, "one store per seat, found from the human's home"
    assert empty_store.resolve() not in found, "a store holding no patch is not evidence"
