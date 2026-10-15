## 2026-10-15 - the commit notice skips the committer

### Fixed
- `scripts/git-hooks/notify-seats`: the post-commit notice went to EVERY running seat, the committing one included. A seat's message to itself is refused ("no link"), so every commit made inside a seat left a burst of refusals in the room's audit - measured by the owner at 18:0xZ with `4genteam activity <room> --problems` (bursts of five, from lead, architect and go-dev; harmless to the work, pure noise in the log). The loop now skips the row whose session equals `$AGENTHUB_SESSION_NAME`, the identity a commit made inside a seat runs under.
- The skip is narrow on purpose: an unset or foreign identity skips nobody, so a commit made outside the room's own seats - the shared checkout's Claude Code session, for instance - still tells every running seat. A seat nobody tells is worse than a refusal nobody reads.

### Testing
- `scripts/tests/test_notify_seats_behind_note.py`: two cases added over the real script. The committing seat is skipped while the other running seat is still told; and an identity from outside the room skips nobody (the control - without it, a hook that skipped every seat would pass). Measured end to end as well: with the identity unset the notice is sent, with the committer's own session it is not, with another room's it is sent again.
