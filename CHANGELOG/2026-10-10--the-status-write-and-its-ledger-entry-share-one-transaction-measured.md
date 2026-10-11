# The status write and its ledger entry do share one transaction, measured

The incident left a question the code alone could not settle. Reading said: the wired status path
returns the ledger's error and never reaches the websocket notification, so a status change fails and
its row rolls back. Measurement said otherwise: rows were observed with the status advanced and no
event beside them.

## The answer

Driven deliberately — the incident's shape (`task_events` with the current columns **minus**
`user_seq`) plus the production seam (`StatusLedger.SaveStatus` over the wired recorder, the row
written through the session manager exactly as the repository's `Save` does):

- the status write **fails**, with `column "user_seq" does not exist`; and
- the row **is not committed** — it still reads `todo`.

So the one-transaction claim holds on this path, and the user sees a failed call rather than a silent
success over a lost event.

## What the first, wrong version of that case taught — and why it is kept

The first version had the save closure write on the **pool** instead of through the session manager.
It auto-committed, and the case then reported, correctly for what it was doing, that the row had
committed. Two facts follow, and both are worth keeping:

1. **A write on the pool bypasses the ledger's transaction.** The seam only holds for a writer that
   goes through `WithSession`/`Transaction`, which is how `SessionRepository.Save` and every
   repository write go. Any path that writes a row directly would produce exactly the
   committed-while-its-event-was-lost shape the incident showed — which is a hypothesis for those
   rows, not a proof about them; production's own history is still the thing to look at.
2. **A harness can manufacture the finding it is looking for.** The wrong version's result was
   indistinguishable, on screen, from a real defect. The correction is in the case's own comment so
   the next reader does not repeat it.
