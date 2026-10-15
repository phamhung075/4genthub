# The client pin moved, so the board line that named the old one moved with it

`NEXT-GEN2.md` §3's "what the pin says" was measured at 05:2xZ, when the pinned client was `5bb6d9c` and the
pin and the branch were two different shas. The lead's `8dbadda1` ("chore(client): bump the pin to the comm
guard and the declared-links fix", 05:59:23Z, one CHANGELOG entry plus the gitlink) took the pin to
**`ae3811c0`**, so the line is corrected in place.

The correction is not only the sha: pin and branch have now **converged** on `ae3811c`, with one measured
exception that matters to the sequence — the branch tip is `4ada3a4` (the pid fix, 05:59:20Z) whose parent is
exactly `ae3811c`, so the **pinned** client does not carry the fix, and the pin moves again only after that fix
is gated and the run tree is rebuilt.

Measured at main: `git ls-tree main agenthub_client` → `ae3811c07e`; `892f867` (the comm guard) and `462e2a1`
(the queue bound) are ancestors of it; `4ada3a4` is not.

## Not in this change

No code, no test, no pin of my own, no harness bytes.
