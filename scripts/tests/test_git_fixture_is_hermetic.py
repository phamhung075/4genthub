"""The guard that keeps a fixture from writing the CALLER's repository.

It is a case rather than a convention because the failure it prevents is invisible until somebody else's
commit is misauthored: on 2026-10-11 a suite run with `GIT_DIR` exported wrote `user.name = scan test`
into the shared `.git/config` and staged six fixture paths into the shared index, and a commit bound for
release was created inside that window with the fixture identity on it. See `gitfixture.py`.

Two halves, because there are two ways for the leak to come back:

  * BEHAVIOURAL - drive the shared helper with `GIT_DIR` pointed at a sentinel repository, and assert the
    sentinel is untouched while the fixture's own repository is a real one with a real commit in it.
  * STRUCTURAL - read every test file in this directory and require an explicit `env=` on every child
    process that can reach git (a `git` argv, or a script that may run git itself). A fixture written
    later cannot quietly opt out of the helper: the case fails and names the file and line.
"""

from __future__ import annotations

import ast
import os
import subprocess
from pathlib import Path

import gitfixture

TESTS = Path(__file__).resolve().parent


def test_a_fixture_git_call_under_a_hostile_git_dir_leaves_the_caller_alone(
    tmp_path: Path, monkeypatch
) -> None:
    """The incident, as an assertion: GIT_DIR says "write there", the fixture must not."""
    caller = tmp_path / "caller"
    caller.mkdir()
    subprocess.run(
        ["git", "init", "-q", str(caller)],
        check=True,
        capture_output=True,
        env=gitfixture.environment(),
    )
    config_before = (caller / ".git" / "config").read_bytes()
    monkeypatch.setenv("GIT_DIR", str(caller / ".git"))

    fixture = tmp_path / "fixture"
    fixture.mkdir()
    gitfixture.git(fixture, "init", "-q", ".")
    gitfixture.git(fixture, "config", "user.email", "fixture@test.invalid")
    gitfixture.git(fixture, "config", "user.name", "fixture test")
    (fixture / "f.txt").write_text("one\n", encoding="utf-8")
    gitfixture.git(fixture, "add", "--", "f.txt")
    gitfixture.git(fixture, "commit", "-q", "-m", "base")

    assert (caller / ".git" / "config").read_bytes() == config_before, (
        "a fixture git call wrote the caller's config"
    )
    assert not (caller / ".git" / "index").exists(), "a fixture git call staged into the caller's index"
    assert not (caller / "f.txt").exists(), "a fixture git call wrote into the caller's worktree"
    assert gitfixture.git(fixture, "rev-parse", "--show-toplevel").stdout.strip() == str(fixture)
    assert gitfixture.git(fixture, "log", "--oneline").stdout.strip(), "the fixture's commit never landed"


def _child_calls_that_can_reach_git(path: Path) -> list[ast.Call]:
    """`subprocess.run(...)` calls whose argv can reach git, directly or through a script."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ):
            continue
        if not node.args:
            continue
        argv = node.args[0]
        if isinstance(argv, (ast.List, ast.Tuple)) and _can_reach_git(argv):
            found.append(node)
    return found


def _can_reach_git(argv: ast.List | ast.Tuple) -> bool:
    for element in argv.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            if element.value == "git" or element.value.endswith((".py", ".sh")):
                return True
        elif isinstance(element, ast.Call) and isinstance(element.func, ast.Name):
            # `str(SCAN)`, `str(CHECK)`, `str(hook)`: a path this check cannot resolve statically, and
            # every one of them in this suite is a script that runs git.
            if element.func.id == "str":
                return True
    return False


def test_every_child_that_can_reach_git_is_given_an_explicit_environment() -> None:
    """A `cwd` scopes the test's own git calls; only `env=` scopes the child's."""
    offenders = []
    for path in sorted(TESTS.glob("test_*.py")):
        for node in _child_calls_that_can_reach_git(path):
            if "env" not in {keyword.arg for keyword in node.keywords}:
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, (
        "these children can reach git without an explicit environment, so a caller's GIT_DIR would "
        "reach them: "
        + ", ".join(offenders)
        + ". Pass env=gitfixture.environment(...) (plus anything the child needs)."
    )


def test_the_process_scrub_drops_the_family_that_environment_already_dropped(monkeypatch) -> None:
    """The gate's MAJOR at `e0e75084`, as an assertion about the RULE rather than about one name.

    `environment()` dropped the whole `GIT_CONFIG*` family from a fixture's own child, but the autouse
    scrub in test_git_commit_capture.py looped over `RELOCATING` only - and that fixture exists because the
    wrapper's children inherit this PROCESS rather than the call. So an exported `GIT_CONFIG_GLOBAL` (a
    commit that demands a signature, or a `core.hooksPath` that would execute the caller's hook) reached
    the child and turned the suite red with no local cause.

    This holds the two environs to one rule; the call site that runs it is pinned where it lives, by
    test_git_commit_capture.py::test_the_scrub_removes_the_ambient_git_config_this_module_runs_with. A child
    that deliberately INHERITS is not spawned here either: the structural case above requires an explicit
    `env=` on every child that can reach git, and that requirement is the other half of this same guard.
    """
    monkeypatch.setenv("GIT_DIR", "/tmp/gate-sentinel-gitdir")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/tmp/gate-evil-gitconfig")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/tmp/gate-evil-system")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_PAGER", "cat")

    for name in ("GIT_DIR", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_COUNT"):
        assert gitfixture.relocates(name), f"{name} can relocate a repository or the config git reads"
    assert not gitfixture.relocates("GIT_PAGER"), "not every variable is a relocating one"

    env = gitfixture.environment()
    removed = gitfixture.without_relocating(monkeypatch)

    for name in ("GIT_DIR", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_COUNT"):
        assert name not in env, f"a fixture's own child would still inherit {name}"
        assert name not in os.environ, f"the process scrub left {name} for an inheriting child"
        assert name in removed, f"the scrub did not report {name}"
    assert os.environ["GIT_PAGER"] == "cat", "the scrub removed a variable that relocates nothing"
