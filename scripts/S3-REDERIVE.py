#!/usr/bin/env python3
"""S3-REDERIVE — re-resolve every line anchor in section 3 of the surface inventory (READ-ONLY).

WHY THIS EXISTS. Section 3 of `ai_docs/api-integration/surface-inventory.md` is a table of the
tables the server registers, each row citing the line where the ORM TableDef, the registry
attach and the DDL live. Those are `file:line` pointers, and a pointer rots the moment anything
is added above it. The drift that made this instrument exist was found BY HAND on 2026-10-10 -
four §3.3 anchors had moved, one of them broken by a commit inside the release set being sealed -
and a seat had to open the file, count lines, and edit them. A census nobody runs is a habit, not
a check, which is why this file is tracked beside `CITATION-AUDIT.py` and `COUNTS-AUDIT.py` and
why `scripts/tests/test_census_audits.py` invokes all three.

HOW IT WORKS. For each row of §3.1-§3.4 it reads the cited file AT `rev` (`git show`, never the
worktree, so the audit measures a commit) and searches for the thing the row claims is there -
the TableDef entry `{Name: "<table>", Model: ...}`, the registry line `<x> Tables = append(`, or
the DDL line `CREATE TABLE [IF NOT EXISTS] <table>` - preferring a path whose match is exactly at
the cited line. `FRESH` means the cited number is where the thing is. The same search runs at
`base`, which turns a stale anchor into attribution rather than absolution: `STALE->BATCH` moved
between base and rev, `STALE->EARLIER` was already stale before the base. EVERY not-fresh anchor
fails the run; the classification says who moved it, not whether it is acceptable.

WHAT IT DOES NOT COVER, said here rather than left to be assumed clean:
  * THE CITATION-LOOKING TOKENS ON NON-TABLE LINES, which is the real uncovered surface. Measured at
    the commit that added this file, by `re.finditer(r"(?:[\w./-]+\.(go|py|sql|ts|tsx|md|json)|)\:(\d+)")`
    over `ai_docs/api-integration/surface-inventory.md`: the two instruments resolve TABLE ROWS and
    nothing else - §1's route rows (144) by `scripts/CITATION-AUDIT.py`, §3.1-§3.4's rows (46 rows,
    66 anchors) here - while 149 such tokens sit on NON-table lines: §2.1 29, §2.3 17, Appendix A 16,
    §1's own prose 15 + 11 + 4, §3.3 14, §4 10, §3.6 7, §5 7, §2.5 5, §2.4 4, §2.2 3, §3.4 2, and
    the rest spread thinner. No instrument resolves them, and SOME ARE QUOTATIONS, which the
    inventory's own rule forbids "repairing": a citation asserts what the code says now, a quotation
    asserts what a document said then. They stay DECLARED-UNCOVERED rather than half-covered by a
    weaker check under a stronger name.
  * NUMBERS are a different instrument's business, and §3.5's are already anchored:
    `scripts/COUNTS-AUDIT.py` reads the document's headline figures by anchored pattern (11 keys,
    10 of them stating a figure in the document - §3.5's seat-table, registered-total and
    ProductionTables counts among them). So §3.5 is NOT "checked by nothing": its counts are
    anchored and its prose is not.
  * any semantic claim about prose. An anchor can resolve perfectly while the sentence beside it is
    wrong; nothing here reads the sentence.
  * ONE MATCH PER PATH, FIRST-FOUND. `find` takes the first line where the species pattern matches in
    the first candidate path (preferring an exact line match), so a file carrying SEVERAL
    `Tables = append(` lines would only ever have its first considered, and a citation to a later one
    would read as stale. No §3.2 row cites a later one today - all 66 anchors are fresh - and the
    `def` and `sql` species are table-named, so for those the first match IS the right one.
  * the worktree, in the other direction too: the two sibling instruments read the WORKTREE document
    while this reads the commit at `rev`, so an uncommitted edit to the inventory can make their
    verdicts disagree. The suite's clean-run cases report that as a red run, never a silent pass.

USAGE:  python3 scripts/S3-REDERIVE.py                    # rev=HEAD, base=<BASE_REV below>
        python3 scripts/S3-REDERIVE.py <rev> [base]       # audit another commit / attribution base
        python3 scripts/S3-REDERIVE.py --self-test        # perturb one anchor in a COPY; require it named
        python3 scripts/S3-REDERIVE.py --doc-file PATH    # audit a copy of the inventory instead of the commit's

EXIT CODES: 0 = every anchor is fresh; 1 = at least one anchor is stale or unresolved; 2 = the
request was refused (an argument that is not a rev, a base or a mode).

THE BASE REV IS ATTRIBUTION, NOT THE VERDICT, AND IT MAY NOT EXIST. `git show` cannot read a
commit a clone has not fetched, and the suite's CI checkout is shallow, so a base that is not in
this checkout prints `BASE UNAVAILABLE` naming the fetch that fixes it and the run continues: the
verdict is decided at `rev` and does not depend on the base. What is never done is passing quietly
without saying so - a check that cannot read its own base must report that, not print a clean line.

WHERE IT LIVES. Tracked in `scripts/`, with ROOT derived from this file's own location, so a clean
clone at any path can run it. Until 2026-10-10 it was seat-local with ROOT hardcoded to one seat's
checkout, which is why a successor could not re-run it - the same move `CITATION-AUDIT.py` made.
"""
import os, re, subprocess, sys

