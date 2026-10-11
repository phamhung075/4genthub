## Grid input panes: open or hide an input under each seat pane (2026-10-07)

### Added
- `scripts/openrig_watch_tools.py`: `inputs open|hide [--rig R]` opens or closes a small `<seat> > input` pane under every
  seat pane of the herdr grid, and `input --seat S` is the loop each runs: a typed line goes to the seat with `rig send`.
  Off by default, idempotent (a second `open` adds nothing), `hide` closes only the input panes. Owner request: the grid
  panes were watch-only. Documented in `ai_docs/operations/watching-openrig-seats.md`.
- Tested: 4 new specs in `test_openrig_watch_tools.py` (14 pass); `open` and `hide` run on the live 10-seat grid
  (opened 10, second open 0, hid 10, second hide 0). A line was not sent to a live seat during the test.
