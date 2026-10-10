"""Every env-family file PRESENT in this tree is either VISIBLE to git or declared HERE.

`.gitignore` hides the env family with a rule the lead ruled stays - `*env.*` (line 15) - because its
job is to make an owner's environment file impossible to commit by accident, and the failure it
prevents (a pushed `DATABASE_URL` / `JWT_SECRET_KEY`) is worse than the one it causes, which is a
FUTURE file going unhidden. The pattern stays; the SILENCE is what this file fixes. A present
env-family file that is hidden is invisible to `git status`, to a reviewer and to a release
checklist, and nothing else in the repository will ever mention it. The incident this row follows is
exactly that class: `.env.testing` was absent AND gitignored, so `scripts/run-mcp-tests.sh` did its
two writes and printed success for a switch it never made
(`test_run_mcp_tests_env_guard.py`). This file is the other half - the one that prints the name
instead of hiding it.

THE FAMILY IS THE DOT-ENV NAME, at any depth: `.env` or `.env.<anything>`. It is deliberately not
every name the broad pattern matches: `*env.*` also matches `env.go` under `.gomodcache/`, and a Go
build cache's files are nobody's environment. What covers a name outside that family is the broad
pattern itself, so this file asserts the pattern is STILL THERE rather than enumerating its matches.

SCOPE, and why: the repository this file lives in, resolved by git itself - so a rule in a nested
`.gitignore` or a wholly-ignored directory wins exactly as git says it does (the `.swarm/` sample
below is declared as that directory rule's doing, not the env rule's). A submodule is a separate
repository with its own patterns and its own copy of this concern, and it is not walked from here.

WHAT "HIDDEN" MEANS HERE: that git does not track the file. A tracked file is never in the set, even
when a rule matches its name, because git carries it regardless - it shows up in `git status`, in a
diff and in a commit. The silence this file is about only ever happens to a file git does not track,
which is exactly why an accident that writes one is invisible.

These tests never read an env file's CONTENTS. The enumeration is names from `git ls-files`, the
verdicts are `git check-ignore`'s, and nothing here opens, prints, creates or commits one.
"""

from __future__ import annotations

import functools
import re
import subprocess
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[2]
GITIGNORE = REPO_ROOT / ".gitignore"

# The broad net, and the rule that names the family: both are asserted to exist below.
BROAD_PATTERN = "*env.*"
DOT_ENV_LINE = ".env"
FAMILY = re.compile(r"^\.env(\.|$)")

# Every member is DATA here rather than a rule somewhere else, because the check's whole job is to
# make this list and the tree agree, loudly. A member's absence is not a failure (a fresh clone, or a
# file the operator has not needed yet); a member's PRESENCE here and absence from the hidden set is.
DECLARED_HIDDEN = {
    ".env": "the operator's live environment file - the target scripts/run-mcp-tests.sh switches",
    ".env.backup": "that script's ONE backup slot: each switch replaces it, it is not a history",
    ".env.dev": (
        "an older copy of the same file, present since 2025-12-20, the same 15775 bytes as .env, and "
        "named by no script in this repository. Listed rather than left silent: this line is the "
        "record of the one file the check below found, and it is what an owner deletes or keeps"
    ),
    ".swarm/agenthub-frontend/.env.sample": (
        "a template inside the .swarm/ scratch tree, so the DIRECTORY rule hides it and not the env rule"
    ),
}

# The visible half of the family: the samples a repository ships so an operator can build an env file.
# These are TRACKED, and a tracked file is not silent - which is why they are not in DECLARED_HIDDEN
# even though a family rule matches their names. What can still go wrong for them is pointed at below.
DECLARED_VISIBLE = {
    ".env.sample": "the tracked sample the operator copies to .env",
    ".env.claude": "the tracked sample for the Claude tooling, 115 bytes",
}

# The negations that expose them: without one, the family rules above (- and, for a name outside this
# family, the broad one) match the sample's name, so a future sample of the same name - in a new
# directory, untracked until someone adds it - would never be offered to git.
SAMPLE_NEGATIONS = ("!.env.sample", "!.env.example", "!**/.env.example")


def _git(*args: str, stdin: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        input=stdin,
        capture_output=True,
        check=True,
    ).stdout


def _present_paths() -> set[str]:
    """Every path git can see here: tracked, untracked-and-visible, and untracked-and-hidden.

    `git ls-files` is asked rather than `os.walk`, so the answer is git's own view - which is the view
    whose silence this file is about. It is the whole tree rather than a pathspec, because a pathspec
    would put the family's definition in two places (a glob here, the regex below) and a rule that
    silently missed a name is exactly what this check exists to prevent; the price is reading the
    ignored listing once (tens of megabytes on this machine, whose build caches live in the tree).
    """
    listed = _git("ls-files", "-z") + _git(
        "ls-files", "-z", "--others", "--ignored", "--exclude-standard"
    )
    return {path for path in listed.decode("utf-8", "surrogateescape").split("\0") if path}


def _family(paths: set[str]) -> set[str]:
    """The dot-env members of a path set, by BASE NAME, at any depth."""
    return {path for path in paths if FAMILY.match(PurePosixPath(path).name)}


