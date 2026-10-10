"""Tests for the three census instruments: scripts/CITATION-AUDIT.py, scripts/COUNTS-AUDIT.py and
scripts/S3-REDERIVE.py - §1's route citations, the headline counts, and §3's table anchors.

WHY EACH TEST EXISTS (each one pins a mistake that was actually made, not decoration):
  * every instrument must be GREEN at HEAD, run as a SUBPROCESS through the interpreter - because
    that is how a gate would run it, and because importing a script cannot catch a bad `__main__`;
  * every instrument must be shown able to FAIL, through its own `--self-test`, which perturbs one
    item in a COPY and requires that item named. This is the whole point of the wiring: two of the
    three instruments exist because a number and a line were never re-derived, and a census that
    cannot go red is the habit these files replaced;
  * `S3-REDERIVE.py` must SAY its attribution base is missing instead of passing quietly. That is
    the shallow-CI checkout, and the test passes a rev that cannot exist, so it is deterministic in
    a full checkout and in a shallow one alike;
  * `CITATION-AUDIT.py --write` - the only surface in the three that can touch the repository - must
    REFUSE under a gate marker and leave the inventory byte-identical. A check that repairs what it
    measures reports clean by construction, so the wiring has to pin that it does not;
  * every report must state how much it READ, so an instrument that silently audits nothing cannot
    read as clean.

The instruments read commits and the worktree but write nothing here: every case runs a script.

Run with the script suite:  python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
CITATION = REPO_ROOT / "scripts" / "CITATION-AUDIT.py"
COUNTS = REPO_ROOT / "scripts" / "COUNTS-AUDIT.py"
S3 = REPO_ROOT / "scripts" / "S3-REDERIVE.py"
INVENTORY = REPO_ROOT / "ai_docs" / "api-integration" / "surface-inventory.md"

# The all-zeros object name cannot exist in any checkout, full or shallow, so the missing-base
# branch is exercised the same way wherever the suite runs.
ABSENT_REV = "0" * 40


def run(*args, env=None):
    return subprocess.run(
        [sys.executable, str(args[0]), *[str(a) for a in args[1:]]],
        cwd=REPO_ROOT, capture_output=True, text=True, env=env,
    )


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("script, marker", [
    (CITATION, r"rows (\d+)"),
    (COUNTS, r"(?m)^.*\smatches$"),
    (S3, r"anchors=(\d+)"),
])
def test_the_census_instrument_is_clean_at_head_and_says_how_much_it_read(script, marker):
    r = run(script)
    out = r.stdout + r.stderr
    assert r.returncode == 0, f"{script.name} is not clean at HEAD:\n{out}"
    found = re.findall(marker, out)
    assert found, f"{script.name} printed no quantity read (marker {marker!r}):\n{out}"
    if found[0].isdigit():
        assert int(found[0]) > 0, f"{script.name} read {found[0]} items and called that clean:\n{out}"
    else:
        assert len(found) >= 10, f"{script.name} reported {len(found)} rows; the audit covers more:\n{out}"


@pytest.mark.parametrize("script", [CITATION, COUNTS, S3])
def test_the_census_instrument_can_fail(script):
    """Its own --self-test perturbs one item in a COPY and requires that exact item named."""
    r = run(script, "--self-test")
    out = r.stdout + r.stderr
    assert r.returncode == 0, f"{script.name} --self-test did not pass:\n{out}"
    assert "PASS" in out, f"{script.name} --self-test printed no verdict:\n{out}"


def test_s3_rederive_says_its_base_is_missing_instead_of_passing_quietly():
    r = run(S3, "HEAD", ABSENT_REV)
    out = r.stdout + r.stderr
    assert "BASE UNAVAILABLE" in out, f"an unreadable base was not named:\n{out}"
    assert ABSENT_REV in out, f"the missing base is not the one reported:\n{out}"
    # The verdict is decided at the rev, so a missing base must not turn it into a refusal...
    assert r.returncode == 0, f"a missing base changed the verdict:\n{out}"
    # ...and it must not swallow the verdict either.
    assert re.search(r"FRESH (\d+)", out), f"no verdict printed beside the missing base:\n{out}"


def test_s3_rederive_refuses_a_rev_this_checkout_does_not_have():
    r = run(S3, "no-such-rev-at-all")
    assert r.returncode == 2, f"expected a refusal, got {r.returncode}:\n{r.stdout}{r.stderr}"


def test_citation_audit_refuses_to_rewrite_under_a_gate_marker_and_leaves_the_inventory_alone():
    """The one surface that can edit the artefact it measures, pinned shut while a gate is up."""
    import os

    before = digest(INVENTORY)
    env = dict(os.environ, CI="1")
    r = run(CITATION, "--write", env=env)
    out = r.stdout + r.stderr
    assert r.returncode == 2, f"--write ran with a gate marker set:\n{out}"
    assert "refusing" in out, f"the refusal was not said in words:\n{out}"
    assert digest(INVENTORY) == before, "the inventory was rewritten despite the refusal"
