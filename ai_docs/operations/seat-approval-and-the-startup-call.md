# The startup `rig whoami` on a non-yolo seat

**Question (owner item, 2026-10-07):** under the default non-yolo policy, seats prompt for the startup
`rig whoami`. Where does that happen, does it block startup, and what is the fix?

**Verdict in one paragraph.** The gate is the seat's **launch posture**, not a permission list: a policy
that is not `builtin:yolo` — including **no policy at all** — resolves to `floor`, and the live pi adapter
maps `floor` to **`omp --approval-mode always-ask`**. The startup file then *orders* `rig whoami --json` as
the first thing a seat does, so on a floor seat the mandated first call is a gated tool call. It **blocks**:
`ask.timeout` is `0` live, which *disables* the automatic selection, so an unanswered prompt waits
indefinitely. The fix belongs in the one place that can carve out a single command **in every approval
mode** — the seat's own omp config, which **this repo already generates** — and it is two lines.

## 1. Where it happens, with file and line

The live daemon for this rig is the **source tree at `/home/daihu/__projects__/openrig`**, not the installed
global package: the running launcher is
`/home/daihu/__projects__/openrig/packages/daemon/dist/adapters/pi-runner.js`, and the installed
`@openrig/cli` 0.6.3 contains **no `approval-mode` string at all** (`grep -rn "approval-mode"
"$(npm root -g)/@openrig/cli"` → nothing). Cite the source tree; the installed copy cannot be the mechanism.

| step | what happens | evidence |
|---|---|---|
| **trigger** | the shipped startup file orders the call: "## Identity — run this first" → `rig whoami --json` | `packages/daemon/assets/guidance/openrig-start.md:9,12` (identical in the installed asset) |
| **trigger (second home)** | the daemon **types the same order into every fresh conversation**: "derive your identity with `rig whoami --json` and read durable obligations with `rig queue list …`" | `packages/daemon/src/domain/startup-orchestrator.ts:602` (installed dist: `startup-orchestrator.js:472`) |
| **posture** | any policy that is not `builtin:yolo` — `locked`, `standard`, `open`, a deliberate `none`, **or absent** — resolves to `floor`; only `yolo` is `full_bypass` | `packages/daemon/src/domain/permission-policy/policy-ref.ts:122`; `dist/…/policy-ref.js:99` ("yolo → full_bypass, else floor") and `:125-126`; the file header: "ABSENT (no value) = the floor (honest absence)" |
| **gate** | the pi adapter turns the posture into the approval mode: `yoloEnabled(process.env, binding.launchPosture) ? "approve" : "no-approve"` → **`--approval-mode always-ask`** | `packages/daemon/src/adapters/pi-runtime-adapter.ts:241` (posture) and `:244` (the flag) |
| **gate (other paths)** | the same mapping on resume and in the runner protocol, so it is not path-dependent | `pi-resume.ts:93`, `pi-runner-protocol.ts:248,279`; `pi-runner.ts:625` (only `yolo`/`always-ask` accepted) and `:638` (`OMP requires --approval-mode yolo or always-ask, not Pi trust flags`) |
| **live proof** | every seat today runs `omp --mode rpc … --approval-mode yolo` | `ps -eo pid,args \| grep omp` — the child of `pi-runner.js`; measured for context-dev, fe-dev, feedback-dev, go-dev2 and the writer |

**The `--approval-mode` flag is omp's own**, not OpenRig's invention: `omp --help` documents
`--approval-mode=<value>  Override tools.approvalMode for this session (always-ask|write|yolo)` and
`--auto-approve  Auto-approve all tool calls (skip approval prompts)` (omp/18.6.0). OpenRig decides *which*
value the seat gets.

