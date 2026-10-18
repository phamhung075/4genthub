# `manage_task` reads the prefix the room cites, and its filters have one spelling

Board task `1f0ae722` (lane hub-go). The task store could not be READ by the instruments that cite
it: an 8-hex id is how every handoff, queue row and changelog in this room names a task, and it was
neither an address nor searchable text; and `list`/`search` published two spellings of the same
filter while honouring only the one the schema buried (`assignee`/`tag`) - so the plural spelling
that `create` takes was silently dropped and answered with the whole board.

The lead tier answered the shape question (`4genteam decide --tier lead`): `hex_address=read_only`,
`assignee_filter=plural`. This change implements exactly that.

## Changed

- `fastmcp/task_management/interface/tool_input_schemas.go`,
  `.../manage_task_description.go`, `.../factories/operation_factory.go`: the singular `assignee`
  and `tag` leave the published `manage_task` schema, the parameter description and the list/search
  allowlists. There is no alias and no dual path: `assignees` and `labels` are the one published
  spelling for both write and read, and the allowlists now carry them, so the filter reaches the
  request instead of being stripped before the handler.
- `.../handlers/search_handler.go`, `.../handler_adapters.go`: `ListTasks`/`SearchTasks` take
  `assignees []string, labels []string` instead of the singular pointers and their
  `[]string{*assignee}` rewrite. `adapterKwStringList` accepts the array or the comma-separated
  string the schema documents and preserves the absent key as "filter nothing".
- `application/facades/task_application_facade.go`: `readableTaskID` resolves the read-only address
  form - 4 to 31 hex characters with no dashes - through the repository's criteria query, so the
  identity scoping every other read gets applies here too. One match returns the canonical id; no
  match leaves the caller's own not-found answer in place; an ambiguous prefix is REFUSED with up to
  five candidate ids named, because the caller's next move is to pick one. `get` and `resume` resolve
  a prefix; the writers do not - they still call `value_objects.NewTaskId` on the caller's own
  string, so a prefix can never mutate anything.
- `infrastructure/repositories/task_repository.go`: `taskRepoCriteriaWhere` gained the `id_prefix`
  condition (`"id"::text LIKE $n`) with no ordering requirement, because eligibility is not identity.
- `fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md`: line 7 quoted the
  removed singular spelling; it now quotes `assignees`. The block is a seed (guard: byte-for-byte
  `guides.lock.json` plus `seedcontent.lock.json`), so the entry's two digests were re-recorded and
  `seedVersion` moved to `1.4.17` with its `seedcontent.lock.json` record.
- `interface/testdata/tools_golden.json`: the two removed properties leave the golden.

## Tests

- `fastmcp/server/httpapp/mcp_task_read_contract_pg_test.go` (new): against a real Postgres through
  the real `POST /mcp` route - `assignees` as an array and as a comma string select the same two
  rows, `labels` selects one, the schema publishes neither `assignee` nor `tag`, a request still
  carrying `assignee` filters NOTHING (the alias is gone, not silently honoured), `get` resolves a
  unique 8-hex prefix, an ambiguous prefix is refused and names both candidate ids, and `complete`
  with a prefix is refused with the row's status unchanged.
- `guides.lock.json` / `seedcontent.lock.json` are read at load, and the seedlibrary, seedmap and
  interface goldens now pass unchanged.

At this change: `go build ./...` clean; `go test ./fastmcp/task_management/... ./fastmcp/seat_management/...`
pass; with `AGENTHUB_TEST_PG_URL` set the new httpapp cases and the tool-golden cases pass. The two
`TestLedgerIntents*` cases in the same httpapp package are red for a reason outside this change
(their `claimed` kind and free-form `handover` payload were removed by `a373feec`); they are reported
as a finding rather than repaired here.
