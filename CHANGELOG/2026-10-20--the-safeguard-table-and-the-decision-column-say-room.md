# the safeguard table and the decision column say room, and the boundaries doc drops its old path

Slice B of `DECISION-2026-10-20-rig-gone.md`: the server stops storing and naming the retired unit.
`agenthub_client` is pinned to `133bbc7` (client main, slice A landed and pushed).

## What changed

- **The package and its files.** `fastmcp/rig_safeguard/**` is `fastmcp/room_safeguard/**`
  (`room_safeguard_orm.go`, `room_safeguard_tables.go`, `room_safeguard_postgresql.sql`,
  `room_safeguard_repository.go` and its tests).
- **The table, its columns and its constraints.** `rig_safeguards` is `room_safeguards`; its `rig`
  column is `room`; `ck_rig_safeguards_{state,safeguard,rig}` are
  `ck_room_safeguards_{state,safeguard,room}`; the index is `ix_room_safeguards_user_connector` and
  the primary key `room_safeguards_pkey`.
- **`room_decisions.rig_name` is `room_name`, and its answer-leg index follows it** to
  `ix_room_decisions_user_room_state_acked`. The DDL, the schema file, the Go `TableDef`, the
  migration set and the decision service's own column list all say the new name.
- **The pull's room filter survives the rename.** `GET /api/v2/decisions/answers` takes `?room=<slug>`,
  `Pull` and `ListAnswers` take the room and filter on `room_name`, and a pull that names no room is
  refused with `invalid-pull` rather than widened to the tenant: the ack is destructive, so a daemon
  handed another room's answers could not apply them and its ack would close a decision nobody
  applied. `room_id` stays as the FK the joins read and `room_name` as the daemon's delivery key; the
  ORM row says why both exist so a later cleanup does not unfilter the pull.
- **`0001_baseline.sql` is regenerated** from the `TableDef` registry, which is the source of truth;
  `0008_the_safeguard_and_decision_names_say_room.sql` carries the rename to a database whose
  catalogue already exists, guarded so a boot that reaches it before the registry creates the tables
  is a no-op rather than SQLSTATE 42P01.
- **One earlier step changes one word.** `0005` names the decisions column in an index statement, so
  the column rename makes a fresh boot fail before `0008` can run (`CREATE INDEX ... (rig_name)` on a
  baseline that no longer has that column, and PostgreSQL resolves the column list before its
  `IF NOT EXISTS` check). The statement carries `room_name`. It is a no-op on any database that
  applied the step (the runner skips it) and on a fresh database (0001 has already created the index
  under that name); only a database that stopped between 0004 and 0008 could miss the column, and
  that state does not survive a boot.
- **The retired `rig` case is deleted from the comm-guard**, with its test rows: a `room` command with
  `send|queue|broadcast` does not exist, so the arm could never fire and a rename would have invented
  a rule. The `tmux` arm, which is the channel a seat can actually reach, carries the rows.
