"""Every git call a script-suite fixture makes goes through here.

WHY THIS MODULE EXISTS (2026-10-11). A run of this suite with `GIT_DIR` exported - the natural thing for
a caller that is itself driving git, and what a leaked `GIT_DIR` from an outer process looks like - wrote

    [user]
        email = scan@test.invalid
        name = scan test

into the superproject's `.git/config` and staged six fixture paths (NEXT_GEN.md, a.txt, f.txt, g.txt,
h.txt, i.txt) into the shared index. Nothing was wrong with the fixtures' own repositories: each built a
throwaway repo and passed `cwd=<that repo>`. Git resolves its repository BEFORE it looks at the working
directory, so `GIT_DIR` in the environment beat `cwd`, and `git config`, `git add` and `git commit`
followed the variable out of the fixture's `tmp_path` and into the caller's checkout. A commit bound for
release (`ea3efb20`) was then authored `scan test <scan@test.invalid>` because it was made inside that
window. The child processes were the second half of the same hole: any script a test ran (the hooks under
test, `S3-REDERIVE.py`, `added_line_check.py`) inherits the test process's environment, so a scoped
`cwd` on the test's own git calls changed nothing for them.

A fixture therefore gets two things from here and nothing else:

  * `environment()`, the caller's environment with every variable that can relocate a repository removed
    (`GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY`,
    `GIT_ALTERNATE_OBJECT_DIRECTORIES`, and the whole `GIT_CONFIG*` family - a redirected config is the
    same leak with a different target file);
  * `git(repo, ...)`, which runs git inside `repo` under that environment.

`relocates()` is the ONE statement of that rule, and there are TWO environs it has to hold in. The one
above scopes a fixture's own child. The other is the TEST PROCESS itself: a child that builds its own
environment by INHERITING never calls `environment()` at all - the commit wrapper under test, and a
generated script that shells out to git, are both like that - so an exported `GIT_DIR`, or
`GIT_CONFIG_GLOBAL`, reaches it through the parent. A case that runs such a child therefore scrubs the
process with `without_relocating(monkeypatch)`, which is `relocates()` over `os.environ`. One rule, two
environs, no drift: dropping the `GIT_CONFIG*` family from `environment()` alone is the half-fix the
reviewer's gate caught at `e0e75084`.

The identity a fixture commits with is still set in ITS OWN repository (`git(repo, "config", "user.email",
...)`), which is the point: with the relocating variables gone, that write lands in the throwaway repo,
because `cwd` is now the only thing that says which repository git uses.

`test_git_fixture_is_hermetic.py` holds both halves of the guard: the behavioural one, and a structural
one that fails if a fixture written later reaches git without passing an explicit environment.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# Read by git BEFORE the working directory, when it decides which repository it is operating on. The
# first three and the object directories move the write targets; GIT_COMMON_DIR moves the shared one;
# the GIT_CONFIG* family (matched by PREFIX, below) moves the config file the write lands in.
RELOCATING = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)

# The part of the rule that cannot be a list: the family is OPEN (git reads GIT_CONFIG_GLOBAL,
# GIT_CONFIG_SYSTEM, GIT_CONFIG_COUNT, GIT_CONFIG_KEY_<n>, ..., and a redirected config is the same leak
# aimed at a different file), so it is matched by prefix.
RELOCATING_PREFIX = "GIT_CONFIG"


def relocates(name: str) -> bool:
    """Whether a variable of this NAME can move the repository git uses or the config it reads.

    THE ONE STATEMENT OF THE DROP RULE (see the module docstring): `environment()` filters a fixture's
    child with it, and `without_relocating()` removes exactly the same names from the test PROCESS, so a
    child that inherits its environment cannot be relocated either.
    """
    return name in RELOCATING or name.startswith(RELOCATING_PREFIX)


def relocating_names(environ: Mapping[str, str] | None = None) -> list[str]:
    """The names `relocates()` admits, of those PRESENT in `environ` (the process environment here)."""
    source = os.environ if environ is None else environ
    return [name for name in source if relocates(name)]


def without_relocating(monkeypatch: Any) -> list[str]:
    """Remove every relocating variable from the PROCESS environment, and report what it removed.

    For a case whose child INHERITS this process's environment: `env=` on the test's own git calls cannot
    scope a child that builds its own environment, so the variables have to be gone from here. The
    parameter is pytest's monkeypatch, duck-typed so this module stays importable without pytest.
    """
    removed = relocating_names()
    for name in removed:
        monkeypatch.delenv(name, raising=False)
    return removed


def environment(**overrides: str) -> dict[str, str]:
    """The caller's environment minus every variable that can relocate a repository.

    `overrides` are applied afterwards, so a fixture can still add what it needs (`PRE_COMMIT_HOME`,
    `OPENRIG_SESSION`, a `PATH` prefix, `CI`) without re-introducing a relocation.
    """
    env = {key: value for key, value in os.environ.items() if not relocates(key)}
    env.update(overrides)
    return env


def git(
    repo: Path,
    *args: str,
    stdin: bytes | None = None,
    env: Mapping[str, str] | None = None,
    check: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess:
    """Run git inside `repo` under an environment that cannot point at another repository.

    `text=False` is for callers that feed bytes on stdin (`git check-ignore -z --stdin`): passing bytes
    with `text=True` is an error, so the two travel together.
    """
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        input=stdin,
        capture_output=True,
        check=check,
        text=text,
        env=environment(**dict(env or {})),
    )
