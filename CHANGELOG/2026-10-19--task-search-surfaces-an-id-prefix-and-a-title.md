# Task search surfaces an id prefix and an exact title

## Changed

- `agenthub_go/fastmcp/task_management/infrastructure/repositories/task_repository.go`,
  `SearchTasks`: the task id is now one of the columns a search word matches
  (`"id"::text ILIKE $n`, alongside title, description and label name). An exact 8-hex id prefix -
  the form a task is quoted in between seats - returns the task itself instead of only the rows whose
  text happens to quote that id.
- The same method orders a match on the WHOLE query ahead of a match on one of its words: id or
  title phrase first, then a description phrase, then the word matches, with `created_at DESC, id
  ASC` inside each rank. Before, ordering was `created_at DESC` alone, so an older task whose exact
  title was typed was paged out by newer rows sharing one common word - the false negative measured
  on the live hub (board `ea443b29`: `search("sanctioned seat channel delivers nothing")` returned
  ten rows and not the task with that title). Every existing filter (status, priority, assignees,
  labels, branch, user scope) is unchanged, and pages stay disjoint because the rank is deterministic
  and the id is still the tiebreaker.

## Tested

- `AGENTHUB_TEST_PG_URL=... go test ./fastmcp/task_management/infrastructure/repositories/ -run
  TestTaskRepoSearch -count=1` -> ok (both the existing search case and the new one).
- The new case fails against the pre-change repository with
  `Search id prefix ... did not surface the task first`, and passes after.