- **`ai_docs/core-architecture/rigd-boundaries.md` is `agent-boundaries.md`**, and its eight hub
  citations (six Go files, `NEXT_GEN.md`, the doc's own naming note) name the new path. The
  frontend's nine citations are fe-dev's, already updated on their branch; they resolve when that
  branch lands.

## Slice D - the hub's live text says room, and its records keep rig

`ai_docs/**` and `AGENTS.md` no longer call the unit a "rig" in text a reader acts on: 251
word-bounded occurrences across 26 files and `AGENTS.md` before, 142 after, and every one of the 142
is a keep-list case rather than a leftover. The substitution is word-bounded and follows grammar
(`rigs` -> `rooms`, `the rig's` -> `the room's`), and it carries the live CLI spellings the client
actually has after slice A: `--room`, `<room>-<seat>@<room>`, `4genteam compact <room>`,
`4genteam up <room> --team <dir>`, `watch --room`, `feed --room`, `policy apply --room`.

What is deliberately still "rig", and why:
- **The retired binary and its verbs** - `rig up`, `rig whoami`, `rig ps`, `rig send`, `rig usage`,
  `rig parked`, `rig terminal open`, "the predecessor CLI's `rig`". A prohibition must name what it
  forbids (`AGENTS.md`'s "never legacy 4genteam" paragraph, the operator skill traps).
- **Dated measurements and snapshot records** - the 2026-10-06 OF4 local-stack account, the
  2026-10-09 policy-repair narration, the 2026-10-11 ecosystem review, the 2026-10-14 measurements in
  `watching-client-seats.md`. Renaming a record of what ran would falsify it.
- **Retired artifact names kept on disk** - `rig.yaml`/`rig-*.yaml`, the `rig/` materialized
  directory, `<store>/<room>/rig/agents/<seat>/skills`, `rig-runtime-switch`, `RIG_CONTINUE_WATCH`,
  `rig-continue.sh`, and the `sync rig` verb (retired, so it is named as retired rather than renamed
  to another verb that does not exist either).
- **`rigd`** is a different word - the component, renamed to `agent` on 2026-10-15 - and is not part
  of this count; it is the named follow-up.

Three commands the docs still taught do not exist - `4genteam sync rig`, whose only successor was
itself removed (`ai_docs/core-architecture/seat-skills.md`), and the recipe's provisioning step that
called it. Those rows are corrected rather than renamed: provisioning is `4genteam up`, which runs
`worktreeEnsure` before launching a seat (`internal/clientlifecycle/worktreesrow.go:176-178`), so
the new-project recipe and the troubleshooting catalog point at `up`, and the daily-operations
cheat-sheet row that only taught the retired verb is dropped.

The client's operator skills move with the same vocabulary: the seven live `<rig>` placeholders on
seven lines in `room-runtime-switch`, `seat-runtime-switch` and `spawn-team` read `<room>`, while
the ~12 named mentions of the predecessor stay as the prohibitions they are. The install skill's
symlink loop cannot be re-run from this seat - the seat guard refuses writes under `~/.claude` -
so the dangling `~/.claude/skills/rig-runtime-switch` link is reported to the lead, not moved.

## The component's own retired name: rigd -> agent

The unit's rename does not touch `rigd`, which is a different word - the always-on component the
client renamed `agent` on 2026-10-15 (`bc725e6`) - but the hub still used it for identifiers and live
prose. The `rigdb` import alias (3 files, 24 references) is `roomdb`; the dead-man sentences in
`ws_connector_safeguard.go` say the agent dead-man; the test helper `rigdHello` is `agentHello` and
the dead-man case is `TestAgentDeadman...`. The provenance sentences that record the rename itself
(`renamed from \`rigd\`, bc725e6`) stay, and so do the fixture ids (`user-rigd`, `rigd-capable`)
because they are data. `cursor_and_state_test.go` also stops citing `ws_rigd_test.go`, a file the room
slice had already renamed - that pointer dangled.

## Verification

- `cd agenthub_go && go test ./...` - green, and green again with
  `AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55433/postgres`, which runs the
  migration cases against a real PostgreSQL 16 instead of skipping them.
- `TestSchemaMatchesGoDefinitions` compares the migration set's indexes, constraints and columns with
  the runtime DDL: it is what caught `0005`'s stale column.
- `TestTheRoomNamesStepRenamesTheSafeguardTableAndTheDecisionColumn` builds the pre-rename shape by
  hand, applies `0008`, and asserts the table, the column, the three CHECK names, the primary key, the
  connector index, `room_decisions.room_name` and its renamed answer-leg index, that the stored rows
  are carried, and that a second application is a no-op.
- `TestPullMintsTheShippedCursorAndRefusesOneItDidNot` proves the argument the service passes, and
  `TestRoomDecisionPgThePullHandsOverOnlyTheRoomItNames` proves the SQL: one tenant, two rooms, one
  answered ask each, and a pull of one room's name carries that room's answer, never the other's,
  while an unnamed pull is the `invalid-pull` refusal. The fixture that writes an ask straight into
  the table now stores the room's own slug in `room_name` rather than the retired literal, because
  the pull keys on it. `TestTheRoomNamesStepIsANoOpWithoutItsTables` pins the guard.
- `TestTheSixSafeguardsStep*` still pass against the shapes `0004` was written for: that fixture keeps
  `rig_safeguards` and `rig` deliberately, because it reproduces history and `0008` is the rename.
- `grep -rIniE '\brig\b' ai_docs AGENTS.md | grep -v reports-status`: 251 before, 142 after, every
  remaining hit a keep-list case listed in the review.
- `python3 scripts/DOC-CITATIONS.py`: 49 docs, 732 citations, 0 violations after the prose pass.
- The client skills commit (`0094402` on `4genthub-min/d-skills`) changes three `SKILL.md` files
  only; `grep '<rig>' agenthub_client/skills` is empty afterwards.
- `scripts/gofmt-check.sh`: clean over 1247 tracked .go files (it was red on main: the rename had
  misaligned nine files, all formatting-only and fixed here).
- `grep -rn 'rigd' agenthub_go --include=*.go` outside tests: 0 except the three provenance sentences.
