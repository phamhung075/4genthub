#!/usr/bin/env python3
"""CITATION-AUDIT — re-resolve every `file:line` in the surface inventory's route tables.

WHY THIS EXISTS. A `file:line` is a pointer that rots the moment code is added above it, and
the surface inventory is the document successors trust for "where is this route registered".
On 2026-10-06 (docs duty pass 3) 21 of its 144 route rows cited a line that was no longer the
registration — `app.go` by 10-11 lines, `seat_mount.go` by 73 — while the mount files that had
not changed still matched exactly. That asymmetry is the point: drift is visible only against
a check, and "it matched last time" is not a check.

HOW IT WORKS. For each table row `| METHOD | `path` | handler | `file:line` |` it reads the
cited file, parses EVERY registration in that file into (method, resolved route, line), and
looks for the one that carries the row's method+route.

The resolution is lexical because a naive grep cannot see these paths: most registrations
compose them from a `base` const declared in the same function (`"POST "+base+"/{id}"`), and
`routes_mount.go` declares SEVEN different bases in one file — so a single file-level base
gives wrong answers, and a per-line lookup of the nearest preceding `base := "..."` is what
makes the tokens and contexts blocks resolve. An empty suffix (`"GET "+base`) and a slash
suffix (`"GET "+base+"/"`) are DIFFERENT registrations and must not be normalised into each
other; conflating them reported three correct citations as stale on the first run.

TRUST NOTHING IT PRINTS WITHOUT OPENING THE FILE. `loose` matches are heuristics by
construction; the rest are resolved from the code but the code may have moved since the read.
A basename can also exist in more than one tree, so the resolver prefers `fastmcp/server/httpapp/`.

WHERE IT LIVES. Tracked beside `COUNTS-AUDIT.py` in `scripts/`, with ROOT derived from this
file's own location, so a clean clone at any path can run it. Until 2026-10-10 it was seat-local
and ROOT was one seat's absolute path, which is why the census behind the inventory's route rows
could not be re-run by a successor; the pass records in the inventory that name a
`~/.openrig/agenthub-seats/<seat>/CITATION-AUDIT.py` path are the records of the runs made before
the move.

USAGE:  python3 scripts/CITATION-AUDIT.py              # audit only, changes nothing
        python3 scripts/CITATION-AUDIT.py --self-test  # perturb one citation in a COPY; require it named
        python3 scripts/CITATION-AUDIT.py --write      # rewrite the stale citations in place (see below)

EXIT CODES: 0 = every citation resolves AND matches; 1 = at least one is stale or unresolved;
2 = the request was refused (a gate marker is set, or an argument is not one of the three modes).
The checking mode is the default and it is the only one a gate may run: it writes nothing, so a
gate that runs it can go red.

`--write` IS EXPLICIT AND GUARDED. A gate that repairs the artefact it measures reports zero
stale BY CONSTRUCTION and can never fail — the one property this fleet spent an evening refusing
everywhere else (the lead's rule, 2026-10-06) — so the rewrite needs BOTH the flag AND the
absence of every marker a gate leaves behind, and refusing is the default answer. With `CI` or
any `PRE_COMMIT_*` variable set it prints the marker it found and exits 2 with the tree
untouched; in a shell where `CI` is set for other reasons the deliberate form is explicit and
visible rather than silent: `CI= python3 scripts/CITATION-AUDIT.py --write`. The rewrite is for
a human who has read the report and decided; the gate's job is to be able to say no. It re-runs
the check afterwards and exits 1 if anything is still stale, so it cannot claim a clean tree it
did not leave.
"""
import os, re, sys

# The repository root, derived from this file's own location: scripts/CITATION-AUDIT.py ->
# scripts/ -> the repository root. It was hardcoded to one seat's checkout until 2026-10-10,
# which is why the census behind the inventory's rows could not be re-run by a successor.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GO = os.path.join(ROOT, "agenthub_go")
INV = os.path.join(ROOT, "ai_docs", "api-integration", "surface-inventory.md")

ROW = re.compile(r'^(?P<lead>\|\s*(?:GET|POST|PUT|PATCH|DELETE)\s*\|\s*`[^`]+`\s*\|\s*[^|]+?\s*\|\s*`)(?P<file>[^`]+):(?P<num>\d+)(?P<tail>`\s*\|\s*)$')
PARSE = re.compile(r'^\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*`([^`]+):(\d+)`\s*\|\s*$')
REG = re.compile(r'(?:HandleFunc|\.Handle)\(\s*([^,]+),')
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")


def index_by_basename():
    idx = {}
    for dp, _dn, fns in os.walk(GO):
        for fn in fns:
            if fn.endswith(".go"):
                idx.setdefault(fn, []).append(os.path.join(dp, fn))
    return idx


