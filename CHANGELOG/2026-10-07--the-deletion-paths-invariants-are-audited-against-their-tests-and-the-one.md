## The deletion paths' invariants are audited against their tests, and the one missing proof is added

- **What the audit found:** both DELETE paths the surface exposes — a room, and a single seat link — are
  implemented and mostly tested already. `DeleteRoom` **refuses a non-empty room** with `ErrRoomNotEmpty`
  naming the count rather than cascading seats away; `RemoveSeat` hard-deletes one seat with its links in
  both directions, its overlay, its resolved snapshots and its reported statuses; and the link delete
  removes exactly one row scoped by the `(from, to, kind)` triple. The row counts, a keeper-room isolation
  control, the **cross-owner** answer (another user gets not-found, not forbidden) and the transactional
  rollback are asserted by `deletion_paths_integration_test.go`, and the link's consequence for the sending
  seat's **policy** is asserted at the mount level by `TestSeatAdminDeleteLinkRemovesItFromTheResolvedPolicy`.
- **The one thing nothing proved, and it is the ruling itself:** nothing re-created what a delete removed.
  The owner's ruling (`945648f5`, *"removing a seat is a hard delete"*) and `RemoveSeat`'s own doc (*"so the
  seat key can be added again from scratch"*) are claims about the **uniqueness constraints** — and a
  tombstone would satisfy every row count, every scoping assertion and the cross-owner check, failing only
  at the create. **CLAIM 5** now removes a seat and creates the same key again, and creates a room with the
  slug `DeleteRoom` removed; those two creates are the only place a tombstone can be caught.
- **An instrument correction, recorded because it is the same class as everything else today:** the first
  pass of this audit reported cross-tenant scoping as an untested gap. **It is not.** The fixture's second
  user is named `other`, and the `CROSS-OWNER` block asserts that user gets `ErrRoomNotFound` and deletes no
  link — the grep that "found" the gap searched for `user2|otherUser|second user|cross` and missed the name
  the file actually uses. The gap list was wrong, not the file.
- Files: `seat_management/application/services/deletion_paths_integration_test.go`, `CHANGELOG.md`,
  `TEST-CHANGELOG.md`.
