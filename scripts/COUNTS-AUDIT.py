#!/usr/bin/env python3
"""COUNTS-AUDIT — re-derive every headline number the surface inventory states, and say which
ones the tree no longer supports.

WHY THIS EXISTS. Three findings in one evening were the same shape, all in one document:
the httpapp registration count was TWO SHORT, §2.1 said `getMCPToolsList` appends THREE
schemas where the code appends FOUR, and §3 said 38 registered tables where the tree has 39.
**A NUMBER NOBODY RE-RAN WHEN A THING WAS ADDED** — a route landed and the count did not move,
a fourth schema was appended and the prose kept three, a table was registered and the section
that names its route never listed it. Nothing was false about the sentences; each was simply
never re-derived against the tree it describes.

This is the READING half of that pair and it is deliberately the weak one: a count that is
re-derived cannot be wrong about the tree, but a count that is EXPECTED here can still be
wrong about the DOCUMENT — if somebody edits the document's number and not this file, this
script reports a difference and a human decides which side moved. That is the correct split:
the script refuses to guess which of the two is authoritative.

A GATE MAY RUN THIS AS-IS. It has no write mode at all, by design: a check that repairs what
it measures reports clean by construction and can never fail (the lead's rule, 2026-10-06).
`CITATION-AUDIT.py` beside it carries the rewriting mode and MUST NOT be run inside a gate.

USAGE:  python3 scripts/COUNTS-AUDIT.py              # exits non-zero if any number differs
        python3 scripts/COUNTS-AUDIT.py --self-test  # perturb an expectation; require it to notice
"""
import os, re, subprocess, sys

# The repository root, derived from this file's own location: the instrument is TRACKED now, so it
# cannot carry one seat's absolute path. scripts/COUNTS-AUDIT.py -> scripts/ -> the repository root.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GO = f"{ROOT}/agenthub_go"

# The numbers as the surface inventory states them. Each entry names the instrument that
# re-derives it, because a number without its instrument is the failure this file exists for.
EXPECTED = {
    "httpapp route registrations": 123,     # grep -rn 'mux.HandleFunc(' fastmcp/server/httpapp, minus _test.go
                                            #   124 -> 125: O1a's GET /{id}/events route landed and THIS expectation
                                            #     never moved, so the audit was already red before the change below.
                                            #   125 -> 123: e6829b32 removed the two always-500 task routes, and the
                                            #     inventory paragraph records the same 125 -> 123. Re-derived, not
                                            #     adjusted: git grep -c 'mux.HandleFunc(' over that directory gives
                                            #     125 at 1a1ae32c and 88d27758, and 123 at HEAD.
    "auth route registrations": 20,         # same pattern, fastmcp/auth/{interface,api}
    "published MCP tools": 10,              # six from ToolDefinitions() + four appended in mcp_routes.go
    "dispatch-only MCP names": 2,           # get_mcp_status, check_session_health
    "core tables": 20,                      # depth-1 entries of database.Tables in models.go
    "auth tables": 3,                       # two in models_auth.go, one in email_token_repository.go
    "seat tables": 14,                      # depth-1 entries of seatDatabaseTables
    "team tables": 2,                       # depth-1 entries of teamManagementDatabaseTables
    "registered tables total": 39,          # 20 + 3 + 14 + 2
    "ProductionTables": 6,                  # declared, never appended
    "SQL CREATE TABLE statements": 16,      # ^CREATE TABLE IF NOT EXISTS in seat_management_postgresql.sql
}


