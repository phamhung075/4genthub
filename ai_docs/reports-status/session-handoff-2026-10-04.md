# Session handoff — 2026-10-04 (principal session 965d22d8)

Written to close the principal Claude session and let a later one resume without re-deriving
anything. Read top to bottom before acting. Verified facts and pending work are separated on
purpose; do not treat a pending item as done because it is written down.

## 1. Pending, in priority order

1. **Push to production.** Owner approved it on 2026-10-04. Two `git push origin main` attempts
   were refused by the harness classifier (stage-2 transient error, not a policy denial), so the
   push was left to the owner. The range is ~67 commits.
   **Update (later, 2026-10-06): LANDED — this item is CLOSED, not still waiting on the owner.**
   The push HAPPENED: `origin/main` = **1b4ce29b** (measured with `git ls-remote origin main`), and
   production `/health` reported **0.0.19 healthy** with the dashboard bundle moving to
   `assets/index-C6aQWb05.js`. The paragraph above is kept AS WRITTEN so the transition stays
   visible — pending, then landed — the same shape items 2 (T6) and 5 (`call_seat`) already use.
   **Preconditions are VERIFIED, not assumed:** production `seats` has **no** `status` column and
   **has** `permission_policy` (the two G1a requirements that would otherwise make create-seat
   return 500), read from `srv-captain--4genthubdb.1.73k3ki67xpxx27sj5mejo9ueq` on host `4genthub`
   with owner authorization. `healthVersion` is bumped **0.0.12 → 0.0.13** in
   `agenthub_go/fastmcp/server/httpapp/http.go` and `http_health_test.go`; production reported
   0.0.12 before the bump, so the deploy is confirmable. After pushing, poll
   `https://api.4genthub.com/health` until it reports 0.0.13. **[SPENT — measured 2026-10-06: the push landed and this check was satisfied by a LATER marker, production reporting **0.0.19** after packet 1; the instruction is kept as the form the check took at this date, not as something still to run.]**
2. **T6: remove `call_agent`.** D1 is decided (owner, 2026-10-04): a new tool named **`call_seat`**,
   served from the seat model; implemented and committed as `2740697e`. `call_agent` is untouched
   and must go — T6 also carries its routes, `-seed-agents`, the library path utils and the
   `agent_library_dir` health field. Two tools for one job must not coexist.
   **Update (later): T6 landed.** The `call_agent` tool, its routes, `-seed-agents` and the
   library-path utils are removed (commits `b0d441bd`, `60bcdb68`); `call_seat` is the published
   seat-call tool now — do not treat this item as still pending.
3. **The `runtime: agy` registry drift.** `rig ps --nodes --json` reported `runtime: agy` for the
   nine `4genthub-dev` seats while those seats emitted Claude statusline samples. Fixing it needs
   `rig down` + `rig up` from a corrected spec because OpenRig cannot switch a runtime in place.
   `4genthub-dev` has since been deleted from OpenRig entirely, so the drift now applies to
   whatever rig is rebuilt from that room.
4. **Cloud/runtime divergence.** The cloud room `4genthub-dev` still holds 9 seats (all `agy`,
   all `yolo`); the runtime now runs a 3-seat `4genthub-min` team as the dev team **[count stale 2026-10-06: it is **10 seats** — see §3's measurement; the cloud half of this item is NOT-CHEAPLY-CHECKABLE from this seat, since the cloud room's seat count needs the cloud/owner surface]**. Reconcile or
   retire the room.
5. **`call_seat` is not on production** until the push deploys. Anything on production that calls
   MCP tools cannot see it yet.
   **Update (later): superseded** by item 2's update — T6 landed and `call_seat` is the published
   seat-call tool. **[Also measured 2026-10-06: the push LANDS this code — `2740697e` and the T6 removals are ancestors of `origin/main` — so the production half is satisfied too by the push item above. Whether production's MCP surface currently lists `call_seat` is NOT-CHEAPLY-CHECKABLE from this seat: it needs a production call this seat's rules forbid.]**

## 2. What landed on 2026-10-04 (then local and unpushed — **since PUSHED**, 2026-10-06)

`2c8d05f3` omp runtime added to the one runtime list; `f66d25a4` every client-side runtime list
made to match the server (frontend `SEAT_RUNTIMES`, `openrig_seat_sync.py`, `openrig_bridge.py`);
`4376846a` `omp` added to the renderer's no-runtime-fragment assertion (proven by mutation);
`4e44899e` `healthVersion` 0.0.13; `2740697e` the `call_seat` tool. Plus `docs(next-gen)`
commits recording omp support, the 167-hour agy limit, the per-seat usage finding and the
review-worker correction.

**Local only, deliberately NOT committed** (project rule): `CLAUDE.md` and `.claude/`. Both were
edited on 2026-10-04 and the edits were live in the working tree:

> **STALE HALF (measured 2026-10-06): `CLAUDE.md` no longer exists.** `ls CLAUDE.md` fails at the repo root, and a glob finds only `CLAUDE.local.md` and `ai_docs/claude-code/*` — so every edit described below describes a file that is gone. **The `.claude/` half still holds:** `.claude/hooks/session_start.py` contains `rig whoami`, and `.claude/hooks/utils/role_enforcer.py` contains no `call_agent`. The project rule itself (never commit `CLAUDE.md`/`.claude`) is unaffected.
- `CLAUDE.md`: the "ABSOLUTE FIRST PRIORITY" block now says *know which seat you are* — run
  `rig whoami --json`, reach the team with `manage_seat`, and **do not call `call_agent`**
  (it answers "template not found" for every name on production). Also the quick reference, the
  MCP tool list, the permissions table, Tier-3 step 4, the teammate template, and
  `DYNAMIC TOOL ENFORCEMENT` → `TOOL SCOPE BY SEAT`.
