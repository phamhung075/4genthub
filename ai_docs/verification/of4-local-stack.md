# OF4 local verification stack — bring-up recipe

**What this is.** Three local, throwaway services used to verify the frontend and the API by
driving a real browser: **Postgres on :54331, the Go server on :8000, the Vite dev server on
:3800**. It is scratch — nothing here is production, and no step needs the owner.

**Who paid for it.** fe-dev re-derived the stack on 2026-10-06 while verifying G6/T3 (row
`qitem-20261006162636-97dec2acda54c34f`); the full account of that run is
`OF4-G6-T3-2026-10-06.md` beside the rig's seat area (outside the repository). **Every
citation below was re-read in this tree by the writer seat on 2026-10-06**; the two items that
can only come from a live run are marked as such, and nothing is documented from prose alone.

---

## 1. Ports, paths, and the one untracked file

| piece | value |
|---|---|
| Postgres | `127.0.0.1:54331`, data dir `/tmp/of4pg/data`, socket dir `/tmp/of4pg/sock` |
| Go server | `0.0.0.0:8000` (`FASTMCP_PORT`), health at `GET /health` |
| Frontend | `localhost:3800` |
| Postgres binaries | `/home/daihu/.cache/agenthub-testpg/bin` — a local install; `pg_ctl` is the entry point |
| Browser | a managed headless Chromium driven with real navigation and real clicks |

**`agenthub-frontend/vite.of4.config.mjs` is UNTRACKED and deliberate** — `git ls-files
agenthub-frontend/vite.of4.config.mjs` → 0, and the file's own header says it is "TEMPORARY
harness config ... delete after use, never commit". It exists because the local server's
credentialed CORS is refused by the browser (so the app must talk to its **own** origin and let
this proxy reach :8000). Two things it must mirror from the project config or the app will not
boot: `resolve.alias` (`@` → `./src`) and React 19's global shim (`define: { global:
'globalThis' }`). Its proxy table sends `/api`, `/health`, `/mcp`, `/auth` (HTTP) and `/ws`
(`ws: true`) to `http://127.0.0.1:8000`.

## 2. Bring-up (the exact commands)

**Postgres:**

```bash
/home/daihu/.cache/agenthub-testpg/bin/pg_ctl -D /tmp/of4pg/data -l /tmp/of4pg/pg.log \
  -o "-p 54331 -k /tmp/of4pg/sock" start
```

**Go server** — build from this tree, then run it with this environment:

```bash
cd agenthub_go && go build -o /tmp/of4pg/agenthub ./cmd/agenthub
DATABASE_TYPE=postgresql DATABASE_HOST=127.0.0.1 DATABASE_PORT=54331 DATABASE_NAME=postgres \
DATABASE_USER=daihu DATABASE_PASSWORD=unused AUTH_ENABLED=false AUTO_MIGRATE=true \
DEFAULT_USER_EMAIL=dev@example.com AGENTHUB_PUBLIC_URL=http://localhost:8000 FASTMCP_PORT=8000 \
/tmp/of4pg/agenthub
```

`GET /health` must answer `healthy` with the version the binary carries
(the release literal is `ReleaseVersion`, `agenthub_go/fastmcp/config/version.go:21`, read into
`healthVersion` at `agenthub_go/fastmcp/server/httpapp/http.go:160`; **it read `0.0.21` in that run.
Corrected 2026-10-06 by the writer seat: this citation named line 159 of `http.go`, which is where the literal
lived when the run was made and where `origin/main` still holds it — the value has since moved into
`config/version.go`, and the old citation would send a reader to a reference rather than the value**).

**Frontend:**

```bash
cd agenthub-frontend && env VITE_DISABLE_AUTH=true VITE_API_URL=http://localhost:3800 \
  npx vite --config vite.of4.config.mjs
```

## 2a. The boot refusal this recipe was missing: the `0001_baseline` mark (measured 2026-10-12)

`AUTO_MIGRATE=true` is **not enough** on this stack. On the existing data dir AND on a brand-new
cluster the boot stops:

```
database: the catalogue already holds tables, so the 0001_baseline baseline is skipped without
running it (its schema is already there); use Runner.MarkBaseline to record it
database init: migration 0003_progress_history_carry_and_drop: the migration's SQL failed:
ERROR: the O1c carry step runs only under the owner's 0001 baseline mark; run
Runner.MarkBaseline('0001_baseline') first (SQLSTATE P0001)
```

**WHY, read from the code and not from the message:** `createAll` populates the catalogue **before**
the migration runner runs, so the frozen `0001_baseline` is skipped **without being recorded**, and the
gated carry step then refuses on a ledger that holds no `0001_baseline` row.
`fastmcp/session_stream/testdb/testdb.go` says exactly this and does the same thing for tests
("records that mark the way an operator does — `Runner.MarkBaseline`").

