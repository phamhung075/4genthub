# The client pin carries the five seat roles in the seat tier

## Changed

- `agenthub_client` pin moves `191fbc9` -> `a2c1df3` (1 commit), fast-forwarded so the reviewer's gated sha
  is the landed sha.

### Added

- **The five seats' roles live in the seat tier** - `skills/rooms/4genthub-min/<seat>/<seat>-role/SKILL.md`,
  one per seat of this room (`lead`, `architect`, `go-dev`, `fe-dev`, `reviewer`). Each carries its seat
  type's role text, its rule names and its output format, ported from the hub's
  `seat-types/{lead,architect,developer,reviewer}.yaml` at the seed version the hub stamps today, `1.4.12`
  (the room's five seats run four types: `go-dev` and `fe-dev` are both `developer`). Each frontmatter
  carries `name`, `description` and `seat-type-version: 1.4.12`, and the body names the hub file it was
  ported from. This is the R1/R3 half of `seats/architect/RULING-seat-context-delivery-model.md`: the render
  is a resolution record, and the per-seat role ports into the one channel that is already delivered - the
  client skill tree's seat tier, which the runtime resolves for that seat alone and installs under the
  seat's own `skills/` at every start.
- **`skills::tests::a_seat_resolves_its_own_role_skill_and_no_other_seats`** (Rust), which reads the shipped
  tree through `SkillResolver::resolve_for_seat`: for each seat its own `<seat>-role` skill resolves, at tier
  `Seat`, from `rooms/4genthub-min/<seat>/<seat>-role/SKILL.md`; the frontmatter parses and names the
  version; the body still carries the type's role text, one of its rule names and its output format; **and
  no other seat's role skill is in the set** (the share tier still resolves in the same call, and `fe-dev`'s
  own `taste-skill` stays theirs).

### Changed

- **The client's render vocabulary drops the retired file half** - `skills/client/rig-runtime-switch/SKILL.md`
  and `skills/client/spawn-team/SKILL.md` no longer teach that the render delivers a seat's `agent.yaml`,
  `startup.files` or `guidance/role.md`; they state the measured mechanism instead (the runtime installs the
  seat's skills from the client tree and writes `<seat dir>/mcp.json` at every start).
  `internal/clientsync/seatpolicy.go`'s package header now names, with `file:line`, what writes a seat's
  files: `install_seat_skills` copies the resolved skill tree into `<seat dir>/skills/`
  (`rust/agenthub-runtime/src/supervisor/mod.rs:400`) and `start_seat` writes `<seat dir>/mcp.json`
  (`:704`). A grep for the retired names over `*.go`, `*.rs`, `*.ts`, `*.tsx` returns comments only.

### Not in this pin

- The Rust test's `TEST-CHANGELOG.md` section rides the L-2 hub commit, not this one (go-dev's park).
- Not installed and not pushed: after the pin, a seat still reads its role text twice (this skill and the
  render's `role.md`) until L-2 lands; build + reseat make any of it live for a seat.

Validated: gated PASS by the reviewer at `a2c1df3` (base main `191fbc9`, 1 commit, 11 files, row
`qitem-20261017004154-a09a652ec089`); its run: cargo `--offline` 167 passed / 0 failed (150 unit + 1
held_send + 15 seat_guard + 1 umask), `go vet` rc 0, `gofmt` clean, `go test -count=1 ./...` 32 packages ok
/ 0 FAIL. The five role texts were checked element by element against the hub's `seat-types/*.yaml`; the L-3
census holds (no code reads `guidance/role.md`, `agent.yaml` or `startup.files`); three falsifications of
the resolver test were run besides the row's own red (a planted cross-seat role, and malformed frontmatter).
