"""The nine seat policy modules must carry the CURRENT commit form, and agree on it.

The fleet commits with ``git commit -m "..." -- <paths>`` and NO prior ``git add``, because the
index is shared: a staged line can be taken by another seat's commit. A new file is the one
exception - ``git add -N`` records an empty blob (e69de29b) so the pathspec commit has something to
name without putting content in the index. The policy modules still told every seat to "stage
explicit paths", which is the old form, so a seat reading its limits text would stage and lose the
line; these tests hold the nine files to the current form.

The suite runs ``python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q`` from the
repository root, so this file is self-contained: the repository root is derived from ``__file__``
and nothing is imported from a conftest.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

# <repo>/scripts/tests/<this file>: the repository root is two levels up.
REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = REPO_ROOT / "scripts" / "team" / "4genthub-min"
POLICY_FILES = sorted(POLICY_DIR.glob("policy-*.json"))

# The prescription the old form was written as. The new form replaces it with the pathspec commit
# and no prior git add, so no sibling may still carry this phrase.
OLD_COMMIT_FORM = "stage explicit paths"

# A sibling is a "commit-form" sibling when it prescribes a commit, which is the key the nine-file
# edit changes; each file declares nine of them. SCOPED ON PURPOSE: the nine modules are not
# byte-identical as a whole - policy-lead.json legitimately says different things for some matches
# it owns (rig up*, rig down*, rig remove*) - so the invariant asserted below is the one the edit
# needs and can hold, not a global cross-file identity the data does not have.
COMMIT_FORM_MARKER = "git commit -m"


def _siblings() -> list[tuple[str, str, str]]:
    """Every (module, match, sibling) the nine policy modules declare under bash.patterns.

    A rule that carries no sibling is skipped: it has no words for the seat and is not what these
    tests are about.
    """
    out: list[tuple[str, str, str]] = []
    for path in POLICY_FILES:
        doc = json.loads(path.read_text(encoding="utf-8"))
        for pattern in doc.get("bash", {}).get("patterns", []):
            if "sibling" in pattern:
                out.append((path.name, pattern["match"], pattern["sibling"]))
    return out


def test_all_nine_policy_modules_are_loaded() -> None:
    names = [p.name for p in POLICY_FILES]
    assert (
        len(names) == 9
    ), f"expected the nine policy modules, found {len(names)}: {names}"


def test_no_sibling_prescribes_the_old_commit_form() -> None:
    offenders = [
        (name, match, sibling)
        for name, match, sibling in _siblings()
        if OLD_COMMIT_FORM in sibling
    ]
    assert not offenders, (
        f"sibling text still prescribes the old commit form ({OLD_COMMIT_FORM!r}); the index is "
        "shared, so a staged path can be taken by another seat's commit. Each must be rewritten to "
        f"the pathspec form with no prior git add (a new file uses `git add -N`): {offenders}"
    )


def _commit_form_siblings() -> list[tuple[str, str, str]]:
    """The (module, match, sibling) triples whose sibling prescribes the commit form."""
    return [
        (name, match, sibling)
        for name, match, sibling in _siblings()
        if COMMIT_FORM_MARKER in sibling
    ]


def test_the_commit_form_siblings_agree_within_each_module() -> None:
    """(a) Within each of the nine files, the nine commit-form siblings are byte-identical.

    One file that kept a divergent copy of the changed key would fold against its own siblings -
    FoldPolicies refuses one match declared with two different siblings - so the edit must move all
    of a file's commit-form words together.
    """
    by_file: dict[str, set[str]] = defaultdict(set)
    for name, _match, sibling in _commit_form_siblings():
        by_file[name].add(sibling)

    disagreeing = {
        name: sorted(sibs) for name, sibs in by_file.items() if len(sibs) > 1
    }
    assert not disagreeing, (
        "a policy module declares its commit-form siblings with more than one wording: "
        f"{disagreeing}"
    )
    assert (
        len(by_file) == 9
    ), f"expected commit-form siblings in all nine modules, found {sorted(by_file)}"
    assert all(len(sibs) == 1 for sibs in by_file.values()), by_file


def test_one_commit_form_match_declares_one_sibling_across_the_nine_modules() -> None:
    """(b) For each commit-form match, the sibling is identical across all nine files.

    This is the invariant that makes the nine-file change safe: replacing the changed key in one
    place per match keeps every file consistent, and no file is left prescribing the old form.
    """
    by_match: dict[str, set[str]] = defaultdict(set)
    for _name, match, sibling in _commit_form_siblings():
        by_match[match].add(sibling)

    assert by_match, "no commit-form sibling found in the nine policy modules"
    disagreeing = {
        match: sorted(sibs) for match, sibs in by_match.items() if len(sibs) > 1
    }
    assert not disagreeing, (
        "a commit-form match is declared with two different siblings across the nine policy "
        f"modules: {disagreeing}"
    )
