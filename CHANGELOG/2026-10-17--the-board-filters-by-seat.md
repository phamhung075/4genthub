## The board filters by seat, and the filter runs before the page cap

`useTaskFilters` has carried a tested assignee predicate since before the board needed it
(`setAssigneeFilter`, `applyFilters` matching `task.assignees.includes(filters.assignee)`, 7 cases),
but nothing rendered it: no page and no component imported the hook, and the board showed every task on
the branch. Finding one seat's work meant reading the assignee of each row by eye.

### Changed
- `agenthub-frontend/src/components/LazyTaskList/LazyTaskListRefactored.tsx`: the board builds its
  summaries for the whole task list, feeds them to `useTaskFilters`, and renders
  `applyFilters(taskSummaries).slice(0, TASKS_PER_PAGE)`. The page cap of 20 now runs AFTER the filter;
  before, a slice-then-filter order would have made a seat whose tasks start past row 20 read as
  "no tasks". The seat options are the assignees the board's own rows carry, in the same
  `@<seat_key>` form the assignment dialog offers, so the control needs no extra request and offers no
  option that matches nothing. The hook's predicate is unchanged.
- `agenthub-frontend/src/components/LazyTaskList/components/TaskListHeader.tsx`: a "Filter by seat"
  select beside Refresh, `All seats` by default, and the count reads `N of M` only while a filter hides
  rows. Both new props are optional, so the header keeps rendering for any caller that shows every task.

### Testing
- NEW `agenthub-frontend/src/tests/components/LazyTaskListSeatFilter.test.tsx`: renders the REAL board
  with 21 tasks, 20 owned by `@lead` and the 21st - past the page cap - by `@fe-dev`. Unfiltered, the
  fe-dev row is absent and the count reads `Tasks (21)`; selecting `@fe-dev` shows that row and
  `Tasks (1 of 21)`; back to `All seats` the capped page returns. The options are asserted as
  `['all', '@fe-dev', '@lead']`.
- Red first: with the order neutralised to `applyFilters(taskSummaries.slice(0, TASKS_PER_PAGE))` the
  case fails (`Tests 1 failed`); restored, it passes.
- RUN: `npx vitest run src/tests/components/LazyTaskListSeatFilter.test.tsx
  src/tests/components/LazyTaskListAgentLoading.test.tsx src/tests/components/LazyTaskListDialogOpen.test.tsx
  src/hooks/useTaskFilters.test.ts` = 4 files, 13 tests, 0 failed. `npx tsc --noEmit -p .` exits 0 with
  no `error TS`. No local vite build (the seat guard refuses it), so the running-stack visual is not
  taken; the rendered board is the surface this commit proves.
