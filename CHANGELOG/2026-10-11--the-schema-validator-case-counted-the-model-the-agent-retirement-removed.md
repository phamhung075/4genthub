## The PG half's two catches: the validator's model count, and a repository fixture that still used a retired role

### Fixed
- `agenthub_go/fastmcp/task_management/infrastructure/database/schema_validator_test.go`: `TestSchemaValidatorRealPostgres` asserted that the validator reports **16** validated models; the ORM now declares **15**, because `76b800b9` retired the `agents` model with the tool that owned it. The case failed with `validated_models = [Project ProjectGitBranch Task TaskDependency Subtask TaskAssignee Label TaskLabel Template GlobalContext ProjectContext BranchContext TaskContext ContextDelegation ContextInheritanceCache]` - fifteen names, all of them present, and the sixteenth gone by design. The count is an invariant rather than an incidental number (it is how this case notices a model added or dropped without the schema following), so the number moves with the ORM and the case stays, with the reason written beside it.
- `agenthub_go/fastmcp/task_management/infrastructure/repositories/subtask_repository_test.go`: `TestSubtaskRepositorySaveFindByIDAndIsolation` built its entity with `[]string{"coding-agent"}`, a bare role name the assignment rule now refuses - `Invalid assignees: ['coding-agent']. An assignee is '@<seat_key>'.` The value is incidental to that case's subject (save, find by id and user isolation), so it is one `'@'` assignee now, which the rule keeps verbatim; the case's own `reflect.DeepEqual` between the entity and the round-tripped row still holds.

### Why the earlier sweep did not catch it, and what did
- The case gates on `AGENTHUB_TEST_PG_URL` and skips loudly without it. `go test ./... -count=1` at `76b800b9` was **rc 0, 136 packages ok, no FAIL** precisely because this package's database-backed cases skipped - a skip is not a pass, which is why the lead's insistence on a run with the DSN earned its keep: the PG-gated pass on a clean export at `76b800b9` failed on this one case, and on nothing else in the five packages it reached before it was interrupted.

### Verified
- With the DSN (`postgresql://agenthub_user@127.0.0.1:55432/postgres`, a live cluster):
  `go test -count=1 -run TestSchemaValidatorRealPostgres ./fastmcp/task_management/infrastructure/database/` -> `ok 1.434s`, and the whole package -> `ok 27.565s`. `gofmt -l` on the package prints nothing.
- The failure was reproduced through the same command on a clean export at the unmodified commit before the fix, so the red is measured rather than inferred from the diff.
- The repositories fixture, measured the same way with the DSN: before the change `--- FAIL: TestSubtaskRepositorySaveFindByIDAndIsolation (3.29s)` with `subtask_repository_test.go:100: Invalid assignees: ['coding-agent']. An assignee is '@<seat_key>'.`; after it `go test -count=1 -run TestSubtaskRepositorySaveFindByIDAndIsolation ./fastmcp/task_management/infrastructure/repositories/` -> `ok 1.575s`, and `gofmt -l` on that package prints nothing. A module-wide grep for the retired bare role names in test files finds only refusal assertions and payloads whose subject is something else, so no second fixture of this shape is left.

### Found by
- The lead's order to measure the PG half of item 3's step-2 acceptance with the DSN, on a clean export at `76b800b9` (row `qitem-20261010202513-5be54f94a1e2c2ba`, the step-3 gate row `qitem-20261010214450-02d43b256d73c8c0`).