# The repository root, derived from this file's own location: scripts/S3-REDERIVE.py -> scripts/ ->
# the repository root. It was seat-local and hardcoded until 2026-10-10.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = "ai_docs/api-integration/surface-inventory.md"
SQLF = "agenthub_go/fastmcp/seat_management/infrastructure/schema/seat_management_postgresql.sql"

# The attribution base. It is the base the instrument was born against: the batch whose drift the
# §3.3 pass was re-deriving. It is a PARAMETER (second positional argument) rather than a rule about
# what a base must be, and a checkout that does not have it says so - see BASE UNAVAILABLE below.
BASE_REV = "a7990665"

_cache = {}


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)


def has_rev(r):
    return git("cat-file", "-e", f"{r}^{{commit}}").returncode == 0


def show(r, p):
    if (r, p) not in _cache:
        o = git("show", f"{r}:{p}")
        _cache[(r, p)] = o.stdout.splitlines() if o.returncode == 0 else None
    return _cache[(r, p)]


def candidates(basename):
    if "c:" + basename not in _cache:
        o = git("ls-files", f"*{basename}")
        _cache["c:" + basename] = [x for x in o.stdout.split() if x.endswith("/" + basename)]
    return _cache["c:" + basename]


def find(r, paths, pat, cited):
    """First match in the first candidate path; prefer a path whose match is exactly at `cited`."""
    first = None
    for p in paths:
        for n, l in enumerate(show(r, p) or [], 1):
            if pat.search(l):
                if first is None:
                    first = (p, n)
                if n == cited:
                    return (p, n)
                break
    return first


def pat_for(kind, table):
    if kind == "def":
        return re.compile(r'\{\s*Name:\s*"' + re.escape(table) + r'"')
    if kind == "reg":
        return re.compile(r'Tables\s*=\s*append\(')
    return re.compile(r'CREATE TABLE (IF NOT EXISTS )?' + re.escape(table) + r'\b', re.I)


def collect(doc, rev, base=None):
    """The rows of §3.1-§3.4 and, for each anchor, where it is at `rev` and at `base`."""
    try:
        i3 = next(i for i, l in enumerate(doc) if l.startswith("## 3."))
        i4 = next(i for i, l in enumerate(doc) if l.startswith("## 4."))
    except StopIteration:
        # A document without the section headings is NOT a crash and NOT a pass: it is a read that
        # found nothing, and the caller refuses on an empty anchor list rather than printing clean.
        return [], []
    sec, rows, anchors, sql_seen = None, [], [], None
    for i in range(i3, i4):
        l = doc[i]
        m = re.match(r"### (3\.\d)", l)
        if m:
            sec = m.group(1)
            continue
        if not sec or sec == "3.5":
            continue
        m = re.match(r"\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|(.+)\|\s*$", l)
        if not m:
            continue
        table = m.group(1)
        cells = [c.strip().strip("`") for c in m.group(3).split("|") if c.strip()]
        rows.append((i + 1, sec, table))
        spec = []
        a1 = re.match(r"([\w./\-]+):(\d+)$", cells[0]) if cells else None
        if a1:
            spec.append(("def", candidates(a1.group(1).split("/")[-1]), int(a1.group(2))))
        if len(cells) > 1:
            a2 = re.match(r"([\w./\-]*):(\d+)$", cells[1])
            if a2:
                if sec == "3.3":                      # ":61" inherits the section's sql file
                    sql_seen = sql_seen or SQLF
                    if a2.group(1):
                        sql_seen = [p for p in candidates(a2.group(1).split("/")[-1])] or [SQLF]
                    spec.append(("sql", sql_seen if isinstance(sql_seen, list) else [sql_seen], int(a2.group(2))))
                else:
                    spec.append(("reg", candidates(a2.group(1).split("/")[-1]), int(a2.group(2))))
        for kind, paths, cited in spec:
            pat = pat_for(kind, table)
            h = find(rev, paths, pat, cited)
            if h is None:
                anchors.append((i + 1, sec, table, kind, cited, paths[0] if paths else "?", None, None))
                continue
            p, n = h
            b = find(base, [p], pat, cited) if base else None
            anchors.append((i + 1, sec, table, kind, cited, p, n, b[1] if b else None))
    return rows, anchors


