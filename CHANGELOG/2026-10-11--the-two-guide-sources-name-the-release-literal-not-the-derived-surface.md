## The two guide sources name the release literal, not the derived surface

### What changed
`scripts/team/4genthub/area-go-backend.txt:18` and `scripts/team/4genthub/project-4genthub.txt:1` told
every seat to "bump healthVersion in fastmcp/server/httpapp/http.go". That is the **derived** surface:
`agenthub_go/fastmcp/server/httpapp/http.go:160` reads `const healthVersion = config.ReleaseVersion`,
so the value a seat must move is the literal at `agenthub_go/fastmcp/config/version.go:25`. Both
sentences now say that, in the wording `scripts/team/4genthub/mission.md:21` already carries after
`47fe30b8`:

- `area-go-backend.txt:18`: "The release version in agenthub_go/fastmcp/config/version.go must be
  bumped in the same commit set so the deploy can be confirmed: healthVersion in
  fastmcp/server/httpapp/http.go derives from it and is what /health reports. Never deploy."
- `project-4genthub.txt:1`: keeps `SAFETY.` first and `Never git push …` intact — the Python test
  asserts both — and now reads "…and bump the release version in
  agenthub_go/fastmcp/config/version.go in the same commit set so the deploy can be confirmed:
  healthVersion in agenthub_go/fastmcp/server/httpapp/http.go derives from it and is what /health
  reports."

Why these files are the source and not only the cloud's copy: they are the room's declared
`instruction` modules (`scripts/team/4genthub/team.json:11,17`), so the cloud's rendered seat text is
published from them. The rendered copies that still carry the wrong sentence — the three
`guidance/role.md` files the lead measured (context-dev:80, reviewer:40, architect:78) and the lead's
own loaded context — are the cloud's to re-render, flagged back with this commit so one pass covers
both halves. Same two-file shape as `47fe30b8`.

### Verified
- The acceptance grep:
  `grep -n 'httpapp/http.go' scripts/team/4genthub/area-go-backend.txt scripts/team/4genthub/project-4genthub.txt`
  returns exactly two lines, each of them the explanatory clause "…derives from it and is what /health
  reports". No instruction to bump that file survives in either source.
- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` → **13 failed, 75 passed**, and
  none of the failures is about these files, measured rather than assumed: grepping both file names
  across `scripts/tests` returns only `test_team_definition.py` (its band table at :104-110 and the
  SAFETY case at :245-249), while the failing modules are `test_census_audits.py` (the audit
  instruments at this tip, since filed as row `qitem-20261011035411`), `test_seat_policy_commit_form.py`
  (5 of ten policy modules loaded), `test_team_roster.py` (declared vs live seats) and, inside
  `test_team_definition.py`, the `[4genthub-ab]` policy-path check and the `[4genthub-min]` band/file
  agreement. **That last one's own assertion text is the proof it is not this change:** it fails with
  `assert {'guide-e2e-dev'} == set()` — an instruction file in the room with no band — and no file name
  or band is touched here. The case that does read this file,
  `test_project_brief_starts_with_the_safety_rule`, **passes**.
- `go test -count=1 ./fastmcp/seat_management/domain/seedlibrary/` → `ok`; that suite reads the txt
  sources and pins the script-test command they must carry.
- This commit touches no Go file and no frontend file, so no build or package suite is affected.

### What this does NOT do
It does not re-render the cloud copies: those are published from these sources through the
seat-context channel, which is the lead's step, and they are flagged with this hash so the re-render
happens once rather than twice.

No test accompanies the wording, for the same reason `47fe30b8` carried none: pinning the sentence
itself is the source-text assertion the testing contract forbids. What the existing guards do check —
the script-test command each source must carry, and that `project-4genthub.txt` still opens with
`SAFETY.` and `Never git push` — they still check, and both were run above.

It leaves every command, band and line count in the two files unchanged: one sentence is replaced in
place in each.

Row: `qitem-20261011035000-4e1f4316c0b0c51d`, filed by the lead as the real successor to
`qitem-20261011010830`, which named three files and closed one.
