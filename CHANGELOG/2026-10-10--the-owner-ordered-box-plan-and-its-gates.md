## The owner-ordered box plan, its owner-gates, and the boxes that stay out — recorded in NEXT_GEN

### Changed

- `agenthub_go/NEXT_GEN.md` — a block at `:457`-`:477`, after the group O/P boxes and before "Deliberately NOT
  queued here", records the owner's ordering of 2026-10-10 (relayed in `qitem-20261010205726-e8717afa2b95177b`):
  **the chain and the seat per box**, **the five owner-gates**, and **the three boxes that stay out**. **It amends
  no box and ticks none** — the `[x]`/`[ ]` marks in its table are the boxes' own as of this write, and the block
  says so.
- **Order and seats** (group O's header, `:425`, plus each box's own head): O1a (`:426`, go-dev, landed) → O1b
  (`:427`, go-dev, landed) → O2 (`:429`, go-dev, landed) → O3 (`:430`, go-dev; its client half rides the
  ONE-CLIENT build) → O4 (`:431`, go-dev) → O5 (`:432`, go-dev) → O6 (`:433`, go-dev) → O7 (`:434`, go-dev, then
  the client); O8 (`:435`, fe-dev or web-dev) starts once O1a lands; O1c (`:428`, go-dev and fe-dev) lands with
  O8; G3 (`:404`, `:405`, `:413`, go-dev); O9 (`:436`) is the owner's own decision list.
- **The owner-gates, recorded as given:** **O1c** → the `0001` baseline mark **+ O8**; **O5** → O9(a), privacy for
  Jev on real data (`:436`: "(a) blocks O5's Jev call on real data"); **O6** → after O5's agreement rate is
  accepted (the box's own head); **O7** → O9(b) (`:436`: "(b) blocks O7"; the box's own tail: "Owner confirmation
  needed first"); **G3's codex clause** → accept the weaker level or restrict links to `claude-code` (`:413`(b)
  records that restriction as already implemented in `handleUpsertSeatLink`, and `:405`'s tail keeps the box open
  on the install that "nothing builds or links (`<pins dir>/bin/seatcheck`, so a guarded seat cannot yet send)"
  and "the codex decision").
- **Stays out:** D1 (`:367`), F5 (`:394`), F7 (`:396`) — each quoted with its own line's reason (D1's ask answered
  2026-10-05 but its build missing; F5 "optional, last" and unbuilt; F7 out of scope by its own wording). The
  block also notes that the doc's own OPEN list at `:355` carries D3 and D5 while the ordering names neither, so
  the silence is recorded rather than filled.
- **The citation discipline is stated in the block, and one citation obeys a different rule on purpose:** every
  cited line is ABOVE the block (the highest is `:436`), so writing it moves none of them; **the `0001` baseline
  ruling sits BELOW it (T12's status line, at `:686` after this insert), so it is quoted verbatim instead of being
  cited by a number this insert would have shifted** — the one place where a line number would have been wrong
  within seconds of being written.
- **Verified after the insert, mechanically:** a 24-pair check asserted that each cited line still carries the box
  label, mark and clause the block attributes to it (`:426` `[x] O1a` … `:436` `[ ] O9`, `:404` `[ ] G3`,
  `:425`'s order sentence, `:355`'s OPEN list, `:367`/`:394`/`:396`'s verdict phrases) — 24/24 held, and the
  quoted T12 sentence was found verbatim at `:686`. **No instrument covers `NEXT_GEN.md`'s line citations**
  (measured: neither `scripts/CITATION-AUDIT.py` nor `scripts/COUNTS-AUDIT.py` names this file), so the check was
  a throwaway run at this revision rather than a standing guard.

### Not touched

- No Go source, test, route, table, migration, or frontend file. `agenthub_go/NEXT_GEN.md` is the only document
  edited. The commit carries explicit paths (`agenthub_go/NEXT_GEN.md` + this entry), because the working tree
  holds other seats' in-flight work at that moment (go-dev's item-3 deletions, fe-dev's frontend fix).