def classify(anchors):
    fresh = [a for a in anchors if a[6] == a[4]]
    batch = [a for a in anchors if a[6] is not None and a[6] != a[4] and a[7] is not None and a[7] != a[6]]
    earlier = [a for a in anchors if a[6] is not None and a[6] != a[4] and not (a[7] is not None and a[7] != a[6])]
    unres = [a for a in anchors if a[6] is None]
    return {"fresh": fresh, "batch": batch, "earlier": earlier, "unres": unres}


def audit(doc, rev, base=None, base_missing=False, quiet=False):
    rows, anchors = collect(doc, rev, None if base_missing else base)
    c = classify(anchors)
    not_fresh = c["batch"] + c["earlier"] + c["unres"]
    if not quiet:
        print(f"rev={rev} base={base}  rows={len(rows)}  anchors={len(anchors)}")
        if not anchors:
            # VACUOUS IS NOT CLEAN. A section 3 stripped of its rows, or a document with none, used to
            # print "every anchor in section 3 is fresh" with exit 0 - a clean line from a read that
            # found nothing. The suite guards this too, but the instrument must not say it at all.
            print(f"REFUSED-VACUOUS: no anchors were collected from section 3 of {DOC} at {rev}, so a "
                  f"clean verdict would mean nothing. This is NOT a pass.")
            return {"rows": rows, "anchors": anchors, **c, "not_fresh": not_fresh, "vacuous": True}
        if base_missing:
            # NEVER A SILENT PASS: the base is attribution, so an unreadable base leaves the verdict
            # intact and must still be said out loud - a shallow CI checkout is the normal case.
            print(f"BASE UNAVAILABLE: {base} is not in this checkout, so drift could not be attributed "
                  f"to a batch or to earlier commits. The FRESH/STALE verdict below is decided at {rev} "
                  f"and is unaffected. To get the attribution: git fetch --deepen=200 origin "
                  f"(or git fetch origin {base}), or pass a base this checkout has.")
        print("  doc sec  table                        kind  cited  HEAD  BASE  verdict")
        for rl, s, t, k, cited, p, n, b in anchors:
            # WITHOUT A BASE THERE IS NO ATTRIBUTION TO ASSERT: the old label said STALE->EARLIER with
            # BASE=None, which claims the drift predates a base that was never read (the reviewer's
            # MINOR on this row).
            v = ("UNRESOLVED" if n is None else "FRESH" if n == cited
                 else "STALE->BATCH" if (b is not None and b != n)
                 else "STALE->EARLIER" if b is not None
                 else "STALE (unattributed)")
            if v != "FRESH":
                print(f"  {rl:4d} {s:4s} {t:28s} {k:5s} {cited:5d} {str(n):>5s} {str(b):>5s}  {v}  {p}")
        stale_rows = {(a[1], a[2]) for a in not_fresh}
        earlier_label = "STALE->EARLIER" if not base_missing else "STALE (unattributed)"
        print(f"\nFRESH {len(c['fresh'])}  STALE->BATCH {len(c['batch'])}  {earlier_label} {len(c['earlier'])}  "
              f"UNRESOLVED {len(c['unres'])}")
        print(f"rows with >=1 not-fresh anchor: {len(stale_rows)} of {len(rows)}  {sorted(stale_rows)}")
        if not_fresh:
            print(f"{len(not_fresh)} anchor(s) are NOT fresh at rev={rev}: re-derive the cited numbers "
                  f"in {DOC} by hand - this instrument is read-only by design")
        else:
            print(f"every anchor in section 3 is fresh at rev={rev}")
    return {"rows": rows, "anchors": anchors, **c, "not_fresh": not_fresh}


