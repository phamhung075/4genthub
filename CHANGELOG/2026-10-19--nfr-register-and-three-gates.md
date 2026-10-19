# The NFR register carries a status and a verification, and the context factory refuses

Date: 2026-10-19
Task: c1c3540b (`NFR register + three enforcement gates (NFR report 2026-10-19)`)

## What was wrong

`ai_docs/reports-status/NFR-analysis-2026-10-19.md` catalogued 43 non-functional claims with no
status vocabulary and no verification: 15 named a mechanism, scope or number the code contradicts,
20 were policy or weaker than claimed, 8 held. Nothing was the doc of record, so a reader had no
way to tell a gate from a sentence.

## What changed

**T1, this commit.** `ai_docs/core-architecture/nfr-register.md` is the doc of record: 43 rows, each
with a status from the seven-word vocabulary (GATE, CONFIG, POLICY, TARGET, GAP, STALE, PARTIAL), its
enforcement and a verification (`test:`, `cmd:`, `file:`, `review` or `none`), its owner and the
`measured` date. The ruling block records the four lead-tier decisions taken with the owner's
delegation: the register is the doc of record; OBS-04 states the client-side completion gate
(`RecordGateVerdict` stays callerless); SEC-04/PORT-01 state the guard boundary; a TARGET row cites a
baseline once measured. The two docs the report contradicted are corrected: line 348 of
`agenthub-system-architecture.md` (tenancy exceptions, the two nullable `user_id` columns, 11 cascade
FK columns across 10 tables) and line 619 (compaction is delivered by the runtime `ForceCompact` relay,
not the retired `forcecompact` binary); `seat-compaction-supervisor.md` drops the retired Python loop,
the binary and its `CAP_SYS_PTRACE` recipe. The report gains a SUPERSEDED marker.

**T2, commit `ffe4f07f` on `main`.** The context factory returns an error when the
repository builder fails instead of installing `MockUnifiedContextService`; the mock (and its test
helper) leaves the production package; `app.go`, `routes_mount.go` and `task_sweeper_wiring.go` take the
error path. The changelog the seat wrote rides that commit as
`CHANGELOG/2026-10-19--the-context-factory-refuses-instead-of-installing-a-mock.md`.

**T3, commit `02a31ec4` on `main`.** The external schema guard gains
`TestSchemaInventoryPinsTenancyAndCascades`: the 49-table union is counted, every `OnDelete` column must
have its line in `testdata/schema_fks.txt` (11 today, all `CASCADE`), and a nullable `user_id` must be
recorded in `testdata/user_id_nullable.txt` (2 today). Red on a removed cascade, a dropped nullable line,
or an unlinked table registerer.

Pending in this task: T4a (frontend typecheck + lint), T4b (CI gofmt/typecheck/lint plus
`agenthub_client` CI), T5 (benchmarks). Their commits extend this entry.

## Evidence

- `python3 scripts/CITATION-AUDIT.py`: rows 148, stale 0, unresolved 0, after the four legs applied.
- Legs 01-04 applied at hub `0a682479`, client `872ae41` (`git apply --check` clean for each).
- T2 claim-checked by the lead at `f8212aec`: `go build ./...` clean,
  `go test ./application/... ./server/httpapp/...` green, no mock reference in production Go.
- After both landings on `main` (`76eb8349`, `ffe4f07f`, `02a31ec4`): `go build ./...` clean and
  `go test -count=1 ./...` 138 packages ok, 0 FAIL.
