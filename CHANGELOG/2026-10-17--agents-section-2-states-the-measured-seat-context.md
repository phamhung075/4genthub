# AGENTS.md section 2 states the measured seat context

## What was wrong

Both bullets of AGENTS.md section 2 named instruments that no longer exist, and the ruling of record repeated
the same claims.

- **The role bullet** said a seat's role arrives as `agents/<seat>/agent.yaml` and `guidance/role.md`, written
  into the launch directory by the launch. The renderer's file half is retired and nothing writes either file.
  The role is the seat tier's skill, `agenthub_client/skills/rooms/<room>/<seat>/<seat>-role/SKILL.md`, which
  the runtime installs into the seat's own `skills/` at every start.
- **The skills bullet** said `4genteam seat reseat` replaces the seat's skills directory with a copy of the
  store's `rig/agents/<seat>/skills` (`clientseat/deliverSkills`, `skills_test.go`). That function is deleted
  with its test, the store side has no writer (`sync room` was its last), and the runtime's
  `install_seat_skills` writes the resolved client tree under the seat's own `skills/` at every seat start.
- **The ruling**, `ai_docs/core-architecture/seat-skills.md`, said `4genteam sync rig` was "the only delivery"
  and that it wrote `resources.skills` and `agent.yaml`. The verb does not exist, and neither file has a writer.

## Changed

- `AGENTS.md` section 2 - both bullets state the measured model: the role arrives as the seat-tier skill the
  runtime installs, and the client delivers nothing.
- `ai_docs/core-architecture/seat-skills.md` - a dated note supersedes the `sync rig` claims in sections 2, 3,
  5 and 6 and the two `sync rig` rows of its tests table; section 1's levels rule and section 5's launch
  configuration stand.

## Evidence

- The client's `sync` group holds `pull`, `messages`, `connector`, `bundle`, `switch`, `install-checker`,
  `offline-install` and `respawn` (`internal/clientsync/sync.go`); there is no `rig` verb.
- `install_seat_skills` (`rust/agenthub-runtime/src/supervisor/mod.rs:411` at client pin `f71becd0`,
  called from the seat start at `:733`, which also writes the seat's `mcp.json` at `:715`) runs at
  every seat start. Measured on this room after its seats' last start: each of the five live seat
  directories carries its own `<seat>-role` skill, and none has `agent.yaml`, `role.md` or `guidance/`.
- The store `<state-root>/rooms/<room>/rig/agents/<seat>/skills` does not exist on this box, so the deleted
  reader had nothing to read.
