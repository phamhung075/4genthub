# Per-seat thinking level rides the model selector suffix

`scripts/team/4genthub-min/team.json` now pins a thinking level per seat: `lead`, `go-dev` and
`fe-dev` at `deepseek/deepseek-flash:low`, `architect` at `deepseek/deepseek-flash:high`,
`reviewer` unchanged (`gemini-3.8-flash-low`, since `agy` is launched with `--model` only,
`rust/agenthub-runtime/src/runner/mod.rs:288`). Same model, same provider, same route; only
reasoning effort moves.

**Why these levels** (measured over 1h, 13:44:52Z): `lead` carried 31.0% of tokens and 60.0% of
turns; `go-dev` 43.4% and 79.5%, the highest in the room, and its slices are narrow and gated by
red tests, so the reviewer catches what low misses. `fe-dev` has no turns in the window but the same
seat type and work shape as `go-dev`. `architect` is pinned high explicitly rather than left to the
model default, because a ruling or schema error there is paid by every other seat. Room baseline:
39.4% of output tokens and 71.9% of turns carried thinking; the four suffixes are the lever the
acceptance gate compares against.

**Chain that carries it.** `team.json` `model` is copied verbatim into the spec the launcher sends
(`internal/clientteam/roomspec.go`, via `4genteam up --team`,
`internal/clientlifecycle/lifecycle.go:310`); the runner passes `seat.model` as `--model`
(`runner/mod.rs:120-122`, test `omp_argv_carries_the_seat_and_its_model` at `:2137`); omp resolves
`provider/model:level` and records `thinking_level_change` (measured on this box at `low`; running
seats record `high` today, the model default).

**Delivery is one act more than a reseat.** `reseat` restarts a seat from `rooms/<room>/spec.json`
(`supervisor/mod.rs:1036-1067`), and that file only gains models through `start_room` (`:621-632`) or
`set_seat_model` (`:1002-1014`). `up --team` sends the spec only when no seat of the room is running
(`seatStartPlan`). So the levels arrive by stopping the room and running
`4genteam up 4genthub-min --team scripts/team/4genthub-min`, which rewrites `spec.json` and starts
every seat from it. `4genteam sync switch <seat> --model <selector> --apply set-model` is the
per-seat alternative; it also PUTs a cloud occupant and the hub's acceptance of a suffix is not
established.

**Verified:** `clientteam.LoadRoomSpec` dry-run prints the four suffixes (exit 0); `omp --model
'deepseek/deepseek-flash:low'` writes `thinking_level_change thinkingLevel=low`; the runner argv test
expects the suffix verbatim.

Task: 925e02b3