def _hidden_with_rule(paths: set[str]) -> dict[str, str]:
    """git's verdict for each path: the rule that hides it, as `'<pattern>' (<source>:<line>)`.

    Asked through `git check-ignore`, so the last matching rule wins exactly as it does for git, and a
    path that is NOT hidden is simply absent from the answer.

    EXIT 1 IS AN ANSWER HERE, and this is the only call in this file that must read it: `check-ignore`
    exits 1 when NOTHING it was asked about is ignored, which is exactly what a CLEAN CHECKOUT looks
    like - the tracked samples are the only family members present, and the negations expose them, so
    the answer is legitimately empty. `_git`'s default `check=True` turned that ordinary state into a
    `CalledProcessError`, which made this guard fail on a fresh clone (`2 failed, 2 passed`) while it
    passed on the pod that has `.env.dev`. Hence `check=False` below and the two exit codes: 0 and 1
    are git's answers, and any other exit - 128 for an unusable repository, say - still raises.
    """
    if not paths:
        return {}
    answer = subprocess.run(
        ["git", "check-ignore", "-v", "-z", "--stdin"],
        cwd=REPO_ROOT,
        input=b"".join(path.encode("utf-8", "surrogateescape") + b"\0" for path in sorted(paths)),
        capture_output=True,
        check=False,
    )
    if answer.returncode not in (0, 1):
        raise subprocess.CalledProcessError(
            answer.returncode, answer.args, answer.stdout, answer.stderr
        )
    fields = answer.stdout.decode("utf-8", "surrogateescape").split("\0")
    rules = {}
    for index in range(0, len(fields) - 3, 4):
        source, line, pattern, path = fields[index : index + 4]
        rules[path] = f"{pattern!r} ({source}:{line})"
    return rules


def _gitignore_lines() -> list[str]:
    """The `.gitignore`'s lines, stripped. A commented line is not a pattern, which is the point of
    comparing bare lines rather than searching the text."""
    return [line.strip() for line in GITIGNORE.read_text(encoding="utf-8").splitlines()]


@functools.lru_cache(maxsize=1)
def hidden_family() -> dict[str, str]:
    """The family's hidden members and the rule hiding each, read ONCE per run (three cases ask)."""
    return _hidden_with_rule(_family(_present_paths()))


def test_the_present_and_hidden_env_family_is_exactly_the_declared_one():
    """The core: an env-family file nobody declared cannot hide in this tree.

    Non-vacuity is mutual with the case below. If the enumeration ever returned nothing, this
    assertion would still fail, because the declared set is not empty; and if a declared member
    stopped being hidden, THAT case fails. Neither can pass by finding nothing.
    """
    hidden = hidden_family()
    unexpected = sorted(set(hidden) - set(DECLARED_HIDDEN))
    assert not unexpected, (
        "env-family file(s) are PRESENT in this tree and HIDDEN from git by a rule this check does "
        "not declare, so git status, a reviewer and a release checklist all show nothing:\n"
        + "\n".join(f"  {path}  <- hidden by {hidden[path]}" for path in unexpected)
        + "\n\nEither declare it in DECLARED_HIDDEN with a reason, or remove the file. Do not narrow "
        f"{BROAD_PATTERN}: it is what keeps an owner's env file out of a commit."
    )


def test_every_declared_member_that_is_present_is_still_hidden():
    """The other direction, and the guard on the ruling: the pattern must keep hiding what it hides.

    A narrowed or deleted pattern is silent too - the files become ordinary untracked files, one
    `git add -A` away from being committed - so a declared member that is present and no longer
    hidden fails here, naming itself.
    """
    hidden = hidden_family()
    exposed = [
        path
        for path in sorted(DECLARED_HIDDEN)
        if (REPO_ROOT / path).exists() and path not in hidden
    ]
    assert not exposed, (
        "env-family file(s) are PRESENT and NO LONGER HIDDEN: git now sees them, so one `git add -A` "
        "offers to commit them:\n"
        + "\n".join(f"  {path}  ({DECLARED_HIDDEN[path]})" for path in exposed)
        + f"\n\nRestore the pattern that hid them (the block that names {DOT_ENV_LINE}, or "
        f"{BROAD_PATTERN})."
    )


def test_the_patterns_that_hide_the_family_are_still_in_gitignore():
    """The ruling, pinned as data: the broad line stays, and it stays an active pattern.

    `*env.*` is what covers a name this file's family would not recognise (`.envrc`, `some.env.json`)
    and what the operator asked for after the incident, so its disappearance is a failure rather than
    a tidy-up. A commented-out line is not a pattern, hence the check for the bare line.
    """
    lines = _gitignore_lines()
    assert BROAD_PATTERN in lines, (
        f"{BROAD_PATTERN} is gone from .gitignore. It is the net over every env-family name this "
        "check does not enumerate; removing it makes an accidental env commit possible again."
    )
    assert DOT_ENV_LINE in lines, (
        f"{DOT_ENV_LINE} is gone from .gitignore: the owner's live env file would become untracked "
        "and visible instead of ignored."
    )


def test_the_samples_are_committed_and_the_negations_that_expose_them_are_still_there():
    """The other half of the rules: an operator must be able to copy a sample.

    A tracked sample is one git already carries, and a negation is what keeps a sample's NAME
    offerable to git at all - without it the family rules match the name, so a future sample in a new
    directory would be born invisible. Both halves are asserted, because either one failing means the
    repository ships no example to build an env file from, quietly.
    """
    lines = _gitignore_lines()
    lost = [negation for negation in SAMPLE_NEGATIONS if negation not in lines]
    assert not lost, (
        "negation(s) are gone from .gitignore: "
        + ", ".join(lost)
        + "\nWithout them the family rules match the sample names, so a sample that is not committed "
        "YET - a new directory's .env.sample - is hidden from git the moment it is written."
    )

    tracked = set(_git("ls-files", "-z").decode("utf-8", "surrogateescape").split("\0"))
    uncommitted = [path for path in sorted(DECLARED_VISIBLE) if path not in tracked]
    assert not uncommitted, (
        "sample(s) the repository is supposed to ship are no longer tracked:\n"
        + "\n".join(f"  {path}  ({DECLARED_VISIBLE[path]})" for path in uncommitted)
        + "\nCommit them again: a clone without an example cannot build an env file."
    )
