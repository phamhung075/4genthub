# The live-harness line said `28302b7b`, and the live path has answered `5b2e15b3` since 04:54Z

§3's "the live acceptance harness, by content" bullet asserted that `reviewer-stage5.sh` and
`ACCEPTANCE-cutover-lab-U3.sh` are byte-identical at `28302b7b…` (151731 B). That was true when it was taken
and is false now, and it is the stale-identity class this room keeps having to correct: a reader who checked
that line would conclude the live harness is `28302b7b`.

Measured 06:0xZ: `reviewer-stage5.sh` still hashes to `28302b7b…` (151731 B) — it is the kept-aside bytes of
the third revision — while the live path `ACCEPTANCE-cutover-lab-U3.sh` has been `5b2e15b38b3c1340…`
(157965 B) since 04:54:5xZ, with its byte-identical staging copy `fe-stage6.sh`. Both were measured again
today rather than quoted.

The correction also points at the ledger instead of restating it: the live bytes, `b35711cd` (stage8, approved
and deliberately not installed), `1142c831` (stage9, at the gate) and the launcher `run-c4.sh` `6253f9cb` live
in the sequence bullet under the C4 preconditions. The reason one path answers two shas is the install rule
the board already records: each revision is installed by overwriting the live name.

## Not in this change

No code, no test, no pin, no harness bytes.
