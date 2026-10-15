# The docs of record stop teaching the five removed client verbs

The client's `sync room`, `sync rig`, `sync status`, `seat sync`, `seat status` and `seat watch` went
with the rigspec route the server deleted. Three documents here still taught them as commands.

### Changed
- `AGENTS.md` §2: the skills line said `share/` and `rooms/<room>/` "are delivered to seats by
  `4genteam sync room`". The delivery is a seat's own restart (`4genteam seat reseat`), which is what
  copies them into the seat directory and declares them in its `agent.yaml`.
- `ai_docs/operations/syncing-seats-with-the-cloud.md`: the header, the diagram, the `## Commands`
  block and the surrounding prose now name what survives (`sync pull ROOM SEAT`, `sync bundle ROOM
  SEAT`, `sync offline-install TARGET`, `seat reseat ROOM --seat NAME`, `send`, `ps`) and state that
  the comparison half - `seat status`, `seat sync`, `seat watch` and the `sync rig` adopt step - is
  gone with `GET /api/v2/rooms/{room}/rigspec` (`cbc51bae`). The document's dated measurements are
  left as the record they are, with the removed verbs marked as removed inside them (the `--relaunch`
  mode table, the exit-code list, the "only cloud rooms sync" bullet, the `watch` polling line).
- `ai_docs/core-architecture/agenthub-system-architecture.md` §2.6: the paragraph naming the client's
  verb surface is corrected by a dated note, because `sync status`, `sync rig`, `seat sync`, `seat
  status` and `seat watch` are gone with the same route. The 2026-10-08 decision record further down
  (§ the fold row) is left as the dated record it is.
- `ai_docs/operations/client-features-for-the-dev-team.md` §1.4: two rows listed `seat sync` as an
  existing capability; both now name `seat reseat` and say when `seat sync` left.

### Verification
- A grep of this tree's live doc surface (`AGENTS.md`, `NEXT-GEN2.md`, `ai_docs/`, `docs/`,
  `scripts/`, root `*.md`) for `sync room|sync status|seat sync|seat status|seat watch|rigspec` now
  returns only historical records (this ledger, dated GATE reports, `NEXT-GEN2.md`'s design history)
  and the server's own `seat status` noun (`agenthub_go/.../machine_status_repository.go` and
  friends), which is a reported seat state, not a client verb.
