## The mcptoolpath round-trip lookup is deterministic, because it was red on about a quarter of runs

### The finding
The reviewer's O4 verdict measured it at `d5a59667`: `fastmcp/server/mcptoolpath` was red on roughly a
quarter of runs at an **unchanged revision**, and red with a message that named a task id the test had not
read. That is the false-red shape `tools/testpg/start.sh` was hardened against, and the one a certification
battery cannot tell from a real red.

`acceptance_scope_tool_path_pg_test.go:207` found the created task with `findMapWith(createRes,
"acceptance_criteria")`, and the helper descended a `map[string]any` with `for _, item := range t` — a range
whose order Go **randomizes**. A create or update response carries that field TWICE: under `data.task` (the
entity, which has an `id`) and under `meta.operation_context` (the echo of the request, which does not).
Whichever branch the range reached first was returned, so `:213` read a nil map element and reported
`manage_task create returned no task id` about a response that plainly contained one.

Measured before the change rather than argued: 8 repeats of `go test -count=1 ./fastmcp/server/mcptoolpath/`
against a real PostgreSQL 16 on port 55451 — **5 PASS / 3 FAIL, 0 skips**, each failure reading
`acceptance_scope_tool_path_pg_test.go:213: manage_task create returned no task id:` with `data.task.id`
visible in the response the failure itself printed.

### The change
The helper, in the test file only; the product path is not implicated. Two rules now decide the answer, and
each closes one half of the defect:

- map keys are visited in **sorted order** (`slices.Sorted(maps.Keys(t))`), so no answer depends on a range;
- a match that carries an `id` **wins** over one that does not, because the entity payload is the one the test
  is about and the request echo is not.

When no match carries an `id` the first match in that order is returned — the old answer, made stable rather
than replaced. All six `findMapWith` call sites in the file inherit the fix.

### Tests
The case itself is unchanged. This was a defect in its helper, not in what it asserts, so no assertion moved.

### Verified
- `gofmt -l` on the touched file: empty.
- `go build ./...` rc 0; `go vet ./fastmcp/server/mcptoolpath/` rc 0.
- 12 repeats of `go test -count=1 ./fastmcp/server/mcptoolpath/` against the same cluster:
  **12 PASS / 0 FAIL / 0 skips**, against 5 PASS / 3 FAIL before.

A first attempt at the red was **invalid and is recorded because it is the trap**: the test-PG helper refused
to start on port 55432 (another seat's cluster held it) and every run **SKIPPED**, which reads exactly like 8
passes. `AGENTHUB_TESTPG_PORT=55451` produced a real cluster, and the skip counter is what separated the two.

### Found by
The reviewer's O4 gate (`GATE-O4-d5a59667-acceptance-scope-and-resume-brief-2026-10-11.md`), which named the
line, the mechanism and the measurement; routed to `go-dev` as `qitem-20261010231526`, high, before the freeze
because a package that is red on a quarter of runs poisons the certification battery.
