# Every open task state can reach blocked

**What this changes.** `value_objects.taskStatusTransitions` — the entity's own rule, and the one
`Task.UpdateStatus` enforces — gains the blocked edge from `todo`, `review` and `testing`.
`in_progress` already had it; `done`, `cancelled` and `archived` deliberately do not (a finished task
is pruned rather than parked, and `archived` is final).

**Why — the ruling.** The owner's ruling of 2026-10-15
(`ai_docs/development-guides/task-lifecycle-sweeper.md`, rule (c)) is that a task must end `done` or
`blocked` after it is created, and the lifecycle sweep enforces it by blocking a task that has stood
still at critical priority past `TASK_BLOCK_AFTER`. The sweep blocks **through `Task.UpdateStatus`** —
no direct SQL, no bypassed invariant — so a state without the edge cannot be blocked at all: a stale
critical `todo`, `review` or `testing` task stayed critical forever and the sweep reported a refusal
every interval. The domain's own `TaskStateTransitionService` rules table
(`domain/services/task_state_transition_service.go`) already carried all three edges; the value-object
table was the one that did not, so this closes an inconsistency rather than opening a hole. The two
alternatives were rejected: narrowing the guide to `in_progress`, or keeping the refusal as documented
behaviour, each makes the owner's "ends `done` or `blocked`" rule false for three of the four states
the sweep sweeps.

**The measurement it rests on.** Before the change the fixture case `todo → blocked` returned
`Transition failed: Cannot transition from todo to blocked`; the `Transition failed:` prefix is the
service's wrapper around the entity's refusal (`TransitionTo` → `Task.UpdateStatus`), so the service
allowed the move and the entity refused it. Two tables in the same domain, disagreeing.

**Consequence for the sweeper lane.** `4genthub-min/task-sweeper` (tip `e66c9543` when this was
corrected; the branch was rebased after this was written, so read the tip from the ref, not from
here) pins that refusal: three cases in `task_lifecycle_sweeper_test.go` carry `wantRefused`, and its
`Refused` counter and comments state that `todo`, `review` and `testing` may not reach blocked. Those
pins describe the state this removes, so they flip to blocks in the same window — otherwise that
branch goes red the moment this lands. **CORRECTED 2026-10-15, on the reviewer's gate of `2b75d092`:**
this lane **does** share a file with that one — `TEST-CHANGELOG.md`, one entry each, mechanically
harmless because each entry is its own line, but "no file that lane touches" was false and a landing
script would have acted on it. A sequence that lands both takes that file with both entries.

**Not in this change.** No sweeper, no guide, no instrument: the table and its comment, three fixture
expectations, the two test pins, and this entry. **The doc this makes stale is repointed separately:**
`ai_docs/core-architecture/agenthub-system-architecture.md` printed this rule's pre-ruling block, and
`4genthub-min/blocked-edges-doc-repoint` carries that repoint and the narrowed comment above.
