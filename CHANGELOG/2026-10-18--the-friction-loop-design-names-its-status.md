# The friction-loop design names its status, and stops claiming an empty seat tier

`ai_docs/operations/seat-friction-loop.md` was written 2026-10-11 as a step-1 design ("DESIGN ONLY. No
skill text is written in this step"), and time made two of its claims false in one direction only: the tree
grew past it.

- **Header.** A second status line dated 2026-10-18 states what is true now: all seven skills are in
  `agenthub_client/skills` (§10 counts the tree), the loop runs on this room, and §8 is history. The
  2026-10-11 line is kept - it is what the step recorded, and deleting it would rewrite the record.
- **`:51`, the empty-tier claim.** "Nothing here is single-seat *today* (`seat-skills.md` §1 records
  `rooms/<room>/<seat>/` as empty); this set would be its first occupants" is false twice: the seat-skills
  ruling no longer records the tier as empty, and `rooms/` holds 20 `SKILL.md` - 16 under
  `rooms/4genthub-min/` (15 seat-level across the five seats: architect 3, fe-dev 4, go-dev 2, lead 3,
  reviewer 3; plus the room-level `architect-ecosystem-review`) and 4 under `rooms/pdf-awesome/fe-dev/`.
  Replaced with that measured sentence.
- **§8, the ratification list.** "The **levels** in §1 (including the first-ever `rooms/<room>/<seat>/`
  occupants)" names an event that did not happen; the lead ratifies the levels, not a first-ever. Replaced
  with a pointer to the count.

Both were the defect class this room has been fixing all day - a doc stating a fact about the tree that the
tree contradicts - except the facts here are counts of skills rather than paths, so the citation sweep did
not see them. The first draft of this sentence stated 19 (the seat-level total) and then added the
pdf-awesome 4 again; the lead caught the double count, and the count is now stated as the split it is.

Measured, 2026-10-18, at client main `3a6eacc` and the hub pin `4b24c15` (both agree):

    git -C agenthub_client ls-tree -r --name-only main skills/rooms/4genthub-min/ | grep -c 'SKILL.md$'   # 16
    git -C agenthub_client ls-tree -r --name-only main skills/rooms/pdf-awesome/  | grep -c 'SKILL.md$'   # 4
    git -C agenthub_client ls-tree -r --name-only main skills/rooms/             | grep -c 'SKILL.md$'   # 20

Patch: one path, `+3 -7`, `git apply --check` rc 0 at hub main `3b742065`, applied and read back in a
scratch tree (the result carries no remaining "first-ever", "would be" or "holds 19" claim; the one
surviving "first occupants" is §10's "no longer its first occupants", which is true).
