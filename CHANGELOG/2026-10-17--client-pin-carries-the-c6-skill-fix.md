# The pin carries the C6 skill fix, and its record awaits a carrier

The hub's gitlink moves `a40d9a0e -> 086dc38` (hub pin, gitlink only). Client main took
`4genthub-min/c6-decision-ladder` as a fast-forward: `a40d9a0 -> 086dc38` (one commit, docs only).

## Changed (client)

C6's close-out measured the ladder at the client tip with a stubbed Jev (throwaway root, own daemon,
`TYPESAFE_BASE_URL`/`JEV_DECISION_LOG_PATH`): A/B/C/E 47 pass, D 7 pass, 0 fail. The verb
(`internal/clientdecide`, `internal/clientjev`) was already correct; the two reds were in the skills
that carry the ladder's halves the verb deliberately cannot enforce:

- `skills/share/jev-decisions/SKILL.md`: exit 5 is split on the `escalate_to` value the verb prints,
  so an escalated ask is read as "ask the next tier", not as a failure.
- `skills/share/room-decision-request/SKILL.md`: the owner step names its destination — the
  `4genteam room queue create` command addressed to `principal@<room>` with the `owner-decision`
  tag, the create's body cap, and the qitem id read back. That read-back is the evidence the gate
  asserts, because the verb cannot prove a row exists.
- `CHANGELOG/2026-10-17--the-owner-step-names-its-destination.md`: the record of the lane.

## Evidence

- Reviewer gate PASS at `086dc38` (row `qitem-20261017060857-c910bc2cead2`): all tests green,
  evidence verified; `go build`, `go vet`, `go test ./internal/{clientskills,clientdecide,clientjev}/...`
  green on the lane.
- The lane's own report: throwaway root, own state dir/socket/daemon/room, Jev stub hit-counted;
  A 0.90 seat decides with one request and no lead named; B 0.60 exits 5 with `escalate_to: lead`
  and the recommendation carried, 0.60 lead names the owner; C credentials/spend/owner-only at 0.95
  goes to the owner by code with zero requests; D the owner escalation is a real `owner-decision`
  row to the principal, asserted by its id; E every outcome logs tier, confidence and option.
- Lead at the merged tip: `git -C agenthub_client merge --ff-only` clean, `main` = `086dc38`; the
  hub commit is a bare gitlink bump (`numstat` 1 file `+1 -1`).

## Held

Held record: a pin commit cannot carry its docs from a seat (pre-commit drops the gitlink, so a
pin+docs commit arrives as docs-only and the docs-only guard refuses it; no hook was bypassed). It
rides any commit that touches a non-doc file, or the owner's `types_or: [file, directory]` one-liner
(`qitem-20261017002819-8e1c6aff25f2`).

The push is not authorized and waits for the owner's word (`qitem-20261017030506`).
