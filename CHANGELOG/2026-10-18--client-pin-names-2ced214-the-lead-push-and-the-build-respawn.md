# Client pin names 2ced214: the lead push and the build respawn

The `agenthub_client` gitlink moves from `4b24c15` to `2ced214`, the merge of the two client branches
that the reviewer held and the lead landed:

- `9d95b29` - the lead may push. `internal/clientguard` and the runtime's `seat-guard.ts` admit the
  lead seat through the canonical session spellings (`agenthub--<room>--lead`, `<room>-lead@<room>`)
  and keep the refusal for every other seat; a force push stays git-destructive for the lead too.
- `8b7ad75` - `scripts/build.sh --respawn` and `up --respawn`: the install stops agent, stops only the
  runtime daemon whose argv names this state root and waits it out, then starts the room from its own
  record. A running daemon keeps the binary it was started with, so this is the one step that puts the
  team back on what was just installed.

The merged client main also carries the two hub-side docs commits it already had (`3a6eacc`,
`8ddad91`). Tests at the merge: client `go test ./...` rc 0 (35 packages), `go vet ./...` rc 0,
`cargo test --offline` 205 passed; hub `go test ./...` rc 0 (138 packages) and the two policy pytest
files 19 passed.

Task: 60e2ef5b-b42c-4d1c-881b-b411977b7499
