## O8's KPI half is held, and its definition pointer is fixed

### Changed
`agenthub_go/NEXT_GEN.md:435` (O8), two edits to the one line:

- **The citation.** The box pointed at "architecture doc section 9" for the KPI definitions. At HEAD,
  section 9 of `ai_docs/core-architecture/agenthub-system-architecture.md` is *Maintenance rules for this
  file*; the definitions are in 2.12, `:241-245`. The pointer now says so.
- **The HOLD**, recorded in the box itself so the next reader finds a decision instead of unowned work. It
  carries the lead's ruling (row `qitem-20261011042139-aea9914d969a9912`), the three facts it rests on, and
  the trigger: the box becomes buildable when a gate writer lands, meaning O5 writing `gate_verdict` as
  `actor_kind` `gate`, with O6's enforce mode for "verified".

### The one fact made more precise
fe-dev's fact (3) was "nothing writes a `gate_verdict`". At the batch tip `708e3131`,
`POST /api/v2/ledger/intents` accepts a client-sent `gate_verdict`. But
`server/httpapp/ledger_mount.go:175` attributes it to the seat or user that sent it, never to `actor_kind`
`gate`, so nothing writes the gate verdict the KPI counts. The box states it that way. The two Go-file hits
for the KPI grep pattern are `wireWorkflowGuidance` (it contains "rework"), not KPI code.

### Not changed
O8 keeps its `[ ]`, and its timeline half is unaffected. Whether O5/O6 are still wanted is the owner's call.
No code changed; nothing was run.
