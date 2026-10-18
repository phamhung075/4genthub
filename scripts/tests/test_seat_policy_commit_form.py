"""The seat policy modules the room declares must carry the CURRENT commit form, and agree on it.

The fleet commits with ``git commit -m "..." -- <paths>`` and NO prior ``git add``, because the
index is shared: a staged line can be taken by another seat's commit. A new file is the one
exception - ``git add -N`` records an empty blob (e69de29b) so the pathspec commit has something to
name without putting content in the index. The policy modules still told every seat to "stage
explicit paths", which is the old form, so a seat reading its limits text would stage and lose the
line; these tests hold the ten files to the current form.

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

# A sibling is a "commit-form" sibling when it prescribes a commit, which is the key the ten-file
# edit changes; each file declares nine of them. SCOPED ON PURPOSE: the ten modules are not
# byte-identical as a whole - policy-lead.json legitimately says different things for some matches
# it owns (rig up*, rig down*, rig remove*) - so the invariant asserted below is the one the edit
# needs and can hold, not a global cross-file identity the data does not have.
COMMIT_FORM_MARKER = "git commit -m"


def _siblings() -> list[tuple[str, str, str]]:
    """Every (module, match, sibling) the ten policy modules declare under bash.patterns.

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


def test_every_policy_module_the_room_declares_is_loaded() -> None:
    names = [p.name for p in POLICY_FILES]
    assert (
        len(names) == 5
    ), f"expected the five policy modules the room's five seats declare, found {len(names)}: {names}"


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
    """(a) Within each policy module, its commit-form siblings are byte-identical.

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
        len(by_file) == 5
    ), f"expected commit-form siblings in all five modules, found {sorted(by_file)}"
    assert all(len(sibs) == 1 for sibs in by_file.values()), by_file


def test_one_commit_form_match_declares_one_sibling_across_the_policy_modules() -> None:
    """(b) For each commit-form match, the sibling is identical across all the modules.

    This is the invariant that makes the multi-file change safe: replacing the changed key in one
    place per match keeps every file consistent, and no file is left prescribing the old form.
    """
    by_match: dict[str, set[str]] = defaultdict(set)
    for _name, match, sibling in _commit_form_siblings():
        by_match[match].add(sibling)

    assert by_match, "no commit-form sibling found in the policy modules"
    disagreeing = {
        match: sorted(sibs) for match, sibs in by_match.items() if len(sibs) > 1
    }
    assert not disagreeing, (
        "a commit-form match is declared with two different siblings across the ten policy "
        f"modules: {disagreeing}"
    )


def _push_patterns() -> dict[str, list[dict[str, str]]]:
    """The `git push*` entries each policy module declares, by module name."""
    out: dict[str, list[dict[str, str]]] = {}
    for path in POLICY_FILES:
        doc = json.loads(path.read_text(encoding="utf-8"))
        out[path.name] = [
            pattern
            for pattern in doc.get("bash", {}).get("patterns", [])
            if pattern["match"].startswith("git push")
        ]
    return out


def test_only_the_lead_module_may_push() -> None:
    """The owner's 2026-10-18 ruling: the lead pushes, every other seat is refused at the policy layer.

    One entry per module and one seat exempt, so the answer to "may this seat push" is unambiguous.
    """
    by_module = _push_patterns()

    assert by_module.get("policy-lead.json") == [{"match": "git push*", "approval": "allow"}], (
        "the lead's policy module must allow the push in exactly one entry: "
        f"{by_module.get('policy-lead.json')}"
    )
    others = {name: entries for name, entries in by_module.items() if name != "policy-lead.json"}
    assert len(others) == 4, f"expected the four non-lead modules, found {sorted(others)}"
    for name, entries in others.items():
        assert len(entries) == 1 and entries[0]["approval"] == "deny", (
            f"{name} must deny the push in exactly one entry: {entries}"
        )