# The document side. THE COLUMN THAT USED TO LIE: `document` in the report printed the value of
# EXPECTED, i.e. this file's memory, so "all matching" was read as "every count in the document is
# right". It never was. Each entry below is an anchored reading of surface-inventory.md itself, and
# a key with no unambiguous anchor prints "-" and is NOT compared, which is the honest half.
DOC = f"{ROOT}/ai_docs/api-integration/surface-inventory.md"
DOC_ANCHORS = {
    # "-> **143** (httpapp 123, auth 20)" - S1's Reproduce line
    "httpapp route registrations":    (r"\(httpapp (\d+), auth \d+\)", 1),
    "auth route registrations":       (r"\(httpapp \d+, auth (\d+)\)", 1),
    # "emitted **143 routes, 10 tools**" - S1's generator line
    "published MCP tools":            (r"emitted \*\*\d+ routes, (\d+) tools\*\*", 1),
    # "20 (core) + 3 (auth) + **14** (seat) + 2 (team) = **39 tables**" - S3.5
    "seat tables":                    (r"\+ \*\*(\d+)\*\* \(seat\)", 1),
    "registered tables total":        (r"\(team\) = \*\*(\d+) tables\*\*", 1),
    # "Plus `ProductionTables`: **6** tables declared but not registered"
    "ProductionTables":               (r"`ProductionTables`: \*\*(\d+)\*\* tables", 1),
    # The document states BOTH 17 and 16 in one sentence: the unanchored `grep -c` counts the file
    # header's COMMENT, the anchored `-cE '^...'` counts statements. My first anchor took the 17 and
    # reported the document wrong - the report was right and the anchor was wrong. Anchor on the
    # anchored form, since 16 is what the audit itself measures and what the row means.
    "SQL CREATE TABLE statements":    (r"-cE '\^CREATE TABLE IF NOT EXISTS'[^\n]{0,40}?\*\*(\d+)\*\*", 1),
    # core/auth are stated inside the S3.5 sentence but not as their own bolded figures
    "core tables":                    (r"runtime: (\d+) \(core\)", 1),
    "auth tables":                    (r"\(core\) \+ (\d+) \(auth\)", 1),
    "team tables":                    (r"\) \+ (\d+) \(team\)", 1),
    "dispatch-only MCP names":        None,   # the document states no such figure
}


def read_document():
    """The figures surface-inventory.md itself states, by anchor. Returns {key: int} for the
    anchored ones only - absence is reported, never guessed."""
    try:
        text = open(DOC, encoding="utf-8").read()
    except OSError as e:
        return {"__error__": str(e)}
    out = {}
    for key, anchor in DOC_ANCHORS.items():
        if not anchor:
            continue
        found = re.search(anchor[0], text)
        if found:
            out[key] = int(found.group(anchor[1]))
    return out


def fenced_count_lines():
    """Counts stated INSIDE fenced blocks. This audit does not verify these by re-running them -
    it cannot - but it CAN compare a fenced figure against the figure it anchors from the same
    document, and that is what caught Appendix A:611 sitting at 121+20=141 while S1 said 143.
    A contradiction FAILS unless the line qualifies itself as historical, because a line that
    quotes a superseded value on purpose ("read 121 ... and was stale") is a correct line.
    """
    try:
        lines = open(DOC, encoding="utf-8").read().splitlines()
    except OSError:
        return []
    hits, fence = [], False
    # Either order, and the mount nouns too. The line that started this row reads
    # "# Counts: 121 httpapp + 20 auth = 141": the noun follows the number in one half and precedes
    # it in the other, and the total is only implied by "121 + 20 = 141".
    noun = re.compile(
        r"\b(\d{2,})\b[^\n]{0,40}?\b(registrations|routes|tables|tools|names|statements|httpapp|auth)\b"
        r"|\b(registrations|routes|tables|tools|names|statements|httpapp|auth)\b[^\n]{0,40}?\b(\d{2,})\b",
        re.I)
    arithmetic = re.compile(r"\b\d{2,}\b\s*[+=]\s*\b\d{2,}\b")
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence and (noun.search(line) or arithmetic.search(line)):
            hits.append((i, line.strip()[:100], line))
    return hits


# A fenced line's noun -> the key whose value it must not contradict.
FENCE_KEYS = {
    "httpapp": "httpapp route registrations",
    "auth": "auth route registrations",
    "tools": "published MCP tools",
    "routes": "httpapp route registrations",     # "143 routes, 10 tools" - the total, both halves
}
# A line that names itself as history is allowed to carry the superseded value.
HISTORICAL = re.compile(r"stale|superseded|no longer|was |read 1|snapshot|REMOVED|historical|formerly",
                        re.I)


def fenced_contradictions(stated):
    """[(lineno, noun, fenced_value, anchored_value, exempt)] for fenced figures that disagree
    with the figure anchored from the same document. This is the half that makes a seeded stale
    input fail instead of merely being printed."""
    out = []
    for lineno, _shown, raw in fenced_count_lines():
        exempt = bool(HISTORICAL.search(raw))
        for m in re.finditer(
                r"\b(\d{2,})\b[^\n]{0,30}?\b(httpapp|auth|tools|routes)\b"
                r"|\b(httpapp|auth|tools|routes)\b[^\n]{0,30}?\b(\d{2,})\b", raw, re.I):
            value = int(m.group(1) or m.group(4))
            word = (m.group(2) or m.group(3)).lower()
            key = FENCE_KEYS.get(word)
            if not key:
                continue
            anchored = stated.get(key, EXPECTED.get(key))
            if anchored is not None and value != anchored:
                out.append((lineno, word, value, anchored, exempt))
    return out