**The other runtimes, for completeness** (they are *not* this gate): the floor is Claude
`--permission-mode acceptEdits` and Codex `-s workspace-write` (`daemon/dist/adapters/yolo-mode.js`,
`claudePostureFlag` / `codexPostureArg`), and OpenRig's own manual states the Claude consequence plainly —
*"It does not add a global `Bash(rig:*)` allowance"*, so other actions "follow native rules and prompts"
(`daemon/docs/reference/getting-started.md:447-449`). The three packaged policy bodies say the same thing for
Pi: *"Pi `--no-approve` is a resource-TRUST posture, not a permission floor (Pi has no permission surface)"*
(`daemon/policies/builtin/{locked,standard,open}.policy.md`). **That sentence is the whole story for omp:** the
policy has no command-level surface on this runtime, so the launch flag is the entire gate.

## 2. Does it block startup? Yes

- **No timeout.** `omp config get ask.timeout` → `0`, and the key's own description reads *"Auto-select the
  recommended ask option after this many seconds (**0 disables**)"*. So under `always-ask` the tool call
  waits until a human answers — an unattended floor seat does not fail fast, it stalls on its first step.
- **What the answers have looked like when a human was there:** the recorded window (go-dev2, 2026-10-05,
  `CRASH-2026-10-05T20-44Z.md` § "Permission measurement") has every `write`/`edit`/`bash`/`eval`/`task`
  **DENIED** by the operator-approval path, 20:43:13–20:44:01Z.
- **Scope, stated honestly:** the startup call is not special to omp — under `always-ask` *every* tool call is
  gated. It is the **first** gated call only because the startup file mandates it first. Allowing it fixes the
  startup step exactly; it does not make a floor seat autonomous.

## 3. The fix — two lines in a file this repo already generates

The seat's approval rules live in its **own omp config**, `agent/config.yml`, and that file is rendered by
**`agenthub_client/src/agenthub_client/seat_policy.py:152`** (`render_config` — the port of the deleted `scripts/openrig_seat_policy.py`, where the same function sat at `:145-161`), which today emits only **deny** rules:

```yaml
bash:
  allowCompoundCommands: true
  patterns:
    - match: "git push*"
      approval: deny
    …
tools:
  approval:
    mcp__agenthub_http_manage_agent: deny
```

omp's schema says the other dispositions exist and that a per-command entry wins over the mode:

- `omp config get bash.patterns` → *"Ordered bash command approval rules. Each item has match and approval
  fields; only '*' wildcards are supported."*
- `omp config get tools.approval` → *"Per-tool approval policies. Set to 'allow' to auto-approve, 'prompt' to
  require confirmation, or 'deny' to block. **Overrides are honored in every approval mode.**"*

**The change** — add to the rendered config, with the other patterns:

```yaml
    - match: "rig whoami*"
      approval: allow
```

That is the whole fix: the startup identity call is auto-approved **even under `always-ask`**, and nothing else
is loosened. Two notes for whoever lands it: the rules are **ordered**, so if a deny pattern ever matches
`rig whoami` the allow must sit above it (none does today); and `allowCompoundCommands: true` means each
command inside `a && b` is evaluated separately, so `cd <dir> && rig whoami --json` matches too.

