# The sequence now running, the ledger it must be read against, and the two corrections the last half hour forced

`NEXT-GEN2.md` gained one block and three in-place corrections. Every identity in them was re-measured by me
between 05:5xZ and 06:0xZ; none is copied from a row.

## The block: the sequence and the ledger

The C4 row documented runs 2/3/4/4b/5/5b/5d and stopped there. The room is now executing something else
entirely, and a successor reading the old row could not tell. The new block names it:

- **the order**: FAIL 1's start-path defect fixed -> its gate -> **one** rebuild into `u3bin` at that sha ->
  `fe-stage9` installed -> `run-c4.sh --all`; the run starts at 10:00Z or on the owner's one-run peak
  exception;
- **the fix, which landed while this was being written**: `4ada3a4` "an unreadable pane pid is not a dead
  pane" (05:59:20Z, `4genthub-min/seat-runtime-socket`, 4 files, +334/−27). `PaneRecord { pid: Option<u32>,
  unread: Option<String> }` replaces the `unwrap_or(0)` collapse; the supervisor asks the same read again
  immediately and refuses only when two reads agree; the refusal states the wait **performed**; and the
  session event's `pid` is `Option<u32>`. Its falsifying test forces the race with a `tmux` shim and fails
  when the re-read is disabled; `cargo test --offline` 105 passed / 0 failed;
- **`u3bin` is stale with respect to that fix**, which is the one fact that would make a run lie: the pair on
  disk (`6fdf9fae…` / `4ac8af76…`) was built at 05:24Z from `462e2a1`, and `unwrap_or(0)` is at
  `pty/mod.rs:154` in all four client tips checked;
- **the instrument ledger has five revisions, not three**: live bytes are still `5b2e15b3`; `b35711cd`
  (stage8) passed the reviewer with no required edits and is deliberately not installed; `1142c831` (stage9)
  is the revision at the gate; `run-c4.sh` `6253f9cb` carries the launcher fix;
- **the calibration pass is not a verdict**: 7 pass / 5 fail / 5 skip, own root, own socket, all off-peak, on
  the superseded pair. Its B2 (0/1/1) is an instrument fault — the seat piped payloads through `wc -c` — so
  it neither proves nor refutes parity 2; and it names a second suspected product defect, three seats ending
  on their own mid-run with the daemon silent.

## The corrections

1. **The C2 pair is landed, not outstanding.** The board said the queue bound and the published depth were
   outstanding. At the source: `pub const MAX_HELD: usize = 8;` at `runner/mod.rs:1167`, enforced at `:1473`,
   with the depth published at `:1492` (held) and `:1499` (the bound's refusal) and a test at `:2235-2249`.
   The grep the board used returns 9 on that file today (2320 lines, not 2207).
2. **`u3bin/PROVENANCE.txt` moved**: 3387 B, head naming `462e2a1` and the pair built 05:24Z, with the
   kept-aside pairs by sha256 — so the 840 B / `0a968fc` reading is that file's own history.
3. The taxonomy bullet's routing line now points at a fix that exists (`4ada3a4`) rather than one being
   written.

## Not in this change

No code, no test, no pin, no harness bytes. `NEXT-GEN2.md` and this entry, one commit above the commit under
the reviewer's gate.