**The operator step**, in order:

1. `database.Runner{Sessions: database.NewSessionManager(cfg), Set: set}.MarkBaseline(ctx, "0001_baseline")`
   with `cfg` from `database.GetInstance(ctx, database.OSDeps())` and `set` from
   `database.LoadMigrations()`.
2. Boot the server as §2 says.

**There is no CLI verb for it** — `grep -rn 'mark-baseline' agenthub_go --include=*.go` matches no file —
so step 1 is a short `main` package run from inside the module with the same `DATABASE_*` environment.
Put it in a gitignored scratch directory (`.gotmp/` is one) and delete it after:
`go run ./.gotmp/<dir>` from `agenthub_go`. It prints `marked: [0001_baseline]`.

**A FRESH cluster works the same way and is the cheaper option when the old data dir's shape is not
wanted** (measured 2026-10-12; this is the cluster the S1 room-decision routes were verified on):

```bash
PGBIN=/home/daihu/.cache/agenthub-testpg/bin; D=/tmp/of4s1; mkdir -p "$D/sock"
"$PGBIN/initdb" -D "$D/data" -U daihu --auth=trust -E UTF8 --locale=C
printf "listen_addresses='127.0.0.1'\nport=54332\nunix_socket_directories='%s'\nfsync=off\n" "$D/sock" \
  >> "$D/data/postgresql.conf"
"$PGBIN/pg_ctl" -D "$D/data" -l "$D/pg.log" -w start
# then the mark from step 1 with DATABASE_PORT=54332, then the server from §2 with the same port
```

The fresh cluster has no `rooms` rows, so create the room the panel is to show **through the route**
(`POST /api/v2/openrig/rooms`, body `{"slug":…,"name":…}`, `Authorization: Bearer local-dev`) rather
than by hand.

## 3. TRAP ONE — every page renders "Not authenticated" with auth already disabled

`VITE_DISABLE_AUTH=true` bypasses **only the route guard**. Verified in the code:

- it is read once, at `agenthub-frontend/src/config/environment.ts:70`;
- its only consumer is `agenthub-frontend/src/components/auth/ProtectedRoute.tsx:19-22`, which
  returns the children early and does nothing else.

It does **not** make the API client authenticated, because the bearer is read from a **cookie**:
`agenthub-frontend/src/services/apiV2.ts:14-16` — `getAuthToken()` returns
`Cookies.get('access_token') || null` — and `getAuthHeaders()` (`:18+`) sets `Authorization`
from it. With no such cookie every `apiV2` request goes out unauthenticated and the pages render
"Not authenticated".

**The remedy**, run in the browser console before reloading:

```js
document.cookie = 'access_token=local-dev; path=/'
```

**Is any bearer really accepted?** Yes, because the server runs `AUTH_ENABLED=false`:
`authinterface.GetCurrentUser` resolves the **development identity for whatever bearer arrived,
without validating it** — stated at `agenthub_go/fastmcp/server/httpapp/ws_mount.go:94-100`
(which applies the same helper to the socket paths so the surfaces cannot drift), and
implemented through `fastmcp/auth/keycloak_dependencies.go:571-582` (`AuthEnabled()`, and
`DevUser` as the identity substituted when validation is off; its id defaults to
`dev-user-00000000-0000-0000-0000-000000000000` at `:584`, or to `DEFAULT_USER_ID` when set).

## 4. TRAP TWO — a second Postgres cluster against the same data directory kills the first, and `/health` stays green