def read_doc(rev, doc_file=None):
    if doc_file:
        with open(doc_file, encoding="utf-8") as fh:
            return fh.read().splitlines()
    doc = show(rev, DOC)
    # A COPY, because the self-test perturbs its own lines and `show` caches by (rev, path): handing
    # out the cached list let the perturbation edit the baseline as well, and the self-test then
    # reported a delta of zero against a baseline of one and called itself FAIL while exiting 0.
    return list(doc) if doc is not None else None


def self_test(rev, base):
    """Perturb ONE anchor in a COPY of the inventory and require the audit to name that row.

    A check that cannot be shown to fail is not a check, and a rotated line number looks exactly
    like a live one. The baseline is MEASURED rather than assumed clean: the assertion is the DELTA
    (one more not-fresh anchor than the unperturbed run) and the NAME (the perturbed line among
    them), because a document with drift of its own must not turn the self-test red.
    """
    import tempfile
    base_missing = not has_rev(base)
    src = read_doc(rev)
    if src is None:
        print(f"self-test: FAIL — cannot read {DOC} at {rev}")
        return 1
    rows, anchors = collect(src, rev)
    if not anchors:
        print("self-test: FAIL — no §3 anchors found to perturb")
        return 1
    rl = anchors[0][0]
    line = src[rl - 1]
    # Shift the FIRST `file:line` or `:line` the row carries by +7, a delta real drift would not
    # produce by accident, and leave the rest of the row alone.
    m = re.search(r"(\d+)(`?\s*\|\s*)$", line)
    if not m:
        print(f"self-test: FAIL — row {rl} carries no number to perturb: {line}")
        return 1
    perturbed = line[:m.start(1)] + str(int(m.group(1)) + 7) + line[m.end(1):]
    src[rl - 1] = perturbed
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write("".join(x + "\n" for x in src))
        tmp = fh.name
    baseline = audit(read_doc(rev), rev, base, base_missing=base_missing, quiet=True)["not_fresh"]
    r = audit(read_doc(tmp, doc_file=tmp), rev, base, base_missing=base_missing, quiet=True)
    named = [a for a in r["not_fresh"] if a[0] == rl]
    ok = len(r["not_fresh"]) == len(baseline) + 1 and len(named) == 1
    print(f"self-test: perturbed the anchor on inventory line {rl} by +7 -> {len(r['not_fresh'])} not-fresh "
          f"reported against a baseline of {len(baseline)}, the perturbed row {'named' if named else 'NOT named'} "
          f"({'PASS' if ok else 'FAIL'})")
    os.unlink(tmp)
    return 0 if ok else 1


def main():
    argv = list(sys.argv[1:])
    if "--self-test" in argv:
        argv.remove("--self-test")
        rev = argv[0] if argv and not argv[0].startswith("-") else "HEAD"
        base = argv[1] if len(argv) > 1 else BASE_REV
        if not has_rev(rev):
            print(f"self-test: FAIL — rev {rev} is not in this checkout")
            return 2
        return self_test(rev, base)

    doc_file = None
    if "--doc-file" in argv:
        i = argv.index("--doc-file")
        if i + 1 >= len(argv):
            print("--doc-file needs a path")
            return 2
        doc_file = argv[i + 1]
        del argv[i:i + 2]

    unknown = [a for a in argv if a.startswith("-")]
    rev = argv[0] if argv else "HEAD"
    base = argv[1] if len(argv) > 1 else BASE_REV
    if unknown or len(argv) > 2:
        print(f"usage: python3 scripts/S3-REDERIVE.py [rev] [base] [--self-test|--doc-file PATH] — "
              f"got: {' '.join(sys.argv[1:])}")
        return 2
    if not has_rev(rev):
        print(f"REFUSED: rev {rev} is not in this checkout (a shallow clone has one commit; "
              f"git fetch --deepen=200 origin)")
        return 2

    doc = read_doc(rev, doc_file)
    if doc is None:
        print(f"REFUSED: cannot read {DOC} at {rev}")
        return 2

    base_missing = not has_rev(base)
    r = audit(doc, rev, base=base, base_missing=base_missing)
    if r.get("vacuous"):
        return 2
    return 1 if r["not_fresh"] else 0


if __name__ == "__main__":
    sys.exit(main())
