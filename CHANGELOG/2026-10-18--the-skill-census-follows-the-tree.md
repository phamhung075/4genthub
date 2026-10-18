# The skill census follows the tree: 49 `SKILL.md`, client 8, rooms 20

The inventory in `ai_docs/operations/seat-friction-loop.md` §10 measured the client tree at **43** `SKILL.md`
on 2026-10-18 (share 21, client 6, rooms 16). The tree on client main `3a6eacc`, and on the hub's pin
`4b24c15`, holds **49**: share 21, client 8, rooms 20. The one commit between the pin and client main adds
no `SKILL.md`, so both bases agree.

- `skills/client/` gained `permanent-change` (`122805b`) and `team-benchmark` (`9c2296b`), so the sweep lists
  **8**, not 6. The `client/` tier is never delivered to a seat; the count is inventory, not delivery.
- `skills/rooms/` gained a second room: `rooms/pdf-awesome/fe-dev/` holds 4 `SKILL.md`
  (`fe-dev-role`, `fe-dev-workflow`, `fe-pdf-awesome-driven`, `taste-skill`; `c3b4d5b`, `3a6eacc`), so the
  level holds **20**, not 16. `rooms/4genthub-min/` still holds its 16 (15 seat-level across 5 seat dirs
  plus the room-level `architect-ecosystem-review`), and the lead seat dir still holds 3.
- `share/` is unchanged at 21. `friction-triage` stays at `rooms/<room>/lead/` by ruling (it is used by
  exactly one seat), so the move that an earlier draft counted at `share/` is not part of this census.

Measured with

    git -C agenthub_client ls-tree -r --name-only main skills/client/ | grep -c 'SKILL.md$'   # 8
    git -C agenthub_client ls-tree -r --name-only main skills/rooms/  | grep -c 'SKILL.md$'   # 20
    git -C agenthub_client ls-tree -r --name-only main skills/share/  | grep -c 'SKILL.md$'   # 21
    git -C agenthub_client ls-tree -r --name-only main                | grep -c 'SKILL.md$'   # 49

The section heading's quoted "the 16 on disk" becomes "the 20 on disk", because the quote names what the
`rooms/` level held. A stale census in a doc of record is the same defect class as a citation to a path
that no longer exists: the reader cannot tell the claim from the tree.
