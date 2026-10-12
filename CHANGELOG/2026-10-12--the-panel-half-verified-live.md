# The sidebar's decision panel, verified live against the cloud route (slice 2, panel half)

2026-10-12. No source changed; this records a live verification and one stack-recipe fix.

## What was proven, and on what

The panel's decision channel (slice 1, `8178870a`) was driven against S1's own binary
(go-dev's `2634db82`, built to `/tmp/of4pg/agenthub-s1`) on the local stack, in a real browser:

- **Read**: `GET /api/v2/openrig/rooms/fe-dev-proof/decisions` → **200** — `{"decisions":[]}` on an empty
  room, which is how `AUTO_MIGRATE=true` creating `room_decisions` was proved *through the route*, with
  no client and no `psql`. With a row present the same route returns the contract's keys
  (`id, qitem_id, author_seat_key, summary, detail, questions, answers, state, created_at, answered_at`)
  and the panel renders the stored questions and options **verbatim**.
- **Click**: one `POST /api/v2/openrig/rooms/fe-dev-proof/decisions/{id}/answer` per question, **200**
  twice; the row's `answers` becomes `{"q1":"ship","q2":"lead"}` with `state: "answered"` and
  `answered_at` set. A click on the already-answered row is refused **409 `state-answered`**.
- **The panel's state**: the row's badge moves from `waiting for you` to `awaiting the room`, the footer
  reads "All questions answered - waiting for the room to apply it.", and the row **stays in the list** —
  the cloud's answer is not closure.
- Screenshots in the seat directory: `OF4-PROOF-2026-10-12-slice2-ask-pending.webp` and
  `OF4-PROOF-2026-10-12-slice2-awaiting-the-room.webp`.

## THE ASK ROW WAS SEEDED, NEVER MIRRORED

S1 mounts exactly two routes (`room_decisions_mount.go:79`, `:82` — the read and the answer); the ingest
route is S2's cloud half (`ARCH-DESIGN-room-decisions-cloud-lane-1-2026-10-12.md` §3,
`POST /api/v2/openrig/decisions` and its ack/state siblings), and S2's daemon half is blocked on the
owner's scope ruling (§4.2). No mirror exists anywhere to borrow: no decisions route in
`agenthub_client`, no room-decision code in the OpenRig daemon's `src`. S1's own pg test says it too —
"the row S2's ask route will create, written straight into the table because that route does not exist
yet" (`room_decisions_pg_test.go:73-74`).

So the ask for this proof was written **straight into `room_decisions` with that test's own seed INSERT**
(a scratch Go program under the tree's gitignored `.gotmp/`, deleted after; no repository file, no cloud
write). The **read and the click are genuine route calls**; the **row is seeded**. `resolved` is not
claimed: only the daemon's own resolution produces it, and no daemon connector exists yet.

## The stack fix this run needed

`AUTO_MIGRATE=true` alone does not boot this binary: `createAll` fills the catalogue before the migration
runner, so the frozen `0001_baseline` is skipped unrecorded and `0003_progress_history_carry_and_drop`
refuses. The recipe now carries the operator step and the measured fresh-cluster path —
`ai_docs/verification/of4-local-stack.md` §2a, committed as `f9dfab2b` with its own changelog entry.

## Teardown

Done: the S1 server stopped, both Postgres clusters stopped, the Vite dev server on `:3800` closed, the
browser tab released. The data directories `/tmp/of4pg` (the pre-S1 shape) and `/tmp/of4s1` (the
S1-verified one) are left in place; bring-up restarts from them via recipe §2 + §2a.
