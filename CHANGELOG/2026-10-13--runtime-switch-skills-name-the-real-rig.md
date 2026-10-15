# Runtime-switch skills and README: `rig` on PATH is the 4genteam shim

### Changed
- `agenthub_client/skills/client/rig-runtime-switch/SKILL.md`, `seat-runtime-switch/SKILL.md`: spec and node operations (`down`, `up <spec>`, `capture`, `parked`, `provider signals`) call the OpenRig CLI by path (`$OPENRIG`), because `rig` is a symlink to `4genteam` whose `down` is the machine-wide `stop`. `sync switch` only records the occupant; `seat reseat` is not a runtime change (it killed a seat and could not relaunch it). A teardown blocked by "no server running" is cleared with a throwaway tmux session. The 5-seat all-omp spec is `rig-architect-omp.yaml`.
- `agenthub_client/README.md`, `CHANGELOG.md`: `ps` added.

### Testing
- Steps were taken from the live 4genthub-min switch on 2026-10-13: all 5 seats read `omp` / `deepseek/deepseek-flash`, `ready`, afterwards.
