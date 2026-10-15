# The C5 snapshot clause corrected, the link source live, and the drift check named as its own unit

Three board corrections from one wake, each with the instrument attached. The measurement that matters
most is the smallest one: the runtime now answers `RoomLinks` with the declared set, live, and it took
no code.

## Changed

- **§6's C5 clause is corrected: two of its three steps are already done and its first step points at a
  subject that no longer exists.** The clause read *"Snapshot the live rig, then `4genteam` takes over
  the five seats, then stop the 4genteam daemon and remove the `rig`-exec paths and `the reference client.sqlite`
  dependencies."* Measured: **no 4genteam rig is left to snapshot** (`pgrep -af 'the reference client|rigd'` → no rows,
  `~/config/4genthub` absent, the only daemons are native `agenthub-runtime`), and **the takeover it sequences
  after the snapshot has already happened** (the live `spec.json` names `omp`/`deepseek/deepseek-flash`
  for all five seats). A snapshot does exist and it is **forensic rather than operative**:
  `client-20261014T175930Z.sqlite` (231313408 B) plus its 60369 B JSON sibling, taken 2026-10-14
  19:59Z. **Ruled, on the lead's own question: that snapshot SATISFIES the clause's original intent (a
  restore point for the rig being retired) and is not a step to repeat** — the tooling retired with the
  rig. The operative baseline is the lead's native one, re-verified here: a consistent `VACUUM INTO`
  copy of the rail (1241088 B; my read-back `pragma quick_check` ok, `queue_rows` 217 against the live
  219, the difference being the traffic written after the copy) plus a 277841 B definitional tar.
- **The link bullet gains the live source: go-dev's item (iii) is done and it needed no code.** The
  definition at `e3074353` declares 23 links; `clientteam.LoadRoomSpec` **already** mapped
  `team.json.links` into the `RoomSpec` the runtime stores, so the missing half was the definition's
  empty array rather than a code path; the live `spec.json` was given the same 23 with its predecessor
  kept (`spec.json.before-links-20261015-052217`, 1655 B); and **the running daemon answers with 23
  links, kind-for-kind** — my own socket probe (`GetRoomLinks`, `4genthub-min`) returns `ok:true` and 23
  rows, first row `{"from":"architect","kind":"can_observe","to":"fe-dev"}`, with **no seat, room or
  daemon restarted**. The bullet also carries the measured note that the architect seat is still
  `claude-code`/`opus` at that tip, which is the definition commit's own change sitting on top of it.
- **The drift check is NAMED as its own unit and deliberately NOT built — ruled, answering go-dev's
  question.** My item (iii) said the cloud copy and the definition are "reconciled by `drift-check`"; no
  such check exists. **It must not be built before the TABLE is ratified**: the cloud holds the plan's 12
  and the definition holds 23, and that difference is **expected by construction** — the owner's pending
  decision, not a defect — so a check landing now would codify an unmade decision as a failure. Its shape
  is written down for after the ratification (per room and per seat, compare cloud against definition,
  name which side holds a link the other does not, stay silent with no cloud copy). Until then the record
  says what is true: one source served live, one dashboard copy, one reconciliation owed.
- **The one-link lab is on the board as measured**, mapped onto the four gate cases: authorized notice
  delivered with the audit pair closed; the unlinked peer in the same room refused in words with no frame
  at the mailbox; the no-links room refused the same way; and the pre-wiring binary delivering both with
  **no audit line** — case (d)'s falsification reproduced against the real verb, on a scratch daemon, with
  no live room touched.

## Instruments

- `pgrep -af 'the reference client|rigd'` → no rows; `ls -d ~/config/4genthub` → no such file.
- `ls -la ~/.config/4genthub/snapshots/` → the 231313408 B forensic sqlite, the 60369 B json, the
  1241088 B native `queue.sqlite` and the 277841 B tarball, with their mtimes.
- `sqlite3` read-only over both rails: `pragma quick_check` → ok for each; `queue_rows` 217 (baseline,
  copied 05:26Z) against 219 (live, read 05:2xZ).
- the socket probe: one newline-terminated `{"action":"GetRoomLinks","payload":{"room":"4genthub-min"}}`
  frame over `/mnt/wslg/runtime-dir/agenthub.sock` → `{"ok":true,"error":null}`, **23** rows.
- `git show e3074353:scripts/team/4genthub-min/team.json` → `links` 23, read back as JSON; the same read
  shows the architect seat still `claude-code`/`opus` at that tip.
- the definition file at that tip and the live `spec.json` agree on all 23, kind for kind.

## Not in this change

No code, no test, no pin. `NEXT-GEN2.md` plus this entry, on the board branch whose base is main
(`02c63789`). The definition commit is NOT in this delta: it was re-based onto go-dev's links tip
`e3074353` at the lead's instruction so `team.json` moves once, and it lands as its own delta
(`4genthub-min/definition-on-declared-links`, tip `9e325182`, patch-id `ae899a1a`).
