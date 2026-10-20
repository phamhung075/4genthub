# INT-03: four child deletes move from the database cascade to the application

INT-03 (a GAP: "foreign keys carry no `CASCADE`; the application owns deletion") was resolved per
column by `RULING-int03-cascades-2026-10-19.md`. Seven cascades stay: a child that cannot outlive
its one parent keeps the database cascade. Four go, because the child spans two aggregates or is
billing state, so the delete is owned by the application and visible in its code.

- `task_contexts.task_id` (`models.go`): the task delete already removes contexts by `task_id`
  (`task_repository.go`). The branch delete did not, so `DeleteBranch` now removes
  `task_contexts` for the branch's tasks (step 9, from the ids it already read) before deleting
  the tasks. This also covers contexts with no `parent_branch_id`.
- `task_labels.task_id` (`models.go`): no new code - the task and branch paths already delete
  their task's label rows; they are now the only delete.
- `task_labels.label_id` (`models.go`): `DeleteLabel` now deletes the label's
  `task_labels` rows in one transaction before the label row.
- `user_token_balances.user_id` (`models_auth.go`): `UserRepository.Delete` now deletes the
  user's balance in one transaction before the user row.

The DDL strings and the `OnDelete` registry values match the schema golden
`testdata/schema_fks.txt`, which loses exactly the four lines; the two-direction pin
(`TestSchemaInventoryPinsTenancyAndCascades`) is green.

Tests: `TestGitBranchRepoDeleteBranchCascade` seeds a context with no parent ids and counts
`task_contexts` by `task_id`; `TestTaskRepoDeleteCascade` counts its context by `task_id`; the new
`TestLabelRepoDeleteRemovesTaskLabels` proves the join row is gone and the task survives;
`TestAuthUserRepositoryDeleteAndResetToken` seeds a balance and counts it by `user_id`.

Known, not fixed here (found by the ruling): the branch and project delete paths do not delete
`task_events`, so a branch whose task has events still fails on its own FK. That is a defect in
the branch path and belongs to its own task.
