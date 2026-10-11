"""The commit wrapper: the capture a victim can find, and the verdict that says which copy is the only one.

The window it protects is real — the pre-commit framework rewinds the WHOLE worktree to the index on every
commit and re-applies the parked diff in a `finally:` — so the case that matters is the one where the
process DIES inside it. That case is built here for real: a commit command that rewinds the file and exits
137, which is exactly what "the restore never ran" looks like from the worktree's side. A test that only
proved the happy path would prove the part that was never at risk.

The other half is WHERE the capture goes. The framework's own patch lands in the committing seat's
$HOME-derived store, which is why a victim cannot find it; these cases assert the capture lands inside the
repository instead, and that recovery is one `git apply` away.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

# <repo>/scripts/tests/<this file>: two levels up is where scripts/git-hooks/ lives.
REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "scripts" / "git-hooks" / "git_commit_capture.py"

THE_PARKED_WORK = "one\ntwo\n"


def _module():
    """The wrapper as a module: COMMIT_COMMAND is the seam that stages the death without one."""
    spec = importlib.util.spec_from_file_location("git_commit_capture", WRAPPER)
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
    _git(repo, "config", "user.email", "capture@test.invalid")
    _git(repo, "config", "user.name", "capture test")
    (repo / "f.txt").write_text("one\n", encoding="utf-8")
    _git(repo, "add", "--", "f.txt")
    _git(repo, "commit", "-q", "-m", "base")
    (repo / "f.txt").write_text(THE_PARKED_WORK, encoding="utf-8")  # the work the window parks
    return repo


def _parked(repo: Path) -> Path:
    return Path(_git(repo, "rev-parse", "--absolute-git-dir").strip()) / "parked-diffs"


def test_the_capture_lands_in_the_repository_not_in_a_store_a_victim_cannot_find(tmp_path: Path) -> None:
    """The framework parks in the COMMITTING seat's $HOME-derived store. This parks in the repo."""
    module = _module()
    repo = _repo(tmp_path)
    module.COMMIT_COMMAND = [sys.executable, "-c", "pass"]  # the commit itself is not the subject here

    assert module.main(["--repo", str(repo), "--", "-m", "never runs"]) == 0

    runs = sorted(_parked(repo).glob("*"))
    assert len(runs) == 1, "one capture per run"
    assert str(runs[0]).startswith(str(repo)), "findable from the repository, not from a seat's HOME"
    patch = next(runs[0].glob("*.patch"))
    assert patch.read_text(encoding="utf-8") == _git(repo, "diff", "--", "f.txt")
    manifest = (runs[0] / "MANIFEST.txt").read_text(encoding="utf-8")
    assert "f.txt" in manifest and "sha1=" in manifest


def test_a_kill_inside_the_window_is_reported_and_the_patch_recovers_the_work(
    tmp_path: Path, capsys
) -> None:
    """The case the whole row exists for: the restore never runs, and the capture is the only copy."""
    module = _module()
    repo = _repo(tmp_path)
    killer = tmp_path / "killer.py"
    killer.write_text(
        "import subprocess, sys\n"
        "# the framework's window: the tree is rewound to the index and the process then dies\n"
        "subprocess.run(['git', '--no-optional-locks', 'checkout', '--', 'f.txt'], cwd=sys.argv[1], check=True)\n"
        "sys.exit(137)\n",
        encoding="utf-8",
    )
    module.COMMIT_COMMAND = [sys.executable, str(killer), str(repo)]

    rc = module.main(["--repo", str(repo), "--", "-m", "lands nothing"])

    assert rc == 3, "a commit that died with a parked path unaccounted for is not success"
    assert (repo / "f.txt").read_text(encoding="utf-8") == "one\n", "the window took the work"
    err = capsys.readouterr().err
    patch = next(_parked(repo).glob("*/*.patch"))
    assert f"git apply {patch}" in err, "the wrapper must name the exact command, not the hazard"
    assert "at-risk" in next(_parked(repo).glob("*/MANIFEST.txt")).read_text(encoding="utf-8")

    subprocess.run(["git", "apply", str(patch)], cwd=repo, check=True)

    assert (repo / "f.txt").read_text(encoding="utf-8") == THE_PARKED_WORK, "one git apply recovers it"


def test_a_real_commit_is_verified_as_landed_and_leaves_nothing_at_risk(tmp_path: Path) -> None:
    """`landed` has to mean THIS commit carries it - and the worktree says so afterwards."""
    module = _module()
    repo = _repo(tmp_path)
    module.COMMIT_COMMAND = ["git", "commit"]  # the real thing, so the real pathspec lands it

    rc = module.main(["--repo", str(repo), "--", "-m", "the parked work lands", "--", "f.txt"])

    assert rc == 0
    manifest = next(_parked(repo).glob("*/MANIFEST.txt")).read_text(encoding="utf-8")
    assert "verdict=landed" in manifest
    assert _git(repo, "status", "--porcelain", "--", "f.txt") == ""
    assert _git(repo, "show", "HEAD:f.txt") == THE_PARKED_WORK


