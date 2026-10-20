"""Tests for `scripts/DOC-CITATIONS.py` - the instrument that makes the tree answer every citation
in `ai_docs`.

WHAT IS BEING PINNED, and why each case exists.
  * It runs through the INTERPRETER as a subprocess, how a gate runs it, and reports a non-zero
    quantity read - an instrument that audited nothing could otherwise print "clean".
  * It NAMES a citation whose line has drifted and one that points at no file: the failure the
    instrument exists for was exactly a citation that looked right.
  * It REPORTS an ambiguous basename instead of guessing one of the two files - the resolution a
    reader could not reproduce is the resolution that rots.
  * It REFUSES an empty scope and an unknown argument rather than passing on nothing.
  * Its own `--self-test` perturbs a citation in a COPY and requires the audit to name it.

Run with the script suite:
    python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

import gitfixture

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
INSTRUMENT = REPO_ROOT / "scripts" / "DOC-CITATIONS.py"

# A tracked file this repository has owned for a while, so the resolver's answer does not depend on
# which branch the tests run on. Its own line count only has to be smaller than the drift below.
STABLE = "scripts/CITATION-AUDIT.py"
DRIFTED_LINE = 999999

COUNTS = re.compile(r"docs (\d+)  citations (\d+)  test names (\d+)  violations (\d+)")


def run(*args, cwd=REPO_ROOT):
    return subprocess.run(
        [sys.executable, str(args[0]), *[str(a) for a in args[1:]]],
        cwd=cwd, capture_output=True, text=True,
        env=gitfixture.environment(),
    )


@pytest.fixture
def doc_tree(tmp_path):
    """A scope of its own: markdown written per test, audited against the REAL tree via `--docs`."""
    scope = tmp_path / "docs"
    scope.mkdir()

    def write(name, body):
        path = scope / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        return path

    write.scope = scope
    return write


def test_the_documents_it_governs_are_clean_and_it_says_how_much_it_read():
    """At the landed tree: zero violations, and a count that proves the scope was read."""
    r = run(INSTRUMENT)
    out = r.stdout + r.stderr
    m = COUNTS.search(out)
    assert m, f"no summary line; the instrument read nothing or its shape changed:\n{out}"
    docs, citations, _tests, violations = (int(x) for x in m.groups())
    assert r.returncode == 0, f"the instrument is not clean at this tree:\n{out}"
    assert violations == 0, out
    assert docs >= 20, f"only {docs} documents in scope; ai_docs is larger:\n{out}"
    assert citations >= 300, f"only {citations} citations read:\n{out}"


def test_a_drifted_line_is_named(doc_tree):
    """The failure that started this instrument: a line number that had already moved."""
    doc_tree("drift.md", f"See `{STABLE}:{DRIFTED_LINE}` for the resolver.\n")
    r = run(INSTRUMENT, "--docs", doc_tree.scope)
    out = r.stdout + r.stderr
    assert r.returncode == 1, f"a citation past the end of its file passed:\n{out}"
    assert f"{STABLE}:{DRIFTED_LINE}" in out, f"the drifted citation was not named:\n{out}"
    assert "lines in" in out, f"the reason does not say the file is shorter:\n{out}"


def test_a_citation_that_is_not_in_backticks_is_read_too(doc_tree):
    """A claim is a claim: the prose form `file:line` is cited as often as the backticked one."""
    doc_tree("prose.md", f"the resolver lives at {STABLE}:{DRIFTED_LINE} in this tree\n")
    r = run(INSTRUMENT, "--docs", doc_tree.scope)
    assert r.returncode == 1, f"an unbackticked drifted citation passed:\n{r.stdout}{r.stderr}"


def test_an_invented_test_symbol_is_named(doc_tree):
    """`TestSeatAdminSetOccupantEmitsOneFrame` named no commit here; a name that looks right is the
    case this rule exists for."""
    doc_tree("symbol.md", "The suite proves it (`TestNoSuchNameInThisRepositoryAnywhere`).\n")
    r = run(INSTRUMENT, "--docs", doc_tree.scope)
    out = r.stdout + r.stderr
    assert r.returncode == 1, f"an undefined test name passed:\n{out}"
    assert "TestNoSuchNameInThisRepositoryAnywhere" in out, out
    assert "func TestNoSuchNameInThisRepositoryAnywhere(" in out, f"the rule was not stated:\n{out}"


def test_a_basename_matching_two_files_is_reported_not_guessed(doc_tree):
    """`models.go` exists in two places. Picking one would be the instrument inventing a fact."""
    doc_tree("ambiguous.md", "The row model is `models.go:1` here.\n")
    r = run(INSTRUMENT, "--docs", doc_tree.scope)
    out = r.stdout + r.stderr
    assert r.returncode == 1, f"an ambiguous basename passed:\n{out}"
    assert "ambiguous" in out, f"ambiguity was not reported as such:\n{out}"
    candidates = re.findall(r"agenthub_go/\S*models\.go", out)
    assert len(set(candidates)) >= 2, f"the candidates were not both named:\n{out}"


def test_a_range_ending_before_it_starts_is_named(doc_tree):
    """`file:103-10` asserts a range; an inverted one is no more true for having both numbers."""
    doc_tree("range.md", f"`{STABLE}:50-10` covers it.\n")
    r = run(INSTRUMENT, "--docs", doc_tree.scope)
    assert r.returncode == 1, f"an inverted range passed:\n{r.stdout}{r.stderr}"
    assert "range ends before it starts" in (r.stdout + r.stderr)


def test_reports_status_is_outside_the_check(doc_tree):
    """Dated records are measurements of a day; a later tree cannot make them wrong, so a bad
    citation inside them is not a violation - and must not be counted as one."""
    doc_tree("live.md", "Nothing cited here.\n")
    doc_tree("reports-status/2026-10-01.md", f"Measured at `{STABLE}:{DRIFTED_LINE}`.\n")
    r = run(INSTRUMENT, "--docs", doc_tree.scope)
    out = r.stdout + r.stderr
    assert r.returncode == 0, f"a reports-status record was audited:\n{out}"
    assert "docs 1 " in out, f"the excluded record was still in scope:\n{out}"


def test_a_scope_with_no_markdown_is_a_refusal_not_a_pass(doc_tree):
    r = run(INSTRUMENT, "--docs", doc_tree.scope)
    assert r.returncode == 2, f"an empty scope passed:\n{r.stdout}{r.stderr}"
    assert "refusing" in (r.stdout + r.stderr)


def test_an_unknown_argument_is_refused(doc_tree):
    doc_tree("live.md", "Nothing cited here.\n")
    r = run(INSTRUMENT, "--write", "--docs", doc_tree.scope)
    assert r.returncode == 2, f"an unknown mode ran:\n{r.stdout}{r.stderr}"
    assert "--write" in (r.stdout + r.stderr)


def test_its_own_self_test_names_the_citation_it_perturbs():
    """A check that cannot be shown to fail is not a check."""
    r = run(INSTRUMENT, "--self-test")
    out = r.stdout + r.stderr
    assert r.returncode == 0, f"the self-test failed:\n{out}"
    assert "PASS" in out, f"no verdict printed:\n{out}"
    assert "perturbed" in out and "named" in out, f"the perturbed citation was not named:\n{out}"


def go_test_site():
    """A REAL test name and its definition line, read from the tree the suite runs against, so this
    case does not break when an unrelated line moves."""
    src = REPO_ROOT / "agenthub_go" / "fastmcp" / "task_management" / "infrastructure" / \
        "database" / "schema_matches_definitions_test.go"
    for n, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
        m = re.match(r"func (Test\w+)\(", line)
        if m:
            return m.group(1), n
    pytest.fail(f"no Go test definition found in {src}")


def test_a_test_name_cited_at_the_wrong_line_is_named(doc_tree):
    """THE MOTIVATING DEFECT, after its name was corrected: the name was real, the line had moved.
    Only the pairing can answer it - and the tight rule must refuse to pass it."""
    name, line = go_test_site()
    cited = f"schema_matches_definitions_test.go:{line + 1}"
    doc_tree("pair.md", f"`{name}` (`{cited}`) fails in both directions.\n")
    r = run(INSTRUMENT, "--docs", doc_tree.scope)
    out = r.stdout + r.stderr
    assert r.returncode == 1, f"a test cited at the wrong line passed:\n{out}"
    assert name in out and "defined at" in out, f"the pairing was not named as such:\n{out}"
    assert f"schema_matches_definitions_test.go:{line}" in out, f"the true line was not given:\n{out}"


def test_the_definitions_own_line_is_not_a_violation(doc_tree):
    """The other direction: the rule must not fail the correct citation."""
    name, line = go_test_site()
    doc_tree("pair.md", f"`{name}` (`schema_matches_definitions_test.go:{line}`) proves it.\n")
    r = run(INSTRUMENT, "--docs", doc_tree.scope)
    assert r.returncode == 0, f"the correct pairing was refused:\n{r.stdout}{r.stderr}"


def test_the_pairing_is_read_across_one_line_break(doc_tree):
    name, line = go_test_site()
    doc_tree("pair.md", f"Proved by `{name}`\n(`schema_matches_definitions_test.go:{line + 1}`).\n")
    r = run(INSTRUMENT, "--docs", doc_tree.scope)
    assert r.returncode == 1, f"a pair split across one line break was not read:\n{r.stdout}{r.stderr}"
    assert "defined at" in (r.stdout + r.stderr)


def test_a_citation_beside_the_name_is_not_a_pairing(doc_tree):
    """LOOSE adjacency is rejected on measurement: a run-on list or a table row puts a test name
    near another citation, and that is not a claim about the test. Only the parenthetical is."""
    name, line = go_test_site()
    doc_tree("loose.md",
             f"`{name}` seeds a row and counts it; the label delete is `label_repository_test.go:10`.\n")
    r = run(INSTRUMENT, "--docs", doc_tree.scope)
    assert r.returncode == 0, f"a non-pairing adjacency was reported:\n{r.stdout}{r.stderr}"


def test_a_production_line_after_the_name_is_the_documents_own_claim(doc_tree):
    """R4: the escape is explicit. Name the test, then cite a production line as its own claim."""
    name, line = go_test_site()
    doc_tree("escape.md",
             f"`{name}` pins the delete at `schema_matches_definitions_test.go:{line + 1}`.\n")
    r = run(INSTRUMENT, "--docs", doc_tree.scope)
    assert r.returncode == 0, f"the documented escape was refused:\n{r.stdout}{r.stderr}"