**Observed, not re-run by this seat** (fe-dev's run, 18:31–18:32 CEST): a second postmaster
started against the same data directory reported

```
pre-existing shared memory block (key 937227, ID 0) is still in use
```

and the running postmaster then found `postmaster.pid` missing and performed an **immediate
shutdown**. Recovery in that run: restart Postgres, then the server; **no data was lost**.

**The trap is what the server does next: it hangs on the dead database connections — every
`/api/v2` call times out — while `/health` still answers `200`.** That is not a coincidence and
its mechanism is verifiable: **`handleHealth` reads no database at all**
(`agenthub_go/fastmcp/server/httpapp/http.go:162-183` — it reports `status`, `timestamp`,
`server`, `version`, `auth_enabled`, `connections` and `status_broadcasting`, then writes 200).
`/health` is therefore a **process-liveness** signal, never a readiness signal, and a green
`/health` over a dead database is exactly what its code predicts.

**Debug rule that follows: when a page or an API call fails while `/health` is green, check the
database before the server.**

## 5. What is session-scoped, and what survives

- The **Go server and the Vite dev server are session-scoped services of the seat that started
  them**, so they die with that session unless restarted from §2.
- **`/tmp/of4pg` (the data directory) outlives a machine stop.** The stack did not survive the
  17:17 stop, the data dir did, and §2 starts from it.

## 6. The data the run used

Room `of4room` with seats `alpha` (developer), `beta` (reviewer), `gamma`, and `blankmodel`
(model `''` — the deliberate empty-model fixture), plus a `4genthub-min rig mirror` room. The
repository's seeding entry point is `4genteam team apply [--team DIR]`
(**corrected 2026-10-09, writer seat: this named `scripts/team_setup.py`, a path absent
from the working tree and the index — the module is now
`agenthub_client/src/agenthub_client/team_setup.py` behind the `4genteam` console script. Measured
then: `4genteam team apply --help` is `[--dry-run] [--team TEAM]`, and `--dry-run` prints the plan
and calls nothing. The old citations `:77-82` and `:925-928` are struck with the path.**) **CORRECTED 2026-10-10 (writer seat, at the pinned client commit `eaa6ba7`): the module that correction names is itself retired — the client's Go port left no Python in the client at all. The live home is `agenthub_client/internal/clientteam/`, behind the same `4genteam team apply` verb.** — **the
exact invocation behind this room was not recorded
in the run account**, so treat that line as the repo's path rather than as the command that
made this data.

## 7. Launching a seat against the local stack

```bash
AGENTHUB_URL=http://127.0.0.1:8000 AGENTHUB_TOKEN=local-dev \
  4genteam sync rig of4room --out /home/daihu/.config/4genthub/agenthub-seats
cd /home/daihu/.config/4genthub/agenthub-seats/of4room/rig && rig up ./rig.yaml --yes --json
```

**The first command replaces `python3 scripts/seat_sync.py rig of4room …`, corrected
2026-10-09 (writer seat): that path is absent from the working tree and the index, while
`4genteam sync rig` is the same operation — measured then, its help is `room` with `--out` and
`--update` — and the environment pair it reads is unchanged.**

Then `rig ps --nodes --rig of4room --full --json` for the launched node's runtime, model and
session state.

**Four limits that cost real time in that run. Each is an operational note rather than a defect**
(their own rows exist where a fix is owed):

1. **`--out` must be the store the tmux-global-PATH `seatcheck` resolves to.** A seat's `HOME`
   is per-seat (`~/.config/4genthub/state/omp/<session>`), so the default store expands to a per-seat
   path and the checker gate **refuses the pull**. `/home/daihu/.config/4genthub/agenthub-seats` is
   where `~/.local/bin/seatcheck` points, and it passes.
2. **The rig build swaps in a fresh rig directory, so anything an operator placed inside it is
   deleted.** A `.env` symlink added to the rig directory was gone after the next build; the
   seats then launched with the correct value while the agent errored `No API key found for
   deepseek`. The rig root is documented to hold `.env`; pull/build do not create it.
3. **A model the page accepts may not be launchable.** In this omp build
   `deepseek/deepseek-chat` and `deepseek/deepseek-v3.2` resolve to the **openrouter** provider
   and `deepseek/deepseek-reasoner` to **zenmux**, all of which fail with no key;
   `omp models find deepseek` lists the models that map to the `deepseek` provider
   (`deepseek-flash`, `deepseek-v4-flash`, `deepseek-v4-flash-vision-exp`, `deepseek-v4-pro`).
   Nothing on the server path validates the model string: the only validator there is
   `resolver.CheckRuntime` (`agenthub_go/fastmcp/seat_management/domain/resolver/runtime.go:23`,
   called from `repositories/names.go:26` and `seatrenderer/renderer.go:45`), which checks the
   **runtime** only. *(The model→provider mapping is omp's, not this repository's.)*
4. **`GET /api/v2/seats/{room}/{seat}` carries the seat's `runtime` and rendered
   `files` but no `model` field** (keys: `files hash policy room runtime seat`), so a check for
   the occupant's *model* must read `GET /api/v2/rooms/{room}/seats` instead.

## 8. Teardown, as the run did it

Stop the member rig (`rig seat stop` / `rig down`), remove the scratch store directory
(`~/.config/4genthub/agenthub-seats/of4room`), and revert any occupant change to the fixture's value.
**Leave the Postgres data dir in place** unless you are done with the stack — it is what makes
the next bring-up cheap.

## See also

**A packet that changes schema needs one gate this page does not cover: the two-binary upgrade test**,
where the OLD binary builds the old schema and the NEW one migrates it — because **the fresh-database
boot described here proves the binary runs and proves nothing about migrations.** The procedure, its
assertions and the two practical facts are in **`schema-upgrade-gate.md`** beside this file.