- `.claude/hooks/session_start.py`: the MANDATORY FIRST ACTIONS banner now names `rig whoami`
  and `manage_seat`. `.claude/hooks/utils/role_enforcer.py`: the `[NO ROLE]` warning no longer
  points at `call_agent`, and `call_agent` left its allow-list.

## 3. Live state at handoff

```
2 rigs · 4 seats · 0 need attention
4genthub-min       3/3 running — lead idle · go-dev working · reviewer working
4genthub-deepseek  1/1 running — the supervisor, self-parking on its queue item
```

**MEASURED 2026-10-06 (`rig ps`, `rig whoami --json`) — the block above is the handoff's own snapshot and three of its lines have since moved:**
- **`1 rig · 10 seats · 0 need attention`** — `4genthub-min` is **10/10 running** (lead, go-dev, go-dev2, reviewer, fe-dev, web-dev, skills-dev, context-dev, feedback-dev, writer), not `3/3`.
- **`4genthub-deepseek` is STOPPED**, not running: `rig ps --include-archived` shows 1 node, 0 running, lifecycle `rec`, snapshot 18h ago. The "supervisor keeps running" paragraph below is therefore stale in its first sentence.
- **`4genthub-dev` is gone** ✓, consistent with its bullet below; only `dev-agy` (2 nodes, **stopped**, needs attention) survives as a stopped archive.

- **`4genthub-min` is the dev team now** (owner instruction). `4genthub-dev` was deleted from
  OpenRig; only its files remain under `~/.openrig/agenthub-seats/4genthub-dev/`.
- **The supervisor keeps running after this session closes** — it is a separate rig, not part of
  the Claude session. **[STALE (measured 2026-10-06): it is STOPPED — the rig shows 0 running with a snapshot 18h old; the self-parking mechanism described here remains accurate as a mechanism.]** It parks itself with `rig queue block --wake-after` and wakes on its own.
  Stop it with `rig down 4genthub-deepseek` if supervision is not wanted.
- **agy is out of service** until roughly Oct 10 (owner-stated ~167 hours). Its seats are skipped
  entirely: no probe, no nudge.
- The Claude 5-hour window was at 1% after the 11:30Z reset; **weekly was at 81%**, four points
  from the 85% gate the supervisor enforces.

## 4. Mechanisms discovered today (do not re-derive)

- **DeepSeek as a brain:** there is no `deepseek` runtime. It is a *provider* carried by
  `runtime: omp`, and OpenRig passes a seat its provider key **only** when the model is written
  `provider/id` (`deepseek/deepseek-flash`). Model ids from `GET https://api.deepseek.com/models`:
  `deepseek-flash`, `deepseek-v4-pro`.
- **Seat credentials:** `recovery.provider_auth_env_allowlist` is daemon-global and forwards only
  vars already in the daemon's environment; the daemon has no `DEEPSEEK_API_KEY`, so that path
  needs a restart. The non-disruptive path: **omp reads the launch directory's `.env`**, so rig
  `4genthub-deepseek` holds `.env` → symlink to `~/.config/deepseek/env`. Proven with the env var
  removed from the environment.
- **`builtin:yolo` is load-bearing for a headless omp seat:** it resolves to `full_bypass`, which
  the OMP adapter turns into `--approval-mode yolo`. omp's default `always-ask` floor parks a
  headless seat in needing-attention forever.
- **Which runtime a rig is really on:** `rig ps --nodes --json`'s `runtime` field is the
  *declared* value and was wrong. The authoritative signal is
  `rig usage series --lane provider_window` — that lane is written only from Claude Code
  statusline JSON, so a session that appears there is a real Claude seat. Use hours, not minutes:
  a 10-minute window came back empty where 6 hours held 588 samples.
- **A usage percentage belongs to the seat that emitted it.** A herdr session read `five_hour 2%`
  while the nine dev seats read 94-98% over the same period.
- **`call_agent` root cause:** production runs the Go image, whose `agent_templates` rows are in
  the Python `rules` format the Go value object rejects, and the lookup swallows the error — so it
  answers "Agent template not found" for every name. `master-orchestrator-agent` additionally has
  no template at all. `manage_seat list/get` **works** on production. **Subsequent update:**
  `agent_templates` has since been dropped — it has no declaration in the Go models/DDL or the
  production SQL (surface-inventory §4) — and the `call_agent` tool itself is gone.
- **OpenRig seat commands need flags:** `rig seat stop <seat> --reason <text>` and
  `rig seat launch <seat> --fresh --reason <text>`. A stopped rig comes back with
  `rig up <rig> --existing --fresh <logical-id>`.
- **CapRover container names carry a `.1.<hash>` suffix** — `srv-captain--4genthubdb` does not
  resolve; the real name is `srv-captain--4genthubdb.1.<hash>`. Use `docker ps` to find it.
- **`rig seat launch` will not reload a seat that is already running**; a fresh occupant is how
  changed startup guidance takes effect.

## 5. Rules that bit today

- Seats commit locally only and **stage by explicit path**; never `git add -A`. Commit with an
  explicit pathspec in this shared worktree.
- `CLAUDE.md`, `.claude` and `agenthub_go/seatcheck` stay out of every commit.
- The owner approves every push; a push to main deploys production.
- Tick nothing in `NEXT_GEN.md` without evidence, and fix the code to be clean rather than adding
  compatibility.
