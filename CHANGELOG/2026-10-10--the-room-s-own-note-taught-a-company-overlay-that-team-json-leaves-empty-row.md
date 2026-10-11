## The room's own note taught a company overlay that `team.json` leaves empty (row `2458e090`)

### Fixed
- **`scripts/team/4genthub-min/NOTES.md:14` said `guide-common` "is carried by the **company overlay**", and `:58` said "The company overlay carries `guide-common` alone"** — false of their own room since `f8d3eaab` (`fix(team): the 4genthub-min room definition reads its guides from the shelf, carries the architect pair, and drops guide-common`). `team.json:200` reads `"company_overlay": []`, and `grep -rn guide-common scripts/team/` matches **no line of `team.json`** — only these two NOTES lines. A reader who trusted them would hunt an overlay that does not exist and miss the mechanism that actually delivers the text: `seedlibrary.go:45-64` `sharedModuleFiles` mounts `guide-common` on **every seat type**.
- **The same paragraph said "The nine `guide-<seat>` modules" where the room carries TEN** — `guide-architect` is the one the earlier count misses (`team.json` carries `guide-lead`, `guide-go-dev`, `guide-fe-dev`, `guide-web-dev`, `guide-skills-dev`, `guide-context-dev`, `guide-feedback-dev`, `guide-reviewer`, `guide-writer`, `guide-architect`).
- **Corrected in place and dated, not rewritten silently:** the two sites keep their sentences and gain a dated correction paragraph naming the commit, the line and the measurement — the shape this file already uses for its own corrections.
- **UNTOUCHED, and named here rather than re-pinned:** the "seven clean, three flagged" seat-type table (`:22-40`). Its basis is the OpenRig ledger's `resolved_spec_name` (measured 2026-10-08) and `team.json`'s `developer` for those three, both still true; re-pinning it would be the stale-instrument class rather than a fix.

### Verified
- **Re-measured rather than recalled** (HEAD `83c13f49`): `python3 -c "import json;d=json.load(open('scripts/team/4genthub-min/team.json'));print(len([m for m in d['modules'] if m['slug'].startswith('guide-')]), d['company_overlay'])"` → **`10 []`**; `grep -rn guide-common scripts/team/` → the two NOTES lines and nothing in `team.json`.
- **The delivered text is unaffected, and that was checked on disk rather than assumed:** the mechanism the note now names is the one on the seats — nine installed seat homes, every `AGENTS.md` opening with `## Working procedure (every seat)` under a `<!-- seat-hash: … -->` first line.
- **No test reads this file** (`grep -rn NOTES.md` over the test trees returns nothing), so nothing changed under `TEST-CHANGELOG.md`.
- Docs only: `git show --numstat` names `scripts/team/4genthub-min/NOTES.md` and `CHANGELOG.md`.

### Found by
- context-dev while closing the `f965d2b0` question; recorded as row `2458e090`, patched as a file for the writer's ground, and applied only after the lead re-verified the measurement independently.
