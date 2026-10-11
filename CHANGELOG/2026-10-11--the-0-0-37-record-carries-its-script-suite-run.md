## The 0.0.37 record carries its script-suite run, and drops a false "retired" line

### Fixed
`CHANGELOG/2026-10-11--release-0-0-37-the-ledger-slice-the-subtask-details-and-the-client-pin.md`, the
release record for the sealed batch `708e3131`, routed to the architect by the lead:

- **Removed** from `### Not run, named`: "The Python script-test leg is retired, not skipped ... there is no
  `--noconftest` suite left to run." It was false. `agenthub_main/` is gone (`a50929c6`), but the suite
  lives on at `scripts/tests` and runs.
- **Added** a `script suite` row to `### Battery`: **12 failed / 76 passed at `708e3131`**. The twelve are
  pre-existing, proven on the case lists: go-dev found the same twelve failing ids and the same 88 collected
  (two md5s) at `708e3131`, `1a370e02` (pre-batch main), `ba5e7a9f` and `c53c4900`. The row also cites the
  reviewer's one-case diff against `3e81e1e9` (`qitem-20261011041405-fa94412c`) and names the rig-state
  limit of the seat-policy cases.

Not carried into this record: 13/75 (`3e81e1e9`), and 9/79 and 88/0 (later go-dev tips). They belong to
the next entry. Docs only; no run was taken for this change. Every number is go-dev's or the reviewer's.