**Where the fix must land, given a change already in flight.** On this rig today the writer is **not** the render:
both on-disk files carry a header a deleted script wrote (`# generated by scripts/openrig_seat_policy.py … -
do not edit` — nine of the ten seats' files still carry it and the tenth has none, measured 2026-10-09), so no
seat has installed from a render yet. But the setting is moving — the client's
`agenthub_client/src/agenthub_client/seat_sync.py` installs a **server-rendered** document
(`runtime/omp-config.yml`, `OMP_CONFIG_RENDER_PATH` at `:136`) into the same `config.yml`, **merged at the key
level** (`merge_config_key`, `:819`; the install step is `:717`), and the comment on the neighbouring render
describes the guide file as going *"where the script that hand-wrote it used to"*. So the two lines belong in
**whichever writer is live when they land**: if the render has taken over, the render's document is the home — and
the only repository-side writer left is the client's port,
`agenthub_client/src/agenthub_client/seat_policy.py`.

**What is verified here, and what is not.** Verified: `bash.patterns` is the live evaluator for a seat —
during this work a **deny** entry fired on this seat's own `rm -rf …`, refused with
`Blocked by bash pattern: rm -rf*`; and omp stores an `allow` entry unchanged (`omp config set` / `get`
round-trip). **Not falsified by this measurement: that omp's evaluator treats `approval: allow` as an
exemption under `always-ask`.** The disposition set is omp's own schema text for `tools.approval`
("*'allow' to auto-approve, 'prompt' to require confirmation, or 'deny' to block. Overrides are honored in
every approval mode*"), and a `set`/`get` round-trip **cannot** test semantics, because omp does not validate
the value at write time — a deliberately bogus disposition round-trips identically (measured, see §4).
Whoever lands the generator change should verify the exemption the way the deny side was verified: a live call
on a seat launched `always-ask`.

**Why the other two fix shapes do not remove the block.** A *documented expectation* tells the operator to
answer the prompt — it does not unblock an unattended seat. A *change to the startup file* moves the gated call
rather than removing the gate: under `always-ask` the first tool call is gated whatever the startup file says.
The only layer that can exempt one command from every mode is the seat's own approval rules — which this repo
already writes.

**Landed here vs specified here.** Landed: this document and the expectation line in the seat guide
(`agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md`, mirrored at
`ai_docs/operations/seat-guides/_common.md`; the `scripts/team/4genthub-min/guide-common.md` copy this sentence
named was removed by `1c7b6631` on **2026-10-09** — it was byte-identical to the library block and no check
compared it).
Specified, not landed: the two-line addition to `render_config` — it belongs in the live writer,
`agenthub_client/src/agenthub_client/seat_policy.py` (the port of the deleted `scripts/openrig_seat_policy.py`),
and code is not this seat's lane. Applying the rendered configs is runtime state; not done here.

## 4. Reproduce

**Operational warning — do not test this by hand.** omp resolves its config from the **real** home (the policy
generator says so in `real_home()`: *"the REAL user's home directory — which `$HOME` is not, inside an omp
seat"*), so `HOME=/tmp/scratch omp config set …` writes the **live** config. During this measurement exactly
that replaced this seat's `bash.patterns` with a single test entry. It was repaired with the generator itself — `scripts/openrig_seat_policy.py` then, `4genteam policy` now:
`apply --rig 4genthub-min` reported `writer: written` and nine `ok`, and the check that did that is
`4genteam policy apply --rig 4genthub-min --check`. **Use `4genteam policy apply --rig <rig> --check` to inspect
and `4genteam policy apply --rig <rig>` to repair; never `omp config set` on a live seat.** The
generator's check is what made the damage visible and scoped (`writer: DRIFT` against nine `ok`).

```bash
# the gate, in the live tree
grep -n "approval-mode" /home/daihu/__projects__/openrig/packages/daemon/src/adapters/pi-runtime-adapter.ts
ps -eo pid,args | grep -E "pi-runner|omp --mode" | cut -c1-200

# the trigger
grep -n "run this first" -A4 "$(npm root -g)/@openrig/cli/daemon/assets/guidance/openrig-start.md"
grep -n "derive your identity" /home/daihu/__projects__/openrig/packages/daemon/src/domain/startup-orchestrator.ts

# the blocking behaviour and the fix surface
omp config get ask.timeout --json
omp config get bash.patterns --json
omp config get tools.approval --json

# the generator, and the check that the rendered file is the live config
# the generator was deleted in 1c7b6631, so read it from its parent commit
git -C /home/daihu/__projects__/4genthub show 1c7b6631^:scripts/openrig_seat_policy.py | sed -n '145,161p'
cat /home/daihu/.openrig/state/omp/<rig>-<seat>@<rig>/agent/config.yml
```

## 5. Boundaries observed

`NEXT_GEN.md` was not edited (the lead's file; the item says to tell the lead, and the report says it).
`ai_docs/index.json` is machine-generated and was already carrying another seat's pending change when this was
written — not touched.
