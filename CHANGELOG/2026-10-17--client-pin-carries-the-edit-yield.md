# The pin carries the edit yield and the ratcheting floor, and the test record lands whole

The hub's gitlink moves 06ab07a -> b9325ef: the report lane 471ec6c with its help-text delta b9325ef,
fast-forwarded (gate PASS qitem-20261017070952). The code-edit floor reads `> 25, cap 40`: base 25, +5 for
each complete UTC day in which every editing seat passes, never down, capped at 40, the step replayed from
the transcripts under the any-call reading the floor gates (seven full days). Beside it, per editing seat,
the edit yield - gate-passed commits per code-edit USD - rendered diag for five daily windows, with drops
printed by reason (no Task:, task not gate-passed, gate passed for another seat, pin-only). Pin-only
commits are excluded by git log --raw type 160000; a gate row that names a sha credits the commit's Task:
trailer (flagged to the reviewer), and the credited seat is the row's source seat. Decision:
seats/architect/RULING-code-edit-share-target.md and Addendum 3.

At the merged tip: go test -count=1 ./... 32 packages rc 0; `4genteam room report 4genthub-min --since 1h`
prints the floor line, the 7-day replay, the two yield lines and the drop counts (no Task: 0, not
gate-passed 6, another seat 3, pin-only 2).

This commit also carries TEST-CHANGELOG.md whole - nine sections that had no carrier: seat-key-destination
(daemon half), fe-dev-loghome, nudge-pass-wakes-silent-seat, one-state-root, send-reply-race, park-way-back,
gate-verdict-consumers, gate-register, and the criteria-shape pin (2026-10-16).
