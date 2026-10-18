# The local verification stack's boot needs the `0001_baseline` mark

2026-10-12. Operator-visible: `ai_docs/verification/of4-local-stack.md` gained section 2a, "The boot
refusal this recipe was missing". No code changed; this is the bring-up procedure only.

## Why

With the S1 binary (go-dev's `2634db82`), `AUTO_MIGRATE=true` alone does **not** boot the local stack.
On the existing data dir and on a brand-new cluster alike, the boot stops:

```
database: the catalogue already holds tables, so the 0001_baseline baseline is skipped without running
it (its schema is already there); use Runner.MarkBaseline to record it
database init: migration 0003_progress_history_carry_and_drop: the migration's SQL failed: ERROR: the
O1c carry step runs only under the owner's 0001 baseline mark; run Runner.MarkBaseline('0001_baseline')
first (SQLSTATE P0001)
```

`createAll` fills the catalogue **before** the migration runner runs, so the frozen `0001_baseline` is
skipped **without being recorded**, and the gated carry step then refuses on a ledger with no
`0001_baseline` row. `fastmcp/session_stream/testdb/testdb.go` states this and performs the same step
for tests, describing it as what an operator does.

## What the recipe now carries

- The operator step: `database.Runner{...}.MarkBaseline(ctx, "0001_baseline")` over a config from
  `database.GetInstance(ctx, database.OSDeps())` and a set from `database.LoadMigrations()`.
- That **no CLI verb exists** for it (measured: `grep -rn 'mark-baseline' agenthub_go --include=*.go`
  matches no file), so it is a short `main` package run from inside the module.
- The measured **fresh-cluster** path — `initdb`/`pg_ctl` on another port, mark, boot — which is the one
  the S1 room-decision routes were verified on, plus the note that a fresh cluster's room is created
  through `POST /api/v2/openrig/rooms` rather than by hand.
