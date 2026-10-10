## A seat is told to resume as soon as its compaction is witnessed

### Fixed
- `scripts/openrig_compact_supervisor.py`: the witness check sat below the "under the limit" guard, so after a real compaction (context ~42k) it was skipped and `WITNESSED` could never be logged. It now runs first.

### Added
- On a witnessed compaction the supervisor sends the seat `RESUME` (re-read the role file and board item, check the working tree, carry on), once, so a compacted seat keeps working without the owner typing continue. A send with no witness sends nothing.
- Tests: `test_a_witnessed_compaction_is_followed_by_a_resume_message_once`, `test_a_send_with_no_compaction_witness_sends_no_resume`; 9 supervisor tests pass.
