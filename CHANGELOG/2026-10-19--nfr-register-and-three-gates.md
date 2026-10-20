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

**T5, commit `81074bd6` on `main`.** `unified_context_bench_test.go` adds `BenchmarkResolveContext`
(19.0-26.0 us/op across two runs, 212 allocs/op) and `BenchmarkTaskEventFrame` (1.4-1.8 us/op,
25 allocs/op) on an i7-12700F; the register's PERF-02 and PERF-05 rows cite the command, the landed
commit and the host, and state the range rather than one number.

**T4b, client half, commit `81abcf6` on client `main`** (hub pin `8407df92`): the client repo gains
`.github/workflows/ci.yml` with a go job (`go vet`, `go test`) and a rust job (`cargo test --locked`).
**T4b, hub half, commit `fe64381f` on `main`** (cherry-pick of `beff2fb7`): the go job runs
`../scripts/gofmt-check.sh` before vet and test, and the frontend job runs `pnpm typecheck` and
`pnpm lint` between install and test. The gate started red - `context_change_test.go` was unformatted
on `main` - so the same commit carries the formatting; `gofmt-check` then reports `clean over 1242
tracked .go file(s)`, exit 0.

**T4a, commit `45fbd0cf` on `main`** (cherry-pick of `408a304c`): `agenthub-frontend` gains its
`typecheck` (`tsc --noEmit -p .`) and `lint` (`eslint src --max-warnings=0`) scripts, the dead CRA
`eslintConfig` block goes, and `eslint.config.mjs` carries `@eslint/js` + `typescript-eslint` +
`eslint-plugin-react-hooks` recommended over `src` with no baseline and no allowlist. 167 files: the
`any`s are replaced by the API's own types (`BranchLike` in `src/types/api.types.ts`), envelopes are
narrowed where they arrive, `catch (error: any)` becomes `unknown` plus a real narrowing, two
`useEffect` dependency arrays are corrected, and `useWebSocketV2` reads the client through its public
accessors. One test that asserted an impossible state (`onSelect: undefined` on a required prop, which
left an unhandled `TypeError`) is deleted, so the suite is 131 files / 1925 tests. Ledgers:
`CHANGELOG/2026-10-19--the-frontend-typecheck-and-lint-gates-run-clean.md` and the `TEST-CHANGELOG.md`
entry.

Both halves are in place, so `ci.yml`'s two new steps call scripts that exist; measured on `main` after
the landing: `pnpm install --frozen-lockfile` ok, `pnpm typecheck` 0, `pnpm lint` 0 problems, `pnpm
test` 130 files / 1920 tests, 0 failures. (The seat measured 131 files / 1925 tests on its own base
`cad91428`, which carries the frontend line's extra test files; `main` does not have those commits.)

## Evidence

- `python3 scripts/CITATION-AUDIT.py`: rows 148, stale 0, unresolved 0, after the four legs applied.
- Legs 01-04 applied at hub `0a682479`, client `872ae41` (`git apply --check` clean for each).
- T2 claim-checked by the lead at `f8212aec`: `go build ./...` clean,
  `go test ./application/... ./server/httpapp/...` green, no mock reference in production Go.
- After both landings on `main` (`76eb8349`, `ffe4f07f`, `02a31ec4`): `go build ./...` clean and
  `go test -count=1 ./...` 138 packages ok, 0 FAIL.
