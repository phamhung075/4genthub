# OpenRig-side defects — one report, three reproductions (2026-10-06)

Three findings against the OpenRig tool surface, consolidated into one entry because they share a genus: **each is a control that cannot fail, and each was found by RUNNING the thing rather than by reading its documentation.** Framed per finding as: what happened, the exact reproduction, the consequence for us, and what a fix would look like. Kept here as the durable copy; the lead sends it.

Repo-side records: the park defect also lives in `agenthub_go/NEXT_GEN.md` (the OpenRig-side defect bullet). Nothing here is this repo's code.

---

## 1. `rig queue block` — a refused park leaves the row `in-progress`, so a seat can believe it is waiting when nothing was recorded

**What happened.** A row was created with a human gate and blocked on the lead. The call looked like a park; the state did not move. Read back, the row was still `in-progress` — indistinguishable, in the moment, from a park that quietly did nothing.

**Exact reproduction.** With a row that needs a human decision:

```
rig queue block <qitem> --on <agent seat> --summary "…" --evidence-ref "…"
```

answers

```json
{"error":"summary_evidence_not_persistable",
 "message":"summary + evidenceRef persist only on a human-seat park (state=blocked on a human seat); the 'blocked' transition cannot store them.",
 "invalidFields":["summary","evidenceRef"]}
```

and the row is left exactly as it was. A **real** park answers `pickup.state: "parked"`; a refused one leaves `"working"`. **Reading the state back is the only way to tell them apart.** The refusal is coherent and the field shape is not broken — those two fields are documented as persisting only on a human-seat park, and an agent seat takes the plain `blocked` path.

**Consequence for us.** Two, and the second is worse. (1) A seat that follows the instruction carries on believing it parked. (2) **The prescribed route does not exist in this topology:** the message tells the caller to park on a human seat, and every peer here is runtime `omp` — there is no human seat — so the instruction leads into a refused call. The hypothesis that the evidence-ref's *shape* triggered it was **disproven by experiment**: a throwaway row parked with an absolute-path evidence ref failed identically with the row left `in-progress`, so the shape is not the trigger.

**What a fix would look like.** Persist `summary` and `evidence_ref` when the blocker is a typed human gate or an agent seat acting for a human; name a route that exists in the topology rather than one that does not; and **never leave the row `in-progress` on a refused park** — that is where the intent dies.

---

## 2. The default read of a durable record is a bounded preview carrying no marker that it is one

**What happened.** A seated reader read a durable record, saw the text end mid-word, and concluded the record had been truncated — a conclusion that reached the owner, and was wrong.

**Exact reproduction.** Read a durable record **without** its full/raw flag: the output is a bounded preview and **nothing in it says so** — no marker, no byte count, no "…more", just a mid-word cut that reads exactly like corruption. Read the same record **with** the flag: the whole thing, intact.

**Consequence for us.** The instrument lied by omission, and the failure mode is the expensive direction: the reader reports a defect that does not exist, and the owner acts on it. Distinguishing the two states required knowing the flag existed.

**What a fix would look like.** Mark a preview **as** a preview in its own output — a line saying the read is bounded, how much was returned, and which flag returns the rest — so "truncated" and "previewed" can never be confused by a reader who does not already know the difference.

---

## 3. The send path has no `--body-file`, and the asymmetry is the defect

**What happened.** A message containing backticked text was sent to a peer. The shell executed the backticks before the message was delivered: it arrived with holes where the quoted text had been and with shell errors in its place. It could not be recalled; the repair was to resend it clean.

**Exact reproduction.** `rig send <seat> "…`command`…"` — the backticks run in the sending seat's shell and the message is delivered mutated. The same body through the queue path, `rig queue create … --body-file <path>`, arrives intact: **`--body-file`'s own help says it exists to kill exactly this class** for multiline bodies.

**Consequence for us.** A message that must carry a path or a command is precisely the case with no body-file equivalent today, so the bodies most needing exactness are the ones most likely to be mangled. This is not rare: **five instances across four seats tonight, two of them self-caught** — a rule written to prevent it caught its own author within the hour.

**What a fix would look like.** Give `rig send` the same shape as `rig queue create`: **a body-file, or a no-expansion mode.** Our ask, stated once: *the hazard is mechanically solved on one path and left open on the other, and a rule that catches its own authors within the hour of being written is evidence that the rule cannot be the control.*

---

## Status

- All three are **OpenRig-side**, not defects in this repo's code.
- All three were **found by running the real thing** — a real park, a real read, a real send — rather than by reading documentation.
- The park defect is also recorded in `agenthub_go/NEXT_GEN.md`; this file is the consolidated copy and the send-ready form.
