# The pin carries the gate-close verdict and the single-successor handoff

The hub's gitlink moves `8a97cf7 -> 516a230` (client main), a two-merge tip: `2b422e5` brings
`72f70bf` (a gate close carries the verdict and is refused without one) and `516a230` brings
`e8dba67` (one handoff emits one successor, and the successor names its source). Both branches were
cut at client `5582628`; `f3c064a` and `272dda3` were already on main as `02eac84` and `36a415f`
(`git cherry main` answers `-` for both), so only these two merges were composed.

The single conflict was one test insert in `rust/agenthub-runtime/src/queue/mod.rs`: the gate-close
test `a_handoff_without_a_note_keeps_the_source_body` and the double-close test
`a_double_close_emits_one_successor` write the same anchor. Resolution: both tests whole, each with
its own successor-list assertions; no production hunk conflicted.

Evidence: reviewer PASS on `72f70bf` (go test ./... 35 packages, cargo 184+1+19+1) and on `e8dba67`
(go test ./... 35 packages, cargo 185+1+19+1); the composed tree runs cargo 186+1+19+1 and five Go
packages (`clientcomplete`, `clientroom`, `commpolicy`, `clientseat`, `clientruntime`) green.
Tasks: `eaed67b8-42dd-4a8d-961c-8dcd3c9f3e80`, `efe7f20c-29b7-4796-a72e-40b15fceb9b5`.
