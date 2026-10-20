# The pin carries the nudge-pass and reader-write fix, and its record awaits a carrier

The hub's gitlink moves `0d0f114 -> 927d52d` (hub pin, gitlink only). Client main took
`4genthub-min/nudge-pass-wakes-silent-seat` as a merge (`927d52d`, parents `0d0f114` + `52b2977`).

## Changed (client)

The owner-visible failure: a queued row addressed to an idle `agy` seat after its relaunch produced
NO nudge attempt (measured 06:09Z: the reviewer sat at its prompt with the row on its rail while the
same pass nudged three omp seats), and the client idle guard then escalated "ignored 3 nudges" to the
lead. Two causes, fixed together:

- `supervisor::pending_nudges` selected only on `seat_is_idle`, which compared the raw state to
  `idle` and read the state file a second time. A relaunched seat's only document was the previous
  generation's `agent_socket_closed`, and `agy` publishes no word of its own, so an idle seat never
  qualified. The pass now selects unless the seat's own word says a turn is in flight
  (`Working|NeedsInput`) and only counts a word from a runtime that has a runner; `seat_is_idle` is
  deleted and the pass reads the word the status already parsed.
- `runner::nudge_seat` could only reach a runner mailbox, so a selected `agy` seat (no mailbox) would
  have recorded a failed delivery to a socket that does not exist. `PendingNudge` carries
  `has_runner`; the nudge routes mailbox-vs-pane as `deliver_text` does, and the attempt log records
  each route's own word (`prompt` for a mailbox; a pane can prove `submitted`/`unconfirmed`).

And the false input that was feeding it: `get_room_status`'s detail else-branch called
`runner::write_state(<seat state>, "agent_socket_closed", "the pane ended without publishing a
death")` — a READ manufactured a death, signed with the reader's pid, for a seat that never ran.
The read now reports the sentence and writes nothing; the writers stay the runner and the observed
death path.

## Evidence

- Reviewer gate PASS at `52b2977` (row `qitem-20261017061826-4c21d8ce1d76`): `cargo test --offline`
  157 unit + 17 integration green, `go test ./...` 32 packages green, evidence verified.
- The lane's own before/after in a throwaway root: at `a40d9a0` no `nudge.jsonl` after 5 s; at this
  tip attempt 1 at +3.1 s, and a reading pane records `submitted`.
- Three new supervisor cases: the agy relaunch with the previous generation's death document selects
  and records attempt 1; all four busy words skip, then idle selects; a document without the word
  selects. A status read over a never-run seat creates no `run/<seat>.state.json` (red with the write
  reinstated).
- Lead at the merged tip: merge parents `0d0f114` + `52b2977`, 4 files `+330/-83`; the hub commit is
  a bare gitlink bump (`numstat` 1 file `+1 -1`).

## Held

Held record: a pin commit cannot carry its docs from a seat (pre-commit drops the gitlink, so a
pin+docs commit arrives as docs-only and the docs-only guard refuses it; no hook was bypassed). It
rides any commit that touches a non-doc file, or the owner's `types_or: [file, directory]` one-liner
(`qitem-20261017002819-8e1c6aff25f2`).

The push is not authorized and waits for the owner's word (`qitem-20261017030506`). The live daemon
still runs the pre-fix build; the fix reaches the room only at rebuild + reseat, after the push.
