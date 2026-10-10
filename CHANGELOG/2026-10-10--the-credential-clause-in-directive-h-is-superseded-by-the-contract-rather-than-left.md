## The credential clause in directive (H) is SUPERSEDED BY THE CONTRACT rather than left as the owner's choice

### Changed
- `agenthub_go/NEXT_GEN.md`, section (H), the acceptance paragraph — the one sentence that recorded the divergence raised with the last commit. It now reads that the acceptance is **superseded by the contract** on the lead's ruling, with the three reasons in the order the ruling gave them, instead of "the two are one decision apart and the choice is the owner's".
- **The reasons, recorded because they are the argument rather than a preference:** (i) refusing means **no secret ever lands in the database**, while a redaction that misses one case stores a live one — so the failure mode of the built contract is a rejected report and the failure mode of the acceptance is a credential at rest; (ii) the rejection **names the field and never the value**, so the reporter learns what to fix, which a silent redaction does not teach; (iii) the refusal is the contract that is **built and tested** (`secretscan.Contains` over the four free-text fields, `seat_feedback_service.go:118-128`), and the acceptance's "stored redacted" predates it.
- The owner can still order redaction later. Until they do, the tree's behaviour is what the record documents, and the lead carries the point to the owner as a product note rather than as a blocker.

### Verified
- The built behaviour is unchanged and was measured before this rewording: `secretscan.Contains(field.text)` over room, seat, session and text returns `&SeatFeedbackRejection{Message: "secret detected in field " + field.path, SecretField: field.path}` and the row is never built (`seat_feedback_service.go:118-128`).
- **Scope:** `git diff --numstat -- agenthub_go/NEXT_GEN.md` reads **1/1** — one sentence rewritten in place — plus this entry. The commit it corrects (`f9c43283`) is NOT amended; a wrong or weak sentence in an immutable commit is corrected above it, the same rule this rig applied to its own earlier message.

### Found by
- Row `469041df`'s divergence, raised in the commit report rather than smoothed over; ruled by the lead 2026-10-10.
