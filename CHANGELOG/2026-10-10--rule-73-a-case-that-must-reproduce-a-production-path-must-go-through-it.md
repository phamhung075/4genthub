## Rule 73: a case that must reproduce a production path must go through that path

From the lead's 18:36Z broadcast to the topology, on the incident work — recorded as a rule because it applies to every test every seat writes, and because the lead's own standard is that a rule living only in a broadcast is a rule nobody can read.

### Added
- `agenthub_go/NEXT_GEN.md`, process lessons: **rule 73**, stated with the instance measured twice by its author.
  - **The instance:** the case that settled the `user_seq` question was written twice. Its **first** version had the save closure write **on the pool** instead of through the session manager — **and the pool path auto-commits** — so the case reported that the row **had committed**, which is exactly the shape the seat was hunting; and **the wrong result was indistinguishable on screen from the defect.** The second version drives the write through the production seam and is the one that settled the question.
  - **The rule:** a case that must reproduce a production path must go through that path (the session manager / `Transaction` for repository writes). Otherwise **a green confirm is worth less than a red**, because the harness has written the hypothesis back to you. The discriminating question before believing a green: *which function did the case call, and is that the function production calls?*
  - **The settled answer is kept with the rule**, since it is the case that produced it: through the production seam the status write **fails naming `user_seq` and the row is not committed** — a failed call, not a clean success over a lost event. **The rows that committed with a lost event therefore have another origin**, and that is recorded as an open question rather than folded into this one.

### Verified
- The instance, the outcome of both versions, and the settled answer are the lead's broadcast and the author's own account; this seat did not re-run either version, and the rule says so by attributing them.
- The general form is stated as a test of the instrument rather than as advice: *a fixture that shares no seam with production tests the fixture.*

### Not run
- No test accompanies this record: it is a rule about how tests are written, and the case it describes belongs to the incident's own work. This entry exists so the rule is readable outside a chat message.
