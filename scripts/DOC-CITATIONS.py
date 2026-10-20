#!/usr/bin/env python3
"""DOC-CITATIONS — every `file:line` and every backticked `Test` name in ai_docs resolves.

WHY THIS EXISTS. `ai_docs/core-architecture/seat-occupant-record.md` reached main on 2026-10-20
citing `TestSeatAdminSetOccupantEmitsOneFrame` at `seat_admin_mount_test.go:527`: a name present in
NO commit of this repository, at a line that had already moved to :547. A reader caught it and no
check did. `scripts/CITATION-AUDIT.py` resolves only the surface inventory's route tables, so every
other citation in `ai_docs` rots unseen. A citation is a CLAIM ABOUT THE TREE; this instrument makes
the tree answer it.

WHAT IT CHECKS, and nothing else.
  1. Every `path/to/file:NNN` (and `:NNN-MMM`): the file resolves INSIDE the repository - as a
     root-relative path, as a suffix of a tracked/on-disk path (`fastmcp/...` for
     `agenthub_go/fastmcp/...`), or by an unambiguous basename - and it has at least NNN lines.
     A basename that matches more than one file is REPORTED, never guessed.
  2. Every backticked `TestXxx` is defined as `func TestXxx(` under `agenthub_go/` or
     `agenthub_client/`. The rule is exact on purpose: the failure that started this tool was a
     name that LOOKED right.

  3. A citation in PARENTHESES DIRECTLY after a test name claims that test's own definition line:
     `TestFoo` (`x_test.go:196`) must find `func TestFoo(` at line 196 of that file. Nothing but
     whitespace may stand between the name and the parenthesis, and the pair may break across one
     line. This is the rule that would have caught the defect that started the instrument even
     after its NAME was corrected: the name was real and the line had moved 20 lines, so only the
     pairing can answer it. The escape belongs to the document: name the test, then state a
     production line as its own claim - not in a parenthetical directly after the name.

SCOPE. `ai_docs/**/*.md`, except `ai_docs/reports-status/**`: those are dated records of what was
measured on a day, and a later tree cannot make them wrong - so they are outside every rewrite and
outside this check too.

WHAT THIS DOES NOT CHECK, AND WHY - EACH ONE MEASURED ON THIS TREE (2026-10-20), so the next reader
does not re-add it:
  * LOOSE PAIRING (a test name and any citation sharing a line): 8 co-citation lines, 5 agreeing;
    the 3 that did not were pairings no document made - a table row carrying seven route citations
    under one name, and a run-on list whose line break put a test name beside another test's file.
    Adjacency is not a pairing.
  * A BARE `:NNN` parsed against the nearest preceding file on its line: 76 lines carry both forms,
    only 32 bare references are attributable to a resolvable same-line file, and ZERO of those 32
    were out of range. A new pairing rule for 10% of the volume, on a premise the loose form had
    already falsified. A second line reference on one line repeats the file or writes a range
    (`:120-127`); a bare `:121` is prose, and this tool does not read it.
  * EVERY backticked `Type.Method` resolved to a declared member: 35 of 38 resolve already, and the
    three exceptions are a struct field, a DTO field, and a method named BECAUSE IT WAS REMOVED -
    a gate that fails a document for correctly recording a removal is worse than no gate.

MODES. The default audits and writes nothing: exit 0 clean, 1 on any violation, 2 refused (an
unknown argument, a doc scope that holds no markdown, a `--docs` directory that does not exist).
`--self-test` perturbs one resolvable citation in a COPY of the documents and requires the audit to
name that exact document line - a check that cannot be shown to fail is not a check.

    python3 scripts/DOC-CITATIONS.py
    python3 scripts/DOC-CITATIONS.py --self-test
    python3 scripts/DOC-CITATIONS.py --docs <dir>      # audit another doc tree against this repo
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

# The repository root, from this file's own location: scripts/DOC-CITATIONS.py -> scripts/ -> root.
# Same convention as CITATION-AUDIT.py and COUNTS-AUDIT.py, so a worktree audits the worktree.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "ai_docs")
# Dated records: a measurement of a day, which a later tree cannot make wrong. The name is
# matched relative to the audited scope, so `--docs` over another tree excludes its own copy.
OUTSIDE = ("reports-status",)
CODE_TREES = ("agenthub_go", "agenthub_client")

EXTS = "go|py|sql|ts|tsx|js|md|json|yaml|yml|sh|rs|toml|css|html"
CITE = re.compile(rf"(?<![\w/.-])([A-Za-z0-9_][\w./-]*\.(?:{EXTS})):(\d+)(?:-(\d+))?(?![\w-])")
TEST_NAME = re.compile(r"`(Test[A-Za-z0-9_]+)`")
# A citation in parentheses, which is what the tight pairing rule reads.
PAIR = re.compile(rf"\(\s*`?([A-Za-z0-9_][\w./-]*\.(?:{EXTS})):(\d+)(?:-\d+)?`?\s*\)")
GO_TEST_DEF = re.compile(r"^func (Test[A-Za-z0-9_]+)\(", re.M)

SKIP_DIRS = {".git", "node_modules", "__pycache__", "target", ".venv", "dist", "build", ".next"}


def walk_files(tops):
    """Every regular file under `tops`, skipping vendored/build directories and .obsolete leaves."""
    for top in tops:
        if os.path.isfile(top):
            yield top
            continue
        for dp, dns, fns in os.walk(top):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in fns:
                if not fn.endswith(".obsolete"):
                    yield os.path.join(dp, fn)


def tracked_paths():
    """The paths the TREE claims: everything `git ls-files` reports, plus the content of every
    submodule, whose files this repository's own index names only as a gitlink.

    WHY NOT A WORKTREE WALK. A seat's scratch directory holds COPIES of tracked files (a lane's
    `.lane-commit-form/` mirrored the whole repository on 2026-10-20), so walking the disk made
    every basename ambiguous against its own copy and resolved citations into files no commit
    carries. A citation is a claim about what the tree ships, so that is what it is checked against.
    A tracked path that is absent from disk is still reported: the file is gone from the checkout.
    """
    def git(*args):
        return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)

    files = git("ls-files", "-z")
    if files.returncode != 0:
        raise RuntimeError(f"git ls-files failed: {files.stderr.strip()}")
    paths = [p for p in files.stdout.split("\0") if p]
    modes = git("ls-files", "-s", "-z")
    if modes.returncode != 0:
        raise RuntimeError(f"git ls-files -s failed: {modes.stderr.strip()}")
    for entry in modes.stdout.split("\0"):
        meta, _, path = entry.partition("\t")
        if meta.split(" ")[0] != "160000":
            continue
        base = os.path.join(ROOT, path)
        if os.path.isdir(base):
            for p in walk_files([base]):
                paths.append(os.path.relpath(p, ROOT).replace(os.sep, "/"))
    return paths


def repo_index():
    """(path map, basename map) over the tracked tree, so a citation resolves to what ships."""
    by_suffix, by_base = {}, {}
    for rel in tracked_paths():
        by_suffix[rel] = os.path.join(ROOT, rel)
        by_base.setdefault(rel.rsplit("/", 1)[-1], []).append(rel)
    return by_suffix, by_base


def line_count(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if not data:
        return 0
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def resolve(cited, by_suffix, by_base):
    """The on-disk path for a cited path, or (None, reason). Never guesses between candidates."""
    want = cited.strip().lstrip("./")
    if want in by_suffix:
        return by_suffix[want], None
    # A citation written relative to a code tree (`fastmcp/x.go` for `agenthub_go/fastmcp/x.go`):
    # a SUFFIX match must name exactly one file, or the reader is being pointed at several.
    hits = [rel for rel in by_suffix if rel.endswith("/" + want)]
    if not hits:
        hits = by_base.get(want.rsplit("/", 1)[-1], [])
    if len(hits) == 1:
        return by_suffix[hits[0]], None
    if not hits:
        return None, "no such file"
    return None, "ambiguous: " + ", ".join(sorted(hits)[:4]) + ("..." if len(hits) > 4 else "")


def go_test_index():
    """Every Go test function under the two code trees, as name -> [(file, definition line)].

    The LINE is here for the tight pairing rule (see audit): the defect this instrument exists for
    had a real name cited at a line that had already moved, and only the definition line can answer
    that claim. A name defined in two packages keeps both sites."""
    index = {}
    for top in CODE_TREES:
        base = os.path.join(ROOT, top)
        if not os.path.isdir(base):
            continue
        for p in walk_files([base]):
            if not p.endswith(".go"):
                continue
            rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
            with open(p, encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh.read().splitlines(), 1):
                    m = GO_TEST_DEF.match(line)
                    if m:
                        index.setdefault(m.group(1), []).append((rel, n))
    return index


def docs_in(scope):
    out = []
    for p in walk_files([scope]):
        if not p.endswith(".md"):
            continue
        rel = os.path.relpath(p, scope).replace(os.sep, "/")
        if any(rel == o or rel.startswith(o + "/") for o in OUTSIDE):
            continue
        out.append(p)
    return sorted(out)


def audit(docs, by_suffix, by_base, tests, base=ROOT):
    """Every violation as (doc, line, reason), plus how many citations and test names were read.

    `base` is only the DISPLAY root - what a violation's path is written against. The self-test
    audits copies under a temp directory and still has to name them the way the document is known
    in the repository, which is what makes its verdict readable and its comparison exact."""
    violations, cites, seen_tests = [], 0, set()
    for doc in docs:
        rel = os.path.relpath(doc, base).replace(os.sep, "/")
        with open(doc, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        for n, text in enumerate(lines, 1):
            for m in CITE.finditer(text):
                cites += 1
                cited, first = m.group(1), int(m.group(2))
                last = int(m.group(3)) if m.group(3) else first
                path, why = resolve(cited, by_suffix, by_base)
                if path is None:
                    violations.append((rel, n, f"{cited}:{m.group(2)} - {why}"))
                    continue
                # BOTH ENDS ARE CLAIMS: `:103-122` asserts the range, so an inverted range is as
                # wrong as a line past the end, and neither can be read from the other.
                if last < first:
                    violations.append((rel, n, f"{cited}:{m.group(2)} - range ends before it starts"))
                    continue
                if not os.path.exists(path):
                    violations.append((rel, n, f"{cited}:{m.group(2)} - tracked but absent "
                                              f"from the checkout"))
                    continue
                have = line_count(path)
                if last > have:
                    violations.append((rel, n, f"{cited}:{m.group(2)} - {have} lines in "
                                              f"{os.path.relpath(path, ROOT)}"))
            for m in TEST_NAME.finditer(text):
                name = m.group(1)
                seen_tests.add(name)
                if name not in tests:
                    violations.append((rel, n, f"`{name}` - no `func {name}(` under "
                                              f"{' or '.join(t + '/' for t in CODE_TREES)}"))
                    continue
                # THE TIGHT PAIRING RULE: a citation in parentheses DIRECTLY after the test name
                # claims that test's own definition line. Nothing but whitespace may stand between
                # the two (a same-line adjacency that only LOOKS like a pair is what made the loose
                # form unusable - it read a run-on list as a claim), and the pair may break across
                # one newline. The escape is the doc's: name the test, then state a production line
                # as its own claim instead of putting it in a parenthetical here.
                seg = text[m.end():]
                if n < len(lines):
                    seg += "\n" + lines[n]
                mp = PAIR.search(seg)
                if not mp or seg[:mp.start()].strip() or seg[:mp.start()].count("\n") > 1:
                    continue
                cited, cnum = mp.group(1), int(mp.group(2))
                path, _why = resolve(cited, by_suffix, by_base)
                if path is None:            # the path rule already reports this citation
                    continue
                site = (os.path.relpath(path, ROOT).replace(os.sep, "/"), cnum)
                if site not in tests[name]:
                    where = " or ".join(f"{f}:{ln}" for f, ln in tests[name][:2])
                    violations.append((rel, n, f"`{name}` ({cited}:{cnum}) - defined at {where}"))
    return violations, cites, seen_tests


def report(violations):
    # A CALLER MAY CLOSE THE PIPE (`| head`): the verdict is already computed, so a closed reader is
    # not a crash to trace - it is still a non-zero exit, because violations were found.
    try:
        for rel, n, reason in violations:
            print(f"{rel}:{n}: {reason}")
    except BrokenPipeError:
        pass
    return 1 if violations else 0


def self_test(by_suffix, by_base, tests):
    """THE RULE, APPLIED TO THIS INSTRUMENT: perturb one resolvable citation in a COPY of the docs
    and require the audit to name that exact document line - one more violation than the baseline,
    and the perturbed one among them. The baseline is MEASURED, so real drift in the documents does
    not turn a correct self-test red."""
    docs = docs_in(DOCS)
    if not docs:
        print("self-test: FAIL - no documents in scope to perturb")
        return 2
    tmp = tempfile.mkdtemp(prefix="doc-citations-")
    try:
        copies = {}
        for doc in docs:
            dst = os.path.join(tmp, os.path.relpath(doc, ROOT))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(doc, dst)
            copies[os.path.relpath(doc, ROOT)] = dst
        baseline, _, _ = audit(docs, by_suffix, by_base, tests)

        target = None  # (rel, lineno, cited, first)
        for rel, doc in copies.items():
            with open(doc, encoding="utf-8") as fh:
                for n, text in enumerate(fh.read().splitlines(), 1):
                    for m in CITE.finditer(text):
                        path, _why = resolve(m.group(1), by_suffix, by_base)
                        if path is not None:
                            target = (rel, n, m.group(1), m.group(2), int(m.group(2)))
                            break
                    if target:
                        break
            if target:
                break
        if not target:
            print("self-test: FAIL - no resolvable citation found to perturb")
            return 1

        rel, n, cited, shard, first = target
        dst = copies[rel]
        with open(dst, encoding="utf-8") as fh:
            text = fh.read()
        # A delta no real drift produces: the cited line is pushed past the end of any file, so the
        # violation is unambiguous and lands on the document line under test.
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(text.replace(f"{cited}:{shard}", f"{cited}:{first + 1000000}", 1))

        got, _, _ = audit(list(copies.values()), by_suffix, by_base, tests, base=tmp)
        named = [v for v in got if v[0] == rel and v[1] == n]
        ok = len(got) == len(baseline) + 1 and len(named) == 1
        print(f"self-test: perturbed {rel}:{n} ({cited}:{shard} -> +1000000) -> "
              f"{len(got)} violation(s) against a baseline of {len(baseline)}, the perturbed line "
              f"{'named' if named else 'NOT named'} ({'PASS' if ok else 'FAIL'})")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    argv = sys.argv[1:]
    by_suffix, by_base = repo_index()
    tests = go_test_index()

    if "--self-test" in argv:
        extra = [a for a in argv if a != "--self-test"]
        if extra:
            print(f"unknown argument(s): {' '.join(extra)} - --self-test takes no others")
            return 2
        return self_test(by_suffix, by_base, tests)

    scope = DOCS
    while argv:
        arg = argv.pop(0)
        if arg == "--docs":
            if not argv:
                print("--docs needs a directory")
                return 2
            scope = os.path.abspath(argv.pop(0))
            if not os.path.isdir(scope):
                print(f"refusing: --docs {scope} is not a directory")
                return 2
        else:
            print(f"unknown argument: {arg} - the modes are the default check, --self-test "
                  f"and --docs <dir>, and nothing else")
            return 2

    docs = docs_in(scope)
    if not docs:
        # A run that read no document is a REFUSAL, not a pass: "clean" would be a claim about
        # nothing.
        print(f"refusing: no markdown in scope at {os.path.relpath(scope, ROOT)}")
        return 2

    violations, cites, seen_tests = audit(docs, by_suffix, by_base, tests)
    print(f"docs {len(docs)}  citations {cites}  test names {len(seen_tests)}  "
          f"violations {len(violations)}")
    return report(violations)


if __name__ == "__main__":
    sys.exit(main())