def sh(cmd, cwd=GO):
    p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return p.stdout.strip()


def counts():
    """Every measurement, each with the command or parse that produced it."""
    m = {}
    m["httpapp route registrations"] = int(sh(
        "grep -rn 'mux.HandleFunc(' --include='*.go' fastmcp/server/httpapp | grep -v _test.go | wc -l"))
    m["auth route registrations"] = int(sh(
        "grep -rn 'mux.HandleFunc(' --include='*.go' fastmcp/auth/interface fastmcp/auth/api | grep -v _test.go | wc -l"))

    # MCP tools: the ToolDefinitions() entries plus the schema blocks appended AFTER the loop.
    # THREE of the appended four carry a `"name": seatcontrollers.X` field, while the connection
    # tool is appended as a whole map (`tools = append(tools, connTool)`), so a name-field count
    # alone reports nine. The loop's own append names `def.Name` and is the sixth of the defs,
    # already counted — hence the +3+1 rather than a count of every `tools = append(`.
    defs = open(f"{GO}/fastmcp/task_management/interface/ddd_compliant_mcp_tools.go").read()
    mcp = open(f"{GO}/fastmcp/server/httpapp/mcp_routes.go").read()
    m["published MCP tools"] = len(re.findall(r'Name:\s*"manage_\w+"', defs)) \
        + len(re.findall(r'"name":\s*seatcontrollers\.\w+', mcp)) \
        + len(re.findall(r'tools = append\(tools, connTool\)', mcp))
    m["dispatch-only MCP names"] = len(re.findall(r'case "(get_mcp_status|check_session_health)"', mcp))

    def depth1_entries(path, start_regex):
        src = open(path).read().splitlines()
        start = next((i for i, L in enumerate(src) if re.search(start_regex, L)), None)
        if start is None:
            return 0
        depth, n, started = 0, 0, False
        for j in range(start, len(src)):
            L = src[j]
            if depth == 1 and re.search(r'\{Name:\s*"', L):
                n += 1
            depth += L.count("{") - L.count("}")
            started = started or "{" in L
            if started and depth <= 0 and j > start:
                break
        return n

    m["core tables"] = depth1_entries(f"{GO}/fastmcp/task_management/infrastructure/database/models.go",
                                      r'^var Tables\s*=\s*\[\]TableDef\{')
    m["seat tables"] = depth1_entries(f"{GO}/fastmcp/seat_management/infrastructure/database/seat_tables.go",
                                      r'^var seatDatabaseTables\s*=\s*\[\]taskdb\.TableDef\{')
    m["team tables"] = depth1_entries(f"{GO}/fastmcp/seat_management/infrastructure/database/team_tables.go",
                                      r'^var teamManagementDatabaseTables\s*=\s*\[\]taskdb\.TableDef\{')
    m["ProductionTables"] = depth1_entries(f"{GO}/fastmcp/task_management/infrastructure/database/models_prod.go",
                                           r'^var ProductionTables\s*=\s*\[\]TableDef\{')
    # Auth tables are counted the way the document counts them: named entries at depth 1 of
    # each registry literal (two in models_auth.go, one in email_token_repository.go).
    m["auth tables"] = depth1_entries(f"{GO}/fastmcp/auth/infrastructure/database/models_auth.go",
                                      r'^var authDatabaseTables\s*=\s*\[\]taskdb\.TableDef\{') + \
        depth1_entries(f"{GO}/fastmcp/auth/infrastructure/repositories/email_token_repository.go",
                       r'^var emailTokenDatabaseTables\s*=\s*\[\]database\.TableDef\{')
    m["registered tables total"] = m["core tables"] + m["auth tables"] + m["seat tables"] + m["team tables"]
    m["SQL CREATE TABLE statements"] = int(sh(
        "grep -cE '^CREATE TABLE IF NOT EXISTS' fastmcp/seat_management/infrastructure/schema/seat_management_postgresql.sql"))
    return m