def test_the_sweep_keeps_a_run_that_holds_the_only_copy(tmp_path: Path) -> None:
    """Retention may remove an old capture only when its own verification says nothing is at risk."""
    module = _module()
    repo = _repo(tmp_path)
    parked = _parked(repo)
    parked.mkdir(parents=True, exist_ok=True)
    old = time.time() - 30 * 86400
    for name, verdict in (("20260101T000000Z-safe", "landed"), ("20260101T000000Z-risky", "at-risk")):
        run_dir = parked / name
        run_dir.mkdir()
        (run_dir / "01-f.txt.patch").write_text("diff --git a/f.txt b/f.txt\n", encoding="utf-8")
        (run_dir / "MANIFEST.txt").write_text(
            f"run {name}\nf.txt bytes=1 sha1=x patch=01-f.txt.patch verdict={verdict}\n", encoding="utf-8"
        )
        os.utime(run_dir, (old, old))

    assert module.main(["--repo", str(repo), "--sweep", "--keep-days", "7"]) == 0

    assert sorted(p.name for p in parked.glob("*")) == [
        "20260101T000000Z-risky"
    ], "the risky capture is never swept, however old it is"


def _seed_run(parked: Path, name: str, verdict: str | None, age_days: float = 30.0) -> Path:
    """A capture of the given age: a patch, a manifest carrying one verdict, or NO manifest at all."""
    run_dir = parked / name
    run_dir.mkdir()
    (run_dir / "01-f.txt.patch").write_text("diff --git a/f.txt b/f.txt\n", encoding="utf-8")
    if verdict is not None:
        (run_dir / "MANIFEST.txt").write_text(
            f"run {name}\nf.txt bytes=1 sha1=x patch=01-f.txt.patch verdict={verdict}\n", encoding="utf-8"
        )
    old = time.time() - age_days * 86400
    os.utime(run_dir, (old, old))
    return run_dir


def test_an_unverified_capture_survives_the_sweep_and_is_never_called_safe(tmp_path: Path, capsys) -> None:
    """THE MAJOR. The manifest written BEFORE the commit says `unverified`, and a wrapper killed with the
    seat (the 2026-10-08 case) never reaches the second write. That capture IS the mid-window-death case
    this tool exists for, so retention must KEEP it - the rule needs proof, and "nothing was recorded" is
    not proof. The landed run beside it is the control: it is swept, so the rule still prunes.
    """
    module = _module()
    repo = _repo(tmp_path)
    parked = _parked(repo)
    parked.mkdir(parents=True, exist_ok=True)
    _seed_run(parked, "20260101T000000Z-killed", "unverified")
    _seed_run(parked, "20260101T000000Z-gone", "landed")

    assert module.main(["--repo", str(repo), "--list"]) == 0
    lines = [ln for ln in capsys.readouterr().out.splitlines() if "-killed" in ln]
    assert len(lines) == 1, "the run must be listed once"
    assert "KEEP" in lines[0], f"an unverified capture must be marked kept, not safe: {lines[0]}"
    assert "safe to sweep" not in lines[0], lines[0]

    assert module.main(["--repo", str(repo), "--sweep", "--keep-days", "7"]) == 0

    survivors = sorted(p.name for p in parked.glob("*"))
    assert survivors == ["20260101T000000Z-killed"], (
        f"the unverified capture must survive the sweep and only the proven-safe one may go: {survivors}"
    )


def test_a_capture_with_no_readable_manifest_survives_the_sweep(tmp_path: Path) -> None:
    """A torn run - the directory exists, the manifest never landed. Nothing recorded anything, so the
    retention rule has no proof to act on and must keep the patches rather than read silence as safety."""
    module = _module()
    repo = _repo(tmp_path)
    parked = _parked(repo)
    parked.mkdir(parents=True, exist_ok=True)
    _seed_run(parked, "20260101T000000Z-torn", None)

    assert module.main(["--repo", str(repo), "--sweep", "--keep-days", "7"]) == 0

    assert sorted(p.name for p in parked.glob("*")) == ["20260101T000000Z-torn"], "silence is not proof"


def test_a_clean_tree_says_nothing_was_parked_instead_of_going_silent(tmp_path: Path, capsys) -> None:
    """The no-op path used to be SILENT: report()'s no-rows branch was unreachable code. A seat that
    expected a capture has to hear that the worktree held no unstaged change before the commit, and the
    wrapper must still hand back git's own return code."""
    module = _module()
    repo = _repo(tmp_path)
    module.COMMIT_COMMAND = ["git", "commit"]
    _git(repo, "checkout", "--", "f.txt")  # a clean tree: nothing for the capture to park

    rc = module.main(["--repo", str(repo), "--", "-m", "nothing to park"])

    assert "nothing was parked" in capsys.readouterr().out, "the no-op path must speak"
    assert rc == 1, "git's own non-zero survives the wrapper untouched"
    assert list(_parked(repo).glob("*")) == [], "a run with no patch leaves no directory behind"


def test_two_runs_in_the_same_second_do_not_share_a_run_directory(tmp_path: Path, monkeypatch) -> None:
    """The label was second-granular, so two runs by one seat in the same second shared a run directory:
    the second overwrote the first's `NN-<name>.patch` files and manifest, and a no-rows second run
    `rmtree`d the first capture - a silent-loss path inside the module built so nothing is lost."""
    module = _module()

    class _AtAPid:
        environ = os.environ

        def __init__(self, pid: int) -> None:
            self._pid = pid

        def getpid(self) -> int:
            return self._pid

    monkeypatch.setattr(module.time, "strftime", lambda *a, **k: "20260101T000000Z")
    monkeypatch.setenv(module.SEAT_ENV, "go-dev")

    monkeypatch.setattr(module, "os", _AtAPid(1111))
    first = module.run_label()
    monkeypatch.setattr(module, "os", _AtAPid(2222))
    second = module.run_label()

    assert first != second, f"one second is not enough to tell two runs apart: {first}"
    assert first.endswith("1111") and second.endswith("2222"), (first, second)
