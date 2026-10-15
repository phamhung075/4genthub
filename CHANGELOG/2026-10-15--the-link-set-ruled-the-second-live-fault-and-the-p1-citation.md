# The link set ruled, the second live fault recorded, and P1's third-reach citation corrected

Three landings on the board, all of them answers the room is already acting on, and none of them code.

## Changed

- **§3 gains THE LINK SET, RULED — the surface, the set to serve, and the source of truth.** It answers
  go-dev's design question in full: **(i)** the surface it could not find is
  `GET /api/v2/rooms/<room>/seats/<seat>/links` — **HTTP 200**, re-measured by me: architect 3,
  lead 3, go-dev 3, fe-dev 2, reviewer 1 = **the plan's 12** links, kind-for-kind with §2's edge table
  (`/rooms/<room>/links` → 404, `/rooms/<room>/seats` → no links field, `/rooms/<room>/seats/<seat>` →
  405 PUT-only). **(ii)** the set to serve is **the 12 plus 11 additions**, derived from the room's own
  traffic — all **171** rail rows grouped by (source seat → destination seat) — because the 12 miss
  `reviewer → go-dev`/`fe-dev` (a gate verdict returns work to its author), the lead's questions and
  answers to every seat, `architect → go-dev`, and `reviewer`/`go-dev → architect`; the kinds are
  per-direction and `Decide`'s intent→kind map is quoted. **(iii)** the **local room definition** is the
  source of truth (the runtime already reads `spec.json`; the cloud copy is the dashboard's, reconciled
  by `drift-check`). **(iv)** `send` gains `--intent` with a **documented default of `notice`**, printed
  in the usage and recorded on the decision line, because a required flag breaks every existing caller.
  **(v)** the unit's ordering is approved — code on the branch, install waits for the links, and the four
  gate cases measured through the existing `--socket` seam against a lab room that declares **exactly one
  link** so case (b) is a real refusal.
- **The live-fault bullet now names TWO faults, and the second is `manage_task` — for EVERY task whose
  create poisons it.** It was "THE ONE LIVE FAULT REMAINS: THE CONNECTOR `400`" and is now two measured
  faults: the connector `400` as recorded, and `manage_task` mutations for a class of tasks. The second
  half carries the repro (`duplicate key value violates unique constraint "uq_task_event_seq"`, SQLSTATE
  **23505**, three attempts 05:02:33Z/35Z/43Z), what is **not** broken (`create` 05:02:29Z, `get`
  unchanged, and `delete`), the reading (per-task event-ledger state, the row created 04:41:51.738959Z
  with `updated_at` 26 ms later), **the scope — three tasks today (`81c907dc`; `b9eddb8e` at 05:17:41Z;
  `e5524d13`, where `complete` fails too) against the control `059eece4`, which has accepted updates at
  05:02:45Z, 05:03:18Z and 05:17:57Z, so the outcome is decided per task at create time and not by the
  clock, the seat or the tool** — the consequence (such a task cannot carry state and cannot even be
  closed, so the only repair a seat has is delete-and-recreate; the room's own unit tasks `b9eddb8e` and
  `bce0edd7` are of that class, so their record lives on the rail), the fix's shape (a deployed-server
  change; the owner approves every deploy, routed to the lead's rail row `e4265ca09e2d`), and the filing
  (go-dev, task `bce0edd7-…`, with acceptance). **Correction recorded in the same landing: the first
  version of this line said ONE TASK, which the second and third failures falsified — the datapoint was
  true and its scope was too narrow, so the scope is what changed; the per-task reading survived, because
  the control still writes.**
- **P1's third-reach sentence is corrected: the symbol it names does not exist.** The plan line cites
  "the `firstRigSession` reach in `agenthub_client/internal/clientsync/connectorverb.go:103`". At
  `892f867`, `firstRigSession` has **0 hits** in the client's Go; its only survivor is the CHANGELOG line
  recording its deletion; `connectorverb.go` is 315 lines and its `:103` is now the comment that records
  the deleted machine-wide fallback; the reaches the file carries are `rigSeatFor` (`:274`),
  `rigTranscript` (`:292`) and `rigSessionCandidates` (`:196`). The correction says nobody should
  implement against either name and that which primitive the third reach is remains open.
- **NEXT IN ORDER (iii) records why the C1 ruling is still blocked** — the defining row does not resolve,
  the rail's 171 rows only quote the phrase, the five transcripts carry the request and not the subject,
  no MCP task carries it, and the reach it most likely names is gone — plus **(iv)** where this landing
  put the three answers above.

## Instruments

- `GET /api/v2/rooms/4genthub-min/seats/<seat>/links` for all five seats → HTTP 200 each,
  counts 3/3/3/2/1 = **12**; the same route for the three spellings go-dev tried → 404 / 200-without-field
  / 405.
- All 171 rail rows, grouped by source→destination seat (the counts are quoted in the bullet).
- `manage_task` repro at 05:02:2x–4xZ, four calls with their outputs (the row text in
  `qitem-20261015050323-fd10cb71d524`).
- **The scope probes, and the control that keeps the reading honest:** `update` on `81c907dc` (fail),
  `update` on `b9eddb8e` at 05:17:41Z (fail), `complete` on `e5524d13` (fail), and `update` on
  **`059eece4` at 05:17:57Z (SUCCESS, its ninth progress block written)** — the same call shape that
  fails elsewhere, so the difference is the task, not the caller. `create`, `get` and `delete` succeed in
  the same minutes. **The successful write is itself in the record: `059eece4`'s Progress 9 names the
  re-probe and its purpose, so nothing was written anywhere as a throwaway.**
- `grep -rni 'firstrigsession'` over the client's `*.go` at `892f867` → **0**; the single survivor is
  `CHANGELOG.md:1015`; `wc -l internal/clientsync/connectorverb.go` → **315**; `grep -n '^func '` in it →
  `RunConnectorVerb:35`, `answersTo:180`, `rigSessionCandidates:196`, `candidatesFrom:216`,
  `entryIdentifiers:241`, `memberOf:257`, `rigSeatFor:274`, `rigTranscript:292`, `transcriptEvents:302`.
- **A trap worth recording, because it nearly produced a false claim:** the first `grep` was run inside
  this worktree's `agenthub_client/`, which is an **empty submodule dir** there — it returned 0 hits with
  no error and would have "confirmed" the deletion vacuously. The measurement above is from the real
  checkout (`/home/daihu/__projects__/4genthub/agenthub_client`), and `find` for the file is what exposed
  the empty directory.

## Not in this change

No code, no test, no pin: the diff is `NEXT-GEN2.md` plus this entry, so the landing stays a
fast-forward with nothing to build.
