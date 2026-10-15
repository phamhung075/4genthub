# Item 4 is ruled: the server moves, the client does not

The owner's brief item 4 asked which side changes for two mismatches: the safeguard vocabulary the
client reports against the closed set the server accepts, and the field an error frame carries its
text in. The lead filed the ask (`qitem-20261015165615-7a39538d8efa`) with its own recommendation —
six names on the server, and the *client* reader changed to `error`. Two of those three clauses are
adopted; the third is reversed on measurement.

The board now carries the ruling where the next reader of §3 finds it, because the change inventory
belongs to a development seat and this note is what the room routes work against.

## Ruled

- **D1 — the server adopts the client's six names** (`compact`, `watchdog`, `messages`, `roomguard`,
  `bridge`, `agent`) **and `rigd` is deleted, not aliased.** The client is the only producer of these
  rows (`agenthub_client/internal/clientsync/agent.go:561-588`); the machine-level supervisor was
  renamed at `bc725e6`; the server's only use of the retired word is a dead-man alert keyed to a name
  no producer has sent.
- **D2 — `rig` is required (1..255) for the four rig-scoped names and exactly empty for
  `bridge`/`agent`.** Enforced in `validate()` (name first, then the scope's rig rule) **and** in the
  table CHECKs, because `rig` is part of the primary key: anything-but-empty would let one machine
  row exist under several spellings.
- **D3 — the error-frame field is `message`, and the server renames `error` → `message`.** This is
  the reversal. Dates read from git, not inferred: doc 2.2's ruled row (`ai_docs/core-architecture/
  rigd-boundaries.md:55`, commit `2004877a`, 2026-10-11 00:34) names `message`; the client reader
  (`agent.go:666-676`, `bc725e6`) reads `message`; the browser socket's own payload (`wsErrorData`,
  `agenthub_go/fastmcp/server/httpapp/ws_mount.go:603-606`) uses `message`. The lone dissenter is
  `wsConnectorError` (`ws_mount.go:619-626`, commit `6b0bdd5f`, 2026-10-02) — **older than the ruling
  it claims to implement**. 2.2's preamble about keeping frame names is about frame TYPES, not field
  names.
- **falsified before ruling:** the only in-tree readers of `error` on a connector frame are ten test
  assertions in two server files (`ws_rigd_test.go`, `ws_connector_test.go`); the u3 harness does not
  parse the field; the frontend has no error-frame path. So nothing outside the tests that pin the
  drifted key depends on it, and the client stays as it is.

## Shape of the change

Server-side plus doc-side only — **no client rebuild, no pin bump, no C4 re-acceptance**. 8 server
items (the ORM constants, `validate()`, the `.sql` CHECKs, the runtime `TableDef`, the module's first
migration `0001_six_safeguards_and_machine_scope.sql`, `raiseRigdDeadmanAlert` →
`raiseAgentDeadmanAlert`, `ws_mount.go:622`, and the test moves) and 6 doc deltas in `rigd-boundaries.md`
(7.2, 7.3, 7.4, 7.6, 7.7; 2.2 needs none). One server commit folds all three decisions into the deploy
the owner already owes.

## Not in this change

No code, no test, no schema, no pin: `NEXT-GEN2.md` plus this entry. Side findings are recorded and
deliberately **not** folded in — `clientservices.RigScoped` has no caller; doc 7.7's service table is a
different, unimplemented vocabulary; `wsErrorData` stays (browser socket, already `message`).
