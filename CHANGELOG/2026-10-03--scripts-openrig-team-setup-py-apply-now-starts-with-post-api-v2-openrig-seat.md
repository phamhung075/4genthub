### Fixed

**openrig_team_setup.py apply failed with 404 seat type not found on a fresh database** (2026-10-03)

- `scripts/openrig_team_setup.py`: `apply` now starts with `POST /api/v2/openrig/seat-types/seed` (idempotent; the server needs `AGENTHUB_PUBLIC_URL`), because the team's seats name seat types that exist only after seeding. Before, a fresh database failed at the first seat with `HTTP 404 seat type "lead" not found` and the docstring did not mention the step. A failing seed stops the run before any other call.

**`AddVersion` lost-race re-read was too broad and hid its own error** (2026-10-03)

- `seat_management/infrastructure/repositories/orm/seat_type_repository.go` `AddVersion`: the winner is re-read only after a unique violation (SQLSTATE 23505), not after any integrity error (a foreign key violation is returned as it is), and a failing re-read is returned (wrapped) instead of being discarded.

**POST /rooms silently returned an existing room** (2026-10-03)

- `server/httpapp/seat_admin_mount.go` `handleCreateRoom`: an existing slug now returns 409 `room "x" already exists` (before: 200 with the stored room, the posted name silently discarded), the same convention as `POST .../seats`. This makes the `(409 exists: ok)` branch of `openrig_team_setup.py` for rooms live instead of dead.
- `seat_management/domain/repositories/names.go`: `ValidateRoomName`, 1 to `MaxRoomNameLength` (200) characters. The ORM column `rooms.name` is unbounded `TEXT`, so there was no ORM limit; 200 is a new domain rule. Before: a 5000-character name was accepted.
- Client note: the frontend `createRoom` now gets a 409 for an existing slug.

**Seat occupant accepted a Claude model on the codex runtime** (2026-10-03)

- `seat_management/domain/repositories/names.go`: new `ValidateOccupant(runtime, model)` (runtime, model pattern, and `claude-*` models only on `claude-code`); `SeatAdminService.SetOccupant` uses it, so `PUT .../occupant`, MCP `manage_seat set_occupant` and `openrig_seat_sync.py switch` get a 400 `invalid occupant: model "claude-..." is a Claude model and cannot run on the codex runtime`. The check is one-directional because claude-code also takes aliases such as `sonnet`.

**`TestFindProjectRootEnvAndUpward` failed under a TMPDIR inside the repository** (2026-10-03)

- `tools/tool_path_test.go`: the upward search tries `.git` before the other markers (documented order in Python `tool_path.py`), so the repository's own `.git` above the temp dir won over the fixture's `pyproject.toml`. The fixture now has its own `.git` directory. No production code changed.

**`TestFindProjectRootParity` failed under a TMPDIR inside the repository** (2026-10-03)

- `utilities/directory_utils_test.go`: case 2 returned the real repository root instead of `<R>/data`. `FindProjectRoot` (matches Python `_find_project_root`) walks up from the anchor and the real `agenthub_main` above the temp tree was found. The test now injects `Env.Exists` that only reports paths under the fixture root. No production code changed.

**Parser tests failed under a TMPDIR inside the repository** (2026-10-03)

- `parsers/rule_content_parser_test.go`: `TestParseMarkdownSections` and `TestParseJSON` expected `general` but got `agent`. `classifyRuleType` (a port of Python `_classify_rule_type`, unchanged) classifies on the lowercase absolute path, and the temp file lived under `agenthub_go/.gotmp`, whose name contains "agent". The two tests now use a relative file name (`writeRelTemp`, working directory = temp dir). No production code changed.

**Secret scanners miss URL credentials** (2026-10-03)

- `agenthub_go/fastmcp/seat_management/domain/secretscan/secretscan.go`, `scripts/openrig_scrub.py`: new pattern `://user:password@` (greedy to the last `@`, so a password containing `@` is covered). Before, `postgres://agent:pass@db/app` in a seat `detail` passed the server scan (200) and the bridge scrubber left it unredacted.
- Shared fixture `secretscan/testdata/scan_cases.json`: `url-credentials`, `url-at-in-password`, `url-plain` (no credentials, not flagged).
- Known limits: empty user or empty password (`://:pass@host`) is not detected; the Python `\s` is Unicode while Go's is ASCII, so exotic whitespace inside the userinfo can differ.

**Concurrent seat-type version creation returns 409, not 500** (2026-10-03)

- `agenthub_go/fastmcp/seat_management/infrastructure/repositories/orm/seat_type_repository.go`: when the insert of a seat type version hits the unique constraint because another writer took the same version, `AddVersion` re-reads the winner's row. Identical runtime and module refs return that row; anything else is `ErrSeatTypeVersionConflict` (HTTP 409).
