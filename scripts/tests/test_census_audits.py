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


def run(*args, env=None, cwd=REPO_ROOT):
    return subprocess.run(
        [sys.executable, str(args[0]), *[str(a) for a in args[1:]]],
        cwd=cwd, capture_output=True, text=True, env=env,
    )


@pytest.fixture(scope="module")
def clean_export(tmp_path_factory):
    """A CHECKOUT OF THE COMMITTED REVISION - what "at HEAD" has to mean for the tree half.

    The instruments derive their root from their own location, so running the export's own copies from
    the export reads the EXPORT: a detached worktree at HEAD with no working-tree edits in it. Without
    this, the suite measured whatever the SHARED checkout happened to contain, so any seat's in-flight
    work turned it red - measured 2026-10-11, `3 failed, 9 passed` in this room while another seat's
    uncommitted route made the httpapp count read 126 against the document's 125. A red with no defect
    behind it, and a batch certification would read it as one in the batch (rule 82's hazard, in a test).

    ONE export for the whole module, because the three instruments share it and a `git worktree add`
    costs a full checkout. It is unregistered in a finally, so a failing test does not leak one.
    """
    if not (REPO_ROOT / ".git").exists():
        pytest.fail(f"the committed-revision reading needs a git checkout; {REPO_ROOT} has no .git")
    export = tmp_path_factory.mktemp("census-export") / "repo"
    subprocess.run(["git", "worktree", "add", "--detach", str(export), "HEAD"],
                   cwd=REPO_ROOT, check=True, capture_output=True, text=True)
    try:
        yield export
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", str(export)],
                       cwd=REPO_ROOT, capture_output=True, text=True)


def in_export(export, script):
    """The export's OWN copy of an instrument: its root follows the export, not this checkout."""
    return export / "scripts" / script.name


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("script, marker", [
    (CITATION, r"rows (\d+)"),
    (COUNTS, r"(?m)^.*\smatches$"),
    (S3, r"anchors=(\d+)"),
])
def test_the_census_instrument_is_clean_at_head_and_says_how_much_it_read(script, marker, clean_export):
    """HEAD, not the working tree - the tree half now measures the committed revision.

    This is the marker the file's name promises. Until 2026-10-11 it ran each instrument against the
    SHARED checkout, so a seat's uncommitted work decided the verdict: the export is what makes the
    sentence true, and the module fixture explains why it is one worktree rather than three.
    """
    r = run(in_export(clean_export, script), cwd=clean_export)
    out = r.stdout + r.stderr
    assert r.returncode == 0, f"{script.name} is not clean at HEAD:\n{out}"
    found = re.findall(marker, out)
    assert found, f"{script.name} printed no quantity read (marker {marker!r}):\n{out}"
    if found[0].isdigit():
        assert int(found[0]) > 0, f"{script.name} read {found[0]} items and called that clean:\n{out}"
    else:
        assert len(found) >= 10, f"{script.name} reported {len(found)} rows; the audit covers more:\n{out}"


def test_counts_audit_refuses_an_anchor_that_matches_nothing(tmp_path):
    """RULE 84, red-first: a DECLARED anchor that stops matching must fail the run and name itself.

    This reproduces the real failure it was written for. Bolding the figure inside the phrase the
    core-tables anchor reads - `runtime: 19 (core)` -> `runtime: **19** (core)`, a style the document
    uses everywhere else, so a reword is entirely plausible - leaves that anchor matching NOTHING. Before
    rule 84 the audit printed `-` for the row, compared nothing for it, and still ended "all numbers
    re-derived and matching": QUIETER as the document drifted, never redder.

    The unbroken copy is asserted to produce no ANCHOR failure rather than a zero exit, because a
    run also reads the working tree and a busy checkout can fail the tree half for reasons that have
    nothing to do with this test.
    """
    unbroken = tmp_path / "unbroken.md"
    unbroken.write_text(INVENTORY.read_text())
    ok = run(COUNTS, "--doc", str(unbroken))
    # The marker, not the word: the COVERAGE block legitimately explains the rule and names it.
    assert "\n  ANCHOR    " not in "\n" + ok.stdout, f"an anchor failed on the document as written:\n{ok.stdout}"

    text = INVENTORY.read_text()
    reworded = re.sub(r"runtime: (\d+) \(core\)", r"runtime: **\1** (core)", text, count=1)
    assert reworded != text, "the anchored phrase moved; this test needs the sentence's new shape"
    broken = tmp_path / "broken.md"
    broken.write_text(reworded)

    r = run(COUNTS, "--doc", str(broken))
    assert r.returncode != 0, f"an unmatchable anchor passed:\n{r.stdout}"
    assert "ANCHOR" in r.stdout and "core tables" in r.stdout, f"the failure is not named:\n{r.stdout}"
    assert "??" in r.stdout, f"the row does not show its document figure could not be read:\n{r.stdout}"


