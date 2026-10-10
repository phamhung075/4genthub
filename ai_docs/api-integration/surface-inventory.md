# 4genthub Go server — authoritative surface inventory

**Status:** authoritative. Every entry below is derived from the Go source at
`agenthub_go/`, not from another document. Dates/HEAD: generated at
`c4ff8d4279971ce5794b9cdc3b469d363c7b19a3`.

**Update 2026-10-05 (NEXT_GEN D5, teams/sharing).** §1.20 and the two team rows of §3.3
were added and every count updated: registrations 132 -> **140**, runtime `Tables` 36 ->
**38**. This delta was generated on top of `b0a1f510`; the rest of the file is unchanged
from the `c4ff8d42` snapshot. **The registration figure has moved since it** — the seat-type
create route (`POST /api/v2/openrig/seat-types`) was added after that snapshot — **and no figure
is restated here: §1 owns the count, with its pattern and date**, because a second copy kept in
this header is a copy that rots on its own, which is exactly what this line had done.

**Scope:** the Go service (`agenthub_go`, `cmd/agenthub`) plus the auth route sets it
mounts. `agenthub-frontend` and `agenthub_main` (Python) are out of scope and were not
touched.

**How to read the route table.** Each row's `Registration` is the exact `file:line`
where the route is registered. Paths shown are the **resolved** paths: many
registrations compose the path from a `const base = "…"` declared in the same function,
so a naive `grep HandleFunc` prints `"POST "+base+"/"` instead of `/api/v2/projects/`.
**Resolve them with the generator rather than by hand:** `cd agenthub_go && go run ./cmd/apirefgen` follows each `RegisterRoutes` call into the package that owns it and prints `<n> routes, <n> tools`; pass `-out /tmp/apiref.ts` to read the resolved list without writing the frontend artefact. At `db9d2bc3` it emitted **143 routes, 10 tools**, independently matching this section's count and resolving the function-scoped bases above (e.g. `/api/v2/tasks/{id}/events`). Writing a regex for this is how a reader reinvents the bug this paragraph describes — three such attempts on 2026-10-08 produced junk path keys while reporting plausible counts.
The commands used and the full registration dump are in the acceptance appendix.

**Reproduce:** `cd agenthub_go && grep -rn "mux\.HandleFunc(" --include='*.go' --exclude='*_test.go' fastmcp/server/httpapp fastmcp/auth | wc -l` -> **145** (httpapp 125, auth 20), re-run at `42de79c2`; the same command returned **146** (httpapp 126) at `6cfd56ab` before `e5ecff63` removed the two machine-token routes, and **145** (httpapp 125) before `e6829b32` removed the two always-500 task routes. *`rg` is NOT installed in this environment, so the earlier `rg -n` form could not run here, and it also counted `*_test.go` registrations — 125 at `db9d2bc3` rather than that pass's no-tests **123**; the tests-inclusive count for `httpapp` is now the number the no-tests figure used to be, which is how this line rots silently if it is quoted without its date.* The command above is the one that produced the number.*

**RE-RUN 2026-10-10 (writer seat) at HEAD `ab8ff69f`: the command above returns the same **144** (httpapp 124, auth 20), `go run ./cmd/apirefgen` independently wrote `144 routes, 10 tools`, and every one of the 124 `httpapp` registrations carries a citation in §1 within three lines — a COVERAGE check only, not a row-by-row re-resolution, so the §1 rows keep the dates their own passes recorded.**

---

## 1. Mounted routes

