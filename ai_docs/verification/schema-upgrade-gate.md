# Schema-upgrade gate — REQUIRED for any packet that changes schema

**What this is.** The **two-binary upgrade test**, on the team's gate list because the owner asked for
it in those words:

> *"I added one check beyond your gates, an UPGRADE test: I booted `origin/main` with `AUTO_MIGRATE=true`
> on a scratch embedded Postgres to create the old schema (rooms had no `team_id`, no `seat_feedback`),
> then booted `fcd4c268` on it twice: healthy 0.0.22, `rooms.team_id` plus FK plus index added,
> `seat_feedback` plus its CHECK created, second boot idempotent. Your fresh-database boot cannot show
> this, and production runs `AUTO_MIGRATE=true` on an existing database. Then I confirmed read-only on
> production: `rooms.team_id`, `seat_feedback` and `ix_rooms_team_id` all exist, 2 rooms rows untouched.
> Please add the upgrade test to your gate list for any packet that changes schema."*

**WHEN IT APPLIES: any packet whose commit set changes schema** — a new table, a new column, a new
constraint or index, or a changed default. **It is a REQUIRED step, not an optional one.**

## WHY IT EXISTS — the sentence that decides it

**A FRESH-DATABASE BOOT WITH `AUTO_MIGRATE=false` PROVES THE BINARY RUNS AND PROVES NOTHING ABOUT
MIGRATIONS.** The boot gates the team already runs (§ the OF4 recipe) start an empty database, so the
schema is built by `createAll` from the runtime `TableDef`s and **no upgrade path is exercised at all**.
**Production is the opposite case: it boots an EXISTING database with `AUTO_MIGRATE=true`**, so the
only code path that matters there — applying a delta to a schema that already has data — is exactly the
one the fresh boot never touches. **The gate exists to exercise that path.**

## THE PROCEDURE, in the order the owner ran it

1. **A scratch database, created through Python.** This box has **no `psql`, `createdb` or `dropdb`
   anywhere on `PATH`** (checked: also absent are `pg_ctl`, `initdb` and `postgres` — **the server
   binaries exist only in the local install at `/home/daihu/.cache/agenthub-testpg/bin/`**, which
   carries `initdb`, `pg_ctl` and `postgres`), while **`psycopg2` IS installed (2.9.11 on Python
   3.14.0)**. **So the recipe must drive Postgres through Python rather than through shell clients** —
   `CREATE DATABASE` and `DROP DATABASE` go through `psycopg2` with autocommit, against the running
   scratch server.
2. **THE OLD SCHEMA, made by the OLD binary:** boot the **old** commit (`origin/main` at the time, i.e.
   the deployed tip) with **`AUTO_MIGRATE=true`** against that scratch database. The result is the
   *pre-packet* schema — for packet 4, `rooms` **without** `team_id` and **no** `seat_feedback`.
3. **THE UPGRADE, made by the NEW binary:** boot the **new** commit (the packet's tip) against the same
   database, and assert **the delta the packet promised**: for packet 4 that was **`health` healthy
   `0.0.22`**, **`rooms.team_id` plus its FK plus its index added**, and **`seat_feedback` plus its
   CHECK constraint created**.
4. **IDEMPOTENCE, which is the half a single boot cannot show:** boot the new binary a **SECOND time**
   against the same database. **The second boot must be clean** — same schema, no error, no duplicate
   object. *(For packet 4 the owner reports it was.)*
5. **TEARDOWN, and this one is a correctness rule rather than tidiness:** **DROP the scratch database
   afterwards.** **A scratch database left migrated will make a later run pass VACUOUSLY** — the "old"
   binary would meet an already-new schema, step 3 would assert a delta that was already there, and the
   gate would report green having tested nothing.
6. **THE PRODUCTION READ, which is a separate step and needs the owner's window:** read-only,
   confirming the delta exists on the real database and that the pre-existing rows are untouched. For
   packet 4: **`rooms.team_id`, `seat_feedback` and `ix_rooms_team_id` all exist, and the 2 `rooms` rows
   are unmodified.** **This step does not replace steps 2–4: it reads a state, it does not exercise the
   transition.**

## WHAT THIS GATE ADDS TO A PACKET'S DOCKET

A packet's docket (see `PACKET4-PUSH-DOCKET.md` for the shape) carries the ordinary gates plus the
boot. **A packet that changes schema carries this one as well, and the docket must say which of its
numbered steps ran, against which two commits, and on which database** — because "the upgrade gate
passed" without those three is not a measurement.

## PROVENANCE

| Part | Whose |
|---|---|
| the requirement, the procedure and the packet-4 assertions and readings | **the owner's** measurement, quoted above |
| no `psql`/`createdb`/`dropdb` on this box; the local server binaries' path; `psycopg2` 2.9.11 present | **verified by this seat** on 2026-10-06 |
| the reason the fresh boot cannot show it | **the owner's**, and independent of the recipe (the fresh boot builds from `createAll`) |
| the drop-afterwards rule | **the owner's** practical fact, recorded because the next run inherits the database |

## Related, and deliberately not duplicated

- **The OF4 local verification stack** (`of4-local-stack.md`) — the ordinary boot gates and the stack
  this gate's scratch server can come from.
- **`agenthub_go/NEXT_GEN.md`** — the schema/DDL rules (the parity guard, the defaults rule) and the
  deploy-packet DDL gate for the `mcp` kind's sixth value.
- **`DO NOT` copy this procedure into the product's documentation** (README, guides): the owner asked
  for it on the **gate list**, and a public page describing how we verify a schema upgrade is not part
  of what a user needs.
