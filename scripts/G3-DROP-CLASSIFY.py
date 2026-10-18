#!/usr/bin/env python3
"""G3-DROP-CLASSIFY - every Python-parity "dropped" marker in the Go tree, classed (READ-ONLY).

WHY THIS EXISTS. G3 of the Python-removal gate ("behaviour Go dropped", the single architecture
file §G3) requires that every Go comment which says the Python implementation did something this
port does not gets a one-word class: logging, unused-arg, unreachable or ported-elsewhere. The
reviewer's pass at 15693b6a produced that table inside a seat session and never committed it, so
the gate could not be read from the tree: a grep for the class words returns only the plan's own
sentence. This instrument and its report (`ai_docs/core-architecture/G3-drop-classification.md`) are
that table, re-derived from the tree and re-runnable, so the next reader does not have to trust a
session that is gone.

A CANDIDATE, defined so a machine can disagree with this file. A comment line (the text after the
first `//`) in a TRACKED, NON-TEST `.go` file under `agenthub_go/` that carries
  (a) an ABSENCE term - dropped, drop, not ported, unported, no-op, no equivalent, unreachable,
      omitted, skipped, not implemented, does not exist - and
  (b) a PYTHON reference - the word `python`/`Python`, a `.py` path, or a snake_case identifier
      (never Go style, so it names a Python construct).
Both, on the same line, because either alone is noise: `dropped` alone matches the domain's own
vocabulary ("a dropped answer is delivered once") and a snake_case token alone matches SQL columns
(`uuid_generate_v4`, `next_action`). The report's second table lists every candidate that is NOT a
marker, with the reason, so nothing the sweep saw disappears silently.

WHAT IT CHECKS. Every candidate must have exactly one row in the report and every row must match a
live candidate: an unclassed candidate and a stale row (the comment moved or was deleted) both FAIL
the run. A class of logging / unused-arg / unreachable / ported-elsewhere is a marker's verdict;
`named` says the site is one of the dropped behaviours already carrying its own note in the tree
(out of G3's bulk scope); `agrees` says Python itself was a no-op, a bug or absent, so nothing was
dropped; `domain` says the absence word is the domain's, not a parity note. The verdicts are
readings, not the regex's: the regex only decides what has to be read.

WHAT IT DOES NOT COVER, said here rather than left to be assumed clean:
  * the Python tree itself (`agenthub_main` was deleted on 2026-10-09; the last copy is the tag
    `python-backend-final`). A Python behaviour no Go comment mentions leaves no marker to class;
    this instrument measures the Go-comment census, and nothing else;
  * `_test.go` files: test prose says "dropped" about fixtures, not about the server;
  * markers whose comment wraps so that the absence term and the Python reference land on
    DIFFERENT lines. The sweep is line-keyed; such a half-line shows up in the report's second
    table when only one half qualified.

ROOT. The sweep is rooted at `git rev-parse --show-toplevel` and REFUSES to run anywhere else.
Paths are repository-relative and the file count is printed, because the same lexical sweep run
inside `agenthub_go` reads as clean for the wrong reason: its pathspec is then a subtree and its
relative paths stop matching the report's rows, which is a different measurement wearing the same
name.

Exit: 0 every candidate classed and no stale row | 1 findings (printed, each named) |
      2 the instrument could not measure (wrong root, no tracked tree, report unreadable).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPORT = "ai_docs/core-architecture/G3-drop-classification.md"
SUBTREE = "agenthub_go"
MARKER_CLASSES = ("logging", "unused-arg", "unreachable", "ported-elsewhere")
NON_MARKER = ("named", "agrees", "domain")
ABSENCE = re.compile(
    r"\b(dropped|drop|not ported|unported|no-op|no equivalent|unreachable|omitted|skipped"
    r"|not implemented|does not exist)\b"
)
PYTHON = re.compile(r"(?i)(python|\.py\b|[a-z][a-z0-9]*_[a-z0-9_]+)")
ROW = re.compile(r"^\|\s*`(?P<key>[^`]+)`\s*\|\s*(?P<disposition>[a-z-]+)\s*\|")


def die(message: str) -> int:
    print(f"G3-DROP-CLASSIFY: {message}", file=sys.stderr)
    return 2


def root() -> Path | None:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return Path(out.stdout.strip())


def candidates(base: Path):
    """Every line-keyed Python-parity drop candidate, in git order."""
    listing = subprocess.run(
        ["git", "-C", str(base), "ls-files", SUBTREE], capture_output=True, text=True
    )
    if listing.returncode != 0:
        raise SystemExit(die(f"git ls-files failed in {base}: {listing.stderr.strip()}"))
    files = [
        p for p in listing.stdout.split()
        if p.endswith(".go") and not p.endswith("_test.go")
    ]
    found = []
    for name in files:
        text = (base / name).read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.split("\n"), 1):
            if "//" not in line:
                continue
            comment = line.split("//", 1)[1]
            if ABSENCE.search(comment) and PYTHON.search(comment):
                found.append((f"{name}:{number}", comment.strip()))
    return files, found


def report_rows(base: Path, report: str = REPORT):
    path = base / report
    if not path.is_file():
        raise SystemExit(die(f"report not found: {report}"))
    rows = {}
    for line in path.read_text(encoding="utf-8").split("\n"):
        match = ROW.match(line)
        if not match:
            continue
        key, disposition = match.group("key"), match.group("disposition")
        if key in rows:
            raise SystemExit(die(f"report carries two rows for {key}"))
        rows[key] = disposition
    return rows


def verify(base: Path, report: str = REPORT):
    """Return (exit code, the finding keys). Every candidate classed, every row live."""
    files, found = candidates(base)
    rows = report_rows(base, report)
    live = {key for key, _ in found}
    unclassed = sorted(live - set(rows))
    stale = sorted(set(rows) - live)
    vocabulary = MARKER_CLASSES + NON_MARKER
    bad = sorted(
        key for key, disposition in rows.items()
        if key in live and disposition not in vocabulary
    )
    marker_classes = Counter(rows[key] for key in live if rows.get(key) in MARKER_CLASSES)
    non_marker = Counter(rows[key] for key in live if rows.get(key) in NON_MARKER)
    summary = [
        f"G3-DROP-CLASSIFY: root={base}",
        f"  swept {len(files)} tracked non-test .go file(s) under {SUBTREE}/ from the repository root",
        f"  candidates={len(found)} markers={sum(marker_classes.values())} "
        f"non-markers={sum(non_marker.values())}",
        "  classes: " + (", ".join(f"{k}={v}" for k, v in sorted(marker_classes.items())) or "none"),
        "  not markers: " + (", ".join(f"{k}={v}" for k, v in sorted(non_marker.items())) or "none"),
    ]
    problems = [f"unclassed candidate: {key}" for key in unclassed]
    problems += [f"stale row (no such candidate): {key}" for key in stale]
    problems += [f"disposition outside the vocabulary: {key} -> {rows[key]}" for key in bad]
    print("\n".join(summary))
    if problems:
        print(f"G3-DROP-CLASSIFY: findings - {len(problems)} to resolve", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1, problems
    return 0, []


def run_self_test(base: Path) -> int:
    """Perturb a COPY of the report and require BOTH failures to be named."""
    rows = report_rows(base)
    if not rows:
        return die("self-test: the report has no rows to perturb")
    victim = sorted(rows)[0]
    text = (base / REPORT).read_text(encoding="utf-8")
    missing_row = "\n".join(line for line in text.split("\n") if f"`{victim}`" not in line)
    stale_key = f"{SUBTREE}/self-test/never.git.go:1"
    stale_row = f"| `{stale_key}` | logging | self-test row no candidate matches |"
    probe = REPORT + ".self-test"
    failures = []
    for name, body, wanted in (
        ("a dropped row", missing_row, victim),
        ("an invented row", text + "\n" + stale_row + "\n", stale_key),
    ):
        (base / probe).write_text(body, encoding="utf-8")
        try:
            code, problems = verify(base, probe)
        finally:
            (base / probe).unlink(missing_ok=True)
        named = [p for p in problems if wanted in p]
        if code != 1 or not named:
            failures.append(f"self-test did not name {wanted} for {name} (exit {code})")
    if failures:
        for failure in failures:
            print(f"G3-DROP-CLASSIFY: {failure}", file=sys.stderr)
        return 2
    print("G3-DROP-CLASSIFY: self-test ok - a dropped row and an invented row are both named")
    return 0


def main(argv) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="print every candidate and its comment")
    parser.add_argument("--self-test", action="store_true", help="perturb a copy and require it to be named")
    args = parser.parse_args(argv)

    base = root()
    if base is None:
        return die("not inside a git worktree")
    if Path.cwd().resolve() != base:
        return die(
            f"the sweep is rooted at {base}; run it there "
            "(a subtree run measures a different population)"
        )
    if args.self_test:
        return run_self_test(base)
    if args.list:
        files, found = candidates(base)
        print(f"root={base} files={len(files)} candidates={len(found)}")
        for key, comment in found:
            print(f"{key}\t{comment}")
        return 0
    code, _ = verify(base)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