**Counts (DATED — carry the date and the pattern, per the counting rule).** **RE-MEASURED 2026-10-08 by go-dev, after the owner ruled both always-500 task routes removed: the `httpapp` figure falls `125 -> 123`, exactly the two removed registrations (`GET /api/v2/tasks/stats/summary` in `task_routes.go` and `GET /api/tasks/{task_id}` in `routes_mount.go`), under the same pattern and scope stated below. The auth half is unchanged at 20, so the total falls `145 -> 143`. The two rows are struck from the tables in this file, and the task-route line references below are renumbered by the same four-line deletion.** **CORRECTED 2026-10-06 (docs duty pass 3): the figure this paragraph has carried since it was written was TWO SHORT. The same pattern returns **125** registrations in `httpapp` + **20** in `fastmcp/auth/{interface,api}` = **145 total.** **RE-MEASURED 2026-10-08 at HEAD `88d27758`, with the control that makes it a drift figure rather than a preference:** **the identical pattern run at `6dc06203` returns 124 — the previous figure, REPRODUCED — and HEAD returns 125: exactly ONE registration was added, and it is named here.** *The addition is `GET /api/v2/tasks/{id}/events` (`task_routes.go:107`), the task-event ledger's read route, which is the `O1a` board row and the only `mux.HandleFunc(` line the two commits differ by `+1` on.* The auth half is unchanged at 20. **Pattern and scope, stated because the previous Reproduce line used a WIDER scope than the figure: non-test `.go` files under `fastmcp/server/httpapp` and `fastmcp/auth`.** AND THE TREE HAD NOT MOVED — the check that makes this a documentation shortfall rather than drift: the identical pattern run at this file's own last commit (**`6dc06203`**) already returns **124**, with **0 registration lines added or removed** between that commit and the tip (compare the `mux.HandleFunc(` line sets). **The two missing registrations are the friction channel's**, now documented in **§1.21** (`seat_feedback_mount.go:73`, `:76`) — which is also why the earlier **122** figure and the sentence built on it (`the 2026-10-05 figure below plus PUT /api/v2/openrig/rooms/{room}/team`) do not close arithmetically.** The earlier dated figures below are kept as the snapshots they are and were **not** re-derived in this pass.** **THESE COUNTS ARE RE-DERIVABLE IN ONE COMMAND, WHICH IS THE POINT OF THEM BEING NUMBERS AT ALL: `scripts/COUNTS-AUDIT.py`, **tracked in this repository since 2026-10-09 — before that it lived at `/home/daihu/.openrig/agenthub-seats/4genthub-min/COUNTS-AUDIT.py`, outside the worktree, so a seat could run it and CI could not**, re-runs every headline figure this document states — the two registration counts, the tool counts, the table counts, the 39 total and the SQL statement count — and exits non-zero when any of them differs from the tree. It is read-only by construction (no `--write` at all), so a gate may run it as it stands. **Both halves of it have been seen to work: it exits 0 on the tree it currently describes, and `python3 COUNTS-AUDIT.py --self-test` perturbs one expectation by one and REQUIRES the audit to notice — that is the control, because a checker never seen to fail is the same object as no checker at all. It was in fact RED before `e6829b32`: its `httpapp` expectation still read 124 while the tree had moved to 125 when `O1a` added `GET /{id}/events`, so the number it was one behind on was found by running it, not by reading it. The expectation now reads 123, which is what both the tree and this paragraph state.** At HEAD **2026-10-06** *(as this paragraph was first written)*, the same pattern gave **122** registrations in `httpapp` + **20** in `fastmcp/auth/{interface,api}` = **142 total**: the 2026-10-05 figure below plus `PUT /api/v2/openrig/rooms/{room}/team` (the D5 room-sharing route, `seat_admin_mount.go:301`). At HEAD **2026-10-05**, the pattern `grep -rn 'mux.HandleFunc(' --include='*.go' fastmcp/server/httpapp | grep -v _test.go` gives **121** registrations across 15 files, plus **20** in `fastmcp/auth/{interface,api}` = **141 total registrations**. The earlier figure — **120** in `httpapp` + 20 = **140 total** — was the snapshot at `c4ff8d42`, before the seat-type create route (`POST /api/v2/openrig/seat-types`, `seat_admin_mount.go:307` today) was added; the two counts differ by that one route, not by a wrong method. No routes are registered outside those packages (`grep -rn 'HandleFunc(' cmd/` → 0 matches; the process only calls `app.Handler()` at `cmd/agenthub/main.go:52`).

**The figures in this paragraph, and every headline count in this document, are re-derived by `scripts/COUNTS-AUDIT.py` — read-only, non-zero on any difference, safe to run in a gate. This is the pointer §3.5 refers to; it did not exist there until 2026-10-09, so that cross-reference was false when it was written. THE §1 `file:line` CITATIONS ARE RE-DERIVED THE SAME WAY BY `scripts/CITATION-AUDIT.py`, tracked beside it since 2026-10-10 (before that it was seat-local, and the pass records below that name a `~/.openrig/agenthub-seats/<seat>/` path are those of the runs made before the move): its default mode writes nothing and exits non-zero on any stale or unresolved row, and its `--write` mode is explicit and refused while a gate marker is set. **THE §3 TABLE ANCHORS ARE RE-DERIVED IN THE SAME WAY BY `scripts/S3-REDERIVE.py`**, tracked beside the other two since 2026-10-10 for the same reason they are (it was seat-local before that): read-only, `git show` only, non-zero on ANY anchor that is not fresh, and it carries a `--self-test` that perturbs one anchor in a copy and must name it.**

**RE-MEASURED 2026-10-09 at `5f405350`, by the writer seat, with both instruments RE-RUN rather than quoted.** The route total is **143** and the MCP tool count is **10**, emitted by the generator itself: `cd agenthub_go && go run ./cmd/apirefgen -out /tmp/apiref-final.ts` -> `wrote /tmp/apiref-final.ts: 143 routes, 10 tools` (the `-out` flag is what keeps the frontend artefact untouched while reading the resolved list). Independently, `python3 scripts/COUNTS-AUDIT.py` exits **0** with all eleven headline rows matching the tree and the document: `httpapp` route registrations **123**, `auth` registrations **20**, published MCP tools **10**, dispatch-only MCP names **2** (the document states no figure for that one), core tables **20** + auth **3** + seat **14** + team **2** = **39** registered tables, `ProductionTables` **6**, and **16** `CREATE TABLE` statements. **Two independent instruments agree, and every figure is UNCHANGED from the 2026-10-08 reading above: no count moved, only the date did** — which is what this re-run establishes and what a reader could not assume, since a count nobody has re-run is not a fact. The command and the commit are half of the count, so both are stated here rather than the number alone.

**RE-MEASURED 2026-10-10 at `6cfd56ab` (writer seat, docs duty pass 6), BOTH INSTRUMENTS RE-RUN RATHER THAN QUOTED — and the reason they were re-run is that they had gone red.** `cd agenthub_go && go run ./cmd/apirefgen -out /tmp/apiref-check.ts` -> `wrote /tmp/apiref-check.ts: **146 routes, 10 tools**`; `python3 scripts/COUNTS-AUDIT.py` -> **exit 1**, on four rows: `httpapp` registrations **126**, seat tables **16**, registered tables **41**, SQL `CREATE TABLE` statements **18** — the figures this pass lands, where the paragraph above stood at 143 / 123 / 14 / 39 / 16. **The tool count is unchanged at 10**, and `auth` at 20. **WHAT MOVED, NAMED RATHER THAN COUNTED: three routes and two tables, from one feature that landed after the 2026-10-09 reading.** The routes are the seat-message family — `POST|GET /api/v2/openrig/rooms/{room}/seats/{seat}/messages` and `POST .../messages/{id}/ack` (`seat_mount.go:228`, `:235`, `:238`, now §1.17) — and the tables are `seat_messages` (`seat_tables.go:377`, DDL `:306`) and `machine_edges` (`seat_tables.go:316`, DDL `:371`), now §3.3. **NOTHING WAS REMOVED: zero documented routes are unmounted at this commit, so the direction of this drift is UNDER-COUNTING rather than a false claim** — a reader who consults this inventory and does not find the seat-message family concludes the family does not exist, which is why an under-count is worth a pass rather than a note. **And a count is only evidence with its instrument attached:** the same two commands here, the commit above, and the three named routes are the whole basis of the numbers in the paragraph.

**RE-RESOLVED 2026-10-10 at `6cfd56ab` (writer seat, docs duty pass 6) — and this pass found what the previous one did not, because a feature landed in files §1.6 and §1.17 cite.** `python3 ~/.openrig/agenthub-seats/4genthub-min/CITATION-AUDIT.py` (checking mode) reported **`rows 143  stale 81  unresolved 0`**: no row pointed at a file that had stopped carrying its method+route — so no row is a false claim about the tree — and **81 line numbers had drifted**, which is exactly the pointer-rot the method above predicts, and the reason the check is a command rather than a habit. **The rewrite was then run OUTSIDE any gate, as that tool's own header requires:** a check that repairs what it measures reports clean BY CONSTRUCTION and can never fail, so a gate runs the checking mode and the rewrite is a deliberate act, run here after reading the report. **Re-read in checking mode afterwards: `rows 146  stale 0  unresolved 0`** — 146 rather than 143 because this pass's three seat-message rows (§1.17) are inside that count. **Those three rows were written with their registration lines taken from the source rather than from the rewriter**, so the check that follows is a measurement of the rewrite and not its echo.

Where a handler is an inline closure wrapping a `routes.*` function, the handler column
names the function that actually performs the work; the registration line is the mount.

**RE-MEASURED 2026-10-10 at `a7990665` (go-dev, at the `e5ecff63` gate), BOTH INSTRUMENTS RE-RUN RATHER THAN QUOTED.** `cd agenthub_go && go run ./cmd/apirefgen -out /tmp/apiref-check.ts` -> `wrote /tmp/apiref-check.ts: **144 routes, 10 tools**`; `python3 scripts/COUNTS-AUDIT.py` -> **exit 1, but on its own memory rather than on this document or the tree**: the tree reads `httpapp` registrations **124**, seat tables **15**, registered tables **40** and SQL `CREATE TABLE` statements **17**, and this document now states those four, while **the instrument and this document now AGREE on all four — `python3 scripts/COUNTS-AUDIT.py` exits 0 with every row matching, because the writer's row `0a94db94` retuned `EXPECTED` to the tree's figures in the same window (`a691276c`) — and this paragraph records the split as it stood rather than leaving a red instrument unexplained.** **WHAT MOVED, NAMED RATHER THAN COUNTED: ONE COMMIT, `e5ecff63` ("one credential: AGENTHUB_TOKEN replaces the per-machine token"), which removed the two `POST`/`DELETE /api/v2/openrig/machines` registrations and the `machine_tokens` table.** The tool count is unchanged at 10 and `auth` at 20, so the route total is **144 = 124 + 20**.

**RE-RESOLVED 2026-10-10 at `a7990665` (go-dev, at the same gate), because that commit edited five mount files and these tables cite lines inside them.** `python3 ~/.openrig/agenthub-seats/4genthub-min/CITATION-AUDIT.py` (checking mode) reported **`rows 144  stale 59  unresolved 0`**: every row still points at a file carrying its method+route, 59 line numbers had drifted (`routes_mount.go` 44, `app.go` 6, `seat_mount.go` 5, `seat_status_mount.go` 2, `seat_feedback_mount.go` 2), and **the rewrite was then run OUTSIDE any gate, as that tool's own header requires** (`--write`), after which the same command reports `rows 144  stale 0  unresolved 0`. **IT THEN REPORTED 3 STALE AGAIN, AND THE CAUSE WAS THIS PASS ITSELF:** the fix of the `seat_mount.go:223` comment added one line to that file, so the three rows citing registrations below it moved by +1 (`227 -> 228` and its neighbours); a second `--write` closes it and the check reads `stale 0`. **That is the pointer-rot the method predicts, caught on the pass that caused it rather than by the next reader.** **NOT COVERED, SAID PLAINLY RATHER THAN IMPLIED: neither instrument resolves §3's table rows, so §3 was not re-derived as a whole — the two rows measured in this pass (`seat_messages` and `machine_edges`, both `e5ecff63` casualties) are corrected and the rest stand unverified rather than implied clean.**

**RE-MEASURED 2026-10-10 at `42de79c2` (writer seat, docs duty pass 7), BOTH INSTRUMENTS RE-RUN RATHER THAN QUOTED — and this pass found a class the count instruments cannot see.** Route total **145** = **125 `httpapp`** + **20 `auth`**, emitted by the generator itself (`cd agenthub_go && go run ./cmd/apirefgen -out /tmp/apiref-final.ts` -> `wrote /tmp/apiref-final.ts: 145 routes, 10 tools`); MCP tools unchanged at **10**. **WHAT MOVED, NAMED:** one registration, `PUT /api/v2/openrig/rooms/{room}/seats/{seat}/pin` (`seat_admin_mount.go:362`, handler `handleSetSeatPin`), from `42de79c2`. `python3 scripts/COUNTS-AUDIT.py` -> **exit 1 on one row**, `httpapp` registrations: the tree reads **125** while this document and that file's `EXPECTED` both said 124 — the tree moved, and both were retuned in this pass.

**THE FINDING THIS PASS ADDS: a route can be missing from the table while every count still looks right, and nothing in either instrument's output would say so.** §1 held **144 rows for 145 live registrations**. The check that finds it is a **set join**, not a count: extract every `| METHOD | \`path\` |` row of §1 and join it against the generator's own emitted route list — **144 rows, zero duplicates, zero rows claiming a route the server does not mount, and exactly one live route with no row** (the pin route above, now added in file order between `permission-policy` and `overlay`). Counts agree with each other by construction when a row is simply absent; only the join disagrees. Run it as: `go run ./cmd/apirefgen -out /tmp/api.ts` in `agenthub_go`, then match each §1 row's method+path against `/tmp/api.ts`.

**CITATIONS.** `python3 scripts/CITATION-AUDIT.py` (checking mode) -> **exit 1, `rows 145  stale 28  unresolved 0`** — no row pointed at a file that had stopped carrying its method+route, and 28 line numbers had drifted, all in the family `42de79c2` edited (`seat_admin_mount.go` +5..+8 below the insertion, `mcp_routes.go` +2). **The rewrite ran outside any gate, as that tool's header requires** (`CI= python3 scripts/CITATION-AUDIT.py --write` -> `rewrote 28 citations`, touching only this file), after which the same command reports **`rows 145  stale 0  unresolved 0`**, exit 0. The `CI=` prefix is the tool's own documented escape: this shell inherits `CI=true` for unrelated reasons and the guard reads that as a gate marker.

**CITATION RE-DERIVATION (2026-10-06, docs duty pass 3) — the `file:line` in every `§1.*` row was re-resolved against the tree rather than trusted.** The method: for each row, read the file's own `base` const, resolve the row's path, and match it to the registration that actually carries that method+path; then compare with the cited number. **21 of the 144 route rows cited a line that was no longer the registration** — `app.go` had drifted 10–11 lines and `seat_mount.go` 73, because **a `file:line` is a pointer that rots every time code is added above it, while the mount files that had not changed still matched exactly** (which is what distinguishes drift from a wrong method). All 21 now cite their registration line, and the check is repeatable: re-resolve, compare, report the set. **Scope: §1's route rows, §2's citations, §5's two quoted-report cites and §3's table citations were all re-derived in this pass (see §3.6 for the table half); §4's gone-list holds commands rather than citations and was NOT re-run.** **The audit is repeatable rather than a one-off: it is kept as `CITATION-AUDIT.py` beside the seat area, with the false-positive caveat in its docstring — its `loose` matches are hypotheses, and three of the first run's reports were exactly that.**

**RE-RESOLVED 2026-10-09 at `257a4ab1` (writer seat, docs pass 5) — ALL 143 ROWS of §1.1–§1.21 were re-resolved by the method above, ROW BY ROW, and NOT ONE had drifted: every cited line is still the registration that carries that row's method+path.** No part of §1 is excluded from that count — §1.16's 26 rows are inside the 143, so the whole of §1 stands re-derived at this commit. **Two controls make the pass a measurement rather than an impression.** (1) **Coverage**: the tables hold 143 rows and the counts hold `143 = 123 httpapp + 20 auth`, re-derived with the appendix's own commands (`grep -rn 'mux.HandleFunc(\|mux.Handle(' --include='*.go' fastmcp/server/httpapp | grep -v '_test.go' | wc -l` -> `123`; the auth half -> `20`). (2) **A registration that exists with no row is the class a row-by-row pass cannot see**, so each cited file's registration lines were counted against its rows: **all eighteen cited files balance exactly** — `routes_mount.go` 44/44, `seat_admin_mount.go` 26/26, `auth_endpoints.go` 10/10, `supabase_endpoints.go` 10/10, `team_mount.go` 8/8, `app.go` 7/7, `task_routes.go` 7/7, `subtask_routes.go` 6/6, `branch_routes.go` 5/5, `misc_mount.go` 4/4, `ws_mount.go` 3/3, and `machine_token_mount.go`, `mcp_routes.go`, `seat_feedback_mount.go`, `seat_mount.go`, `seat_status_mount.go`, `session_stream_routes.go` 2/2 each, `seat_rigspec_mount.go` 1/1. **The only non-test change under `httpapp/` or `auth/` since the 2026-10-08 pass is `e6829b32`, the removal of the two always-500 task routes — the change the counts paragraph above records, whose four-line deletion is why the task-route references below were renumbered** (`git log --oneline 88d27758..HEAD -- agenthub_go/fastmcp/server/httpapp agenthub_go/fastmcp/auth -- ':(exclude)*_test.go'` → one line; the window's only other Go edits are test files, `ff6fed10` and `c3f45214`). **That is why a pass run today returns zero where the 2026-10-06 pass found 21: no registration file was edited between the two passes, so no pointer could rot.** **What the pass did NOT establish: the routes' behaviour**, only that each row's pointer still resolves to the registration for its method+path; the §1.14 handler column keeps its documented convention (the mount registers a closure bound to a local, `create` / `list`, and the column names the `routes.*` function that closure calls).

**RE-RESOLVED 2026-10-10 at `1b5c52b3` (writer seat) — the TWELVE `### 1.x` header-line citations, which the preamble above lists as outside both instruments, were resolved one at a time.** **Three were stale and are repaired:** §1.13 `routes_mount.go:211 → :262` and §1.14 `:310 → :361`, both to the `const base = …` line of their own section — the convention §1.9–§1.11 already follow, where the cited line IS that const — and §1.15 `:389 → :440`, the `func mountTaskSummaryRoutes(…)` whose registrations are exactly the rows the section lists (`:442`–`:475`), where `:389` was a `}))` closing a *token* handler and so named the wrong family altogether. **Five were already exact:** §1.9/§1.10/§1.11 (`const base = …`) and §1.18/§1.19 (`RegisterRoutes`). **Four are left as they are, because their intent is not something the document fixes:** §1.2 `branch_routes.go:59`, §1.3 `task_routes.go:48`, §1.4 `subtask_routes.go:12` and §1.5 `session_stream_routes.go:12` each point into handler bodies in the file the header names (`branch_routes.go:59` is `if !result.Success() {`, `task_routes.go:48` is a struct field, `subtask_routes.go:12` is `type SubtaskController interface {` — the most plausible of the four — and `session_stream_routes.go:12` is a bare `)`), and no section states what that line should designate, so a change there would be a guess wearing a repair's clothes. **What this pass did NOT establish: that a header citation is meaningful.** Nine of the twelve name a line no stated convention defines, and no instrument reads any of them — the file name beside them carries the meaning, the line is vestigial in four cases and wrong in three until today.

Path convention for the Registration column: paths are relative to `agenthub_go/`; from
§1.2 on, the column gives the BASENAME (`branch_routes.go:61`) because the section header
already names the full file, while §1.1 and §1.6–§1.12 give the path from `agenthub_go/`.
Both forms point at the same kind of thing — the line that registers the route.

### 1.1 Server-level and `app.go`

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/health` | `handleHealth` | `fastmcp/server/httpapp/app.go:123` |
| POST | `/api/v2/projects/` | `routes.CreateProject` | `fastmcp/server/httpapp/app.go:146` |
| GET | `/api/v2/projects/` | `routes.ListProjects` | `fastmcp/server/httpapp/app.go:159` |
| GET | `/api/v2/projects/{id}` | `routes.GetProject` | `fastmcp/server/httpapp/app.go:167` |
| PUT | `/api/v2/projects/{id}` | `routes.UpdateProject` | `fastmcp/server/httpapp/app.go:175` |
| DELETE | `/api/v2/projects/{id}` | `routes.DeleteProject` | `fastmcp/server/httpapp/app.go:196` |
| POST | `/api/v2/projects/{id}/health-check` | `routes.ProjectHealthCheck` | `fastmcp/server/httpapp/app.go:204` |

**The project-creation contract, STATED rather than implied — `POST /api/v2/projects/` (the trailing slash is part of the route) accepts `application/x-www-form-urlencoded` ONLY.** `app.go:146` registers it and `:151` parses the body with `_ = r.ParseForm()`, then refuses a body with no `name` through the shared `missingForm(r, "name")` helper (`:152`; it validates presence via `r.PostForm.Has`, `http.go:132`, and the `422` is `writeMissing`, `http.go:124`), and only then reads the VALUE with `r.PostForm.Get("name")` / `Get("description")` at `:156`: **CITATIONS RE-RESOLVED 2026-10-09 — this clause read `:135`/`:137-144`, the same region eleven lines above; and the mechanism it named (the value read) is one half of the handler while the check that produces the `422` is the other, so the clause now states both.** **`name` is required and `description` is optional**, and neither a JSON body nor a multipart body is read at all. **A JSON or multipart request is therefore refused with the SAME `422` that reports `body.name` missing**, because `ParseForm` reads neither encoding — so the refusal names a **MISSING FIELD** rather than the **ENCODING**, which is why two independent callers concluded they had a payload problem when they had a content-type problem. The application itself sends exactly this shape (`agenthub-frontend/src/services/apiV2.ts:475` posts `name`/`description` with `Content-Type: application/x-www-form-urlencoded`, and its flow measures **200** end to end), so **the route is not wrong — it was merely unstated.** **THE REUSABLE HALF: A REFUSAL THAT NAMES THE WRONG CAUSE COSTS A CALLER THE SAME TIME AS A SILENT FAILURE** — the same family as the reason text that never reached the chip, the preview read that looked truncated, and the grep that looked absent from the wrong field; and this is that family's **cheapest instance to fix, because the fix is a documented contract rather than a change to the refusal.**

`App.Handler` (`app.go:120`; **re-resolved 2026-10-09, this read `:111`**) is the sole mux builder; it calls `mountRoutes`,
`mountWebSockets`, the five `mountSeat*`/`mountMachineToken` functions, `mountMiscRoutes`,
and the two auth `RegisterRoutes` methods.

### 1.2 Branches — base `/api/v2/branches` (`branch_routes.go:59`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/branches/{$}` | `routes.CreateBranch` | `branch_routes.go:61` |
| GET | `/api/v2/branches/{id}` | `routes.GetBranch` | `branch_routes.go:70` |
| DELETE | `/api/v2/branches/{id}` | `routes.DeleteBranch` | `branch_routes.go:74` |
| POST | `/api/v2/branches/project/{project_id}/summaries` | `routes.GetProjectBranchesWithTaskCounts` | `branch_routes.go:78` |
| POST | `/api/v2/branches/summaries/bulk` | `routes.GetBulkSummaries` | `branch_routes.go:82` |

### 1.3 Tasks — base `/api/v2/tasks` (`task_routes.go:48`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/tasks/` | `routes.CreateUserTask` | `task_routes.go:50` |
| GET | `/api/v2/tasks/` | `routes.ListUserTasks` | `task_routes.go:85` |
| GET | `/api/v2/tasks/{id}` | `routes.GetUserTask` | `task_routes.go:99` |
| GET | `/api/v2/tasks/{id}/events` | `routes.GetTaskEvents` | `task_routes.go:103` |
| PUT | `/api/v2/tasks/{id}` | `routes.UpdateUserTask` | `task_routes.go:113` |
| DELETE | `/api/v2/tasks/{id}` | `routes.DeleteUserTask` | `task_routes.go:136` |
| POST | `/api/v2/tasks/{id}/complete` | `routes.CompleteUserTask` | `task_routes.go:140` |

**DRIFT FOUND AND REPAIRED 2026-10-08 at HEAD `88d27758` (docs duty pass 4).** *Three rows in the table above cited a line that is no longer a registration (`PUT {id}` 107->117, `DELETE {id}` 130->140, `complete` 134->144) and one route had no row at all.* **The control that names the cause rather than assuming it: every moved row moved by EXACTLY +10, and the insertion that did it is the `GET /{id}/events` route — one registration plus its closure, added above them.** *So this is the rotted-pointer class the §1 citation pass predicted, reproduced on schedule, and the fix is a line number, not a re-reading of the table.* **Re-resolve a row by reading the file's own `base` const and matching the row's method+path to the registration that carries it — never by trusting the number.**

### 1.4 Subtasks — base `/api/v2/subtasks` (`subtask_routes.go:12`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/subtasks` | `routes.CreateSubtask` | `subtask_routes.go:14` |
| GET | `/api/v2/subtasks/task/{id}` | `routes.ListSubtasks` | `subtask_routes.go:28` |
| GET | `/api/v2/subtasks/{id}` | `routes.GetSubtask` | `subtask_routes.go:32` |
| PUT | `/api/v2/subtasks/{id}` | `routes.UpdateSubtask` | `subtask_routes.go:36` |
| DELETE | `/api/v2/subtasks/{id}` | `routes.DeleteSubtask` | `subtask_routes.go:49` |
| POST | `/api/v2/subtasks/{id}/complete` | `routes.CompleteSubtask` | `subtask_routes.go:53` |

### 1.5 Sessions — base `/api/v2/sessions` (`session_stream_routes.go:12`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/api/v2/sessions` | `routes.ListSessions` | `session_stream_routes.go:14` |
| GET | `/api/v2/sessions/{id}/events` | `routes.GetSessionEvents` | `session_stream_routes.go:19` |

### 1.6 MCP transport (`mcp_routes.go`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/mcp` | JSON-RPC dispatcher (`handleJSONRPC`) | `mcp_routes.go:76` |
| GET | `/mcp` | `mcpSSEHandler` (SSE) | `mcp_routes.go:141` |

### 1.7 WebSockets (`ws_mount.go`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/ws/realtime` | `handleRealtime` | `ws_mount.go:68` |
| GET | `/ws/connector` | `handleConnector` | `ws_mount.go:69` |
| GET | `/ws/sessions/{id}` | `handleSessionViewer` | `ws_mount.go:70` |

**DECLARED OUT OF SCOPE — THE THREE UNMOUNTED OLD-PROTOCOL WEBSOCKET ENDPOINTS (owner decision, 2026-10-06).** **The old-protocol surface served by `fastmcp/websocket/server.go` is NOT mounted on the live handler:** it registers **`/ws/{user_id}`** (`server.go:92`), **`/ws/health`** and **`/ws/stats`** (`server.go:93-94`) on **its own app**, and **nothing outside that package constructs it** (`NewWebSocketServer` has no non-test caller — the only imports of the package elsewhere are `wslib` for the `WebSocket` type, in `ws_mount.go:37` and `server/routes/websocket_routes.go:25`). **THE OWNER DECLARED THESE THREE OUT OF SCOPE RATHER THAN MOUNTING THEM, which is the honest closure of the parity claim: THE PORT IS COMPLETE FOR THE SURFACE IN USE, with `/ws/{user_id}`, `/ws/health` and `/ws/stats` DELIBERATELY EXCLUDED** — so nothing reads as though the old protocol is fully served. **AND IT IS A DECISION RATHER THAN AN OMISSION:** mounting them would have added endpoints **nothing consumes**, and **the owner chose the honest label over the tidier-looking port.**

### 1.8 MCP registration / metrics (`misc_mount.go`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/register` | `mcpRegistrationStore.register` | `misc_mount.go:63` |
| POST | `/unregister` | `mcpRegistrationStore.unregisterResponse` | `misc_mount.go:67` |
| GET | `/registrations` | `mcpRegistrationStore.listResponse` | `misc_mount.go:70` |
| GET | `/ws/metrics` | `handleWebSocketMetrics` | `misc_mount.go:73` |

### 1.9 Connections — base `/api/v2/connections` (`routes_mount.go:84`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/api/v2/connections/health` | `routes.HealthCheck` | `routes_mount.go:85` |
| GET | `/api/v2/connections/status` | `routes.ConnectionStatus` | `routes_mount.go:88` |

### 1.10 Alerts — base `/api/v1/alerts` (`routes_mount.go:97`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/api/v1/alerts/rules` | `routes.ListAlertRules` | `routes_mount.go:99` |
| POST | `/api/v1/alerts/rules` | `routes.CreateAlertRule` | `routes_mount.go:102` |
| PUT | `/api/v1/alerts/rules/{rule_id}` | `routes.UpdateAlertRule` | `routes_mount.go:110` |
| DELETE | `/api/v1/alerts/rules/{rule_id}` | `routes.DeleteAlertRule` | `routes_mount.go:118` |
| GET | `/api/v1/alerts/events` | `routes.ListAlertEvents` | `routes_mount.go:122` |
| POST | `/api/v1/alerts/events/{event_index}/acknowledge` | `routes.AcknowledgeAlert` | `routes_mount.go:125` |
| POST | `/api/v1/alerts/check-rules` | `routes.CheckAlertRules` | `routes_mount.go:134` |
| POST | `/api/v1/alerts/test-webhook` | `routes.TestWebhook` | `routes_mount.go:137` |

### 1.11 Performance — base `/api/v1/performance` (`routes_mount.go:150`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/api/v1/performance/metrics/overview` | `routes.GetPerformanceOverview` | `routes_mount.go:151` |
| GET | `/api/v1/performance/metrics/timeseries` | `routes.GetPerformanceTimeseries` | `routes_mount.go:155` |
| GET | `/api/v1/performance/metrics/alerts` | `routes.GetPerformanceAlerts` | `routes_mount.go:159` |
| POST | `/api/v1/performance/metrics/clear-cache` | `routes.ClearPerformanceCache` | `routes_mount.go:163` |

### 1.12 Broadcast

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/broadcast/notify` | `routes.TriggerBroadcast` | `routes_mount.go:206` |

### 1.13 Contexts — base `/api/v2/contexts` (`routes_mount.go:262`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/contexts/{level}` | `routes.CreateContext` | `routes_mount.go:264` |
| GET | `/api/v2/contexts/{level}/{context_id}` | `routes.GetContext` | `routes_mount.go:282` |
| PUT | `/api/v2/contexts/{level}/{context_id}` | `routes.UpdateContext` | `routes_mount.go:287` |
| DELETE | `/api/v2/contexts/{level}/{context_id}` | `routes.DeleteContext` | `routes_mount.go:300` |
| GET | `/api/v2/contexts/{level}/{context_id}/resolve` | `routes.ResolveContext` | `routes_mount.go:304` |
| POST | `/api/v2/contexts/{level}/{context_id}/delegate` | `routes.DelegateContext` | `routes_mount.go:308` |
| POST | `/api/v2/contexts/{level}/{context_id}/insights` | `routes.AddInsight` | `routes_mount.go:321` |
| POST | `/api/v2/contexts/{level}/{context_id}/progress` | `routes.AddProgress` | `routes_mount.go:335` |
| GET | `/api/v2/contexts/{level}/list` | `routes.ListContexts` | `routes_mount.go:344` |
| GET | `/api/v2/contexts/{level}/{context_id}/summary` | `routes.GetContextSummary` | `routes_mount.go:348` |

### 1.14 Tokens — base `/api/v2/tokens` (`routes_mount.go:361`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/tokens` | `routes.GenerateTokenHandler` | `routes_mount.go:371` |
| POST | `/api/v2/tokens/` | `routes.GenerateTokenHandler` | `routes_mount.go:372` |
| POST | `/api/v2/tokens/generate` | `routes.GenerateTokenHandler` | `routes_mount.go:373` |
| GET | `/api/v2/tokens` | `routes.ListTokens` | `routes_mount.go:379` |
| GET | `/api/v2/tokens/` | `routes.ListTokens` | `routes_mount.go:380` |
| GET | `/api/v2/tokens/legacy/tokens` | `routes.ListTokens` | `routes_mount.go:381` |
| GET | `/api/v2/tokens/health` | `routes.TokenServiceHealth` | `routes_mount.go:382` |
| GET | `/api/v2/tokens/{token_id}` | `routes.GetTokenDetails` | `routes_mount.go:386` |
| DELETE | `/api/v2/tokens/{token_id}` | `routes.DeleteToken` | `routes_mount.go:390` |
| PATCH | `/api/v2/tokens/{token_id}/revoke` | `routes.RevokeToken` | `routes_mount.go:394` |
| PATCH | `/api/v2/tokens/{token_id}/reactivate` | `routes.ReactivateToken` | `routes_mount.go:398` |
| POST | `/api/v2/tokens/{token_id}/rotate` | `routes.RotateToken` | `routes_mount.go:402` |
| POST | `/api/v2/tokens/validate` | `routes.ValidateTokenEndpoint` | `routes_mount.go:406` |
| POST | `/api/v2/tokens/cleanup` | `routes.CleanupExpiredTokens` | `routes_mount.go:414` |

### 1.15 Summary / remaining task routes (`routes_mount.go:440`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/tasks/summaries` | `routes.GetTaskSummaries` | `routes_mount.go:442` |
| GET | `/api/tasks/{task_id}/context/summary` | `routes.GetTaskContextSummary` | `routes_mount.go:457` |
| POST | `/api/subtasks/summaries` | `routes.GetTaskRouteSubtaskSummaries` | `routes_mount.go:463` |
| GET | `/api/performance/metrics` | `routes.GetPerformanceMetrics` | `routes_mount.go:472` |
| POST | `/api/v2/tasks/{task_id}/subtasks/summaries` | `routes.GetUserSubtaskSummaries` | `routes_mount.go:475` |

### 1.16 OpenRig seat management — admin (`seat_admin_mount.go`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/openrig/rooms` | `handleCreateRoom` | `seat_admin_mount.go:317` |
| GET | `/api/v2/openrig/rooms` | `handleListRooms` | `seat_admin_mount.go:320` |
| DELETE | `/api/v2/openrig/rooms/{room}` | `handleDeleteRoom` | `seat_admin_mount.go:323` |
| PUT | `/api/v2/openrig/rooms/{room}/team` | `handleSetRoomTeam` | `seat_admin_mount.go:326` |
| GET | `/api/v2/openrig/seat-types` | `handleListSeatTypes` | `seat_admin_mount.go:329` |
| POST | `/api/v2/openrig/seat-types` | `handleCreateSeatType` | `seat_admin_mount.go:332` |
| POST | `/api/v2/openrig/seat-types/{slug}/versions` | `handleCreateSeatTypeVersion` | `seat_admin_mount.go:335` |
| GET | `/api/v2/openrig/modules` | `handleListModules` | `seat_admin_mount.go:338` |
| GET | `/api/v2/openrig/modules/{slug}/versions/{version}` | `handleGetModuleVersion` | `seat_admin_mount.go:341` |
| PUT | `/api/v2/openrig/modules/{slug}/versions/{version}` | `handlePutModuleVersion` | `seat_admin_mount.go:344` |
| POST | `/api/v2/openrig/rooms/{room}/seats` | `handleCreateSeat` | `seat_admin_mount.go:347` |
| GET | `/api/v2/openrig/rooms/{room}/seats` | `handleListSeats` | `seat_admin_mount.go:350` |
| DELETE | `/api/v2/openrig/rooms/{room}/seats/{seat}` | `handleRemoveSeat` | `seat_admin_mount.go:353` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/occupant` | `handleSetSeatOccupant` | `seat_admin_mount.go:356` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/permission-policy` | `handleSetSeatPermissionPolicy` | `seat_admin_mount.go:359` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/pin` | `handleSetSeatPin` | `seat_admin_mount.go:362` |
| PUT | `/api/v2/openrig/rooms/{room}/overlay` | `handleRoomOverlay` | `seat_admin_mount.go:365` |
| GET | `/api/v2/openrig/overlay` | `handleGetCompanyOverlay` | `seat_admin_mount.go:368` |
| PUT | `/api/v2/openrig/overlay` | `handleCompanyOverlay` | `seat_admin_mount.go:371` |
| GET | `/api/v2/openrig/rooms/{room}/overlay` | `handleGetRoomOverlay` | `seat_admin_mount.go:374` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/overlay` | `handleSeatOverlay` | `seat_admin_mount.go:377` |
| GET | `/api/v2/openrig/rooms/{room}/seats/{seat}/overlay` | `handleGetSeatOverlay` | `seat_admin_mount.go:380` |
| PUT | `/api/v2/openrig/rooms/{room}/seats/{seat}/links` | `handleUpsertSeatLink` | `seat_admin_mount.go:383` |
| GET | `/api/v2/openrig/rooms/{room}/seats/{seat}/links` | `handleListSeatLinks` | `seat_admin_mount.go:386` |
| DELETE | `/api/v2/openrig/rooms/{room}/seats/{seat}/links/{to}/{kind}` | `handleDeleteSeatLink` | `seat_admin_mount.go:389` |
| GET | `/api/v2/openrig/settings` | `handleGetSettings` | `seat_admin_mount.go:392` |
| PUT | `/api/v2/openrig/settings` | `handlePutSettings` | `seat_admin_mount.go:395` |

**Update 2026-10-06 (D5 sharing).** `PUT /api/v2/openrig/rooms/{room}/team` (`handleSetRoomTeam`) is new — it is the route that shares one room, read-only, with one team's members, or makes it private again — and **every Registration line in this section was refreshed from the source in the same pass**, because that insertion shifted them all; all 26 rows were then re-checked one by one against the registrations they cite.

**Update 2026-10-05 (docs truth-audit).** The `POST /api/v2/openrig/seat-types` row was **missing** (the D3 create-a-seat-type route, `seat_admin_mount.go:307`) and every Registration line in this section was stale by the insertion; both are corrected here from the source at HEAD, which is why this section went from 24 to 25 rows.

Note: the mutating rows are wrapped in `seatMutation(kind, action, fn)` (a broadcast +
audit wrapper), except `handleCreateRoom`/`handleListRooms` and the GETs.

### 1.17 OpenRig seat management — seat resolution / machine / status / rigspec

| Method | Path | Handler | Registration |
|---|---|---|---|
| GET | `/api/v2/openrig/seats/{room}/{seat}` | `handleResolveSeat` | `seat_mount.go:210` |
| POST | `/api/v2/openrig/rooms/{room}/seats/{seat}/messages` | `handleSendSeatMessage` | `seat_mount.go:220` |
| GET | `/api/v2/openrig/rooms/{room}/seats/{seat}/messages` | `handlePullSeatMessages` (`authed`) | `seat_mount.go:228` |
| POST | `/api/v2/openrig/rooms/{room}/seats/{seat}/messages/{id}/ack` | `handleAckSeatMessage` (`authed`) | `seat_mount.go:231` |
| POST | `/api/v2/openrig/seat-types/seed` | `handleSeedSeatTypes` | `seat_mount.go:234` |
| GET | `/api/v2/openrig/rooms/{room}/rigspec` | `handleRoomRigSpec` | `seat_rigspec_mount.go:105` |
| POST | `/api/v2/openrig/seat-status` | `handlePostSeatStatus` (`authed`) | `seat_status_mount.go:112` |
| GET | `/api/v2/openrig/machines` | `handleListMachines` | `seat_status_mount.go:115` |

**DRIFT FOUND AND REPAIRED 2026-10-08 (same pass as §1.3).** *Both rows in this section cited a line no longer in the file (`seat-status` 91->95, `machines` 94->98).* **The control: both moved by EXACTLY +4 — four lines were added above them in one change, so the drift is one insertion rather than two coincidences.**

**AUTH CHANGED 2026-10-10 AT THE `e5ecff63` GATE, AND THE ROWS ABOVE SAY WHAT THE MOUNT SAYS.** The pull and the ack were `machineAuthed` when pass 6 wrote them; `e5ecff63` replaced that wrapper with `authed` and deleted it, so both rows now carry `authed` like the send. **THE CODE COMMENT ABOVE THOSE TWO REGISTRATIONS SAID "MACHINE-authenticated" UNTIL THIS PASS** (`seat_mount.go:223`), which is the same defect in the file a reader opens first; it now states the user token and the ack body's `machine_id` as data, matching the residual-limit paragraph at the top of that file. **The line numbers in this row set were re-resolved in the same pass, not adjusted by hand** — see §1's pass record above.

### 1.18 Auth — `/api/auth/*` (`fastmcp/auth/interface/auth_endpoints.go:1087`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/auth/register` | `AuthController.Register` | `auth_endpoints.go:1103` |
| POST | `/api/auth/login` | `AuthController.Login` | `auth_endpoints.go:1117` |
| POST | `/api/auth/refresh` | `AuthController.RefreshToken` | `auth_endpoints.go:1131` |
| POST | `/api/auth/dev-login` | `AuthController.DevLogin` | `auth_endpoints.go:1145` |
| POST | `/api/auth/logout` | `AuthController.Logout` | `auth_endpoints.go:1154` |
| GET | `/api/auth/provider` | `AuthController.GetProviderConfig` | `auth_endpoints.go:1165` |
| POST | `/api/auth/registration-success` | `AuthController.HandleRegistrationSuccess` | `auth_endpoints.go:1169` |
| GET | `/api/auth/verify` | inline (provider echo) | `auth_endpoints.go:1175` |
| GET | `/api/auth/password-requirements` | inline | `auth_endpoints.go:1180` |
| POST | `/api/auth/validate-password` | `ValidatePasswordRequirements` | `auth_endpoints.go:1199` |

### 1.19 Auth — Supabase (`fastmcp/auth/api/supabase_endpoints.go:333`)

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/auth/supabase/signup` | `SupabaseAuthController.SignUp` | `supabase_endpoints.go:349` |
| POST | `/auth/supabase/signin` | `SupabaseAuthController.SignIn` | `supabase_endpoints.go:363` |
| POST | `/auth/supabase/signout` | `SupabaseAuthController.SignOut` | `supabase_endpoints.go:377` |
| POST | `/auth/supabase/password-reset` | `SupabaseAuthController.PasswordReset` | `supabase_endpoints.go:391` |
| POST | `/auth/supabase/update-password` | `SupabaseAuthController.UpdatePassword` | `supabase_endpoints.go:405` |
| GET | `/auth/supabase/verify-token` | `SupabaseAuthController.VerifyToken` | `supabase_endpoints.go:424` |
| POST | `/auth/supabase/resend-verification` | `SupabaseAuthController.ResendVerification` | `supabase_endpoints.go:438` |
| GET | `/auth/supabase/oauth/` | `SupabaseAuthController.GetOAuthURL` | `supabase_endpoints.go:452` |
| GET | `/auth/supabase/me` | `SupabaseAuthController.VerifyToken` | `supabase_endpoints.go:463` |
| GET | `/auth/supabase/health` | `SupabaseAuthController.HealthCheck` | `supabase_endpoints.go:477` |

### 1.20 Teams — base `/api/v2/openrig/teams` (`team_mount.go`)

Added by NEXT_GEN D5 (teams and sharing, slice 1). `{team}` is the team slug, looked up
within the caller's memberships.

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/openrig/teams` | `handleCreateTeam` | `team_mount.go:72` |
| GET | `/api/v2/openrig/teams` | `handleListTeams` | `team_mount.go:75` |
| GET | `/api/v2/openrig/teams/{team}` | `handleGetTeam` | `team_mount.go:78` |
| DELETE | `/api/v2/openrig/teams/{team}` | `handleDeleteTeam` | `team_mount.go:81` |
| GET | `/api/v2/openrig/teams/{team}/members` | `handleListTeamMembers` | `team_mount.go:84` |
| POST | `/api/v2/openrig/teams/{team}/members` | `handleAddTeamMember` | `team_mount.go:87` |
| PATCH | `/api/v2/openrig/teams/{team}/members/{user}` | `handleUpdateTeamMember` | `team_mount.go:90` |
| DELETE | `/api/v2/openrig/teams/{team}/members/{user}` | `handleRemoveTeamMember` | `team_mount.go:93` |

### 1.21 Friction channel — base `/api/v2/openrig/feedback` (`seat_feedback_mount.go`)

**Added to this inventory on 2026-10-06 (docs duty pass 3): these two registrations were MOUNTED and were not documented here**, which is what made §1's count two short (§1's corrected counts paragraph carries the measurement).

| Method | Path | Handler | Registration |
|---|---|---|---|
| POST | `/api/v2/openrig/feedback` | `handleSubmitSeatFeedback` | `seat_feedback_mount.go:60` |
| GET | `/api/v2/openrig/feedback` | `handleListSeatFeedback` (inline closure behind `authed`) | `seat_feedback_mount.go:63` |

**Auth — read from the mount rather than assumed.** Both the POST and the GET take the user token (`authed`); the POST writes the row under that token's user id, so it cannot write outside its tenant. There is no machine token.

**Request shape — defined at `seat_feedback_mount.go:64-70`** (`seatFeedbackSubmission`: `room`, `seat`, `layer`, `text` required; `session` optional). The `layer` vocabulary is the DDL's closed set (`runtime`, `openrig`, `cloud`, `seat-context`, `workspace`, `other`) rather than a list in this document; the credential scan and the page that groups by layer are described once in `README.md`'s *Rig and OpenRig workflow* section. **The third door onto the same writer is the MCP tool `submit_feedback` (§2.3) and the fourth is the shell client, invoked as `4genteam feedback ...` — the script it runs is `agenthub_client/src/agenthub_client/seat_feedback.sh`, carried in the client package by `[tool.setuptools.package-data]` (2026-10-09); it was `scripts/seat_feedback.sh` until the client relocation, and a path is not a door if the file is not there.**

---

## 2. MCP tool surface

### 2.1 How this was established

The server binary and a throwaway Postgres could not be started on this host (no
`postgres`/`pg_ctl`/`initdb`/`psql` binaries: `which postgres pg_ctl initdb psql` →
empty). The live registry was therefore taken from **the code that builds the list**, and
corroborated with the repository's own registry test, which drives the real registered
`POST /mcp` handler through `httptest`:

```
cd agenthub_go
GOCACHE=$PWD/.gocache/rig-surface TMPDIR=$PWD/.gotmp \
  go test ./fastmcp/server/httpapp/ \
  -run 'TestMCPToolsListMatchesGolden|TestMCPToolsListPublishesManageSeat|TestMCPToolsListPublishesCallSeat|TestConnectionToolDefinition' -v
```

Raw output:

```
=== RUN   TestMCPToolsListPublishesCallSeat
--- PASS: TestMCPToolsListPublishesCallSeat (0.00s)
=== RUN   TestMCPToolsListPublishesManageSeat
--- PASS: TestMCPToolsListPublishesManageSeat (0.00s)
=== RUN   TestConnectionToolDefinition
--- PASS: TestConnectionToolDefinition (0.00s)
=== RUN   TestMCPToolsListMatchesGolden
--- PASS: TestMCPToolsListMatchesGolden (0.00s)
PASS
ok  	agenthub/fastmcp/server/httpapp	0.014s
```

The `tools/list` result is built by `App.MCPToolsList`
(`fastmcp/server/httpapp/mcp_routes.go:277`), which does exactly two things:

1. iterates `DDDCompliantMCPTools.ToolDefinitions()`
   (`fastmcp/task_management/interface/ddd_compliant_mcp_tools.go:221`), and
2. appends **four** schemas `ToolDefinitions` does not carry — `manage_seat`, `call_seat`, `submit_feedback` and the connection tool (`mcp_routes.go:303`, `:312`, `:321`, `:330`).

There is no other filter or source.

**Citations re-derived and one claim corrected (2026-10-06, docs duty pass 3).** Every line above was re-resolved against the tree rather than trusted: `getMCPToolsList` *(the name in that pass; since renamed `App.MCPToolsList`, `mcp_routes.go:275`, 2026-10-09 — see the re-resolution note below)* had moved **236 → 257** and `ToolDefinitions` **218 → 221**; and **the appended count read THREE where the code appends FOUR** — `tools := make([]map[string]any, 0, len(defs)+4)` (`mcp_routes.go:262`) with four appends (`:278`, `:287`, `:296`, `:305`) — **which this same document's §2.3 table and §2.5 already called four, so this section was contradicting its own table as well as the code.** The stale range `249-274` is now the four real lines.

**RE-RESOLVED 2026-10-09 at HEAD `36716e6e` (§2 pass), and the builder was RENAMED rather than merely moved.** `App.getMCPToolsList` **resolves nowhere**: `git grep getMCPToolsList` returns prose only, never a `.go` declaration, because the one-line alias was deleted (recorded in `CHANGELOG/`). The method is **`App.MCPToolsList`** (`mcp_routes.go:275`), which is what the citations above now read. The `make([]map[string]any, 0, len(defs)+4)` line is `:285`, and the four appends are `:301`, `:310`, `:319`, `:328`. Also re-resolved in this pass: `handleJSONRPC` `173 → 174`, `authorizeMCPMethod` `145 → 146`, `dispatchMCPTool` `324 → 347`, `get_mcp_status` `357 → 380`, `check_session_health` `363 → 386`, the unknown-tool `default` `469 → 492`, and `tool_config.go` `22 → 21` (where `var toolEnvDefaults` is declared). **The control that separates this from a blanket renumbering:** every line §2.3 attributes to `ToolDefinitions()` is exact at this HEAD (`ddd_compliant_mcp_tools.go:223`, `:227`, `:233`, `:239`, `:244`, `:249`), every `IsWorkflowGuidanceEnabled` call site in §2.5 is exact (`git_branch_mcp_controller.go:176`, `subtask_mcp_controller.go:336`, `agent_mcp_controller.go:249`), and `app.go:71` and `ddd_compliant_mcp_tools.go:65` are exact — so the drift is confined to `mcp_routes.go`, the file that gained the most lines above these pointers. The ten names themselves are unchanged, and the acceptance command above **plus `TestMCPToolsListPublishesSubmitFeedback`** (the command as written omits it) passes at this HEAD: all five `PASS`, `ok agenthub/fastmcp/server/httpapp 0.024s`.

### 2.2 MCP protocol methods (NOT tools)

`handleJSONRPC` (`fastmcp/server/httpapp/mcp_routes.go:176`) implements these JSON-RPC
methods. They are the protocol layer and MUST NOT be listed as tools:

`initialize`, `notifications/initialized`, `ping`, `tools/list`, `resources/list`,
`prompts/list`, `tools/call` (all in `handleJSONRPC`, `mcp_routes.go:176`).

`initialize` and `tools/list` additionally require a bearer token when
`AUTH_ENABLED=true` (default), enforced in `authorizeMCPMethod` (`mcp_routes.go:148`).
`resources/list` and `prompts/list` return empty lists.

### 2.3 Published tools (`tools/list`)

Ten tool names, always present except `manage_context` (see note):

| Tool | Source | File:line |
|---|---|---|
| `manage_task` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:223` |
| `manage_subtask` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:227` |
| `manage_context` | `ToolDefinitions` (conditional) | `ddd_compliant_mcp_tools.go:233` |
| `manage_project` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:239` |
| `manage_git_branch` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:244` |
| `manage_agent` | `ToolDefinitions` | `ddd_compliant_mcp_tools.go:249` |
| `manage_seat` | appended schema | `mcp_routes.go:304` (`ManageSeatToolName`, `manage_seat_controller.go:12`) |
| `call_seat` | appended schema | `mcp_routes.go:313` (`CallSeatToolName`, `call_seat_controller.go:14`) |
| `submit_feedback` | appended schema | `mcp_routes.go:322` (`SubmitFeedbackToolName`, `submit_feedback_controller.go:18`; args `room, seat, session, layer, text`) |
| `manage_connection` | appended schema | `mcp_routes.go:330` (`tools = append(tools, connTool)`; built at `:326` by `connTool, err := connectionToolDefinition()`; definition `mcp_connection_tool.go:39`) |

Note: `manage_context` is emitted only when `ContextController != nil`; the constructor
sets it when `DatabaseAvailable` is true (`ddd_compliant_mcp_tools.go:110-114`), and
`app.go:71` passes `DatabaseAvailable: true`. So on a wired server all ten are present.
**Measured at HEAD `763b8196` (2026-10-06): a booted server answers `tools/list` with exactly
these ten names.** **RE-MEASURED 2026-10-09 at HEAD `36716e6e`: the five registry tests pass (`ok agenthub/fastmcp/server/httpapp 0.024s`), so all ten names stand and the count is unchanged — see §2.1's re-resolution note.**

**RE-RESOLVED 2026-10-10 at HEAD `f81a2d2f` (writer seat) — this table's ten rows are the ones NO instrument reads, and five of their anchors had drifted.** `scripts/S3-REDERIVE.py` declares the gap in its own coverage block: these 10 rows carry 15 anchors, and `scripts/CITATION-AUDIT.py` skips them because its row shape needs a METHOD in the first cell where this table puts a tool NAME. All 15 were audited by hand against the tree: **ten resolve exactly** (`ddd_compliant_mcp_tools.go:223`, `:227`, `:233`, `:239`, `:244`, `:249`; `manage_seat_controller.go:12`; `call_seat_controller.go:14`; `submit_feedback_controller.go:18`; `mcp_connection_tool.go:39`) and **five were stale, every one of them in `mcp_routes.go`**: `302 → 304`, `311 → 313`, `320 → 322`, `328 → 330`, and the bare `:324 → :326`. The table above now reads the current lines. **The same sweep re-resolved the rest of this file's pointers in §2.1–§2.4, because drift is a function of the lines inserted above a citation and of nothing else:** `App.MCPToolsList` `275 → 277`, the `make([]map[string]any, 0, len(defs)+4)` line `285 → 287`, the four appends `301/310/319/328 → 303/312/321/330`, `handleJSONRPC` `174 → 176`, `authorizeMCPMethod` `146 → 148`, `dispatchMCPTool` `347 → 349`, `get_mcp_status` `380 → 405`, `check_session_health` `386 → 411`, and the unknown-tool `default` `492 → 518`. **The two dated passes above keep their own numbers as the record of what was measured then; these are the live pointers — the note that the four appends were `:301`, `:310`, `:319`, `:328` remains true of `36716e6e` and false of this HEAD.** **The control against a blanket renumbering:** §1.6's two rows (`mcp_routes.go:76` and `:141`) did not move and `CITATION-AUDIT.py` still reads them fresh, so the +2 insertion sits between `:141` and `:146`, while `get_mcp_status`, `check_session_health` and the `default` drifted by +25/+25/+26 — a second and larger insertion sits below `:349`. **What the pass did NOT establish: the tool surface itself.** No tool name was added, removed or renamed since the 2026-10-09 re-measurement, and no booted server was asked for `tools/list` this time; only pointers moved.

`tools_golden.json`
(`fastmcp/task_management/interface/testdata/tools_golden.json`) contains only the six
Python-registry tools; `TestMCPToolsListMatchesGolden` filters the **four** names the Go server
appends (`manage_seat`, `call_seat`, `submit_feedback`, `manage_connection`) and asserts the
rest equals golden.

### 2.4 Dispatch-only names (callable via `tools/call`, NOT advertised by `tools/list`)

`dispatchMCPTool` (`mcp_routes.go:349`) also handles two legacy names that are **not**
published in `tools/list`:

- `get_mcp_status` (`mcp_routes.go:405`)
- `check_session_health` (`mcp_routes.go:411`)

Anything else returns `{"error":"Unknown tool: <name>"}` (`mcp_routes.go:518`, `default`).

### 2.5 Configuration gating — important negative finding

The Python-derived `ToolConfig` subsystem still exists in Go
(`fastmcp/task_management/infrastructure/configuration/tool_config.go:21`, where `var toolEnvDefaults` is declared) with a
`TOOL_*` enablement table (`manage_project`, `manage_task`, `manage_subtask`,
`manage_agent`, `manage_seat`, `manage_document`, `update_auto_rule`, `validate_rules`,
`regenerate_auto_rule`, `validate_tasks_json`, `create_context_file`, `manage_context`).

**In this Go server that table does not gate `tools/list`.** Evidence:
`DDDCompliantMCPTools` builds a `ToolConfig` and passes it to controllers
(`ddd_compliant_mcp_tools.go:65`, `cfg, err := configuration.NewToolConfig(...)`), but the only method any caller invokes on it is
`IsWorkflowGuidanceEnabled()` (`git_branch_mcp_controller.go:176`,
`subtask_mcp_controller.go:336`, `agent_mcp_controller.go:249` — all three verified present). `GetEnabledTools` has no
caller outside `fastmcp/config` (its `ToolRegistry`/`ToolConfigLoader` are unused by the
HTTP path). `ToolDefinitions()` and `MCPToolsList` read no environment variable.
Therefore `TOOL_*` and the six phantom names (`manage_document`, `update_auto_rule`,
`validate_rules`, `regenerate_auto_rule`, `validate_tasks_json`, `create_context_file`)
have no effect and are never advertised.

A cross-check inventory produced by the reviewer at the same HEAD stated the tool list is
`TOOL_*`-gated. That claim is **not supported by the Go source**; this document records the
code as authoritative and flags the discrepancy in §5.

---

## 3. Tables

The runtime table registry is `database.Tables` (base package,
`fastmcp/task_management/infrastructure/database/models.go:600`). Two packages append to
it in `init()`; `ProductionTables` is deliberately separate.

### 3.1 Core task-side — `Tables` in `models.go` (20)

| Table | Model | Declaration |
|---|---|---|
| `agent_sessions` | `AgentSession` | `models.go:601` |
| `agents` | `Agent` | `models.go:618` |
| `api_tokens` | `APIToken` | `models.go:636` |
| `context_delegations` | `ContextDelegation` | `models.go:653` |
| `context_inheritance_cache` | `ContextInheritanceCache` | `models.go:682` |
| `global_contexts` | `GlobalContext` | `models.go:706` |
| `labels` | `Label` | `models.go:725` |
| `missed_notifications` | `MissedNotification` | `models.go:736` |
| `projects` | `Project` | `models.go:751` |
| `templates` | `Template` | `models.go:763` |
| `agent_session_events` | `AgentSessionEvent` | `models.go:784` |
| `project_contexts` | `ProjectContext` | `models.go:796` |
| `project_git_branchs` | `ProjectGitBranch` | `models.go:818` |
| `branch_contexts` | `BranchContext` | `models.go:836` |
| `tasks` | `Task` | `models.go:857` |
| `subtasks` | `Subtask` | `models.go:893` |
| `task_assignees` | `TaskAssignee` | `models.go:927` |
| `task_contexts` | `TaskContext` | `models.go:940` |
| `task_dependencies` | `TaskDependency` | `models.go:965` |
| `task_labels` | `TaskLabel` | `models.go:975` |

### 3.2 Auth tables — appended to `Tables` via `init()`

| Table | Model | Declaration | Registered by |
|---|---|---|---|
| `users` | `User` | `fastmcp/auth/infrastructure/database/models_auth.go:58` | `models_auth.go:155` |
| `user_token_balances` | `UserTokenBalance` | `models_auth.go:120` | `models_auth.go:155` |
| `email_tokens` | `EmailTokenModel` | `fastmcp/auth/infrastructure/repositories/email_token_repository.go:53` | `email_token_repository.go:86` |

### 3.3 Seat-management and team tables — appended to `Tables` via `init()`

Declared in `fastmcp/seat_management/infrastructure/database/seat_tables.go` (`seatDatabaseTables`, **15 entries**, `seat_tables.go:16`) and
`team_tables.go` (`teamManagementDatabaseTables`, **2 entries**, `team_tables.go:24`). **The two are composed and registered in ONE place** — `seatManagementDatabaseTables` (`seat_tables.go:397`, `append([]taskdb.TableDef{}, teamManagementDatabaseTables...)` then `seatDatabaseTables...`) and the package's `init()` (`seat_tables.go:402`). **`team_tables.go` contains no `init()` and does not append; an earlier version of this section cited an append at `team_tables.go:56`, which does not exist.** The same **17** tables are declared as DDL in
`fastmcp/seat_management/infrastructure/schema/seat_management_postgresql.sql`: **the 15 seat tables plus the 2 team tables** (note for a reader counting
statements: `grep -c 'CREATE TABLE IF NOT EXISTS'` returns **18** because the file's header
COMMENT at line 6 contains that phrase; `grep -cE '^CREATE TABLE IF NOT EXISTS'` -> **17**, one per table, and no
table is declared twice). **BOTH FIGURES IN THIS PARAGRAPH MOVED WHEN `seat_feedback` LANDED** — the 15/16 pair that stood here was the 15-table state, and the one-table difference is precisely the table this section did not list. **THEY MOVED AGAIN AT PASS 6 (2026-10-10), by TWO AND NOT BY ONE: `seat_messages` (`seat_tables.go:377`, DDL `:306`) and `machine_edges` (`seat_tables.go:316`, DDL `:371`) are what the two entries and the two statements are** — the pair counts 16/18/19, and the note above is why the unanchored `grep -c` reads one higher than the anchored form rather than equal to it. **AND THEY MOVED AGAIN ON 2026-10-10 AT THE `e5ecff63` GATE, DOWN BY ONE RATHER THAN UP: that commit dropped `machine_tokens`, so `seatDatabaseTables` counts 15 and the file declares 17 statements (18 unanchored, the header comment again) — the pair this paragraph states is therefore 15/17/18. `scripts/COUNTS-AUDIT.py` was red on its own memory for the length of that gate and is GREEN again now that its `EXPECTED` carries 15/17 (writer's row `0a94db94`).**

| Table | Model | Declaration (Go) | SQL |
|---|---|---|---|
| `modules` | `ModuleORM` | `seat_tables.go:17` | `seat_management_postgresql.sql:46` |
| `module_versions` | `ModuleVersionORM` | `seat_tables.go:36` | `:61` |
| `seat_types` | `SeatTypeORM` | `seat_tables.go:59` | `:77` |
| `seat_type_versions` | `SeatTypeVersionORM` | `seat_tables.go:79` | `:93` |
| `teams` | `TeamORM` | `team_tables.go:25` | `:121` |
| `team_members` | `TeamMemberORM` | `team_tables.go:45` | `:135` |
| `rooms` | `RoomORM` | `seat_tables.go:102` | `:159` |
| `seats` | `SeatORM` | `seat_tables.go:125` | `:177` |
| `overlays` | `OverlayORM` | `seat_tables.go:158` | `:200` |
| `seat_links` | `SeatLinkORM` | `seat_tables.go:190` | `:225` |
| `resolved_seats` | `ResolvedSeatORM` | `seat_tables.go:216` | `:245` |
| `seat_settings` | `SeatSettingsORM` | `seat_tables.go:241` | `:263` |
| `seat_feedback` | `SeatFeedbackORM` | `seat_tables.go:321` | `:278` |
| `machines` | `MachineORM` | `seat_tables.go:253` | `:324` |
| `seat_messages` | `SeatMessageORM` | `seat_tables.go:357` | `:306` |
| `seat_status` | `SeatStatusORM` | `seat_tables.go:267` | `:335` |
| `machine_edges` | `MachineEdgeORM` | `seat_tables.go:296` | `:355` |

**`seat_feedback` IS THE ROW THIS DOCUMENT WAS MISSING (added 2026-10-06, pass 3).** It is registered (`seat_tables.go:321`), declared in the DDL (`:278`), and read by `NewORMSeatFeedbackRepository` over `seat_feedback` (`seat_management/infrastructure/repositories/orm/seat_feedback_repository.go:25`, `:47`); **`app.go:61-63` records that the boot needs the table registered, which is why it is in the composition rather than beside the routes.** **Its absence is what made §3.5's total one short and §3.3's SQL count one under the file's own `grep -cE`.**

### 3.4 `ProductionTables` — declared but NOT appended to `Tables` (6)

`fastmcp/task_management/infrastructure/database/models_prod.go:96`. The file's header
(`models_prod.go:8-12`) states these are intentionally not appended (they reference the
auth `users` table and would mis-order DDL). They are therefore **not** created by
`CreateTables`.

| Table | Model | Declaration |
|---|---|---|
| `agent_import_history` | `AgentImportHistory` | `models_prod.go:105` |
| `applied_migrations` | `AppliedMigration` | `models_prod.go:126` |
| `token_transactions` | `TokenTransaction` | `models_prod.go:143` |
| `user_agent_configurations_md` | `UserAgentConfigurationMd` | `models_prod.go:170` |
| `user_api_tokens` | `UserAPIToken` | `models_prod.go:190` |
| `user_sessions` | `UserSession` | `models_prod.go:225` |

### 3.5 Totals

- `database.Tables` at runtime: 20 (core) + 3 (auth) + **15** (seat) + 2 (team) = **40 tables** — **corrected from 38 on 2026-10-06 (pass 3): the inventory had never listed `seat_feedback`, which is the fourteenth seat table (§3.3).** **CORRECTED FROM 39 AT PASS 6 (2026-10-10): the seat block gained `seat_messages` and `machine_edges` (§3.3), so it is 16 and the total is 41 — two tables, not one.** **CORRECTED FROM 41 AT THE `e5ecff63` GATE (2026-10-10): the same commit that replaced the per-machine token removed `machine_tokens` (§3.3), so the seat block is 15 and the total is 40.**
- Plus `ProductionTables`: **6** tables declared but not registered for creation.
- **Both totals, and every count in this document, are re-derived by `scripts/COUNTS-AUDIT.py` in this repository — read-only, non-zero on any difference, safe to run in a gate (§1 carries the same pointer). It was TRACKED on 2026-10-09; before that it lived outside the worktree, so the pointer here named a path a reader could not follow. §3's OWN `file:line` anchors — the Declaration and SQL columns of §3.1–§3.4 — are re-derived by `scripts/S3-REDERIVE.py`, tracked beside it since 2026-10-10 with ROOT derived from its own location: it reads COMMITS (`git show`), exits non-zero on ANY anchor that is not fresh (an anchor stale since before its attribution base counts, because a verdict that passed those could not fail), and prints `BASE UNAVAILABLE` rather than passing quietly when that base is not in the checkout — the shallow-clone case.**
- Every table in §3.1–3.4 carries a `user_id` column except `applied_migrations`
  (a migration ledger; `models_prod.go:118`).

### 3.6 Re-derivation of this section (2026-10-06, docs duty pass 3)

**Every citation in §3.1–§3.4 was re-measured against the tree rather than trusted, and the section was found ONE TABLE SHORT AND STALE IN EVERY LINE NUMBER OF §3.3.** (a) **`seat_feedback` was missing entirely** — registered at `seat_tables.go:317`, declared in the DDL at `:278`, read by `NewORMSeatFeedbackRepository` (`seat_feedback_repository.go:25`, `:47`); **with it the seat block is 14 tables and the runtime registry is 39, not 38.** (b) **Every `seat_tables.go`, `team_tables.go` and SQL line number in §3.3 was stale** — the Go cites by 3–36 lines, the SQL cites by 12–66. (c) **`team_tables.go:56`, cited as an append site, does not exist**: `team_tables.go` has no `init()` at all; the composition and the single append are `seat_tables.go:357` and `:362`. **§3.1, §3.2 and §3.4 came through clean — the 20 core entries, the three auth entries and the six `ProductionTables` matched name-for-name and line-for-line — and that is the control that says this method finds real drift rather than inventing it.** **The counting method is worth keeping: entries are counted at DEPTH 1 of each registry's literal (`{Name: "...", Model: ...}`), because a plain `grep -c 'Name:'` counts every COLUMN and reports 572 for a 20-table registry.** **§4's gone-list holds commands and their outputs rather than citations; those were not re-run in this pass.**

---

## 4. Gone list

Each entry states the exact command and its result. "NO MATCH" = the command exited with
no output.

| Retired item | How established it is gone | Command | Result |
|---|---|---|---|
| `agenthub_main/agent-library` (Python agent library) | directory absent on disk and untracked in git; removed by commit `60bcdb68` | `ls agenthub_main/agent-library` ; `git ls-files 'agenthub_main/agent-library*' \| wc -l` ; `git log --oneline -1 -S'agent-library' -- agenthub_main` | `No such file or directory` ; `0` ; `60bcdb68 refactor(agents): remove the Python agent library and agent management (T8 Python half)` — **RE-MEASURED 2026-10-10: the third command now answers `a50929c6 chore: remove agenthub_main, the retired Python backend`**, because that later commit deleted the rest of the tree the path lives in; `60bcdb68` remains the library's own removal (see the note below) |
| `call_agent` **tool** (MCP tool "load agent instructions") | no tool definition, absent from `tools_golden.json`, and the test suite asserts its absence | `grep -rn 'Name: *"call_agent"' agenthub_go --include='*.go' \| grep -v .gomodcache` ; `grep -n 'removed call_agent tool' agenthub_go --include='*_test.go'` | `NO MATCH` ; `call_seat_mcp_test.go:64: t.Fatal("tools/list still publishes the removed call_agent tool")` *(line corrected from `:62` on re-execution, 2026-10-06)* |
| `/api/v2/openrig/agents` route | no registration anywhere in the Go tree | `grep -rn 'openrig/agents' agenthub_go --include='*.go' \| grep -v .gomodcache` | `NO MATCH` |
| `agent_templates` table | no declaration in Go models/DDL or in the production SQL | `grep -rn 'agent_templates' agenthub_go --include='*.go' --include='*.sql'` ; `grep -rn 'agent_templates' agenthub_main --include='*.sql'` | `NO MATCH` (Go); the `agenthub_main` half is **UNRUNNABLE as written since 2026-10-10** — that tree was removed by `a50929c6` (see the note below) |
| `user_agent_instances` table | same as above | `grep -rn 'user_agent_instances' agenthub_go --include='*.go' --include='*.sql'` ; `grep -rn 'user_agent_instances' agenthub_main --include='*.sql'` | `NO MATCH` (Go); the `agenthub_main` half is **UNRUNNABLE as written since 2026-10-10** — that tree was removed by `a50929c6` (see the note below) |

**RE-EXECUTED 2026-10-06 (docs duty pass 3) — every command in this table was run again and its result compared with the text above.** **All five entries still hold**: the directory is absent and untracked, the removal commit is still `60bcdb68`, `call_agent` has no tool definition, and `openrig/agents`, `agent_templates` and `user_agent_instances` all return nothing in both trees. **One line number had moved and is corrected in the table: the assertion is at `call_seat_mcp_test.go:64`, not `:62`** — the same drift class as §1–§3, caught here by re-running rather than by re-deriving, which is why the two are different jobs. **And the distinction's three citations were verified by READING the lines rather than by grepping for the word**: `ddd_compliant_mcp_tools.go:249` is the `manage_agent` definition, `unified_agent_description.go:101` is `props.Set("call_agent", …)`, and `tool_input_schemas.go:126` is the `call_agent` schema entry — **so the tool is gone and the field is live, exactly as the note says.**

**RE-MEASURED 2026-10-10 (writer seat, docs duty pass 7) — the five conclusions hold; two RESULTS in the table and ONE of the distinction's three citations had moved, and each is named here rather than quietly swapped.** (a) **The pickaxe answers a different commit today, and it is not a contradiction:** `git log --oneline -1 -S'agent-library' -- agenthub_main` returns **`a50929c6 chore: remove agenthub_main, the retired Python backend`**, because that later commit deleted the rest of the tree the path sits in, while **`60bcdb68` remains the library's own removal** (its diff carries 261 lines of `agent-library/README.md`). Both are corrected in the table. (b) **The second half of the `agent_templates` and `user_agent_instances` greps is now UNRUNNABLE rather than negative:** `agenthub_main` no longer exists, so that command errors `No such file or directory` instead of returning `NO MATCH`, while the Go half still returns nothing — **so from here the honest phrasing is one tree, not "both trees"**, and both cells say so. (c) **One of the distinction's three citations is DEAD and the other two are ALIVE — and the near-miss is worth more than the fix.** `agent_mcp_controller/unified_agent_description.go` was **DELETED by `8fa51fd7`** (`fix(mcp): the served manage_agent description stops advertising the retired library`), and in the commit before, its `:101` was exactly `props.Set("call_agent", unifiedAgentStringProperty(unifiedParamDesc("call_agent")))` — so THAT pointer is the one re-pointed, to the description's current home `mcp_controllers/agent_mcp_controller/manage_agent_description.go:26`/`:45`. **The other two are unchanged at HEAD and carry precisely what the 2026-10-06 note says:** `ddd_compliant_mcp_tools.go:249` is `ToolDefinition{Name: "manage_agent", …, Parameters: asOrdered(agent_mcp_controller.GetManageAgentDescription(), …)}` and `tool_input_schemas.go:126` is `{"call_agent", "[OPTIONAL] ", `{"type":"string"}`}`. **THE HAZARD HERE IS NOT DRIFT, IT IS AN UNCOMMITTED NEIGHBOUR:** while this pass ran, item 3's in-flight edits had those two same lines reading `}` and a comment inside `toolInputSchema`, in files of 296 and 177 lines instead of 311 and 186 — a pass that took its line numbers from the working tree would have "corrected" two live citations to a state HEAD does not have. **Measure at HEAD, in a worktree, or the working tree will be mistaken for the repository.** **(d) A watcher for whoever passes next: the field IS live at HEAD and that expires with item 3** — `manage_agent` itself is being retired (`NEXT_GEN.md`'s item-3 ruling, and its step-1 test is already in the working tree), so once that lands this distinction is a dated record rather than a present-tense claim. **(e) The same in-flight work moves the instruments:** `scripts/COUNTS-AUDIT.py` in this pass's dirty working tree reported published MCP tools **9** against this file's 10, core tables 19 against 20 and registered tables 39 against 40, while the same audit on a clean HEAD copy ends "all numbers re-derived and matching" with rc 0 — so a red COUNTS standing beside an item-3 edit is the tree, not the document.

**Distinction that must not be collapsed:** `call_agent` the **tool** is gone, but
`call_agent` remains a **parameter/field of the `manage_agent` tool** (register/update):
`ddd_compliant_mcp_tools.go:249` (the `manage_agent` definition, reading
`agent_mcp_controller.GetManageAgentDescription()`), `tool_input_schemas.go:126` (the `call_agent`
schema entry) and `mcp_controllers/agent_mcp_controller/manage_agent_description.go:26`/`:45` — which
**replaces** the deleted `unified_agent_description.go:101` (see the note above). The handler that
consumes it is `mcp_routes.go:481`-`:486`, and the served schema is pinned by
`testdata/tools_golden.json:668` through `mcp_routes_test.go:119`.
That field is deliberate and still live. A sentence about one
must not be read as a sentence about the other.

---

## 5. Contradictions between existing docs and the code — ALL CLOSED

This section was the rewrite worklist for owner directive (A). Every item below has been
corrected; each entry keeps the original finding so the audit trail survives, and names
the correction. The checks themselves are unchanged and re-runnable from Appendix A.

1. **`ai_docs/api-integration/mcp-tools-api-complete.md`** — **CLOSED** (`95ffca45`).
   The original finding: it documented the removed `call_agent` **tool** as live, listed
   eight tools and omitted `manage_seat` and `call_seat`, and claimed every tool requires
   `action`. The file now carries the ten published tools (`manage_seat` at line 13,
   `call_seat` at line 14), a `### call_agent — retired` section, and an explicit note
   that the two seat tools and `manage_connection` take no `action`.
2. **`api-parameter-handling-complete.md`** — **CLOSED**; the page was deleted, the seat-tool
   exception to the `action` rule is stated in the tool table of this file.
3. **`ai_docs/core-architecture/agenthub-system-architecture.md section 3`** — **CLOSED** (`95ffca45`
   and the 2026-10-06 truth-audit). The original finding: "32+ specialized agents", a
   **SQLite (fallback)** claim, and SQLAlchemy/Alembic described as the persistence path.
   The Python module tree and its SQLAlchemy examples are now covered by the
   **Retired implementation note** at line 224; the Database Layer states the Go
   `TableDef`/Postgres-only reality; the development, test and directory sections point at
   `agenthub_go`; and the "4-tier" framing appears only as the `{level}` set of the
   mounted `/api/v2/contexts/{level}` routes.
4. **`agenthub_go/PROD_READINESS_REPORT.md`** (Go module root, not `ai_docs`) —
   **SUPERSEDED IN PLACE** (`95ffca45`). A status block above the blocker table marks B4
   and B6 as no longer describing HEAD (`App.MCPToolsList` builds from
   `ToolDefinitions()`; `GET /mcp` is `mcpSSEHandler`; `models_prod.go` declares six
   `ProductionTables`), while the original findings stay visible as the dated record they
   are. **The block is a QUOTATION and is treated as one — the ONE line number it carries is
   `mcp_routes.go:275`, the REPORT'S own, written at `c4ff8d42` and still the live registration
   for `App.MCPToolsList` (re-derived 2026-10-09, when the method was renamed from
   `getMCPToolsList`); it gives NO number for `GET /mcp`, whose live registration is
   `mcp_routes.go:139` (`mux.HandleFunc("GET /mcp", mcpSSEHandler)`).** **CORRECTED 2026-10-09,
   on the reviewer's gate of `56cabe97`+`e116a5cf`: this clause read "`mcp_routes.go:116`" for the
   `GET /mcp` handler AND "this clause carried `:138`", and called the numbers the report's own —
   both were OURS. Measured at the gate: `git grep -n 'mcp_routes\.go:116'` over the tracked tree returned
   ONE hit — this document's own sentence (**re-run it now and it returns five, because this correction and
   its CHANGELOG entry quote the string; at NO revision does it appear in the report itself**), the report holds ZERO occurrences of `116` at `c4ff8d42`,
   `95ffca45` and `HEAD`, and `git log -S'mcp_routes.go:116' --
   agenthub_go/PROD_READINESS_REPORT.md` is EMPTY, so no commit ever put that string in the
   report. `:116` was our stale number for the `GET /mcp` registration, **misattributed to the
   report — a citation wearing a quotation's clothes, which is the exact failure the companion
   rule in Appendix A exists to prevent**, and it is why this instance now states which single
   number is genuinely the report's.** The report's B4 sentence has since
   been corrected to the live name and the ten/four count while the rest of the block stays
   the dated quotation it is.
5. **Cross-check `/tmp/inv.md`** (reviewer inventory, HEAD `c4ff8d42`) — retained for its
   method only. Its three divergences from the code are settled in this document: the
   `TOOL_*` gating claim in §2.5, `initialize`/`ping` as protocol methods rather than
   dispatch cases in §2.2, and the route count in §1 (its `112` was `httpapp`-only; **§1
   carries the current figure, with its pattern and date**). Its table sections omit the three auth tables and
   the six `ProductionTables`, both carried in §3.

---

## Appendix A — acceptance commands

Run from `/home/daihu/__projects__/4genthub/agenthub_go` unless noted.

**Why every count below carries its command:** a count of text is not a count of structure, and four conflations found in this rig are the reason — an `httpapp`-only glob read as the whole tree (which hid the 20 auth registrations), a registration read as its truncated `base + suffix` tail, a header COMMENT counted as a `CREATE TABLE` statement (the unanchored 14 versus the anchored 13), and `initialize` read as a dispatch case when it is a `handleJSONRPC` protocol method. Each count below is therefore the structurally anchored form, and where two counts of one thing disagree, the discrepancy is evidence to CHECK rather than a story to tell.

```bash
# Every route registration (the source of §1)
grep -rn 'mux.HandleFunc(\|mux.Handle(' --include='*.go' fastmcp/server/httpapp | grep -v '_test.go'
grep -rn 'mux.HandleFunc(' --include='*.go' fastmcp/auth | grep -v '_test.go'
grep -rn 'mux.HandleFunc(\|mux.Handle(' --include='*.go' fastmcp/server/httpapp | grep -v '_test.go' | wc -l
grep -rn 'mux.HandleFunc(' --include='*.go' fastmcp/auth | grep -v '_test.go' | wc -l

# No other mount sites exist
grep -rn 'HandleFunc(' --include='*.go' cmd | grep -v '_test.go' | wc -l   # 0

# MCP registry (see raw output in §2.1)
GOCACHE=$PWD/.gocache/rig-surface TMPDIR=$PWD/.gotmp \
  go test ./fastmcp/server/httpapp/ \
  -run 'TestMCPToolsListMatchesGolden|TestMCPToolsListPublishesManageSeat|TestMCPToolsListPublishesCallSeat|TestConnectionToolDefinition' -v

# Base-path constants resolved in §1
grep -rn 'const base' --include='*.go' fastmcp/server/httpapp | grep -v '_test.go'

# Tables
grep -n '^\t{Name: "' fastmcp/task_management/infrastructure/database/models.go
grep -n '^\t{Name: "' fastmcp/task_management/infrastructure/database/models_prod.go
grep -n '^\t{Name: "' fastmcp/seat_management/infrastructure/database/seat_tables.go
grep -n '^\t{Name: "' fastmcp/seat_management/infrastructure/database/team_tables.go
grep -n '^\t{Name: "' fastmcp/auth/infrastructure/database/models_auth.go
grep -n '^\t{Name: "' fastmcp/auth/infrastructure/repositories/email_token_repository.go

# Gone list (see §4)
grep -rn 'openrig/agents' agenthub_go --include='*.go' | grep -v .gomodcache          # NO MATCH
grep -rn 'Name: *"call_agent"' agenthub_go --include='*.go' | grep -v .gomodcache     # NO MATCH
grep -rn 'agent_templates\|user_agent_instances' agenthub_go --include='*.go' --include='*.sql'  # NO MATCH
ls agenthub_main/agent-library                                                        # No such file or directory
```

**Counts measured 2026-10-08 at `62b734ec`: 123 `httpapp` + 20 `auth` = 143 registrations** — a snapshot, not a constant: re-run the two `wc -l` commands at the top of the block above rather than quoting this line. **The same line read `121 httpapp + 20 auth = 141` and was stale**; `go run ./cmd/apirefgen` independently reported **143 routes, 10 tools** at that commit. **Where this document drifts — measured, not assumed (2026-10-09).** Three re-resolution passes under one method, three different results. **§1 was re-resolved 2026-10-06 and came back with 21 stale route rows plus two citations in §2.** **§2 was re-resolved 2026-10-09 at `36716e6e` and came back with eight stale pointers and one renamed symbol.** **§3 was re-resolved at the same HEAD and came back with NOTHING** — twenty registry lines, sixteen Go entry lines, sixteen SQL lines, three §3.2 cites, six §3.4 entries, the registry variable, `ProductionTables`, the composition and its `init()`, the `seat_feedback` repository lines and `app.go:61-63` all exact, and every count re-deriving (`20+3+14+2 = 39`; the SQL file's 17-versus-16 pair explained by the header comment's own phrase at line 6). **§1 was then re-resolved a second time on 2026-10-09 and also came back with NOTHING — all 143 rows — because no route registration had moved above them since the first pass.**

**The appendix's own acceptance block was re-run at this HEAD as the pass's control, and every figure holds: `123 httpapp + 20 auth = 143` registrations, `HandleFunc(` in `cmd` → 0, the table entry counts `20 / 6 / 14 / 2 / 2 / 1`, and all three gone-list searches → NO MATCH.**

So the model is **not** "old citations rot": **a `file:line` drifts as a function of lines inserted above it since the last resolution, and of nothing else.** §2 drifted because `mcp_routes.go` gained the most lines while §2's pointers stood still; §3 did not drift because the table definitions did not move. **The operational step that follows from the model, and the one that found six citations in a pass where a symbol sweep had found none: RE-RESOLVE BY GREPPING THE CITED FILE'S NAME — `mcp_routes\.go:` — NOT THE SYMBOL.** Drift concentrates in the files that gained lines, so the unit of search is the citation's own `file:name`, not the identifier it mentions; a symbol sweep answers a different question (does this name still exist anywhere) and is blind to a pointer that moved inside a file whose symbol kept its name. **What that buys a later reader is which section to re-read first — the one whose cited file has gained the most lines above its own citations — and, where a symbol was renamed rather than moved, the knowledge that the line number is the smaller half of the defect.**

**THE CENSUS, run once over the whole cited surface (2026-10-09 at `56cabe97`) so this model is not argued from its own three passes: 299 distinct `file:line` pairs over 61 distinct cited basenames (79 distinct file strings as written), 292 of them resolving, NONE with a line beyond EOF — and all 7 flags are the resolver's own prefix gap, not a document defect.** The docs are written for a reader standing in `agenthub_go/`, so `server/routes/websocket_routes.go:25` means `agenthub_go/fastmcp/server/routes/websocket_routes.go:25`; **202 of the 292 resolve ONLY through that prefix**, and the seven that a prefix-blind resolver flags (`websocket_routes.go`, `seat_feedback_repository.go`, `unified_agent_description.go`, `task_status.go`, `task.go`, `rigspec.go`, `names.go`) all exist in the tree at the deeper path. Two traps the resolver must be built around, both measured: **(i) THE SAME-NAME TRAP — 52 of the 299 pairs are written as a bare basename that matches more than one `.go` file**, and 12 of the 61 cited basenames are ambiguous in this tree (`main.go` alone matches 122 files, `server.go` 14, `version.go` 10, `runtime.go` 9, `http.go` 7, `resolver.go` 5, `names.go` 3; `task_routes.go`, `subtask_routes.go`, `session_stream_routes.go`, `rigspec.go` and `models.go` 2 each), **so a bare-basename lookup silently picks one and can pass a citation for the wrong reason — the two `branch_routes.go` files (`routes/` versus `httpapp/`) are the worked case from that pass**. **(ii) THE SILENT FILTER — excluding `_test.go` hides a case rather than reporting it, and exactly 1 citation in this census lands in a test file**, so the exclusion is COUNTED and its one hit named; a filter applied silently turns "nothing found" into "nothing there". Commands, from the repo root:

```bash
grep -rhoE '[A-Za-z0-9_./-]+\.go:[0-9]+' ai_docs README.md | sort -u | wc -l                                 # 299 distinct pairs
grep -rhoE '[A-Za-z0-9_./-]+\.go:[0-9]+' ai_docs README.md | sed 's/.*\///; s/:.*//' | sort -u | wc -l       # 61 cited basenames
```

**Both figures are a snapshot at that HEAD, like every count in this appendix: re-run rather than quote** — the same command at `e116a5cf` returns **301**, because this paragraph's own two example citations (`server/routes/websocket_routes.go:25` and its `agenthub_go` twin) are pairs the census then counts, which is the snapshot caveat demonstrated on the paragraph that states it. What the census buys is a ceiling on the SEARCH, **not a verdict of correctness: the surface RESOLVES across 299 pairs — and resolving is not being right.** §5.4's `:116` resolved and was wrong; that gap is what the companion rule below closes, and it is why the claim is "the surface resolves", never "the surface is clean". **7 flags, every one of them the instrument's**, and the two traps named above are the reason a smaller number would not have been trustworthy.

**THE COMPANION RULE, because this sweep will land on text that is NOT a citation: A CITATION ASSERTS WHAT THE CODE SAYS NOW; A QUOTATION ASSERTS WHAT A DOCUMENT SAID THEN.** Only the first can be a finding — a quotation that disagrees with the current code is doing its job, and "repairing" its line numbers destroys the record the quotation exists to keep. **The sweep above hits quotations by construction**, because it searches the cited file's `name:` and a quotation of that file's text carries the same `file:line` shape as a citation of it; there is no pattern that separates them, so the separation has to be made by reading what the sentence ATTRIBUTES. **The test: "the handler is X" is a citation and can be wrong; "the report said X" is a quotation and is wrong only if the report did not say it.** **DO NOT REPAIR A QUOTATION — check that it attributes correctly, then leave the text alone.** The first two instances are the a2635977 false clause, kept verbatim inside its own correction (`CHANGELOG/`, the pre-split `:18` and `:32`) exactly so the error and its fix both stay readable, and §5.4's block from `PROD_READINESS_REPORT.md`, whose ONE number (`mcp_routes.go:275`) is **the report's own, taken at `c4ff8d42`**, and stays as that dated record. **THE COUNTER-INSTANCE IS THE RULE'S OWN TEST, AND IT CAUGHT ME: that same §5.4 sentence had ALSO called `mcp_routes.go:116` the report's, and the report never carried it** — zero occurrences of `116` at `c4ff8d42`, `95ffca45` and `HEAD`, and `git log -S'mcp_routes.go:116' -- agenthub_go/PROD_READINESS_REPORT.md` EMPTY — **so OUR stale number for the `GET /mcp` registration had been dressed as the report's, which is precisely the failure this rule exists to prevent; §5.4 was corrected on the reviewer's gate of `56cabe97`+`e116a5cf` because of it. A number is not a quotation because the sentence around it says "the report's"; it is one because the SOURCE DOCUMENT CARRIES IT — check the attribution in the source, never in the sentence that claims it.** **A THIRD instance, and it is the rule proving itself: `CHANGELOG/`, pre-split `:1940` — the 2026-10-06 entry, "the project-creation contract stated" — quotes `app.go:135` and `:137-144`, the PRE-FIX state. By the test it is a quotation** ("the entry of 2026-10-06 said"), **it is kept as the dated record, and the live citation for the current state is the dated correction at `:38`.** **The reviewer cited that same line as `:1934` minutes before this paragraph was written; it reads `:1940` now because the two commits above it inserted six lines at the top of the file — the rot model demonstrated on a citation made and broken inside ten minutes, and precisely why a quotation is not "repaired" when the sweep lands on it: the repair would have chased a moving number through a record whose whole value is that it does not move.**
