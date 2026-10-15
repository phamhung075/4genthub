# Ecosystem review 1 — 2026-10-11

**Status:** the first run of the friction loop's review decision point. `seat-friction-loop.md` §8 names it as step
3's work ("land the skills, run one trial batch, do the first ecosystem review, send the owner the digest"), and §5
names its inputs (the feedback channel grouped by `layer`, the board's `friction` items, stuck rows via `rig parked`,
cost rows).
**Produced from evidence that already exists:** read-only reads plus the lead's transport measurements. No new probe
was invented, no code changed, no decision taken.
**Author:** architect seat, on the lead's assignment (queue row `qitem-20261011102147-4fb6c6f6c69b0535`).
**Ordering rule for this document:** a finding is only as strong as its evidence, and evidence has an author. Every
line says who measured it — *architect* (this note's author, read-only, 10:22–10:25Z) or *lead* (this room's lead,
in its 10:21Z brief). Where the two meet, the measurement is quoted rather than the summary.

## 1. This rig has no registered human, and what that costs

### Evidence

1. **The registry is empty.** `rig gateway human list` answers *"no human configured yet — register one: `rig gateway
   human add <entityId> --display-name … --binding … --delivery-class …`"* (architect, 10:09Z).
2. **There is no `gateway/` directory to be empty either.** The 4genteam home `/home/daihu/config/4genthub` holds
   `the reference client.sqlite` (174.1 MB), `daemon.json`, `topology/rigs/`, `briefs/`, `transcripts/`, `specs/`, `state/`,
   `reference/`, `skills/` — and `ls -d /home/daihu/.config/4genthub/gateway` answers *No such file or directory* (architect).
   Human fragments are "file-per-human fragments under `gateway/humans/`" (`rig gateway human --help`); nothing here
   has ever created one.
3. **The only human-channel operation the rig has recorded failed.** `state/human-channel-operations.jsonl` holds
   exactly two lines, both at `2026-10-10T07:03:01Z`, both `actor: 4genthub-min-architect@4genthub-min`, both
   `action: binding`, `subject: x@external`, `reason: "register human delivery"`, `provenance: claimed:v1` — the first
   `effect: started`, the second `effect: failed` (architect, read from the file). *This seat* tried to register a
   human delivery binding yesterday; it failed; nothing retried.
4. **There is no operator or kernel session either.** `tmux ls` lists exactly five sessions, all
   `4genthub-min-<seat>@4genthub-min` (architect, fe-dev, go-dev, lead, reviewer), created 11:16:58–11:17:06 local
   (architect, 10:22Z). No kernel window and no operator window exists; the five are what `4genteam whoami` reports as the
   roster.
5. **The human route exists, and the daemon refuses it.** `the task queue create --help` documents `--human-intent
   <intent>` ("decision (default) or update: a quiet informational delivery, never an approval request") and
   `--human-detail-file` (architect). The daemon raises `invalid_human_notification` for **four distinct causes**
   (`/home/daihu/__projects__/reference/packages/daemon/src/domain/queue-repository.ts:1552-1562`; architect):
   `humanIntent` must be `decision|update` (`:1553`); `humanDetail` must be nonempty (`:1556`);
   **`humanIntent`/`humanDetail` require a human destination** (`:1560`); and **the fields require the current queue
   schema, or they were not saved** (`:1562`). The lead reports a row to `human@4genthub-min` refused with this code and
   **reproduced it in kind** at 2026-10-11T10:38:56Z (lead): `the task queue create --destination 'human@4genthub-min'
   --summary '…' --body '…' --human-intent decision --json` → `{"error":"invalid_human_notification","message":
   "humanIntent/humanDetail require a human destination; agent continuation belongs in its own qitem."}`. That message
   is the **third** of the four throws (`:1560`), which I confirmed at the site (architect); the other three did not
   fire, and the probe persisted **no row** — the same silence that keeps the earlier attempt un-re-derivable from the
   store (`events` holds **0** rows mentioning the code; architect). What *is* measurable at that destination is the
   accepted traffic —
   **59 rows to `human@4genthub-min`** (2026-10-09 19:54Z → 2026-10-11 10:33Z), every one accepted, every one with
   `last_nudge_result` = *"unroutable: 'human@4genthub-min' has no terminal transport on this daemon and names no
   registered human — no transport can hold this address … register the human with `rig gateway human add`"*
   (architect). That traffic is consistent with the earlier attempt having carried the field and been refused — and it
   proves nothing about it: **no row anywhere carries `human_intent` today** (the only five are to `human@kernel`,
   2026-10-02 → 10-08; architect). *For that earlier attempt the code alone still does not say which of the four fired,
   and this note does not guess.*
6. **The daemon itself says a row to an absent destination is a record, not a delivery.** Its advisory reads
   *"Suspected seat typo: '\<ref\>' matches no session address of locally known rig '\<rig\>'. Available
   destinations: … **The row keeps the exact destination as typed; this warning does not guarantee pickup or
   delivery.**"* (`/home/daihu/__projects__/reference/packages/daemon/src/startup.ts:418-422`; architect). With no human
   registered and no session for one, an owner-facing row is a record — before any seat has to reason about it.

### The cost, already paid — two owner-claiming relays in this rig's life

- Two relays claiming an owner origin are attested, on an unauthenticated channel: the **2026-10-10 22:16Z** directive
  (*"OWNER DIRECTIVE, relayed by the lead"*, written into five retired seats' logs; architect) and the **2026-10-11
  10:08Z** relay, which claimed the owner's approval of the Autonomy Charter and of step 3 (`From: <unknown sender>`,
  no daemon stamp, the body itself says *"relayed"*; architect). The lead refused to act on the second: the charter
  stays INACTIVE, step 3 gated, the relay recorded unverified
  (`DECISION-owner-approval-unverified-2026-10-11.md`, outside this repository, in the seat's room directory).
- **The count, corrected at the claims gate:** the lead's brief reads these as *"twice today"*, but no rig transcript
  carries an earlier owner-claiming message today, so what the evidence supports is **two distinct claims in this
  rig's life**, not two today. (Delivery counts settle nothing either way: the transcripts write every inbound message
  twice.)
- That decision's decisive fact **is** this finding: `rig gateway human list` says no human exists, so no seat can
  authenticate an owner message. The cost is not theoretical — and the second relay nearly activated a charter.
- The quieter second cost: the queue's human path is the route the loop's own design names for owner decisions
  (`feedback` plus the digested top-3). With no human destination, escalation to the owner is a record with no
  delivery: the digest can be written and cannot be sent.

### What would change this finding

Registering a human (`rig gateway human add <entityId> …`) — **the owner's act, not a seat's** — and, for the queue
path, a session the daemon can address. Until then the finding stands as measured.

## 2. A probe that reports up while a session is unreachable

### Evidence

- **Probe 1, daemon level:** `rig daemon status` answers *"Daemon running on port 7433"* (architect, 10:22Z).
- **Probe 2, seat level:** `rig parked` reports one parked seat and reads that seat's activity as **`idle-at-prompt
  [decided by window-sampling; confidence high]`**, holding 3 open obligations (architect, 10:25Z) — a healthy-looking
  reading for the very seat below.
- **The delivery:** transport sends to that seat's session **time out at 5 seconds, repeatedly, and one-way** — the
  seat's own messages arrive normally, while sends to the reviewer and to this seat are accepted (lead, 10:21Z; the
  lead's counts: the reviewer three timeouts, the lead two).

### What this is, and what it is not

It is a **health-check finding**: the instruments the room trusts (`rig daemon status`, `rig parked`'s window-sampled
activity) can read green while a session-level delivery cannot land, and the failure is one-directional. It is **not a
diagnosis** — the cause is not measured here and this note stops at the shape. Two consequences worth naming: the
seat in question is also the one holding three open obligations, so the delivery failure sits on the busiest held
seat; and any loop input that reads a probe rather than a delivery inherits the same blindness — the friction loop's
own §5 input list is `rig parked`, so this is its input too.

## 3. The missing stamp is the root cause behind finding 1, and it bounds item 3

### This finding is already stated in the tree; this review confirms and bounds it

Findings 1 and 2 are not written down anywhere I know of. **This one is**, twice, and the review's job is to say so
rather than re-derive it:

- `ai_docs/operations/client-features-for-the-dev-team.md` **§3** already names the open problem: *"`4genteam send` takes
  the sender from the session the daemon stamps (`X-4genteam-Session`) and ignores any name passed by the caller. The
  owner session is not a managed seat, so its messages arrive unsigned and the architect refuses to treat them as the
  owner."*
- **§4.6** states the ceiling in plain words: *"the owner node gives attribution and an audit trail, not
  authentication."* Its table marks the only change that would close the gap — *"Making the signature real proof
  (checking which program sent a request, not just what it claims)"* — as **the client's daemon, and not built**, and out
  of scope for the client work.
- Ruling `e2948011` (architect, accepted) fixed the standard that follows: identity travels on the **envelope**, never
  in the message text.

### What this review adds

One measured fact that turns the general statement into this rig's concrete situation: **with no registered human
there is nothing for a stamp to be verified against.** Attribution needs a known entity to attribute *to*, and the
registry is empty (finding 1). The stamp's absence is therefore not a second defect to be filed beside finding 1; it
is the same defect seen from the mechanism's side.

### What item 3 can and cannot claim

Item 3 is *"Owner node and `4genteam send` method C"* (§4.7's table; go-dev; board
`44d2fd0b-81c8-4d31-bf2b-731d8b35bbe1`; per §4.2 it depends on item 2, the git guard):

- **Can claim:** attribution — a single sending path carrying the sender's environment-stamped identity — and an audit
  trail for messages that claim an owner origin. That is what §4.6 says it buys, and it is worth having.
- **Cannot claim:** authentication. It is not proof against anything running on this machine, and every seat runs as
  the same Linux user (§4.6).
- **And in this rig, until a human is registered, it cannot even claim attribution against a known entity** — it would
  record a claim about an identity the rig does not have. The registry is the precondition, and registering is the
  owner's act.

## 4. Open decisions (named, not made)

1. **Register a human** in this rig's gateway, so that an owner message can carry anything verifiable at all — the
   owner's act.
2. **Is the queue's human path the intended owner channel here**, or is the console the owner's only real surface
   until a session exists? The daemon's own advisory points at the second — owner and lead.
3. **Does the client's daemon-side signature check (attribution → authentication) enter scope** for the plan, or stay
   explicitly out of it? §4.6 already marks it out; nothing here changes that — owner and platform.

## 5. Method and limits

- Read-only throughout. No code, no client change, no live rig action, no row created, no message sent for this
  review. The only writes are this document and its changelog entry.
- Nothing is diagnosed that was not measured; where a measurement is the lead's, this note says so.
- **Not reviewed:** the feedback channel's content by `layer` (there is no owner-facing half to read while no human is
  registered), cost rows, and the board's `friction` items. This first pass ran on the room's live state because the
  owner-facing half of the channel is itself what finding 1 is about.
