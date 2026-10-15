# AGENTS.md told every seat to run a retired program

## What was wrong
`AGENTS.md` §1 ("Identity first") opened with **`Run `4genteam whoami --json``** and promised "your rig,
pod, member, peers, edges and transcript path". Measured 2026-10-14 19:5xZ on this box:

- `command -v rig` → `/home/daihu/.nvm/versions/node/v24.21.0/bin/rig`, a symlink to
  `../lib/node_modules/@reference/cli/dist/bin-wrapper.js`; `rig --version` → `0.6.10`. The old
  `~/.local/bin/rig → 4genteam` symlink is **gone** (go-dev measured the same).
- `4genteam whoami` → `daemon unreachable — topology and peer info unavailable. Node ID: — Session:
  agenthub--4genthub-min--lead Resolved: partial via session name`. The 4genteam daemon is retired;
  the answer is a partial identity and no peers.
- `4genteam whoami --json` → exit 0 with `identity{rigName, memberId, runtime, sessionName,
  logical_id, role, model}`, `peers[4]`, `edges{}`, `transcript{enabled: true, path: …}`.

So the one instruction every seat reads before it does anything pointed at a program the rig no
longer runs, and it named `pod`, an 4genteam concept the native room has no field for.

## Change
`AGENTS.md` §1 now reads `Run `4genteam whoami --json`` and promises "your rig, seat, peers, edges
and transcript path" — each of which the measured output actually carries.

## Scope
The rig repo's `AGENTS.md` only. The same defect survives inside the client under `skills/` and
`docs/AGENT-SETUP.md`, which is the client repo's C3 tranche and go-dev's; `9da3b5c6`
("remove the reference client mentions across skills and docs") touched this repo and bumped the submodule
pointer, but did not sweep the client's own skills, so e.g.
`agenthub_client/skills/share/development-team/SKILL.md:14` still says `4genteam whoami --json` and
`docs/AGENT-SETUP.md:404` still describes `4genteam whoami --json` as the startup check.

## Evidence
`git show --numstat` on the commit carrying this file; the two `whoami` invocations above.