def test_the_clean_revision_reading_is_not_a_no_op(clean_export):
    """BOTH DIRECTIONS, because either one alone is satisfied by a test that measures nothing.

    (1) GREEN on the export as committed.
    (2) RED for a genuine TREE mismatch: one counted line added to the export's httpapp must move the
        route count. The probe is a COMMENT carrying `mux.HandleFunc(`, which is enough because the
        instrument counts the PATTERN with grep - its documented naivety, and the cheapest honest probe.
    (3) RED for a genuine DOCUMENT mismatch: the export's own document reworded to a figure the tree
        does not support must fail and name the row. (2) and (3) are different halves: a run could
        genuinely read the tree while ignoring the document, or the reverse.
    (4) GREEN after each restore, so the red is the probe's doing and not a coincidence.

    A no-op isolation - an export that is empty, or one whose instruments read the shared checkout
    anyway - passes (1) and fails (2) or (3). That is the whole reason this case exists.
    """
    counts = in_export(clean_export, COUNTS)
    app = clean_export / "agenthub_go/fastmcp/server/httpapp/app.go"
    doc = clean_export / "ai_docs/api-integration/surface-inventory.md"

    first = run(counts, cwd=clean_export)
    assert first.returncode == 0, f"the export as committed is not clean:\n{first.stdout}"

    original = app.read_bytes()
    try:
        app.write_bytes(original + b'\n// probe: mux.HandleFunc("GET /counts-probe", handleHealth)\n')
        r = run(counts, cwd=clean_export)
        assert r.returncode != 0, f"a counted line added to the tree moved nothing:\n{r.stdout}"
        assert "httpapp route registrations" in r.stdout, f"the moved count is not named:\n{r.stdout}"
    finally:
        app.write_bytes(original)
    assert run(counts, cwd=clean_export).returncode == 0, "the restore did not return the export to green"

    text = doc.read_text()
    lowered = re.sub(r"\(httpapp (\d+), auth (\d+)\)",
                     lambda m: f"(httpapp {int(m.group(1)) - 1}, auth {m.group(2)})", text, count=1)
    assert lowered != text, "the document no longer states the route pair this probe needs"
    try:
        doc.write_text(lowered)
        r = run(counts, cwd=clean_export)
        assert r.returncode != 0, f"a document figure the tree does not support passed:\n{r.stdout}"
        assert "DOCUMENT says" in r.stdout, f"the disagreement is not named as one:\n{r.stdout}"
    finally:
        doc.write_text(text)
    assert run(counts, cwd=clean_export).returncode == 0, "the restore did not return the export to green"


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


def test_s3_rederive_does_not_assert_an_attribution_without_a_base(tmp_path):
    """STALE, and SAID to be unattributed - never STALE->EARLIER, which claims the drift predates a
    base that was never read. The reviewer's MINOR on this row, pinned."""
    lines = INVENTORY.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(n for n, l in enumerate(lines) if l.startswith("## 3."))
    i = next(n for n in range(start, len(lines))
             if re.match(r"^\|\s*`[^`]+`\s*\|\s*`[^`]+`\s*\|", lines[n]) and re.search(r"\d+`?\s*\|\s*$", lines[n]))
    lines[i] = re.sub(r"(\d+)(`?\s*\|\s*)$", lambda m: str(int(m.group(1)) + 7) + m.group(2), lines[i], count=1)
    perturbed = tmp_path / "perturbed-inventory.md"
    perturbed.write_text("".join(lines), encoding="utf-8")

    r = run(S3, "HEAD", ABSENT_REV, "--doc-file", perturbed)
    out = r.stdout + r.stderr
    assert r.returncode == 1, f"a stale anchor did not fail the run:\n{out}"
    assert "STALE (unattributed)" in out, f"the drift was not named:\n{out}"
    assert "STALE->EARLIER" not in out, f"an attribution was asserted for a base that is missing:\n{out}"


def test_s3_rederive_refuses_a_document_it_can_read_nothing_from(tmp_path):
    """A section 3 with no rows used to print 'every anchor in section 3 is fresh' and exit 0: a clean
    verdict from a read that found nothing. A document without the headings is not a crash either."""
    stripped = tmp_path / "no-section-3.md"
    stripped.write_text("# a document with no section 3 at all\n\n## 2. Something else\n\nprose\n", encoding="utf-8")

    r = run(S3, "--doc-file", stripped)
    out = r.stdout + r.stderr
    assert r.returncode == 2, f"a vacuous read was not refused:\n{out}"
    assert "REFUSED-VACUOUS" in out, f"the refusal was not said in words:\n{out}"
    assert "every anchor in section 3 is fresh" not in out, f"a clean line was printed anyway:\n{out}"


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
