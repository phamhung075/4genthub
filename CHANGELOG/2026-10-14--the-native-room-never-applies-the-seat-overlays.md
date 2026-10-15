## The native room carries the seat overlays and never applies them

### What was wrong
Measured 2026-10-14 on the live room `4genthub-min`, while briefing the seats.

- The team definition `scripts/team/4genthub-min/team.json` declares, per seat, `seat_overlays` naming that
  seat's guide and policy — `lead` → `guide-lead`, `policy-lead`; `go-dev` → `guide-go-dev`, `policy-go-dev`;
  `fe-dev` → `guide-fe-dev`, `guide-e2e-dev`, `policy-fe-dev`; `reviewer` → `guide-reviewer`,
  `policy-reviewer`; `architect` → `guide-architect`, `policy-architect` — and its `modules` list says where
  each slug's file is (`../../../agenthub_go/fastmcp/seat_management/domain/seedlibrary/blocks/guide-<seat>.md`,
  `policy-<seat>.json`). Every one of those files is present on disk.
- `internal/clientteam/roomspec.go:57-62` carries the slugs into the runtime's room spec as `overlays`.
- **The runtime stores them and never reads them again.** `rust/agenthub-runtime/src/types.rs:146` is
  `pub overlays: HashMap<String, Vec<String>>`, and `grep -rn overlays rust/agenthub-runtime/src` returns that
  line and nothing else (the only nearby hits are `company_overlay` in `context/mod.rs`, a different field).
  `agent_dir` is in the same shape: `types.rs:130` declares it, and the only other mentions are `None` in
  three test fixtures. The room's `spec.json` on disk therefore holds a populated `overlays` map while every
  seat has `agent_dir: null`, `cwd: null` and `permission_policy: null`.
- Consequence, in the seats themselves: `~/.config/4genthub/rooms/4genthub-min/seats/<seat>/` holds only the
  agent's own databases — no guide, no policy. The live go-dev and reviewer panes were observed hunting for a
  role guide (`grep -rl 'go-dev' /tmp --include='*.md'`; "the old rig dir is gone"; `local:agents/reviewer`)
  because the OpenRig-era launch directory `/home/daihu/.openrig/agenthub-seats/4genthub-min/rig` no longer
  exists and the native launch writes no replacement.

### Why it matters for the cutover
The five live seats run on `agenthub-runtime runner` **without the role guide and the per-seat permission
policy the rig defines**. C1's check is met (no `openrig`, no `pi-runner.js`, five seats running — see
evidence) and stays met; this is a different, silent loss of seat configuration that the OpenRig launch used
to perform, and it is invisible to every check that only asks whether a process is up.

### Not changed
Nothing was changed for this entry; it is a record. The repair needs a ruling — either the client resolves
the overlay slugs against the team definition and hands each seat a materialised launch directory, or the
runtime resolves them itself from a spec that carries the file paths rather than the slugs.

### Evidence
- `ps -eo pid,ppid,args | grep -E 'agenthub-runtime|pi-runner|openrig'`: five
  `agenthub-runtime --state-dir /home/daihu/.config/4genthub runner 4genthub-min/<seat>` processes under the
  room's tmux session, no `openrig`, no `pi-runner.js`.
- `4genteam up 4genthub-min --team <team dir> --room-only`: exit 0, five seats `running`.
- `cat ~/.config/4genthub/rooms/4genthub-min/spec.json`: `agent_dir`, `cwd`, `permission_policy` null for
  every seat; `overlays` populated.
- `grep -rn overlays rust/agenthub-runtime/src`: one line, the field declaration.