def main():
    if "--doc" in sys.argv:
        # Point the reader at another copy. This exists so the audit can be SHOWN to fail on a
        # seeded stale input without editing the document anybody else reads - the demonstration
        # runs against a scratch copy and discards it.
        global DOC
        DOC = sys.argv[sys.argv.index("--doc") + 1]
    if "--self-test" in sys.argv:
        # THE RULE, APPLIED TO THIS INSTRUMENT: a check that cannot be shown to fail is not a
        # check. Perturb one expectation and require the audit to notice - a hand-edit of the
        # world that expects to be told, which is the only instrument that catches the class
        # this file exists for.
        key = next(iter(EXPECTED))
        real = EXPECTED[key]
        struck = counts()
        EXPECTED[key] = struck[key] + 1          # deliberately wrong by one
        try:
            rc_tree = main_report(quiet=True)
        finally:
            EXPECTED[key] = real
        # AND THE DOCUMENT HALF, because a column that cannot be shown to fail is the same fault
        # this file exists to catch: stand a wrong figure where the anchored reading lands, and
        # require the report to notice. Perturb the reader, not the document - the document is
        # shared and this audit still edits nothing.
        global read_document
        real_reader = read_document
        read_document = lambda: {k: (v + 1 if k == key else v) for k, v in real_reader().items()}
        try:
            rc_doc = main_report(quiet=True)
        finally:
            read_document = real_reader
        ok = rc_tree != 0 and rc_doc != 0
        print(f"self-test: perturbed '{key}' by +1 -> tree exit {rc_tree}, document exit {rc_doc} "
              f"({'PASS' if ok else 'FAIL: a check did not notice'})")
        return 0 if ok else 1

    return main_report()


def main_report(quiet=False):
    measured = counts()
    stated = read_document()
    fenced = fenced_count_lines()
    width = max(len(k) for k in EXPECTED)
    bad = 0
    doc_known = 0
    if not quiet:
        print(f"{'number':<{width}}  {'doc':>4}  {'expected':>8}  {'tree':>6}  verdict")
    for k, expected in EXPECTED.items():
        got = measured.get(k)
        doc = stated.get(k)
        if doc is not None:
            doc_known += 1
        tree_ok = got == expected
        doc_ok = doc is None or doc == expected
        bad += 0 if (tree_ok and doc_ok) else 1
        if quiet:
            continue
        why = []
        if not tree_ok:
            why.append(f"TREE has {got!r}, this file expects {expected}")
        if not doc_ok:
            why.append(f"DOCUMENT says {doc}, this file expects {expected}")
        if not why:
            why = ["matches" if doc is not None else "tree matches; document states no figure"]
        print(f"{k:<{width}}  {doc if doc is not None else '-':>4}  {expected:>8}  "
              f"{got if got is not None else '?':>6}  {'; '.join(why)}")
    if quiet:
        return 1 if bad else 0

    print()
    print("COVERAGE - what this audit reads, and what it does not")
    print(f"  READS     the tree, for all {len(EXPECTED)} quantities above, by the command named beside")
    print("            each in EXPECTED.")
    print(f"  READS     the DOCUMENT figure for {doc_known} of {len(EXPECTED)}, by anchored pattern over")
    print("            surface-inventory.md; '-' means the document states no figure for that key.")
    print("            This column used to print EXPECTED, i.e. this file's memory, which is how")
    print("            'all matching' came to be read as 'every count in the document is right'.")
    print("  DOES NOT  read any file other than surface-inventory.md.")
    print("  DOES NOT  check file:line citations - CITATION-AUDIT.py owns those.")
    if fenced:
        print(f"  READS     {len(fenced)} count line(s) INSIDE fenced blocks and cross-checks them against")
        print("            the anchored figures above. It does not re-run their commands, so a fenced")
        print("            line whose command would now return something else is caught only if its")
        print("            figure disagrees with an anchored one - which is how Appendix A:611 was")
        print("            found sitting at 121+20=141 while S1 said 143.")
        for lineno, text, _raw in fenced:
            print(f"              surface-inventory.md:{lineno}  {text}")
    else:
        print("  DOES NOT  find any count stated inside a fenced block (none matched this pattern).")
    contradicted = fenced_contradictions(stated)
    hard = [c for c in contradicted if not c[4]]
    bad += len({c[0] for c in hard})
    for lineno, word, value, anchored, exempt in contradicted:
        tag = "carries a historical qualifier - reported, not counted" if exempt else "CONTRADICTS - counted"
        print(f"  FENCED    line {lineno}: {word} reads {value}, the anchored figure is {anchored} ({tag})")
    if not contradicted:
        print("  FENCED    no fenced figure contradicts an anchored one.")
    print()
    if bad:
        print(f"{bad} row(s) differ. Decide which side moved - the tree, the document, or this file -")
        print("before editing any of them. This audit edits nothing.")
    else:
        print("all numbers re-derived and matching: the tree agrees with this file, and this file agrees")
        print("with every document figure it anchors, including the fenced lines it does not re-run.")
        print("That is not a claim that every count in the document is right - see COVERAGE above.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