def resolve_file(rel, idx):
    p = os.path.join(GO, rel)
    if os.path.exists(p):
        return p
    c = idx.get(os.path.basename(rel), [])
    pref = [x for x in c if "/httpapp/" in x] or c
    return pref[0] if pref else None


def norm(route):
    """Normalise the path marker only. The trailing slash is KEPT: `"GET "+base` and
    `"GET "+base+"/"` are two different registrations, and stripping the slash makes them
    indistinguishable - which reported two correct citations as stale.

    AND THE `{$}` MARKER IS DROPPED WITHOUT ITS PRECEDING SLASH, which is the second form of the
    same mistake: the pattern `/api/v2/branches/{$}` MATCHES THE PATH `/api/v2/branches/`, because
    the slash before the marker is part of the literal (measured against the mux itself: POST to
    `/api/v2/branches/` reaches the handler with that pattern, while the bare `/api/v2/branches`
    is a 301 REDIRECT and never reaches it). Removing `/{$}` produced the redirect form, which made
    this tool report a correct document as stale."""
    return route.replace("{$}", "")


def registrations(path):
    """Every registration in the file as (line, method, resolved_route) — base resolved lexically."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    out, bases = [], {}
    for i, L in enumerate(lines, 1):
        mb = re.search(r'\b(\w*base\w*)\s*:?=\s*"([^"]+)"', L)
        if mb:
            bases[mb.group(1)] = (i, mb.group(2))       # nearest preceding wins
        m = REG.search(L)
        if not m:
            continue
        expr = m.group(1)
        method = next((x for x in METHODS if expr.lstrip('"').startswith(x + " ")), None)
        if not method:
            continue
        expr = expr.lstrip('"')                          # the opening quote of the first fragment
        if expr.endswith('"'):
            expr = expr[:-1]
        parts, cur, route_ok = expr.split("+"), "", True
        for part in parts:
            t = part.strip()
            if t in bases:                               # a base const declared above
                cur += bases[t][1]
            elif t:                                      # the registration's quoted text
                cur += t.strip('"')
        if route_ok:
            out.append((i, method, cur[len(method):].strip()))  # drop the "POST " prefix
    return out


def true_line(path, method, route):
    if not path:
        return None, "no file"
    regs = registrations(path)
    target = (method, norm(route))
    for i, m, r in regs:                                 # 1. resolved route, exact
        if (m, norm(r)) == target:
            return i, "resolved"
    for i, m, r in regs:                                 # 2. last segment agrees: verify by hand
        if m == method and route.strip("/") and route.strip("/").split("/")[-1] in r:
            return i, "loose"
    return None, "no match"


def audit(path, verbose=True):
    """Resolve every citation in `path`. Returns the parsed rows plus stale/unresolved sets."""
    idx = index_by_basename()
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines(keepends=True)

    rows = []
    for n, ln in enumerate(lines, 1):
        m = PARSE.match(ln.rstrip("\n"))
        if m:
            rows.append(dict(inv=n, method=m.group(1), route=m.group(2), file=m.group(4),
                             cited=int(m.group(5)), path=resolve_file(m.group(4), idx)))

    stale, unresolved = [], []
    for r in rows:
        real, how = true_line(r["path"], r["method"], r["route"])
        if real is None:
            unresolved.append((r, how))
        elif real != r["cited"]:
            stale.append((r, real, how))

    if verbose:
        print(f"rows {len(rows)}  stale {len(stale)}  unresolved {len(unresolved)}")
        for r, real, how in stale:
            print(f'  inv:{r["inv"]:>4} {r["method"]:6} {r["route"][:46]:<46} {r["file"]}: {r["cited"]:>4} -> {real:>4} [{how}]')
        for r, how in unresolved:
            print(f'  UNRESOLVED inv:{r["inv"]} {r["route"]} ({how}) — check by hand')
    return dict(lines=lines, rows=rows, stale=stale, unresolved=unresolved)


# THE MARKERS A GATE LEAVES BEHIND, so `--write` can refuse instead of editing a tree nobody is
# reading. `CI` is set by every CI runner worth the name and by the agent shells in this fleet,
# which is why the refusal names the marker it found and prints the explicit form a human uses.
# The PRE_COMMIT_* family is what pre-commit sets for the hook it runs, and pre-commit is what
# executes this repository's hooks: it also rewinds the whole worktree to the index while a hook
# is up, so a rewrite there would edit a tree whose content is not what the caller sees.
GATE_MARKERS = (
    "CI",
    "PRE_COMMIT_HOME",
    "PRE_COMMIT_ORIGIN",
    "PRE_COMMIT_SOURCE",
    "PRE_COMMIT_FROM_REF",
    "PRE_COMMIT_TO_REF",
    "PRE_COMMIT_COMMIT_OBJECT_NAME",
    "PRE_COMMIT_COMMIT_MSG_SOURCE",
    "PRE_COMMIT_PRE_REBASE_UPSTREAM",
    "PRE_COMMIT_PRE_REBASE_BRANCH",
    "PRE_COMMIT_LOCAL_BRANCH",
    "PRE_COMMIT_REMOTE_BRANCH",
)


def gate_marker(env=None):
    """The first gate marker in `env`, as `NAME=value`, or None when no gate is up."""
    env = os.environ if env is None else env
    for name in GATE_MARKERS:
        if env.get(name):
            return f"{name}={env[name]}"
    return None


def main():
    if "--self-test" in sys.argv:
        # THE RULE, APPLIED TO THIS INSTRUMENT: a check that cannot be shown to fail is not a
        # check, and this one exists because a citation that has rotted looks exactly like a
        # live one. So perturb ONE citation in a COPY, by a delta no real drift would produce
        # by accident, and require the audit to name that exact row - and only it.
        import tempfile
        src = open(INV, encoding="utf-8").read().splitlines(keepends=True)
        target = next((n for n, ln in enumerate(src, 1) if PARSE.match(ln.rstrip("\n"))), None)
        if target is None:
            print("self-test: FAIL — no citation rows found to perturb")
            return 1
        m = PARSE.match(src[target - 1].rstrip("\n"))
        src[target - 1] = src[target - 1].replace(f"{m.group(4)}:{m.group(5)}",
                                                  f"{m.group(4)}:{int(m.group(5)) + 7}")
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
            fh.write("".join(src))
            tmp = fh.name
        # THE BASELINE IS MEASURED, NOT ASSUMED. The first version of this self-test demanded exactly
        # one stale row, so it FAILED the moment the document carried any real drift of its own - the
        # perturbation was fine and the precondition was wrong. What the self-test can assert without
        # assuming a clean document is the DELTA and the NAME: one more stale row than the unperturbed
        # run, and the perturbed line among them.
        baseline = len(audit(INV, verbose=False)["stale"])
        r = audit(tmp, verbose=False)
        named = [s for s in r["stale"] if s[0]["inv"] == target]
        ok = len(r["stale"]) == baseline + 1 and len(named) == 1
        print(f"self-test: perturbed the citation on line {target} by +7 -> {len(r['stale'])} stale reported against a "
              f"baseline of {baseline}, the perturbed row {'named' if named else 'NOT named'} ({'PASS' if ok else 'FAIL'})")
        os.unlink(tmp)
        return 0 if ok else 1

    argv = list(sys.argv[1:])
    unknown = [a for a in argv if a not in ("--write",)]
    if unknown:
        print(f"unknown argument(s): {' '.join(unknown)} - the modes are the default check, "
              f"--self-test and --write, and nothing else")
        return 2
    write = "--write" in argv

    result = audit(INV)
    if not write:
        # THE GATE'S MODE, AND THE ONLY ONE IT MAY RUN. It writes nothing and it is non-zero the
        # moment one row is stale or unresolved, so a gate that runs it can actually go red.
        return 1 if (result["stale"] or result["unresolved"]) else 0

    marker = gate_marker()
    if marker:
        print(f"refusing --write: a gate marker is set ({marker}). A rewrite inside a gate edits a "
              f"tree whose reader is not this caller, and a check that repairs what it measures "
              f"reports clean by construction. A human in a shell where CI is set for other reasons "
              f"says so explicitly: CI= python3 scripts/CITATION-AUDIT.py --write")
        return 2

    if not result["stale"]:
        print("rewrote 0 citations: nothing is stale")
        return 0

    lines, fixed, could_not = result["lines"], 0, []
    for r, real, _how in result["stale"]:
        i = r["inv"] - 1
        m = ROW.match(lines[i].rstrip("\n"))
        if not m:
            could_not.append(r["inv"])
            print(f"  cannot rewrite inv:{r['inv']} (row shape changed)")
            continue
        lines[i] = m.group("lead") + m.group("file") + ":" + str(real) + m.group("tail") + "\n"
        fixed += 1
    with open(INV, "w", encoding="utf-8") as fh:
        fh.write("".join(lines))
    print(f"rewrote {fixed} citations in {INV}")

    # AND IT VERIFIES ITS OWN WORK: "I rewrote them" is a claim about the writing, not about the
    # tree, so the checking pass is re-run and the exit code that comes back is the TREE's.
    after = audit(INV)
    if could_not or after["stale"] or after["unresolved"]:
        print(f"STILL NOT CLEAN after the rewrite: {len(after['stale'])} stale, "
              f"{len(after['unresolved'])} unresolved, {len(could_not)} row(s) unwritable")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
