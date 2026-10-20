# The pin carries the send refusal that separates a missing declaration from a mismatched intent

The hub's gitlink moves `02eac84 -> 36a415f` (client main). `4genteam send` now answers `intent not
licensed` when the pair declares a link that licenses some other intent, and keeps `no link` only for a
pair that declares nothing. `commpolicy.Decide` scans the pair's declarations across every kind before it
picks the word; `WouldLicense` and the licence hint are unchanged, so the refusal still names the kind that
would license the notice and what the declared edge licenses instead.

Why: review 3 line 5 — fe-dev's `escalates_to` edge to the lead was declared, the report was licensed, and
the notice's refusal said `no link`, which read as "the edge is not admitted".

Evidence: reviewer gate PASS at `272dda3` (row `qitem-20261018234752-6e7ccee8d95e`); task `56471d22` closed
through the gate (0.97 / 0.99); rebased onto `02eac84` as `36a415f`, where `go test ./...` rc 0 and cargo
tests are 185 + 1 + 19 + 1 passed. Red-first: forcing the old word back fails `TestDecide`, the kind matrix
and both send cases.
