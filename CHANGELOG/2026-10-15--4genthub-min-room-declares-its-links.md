# The 4genthub-min room declares its links again

### Fixed
- `scripts/team/4genthub-min/team.json`: `links` was `[]`, so the client's send gate (`commpolicy`, default deny) refused
  every seat-to-seat message with `no link` and `4genteam up` refused the room ("a room of 5 seats needs its links").
  The room now declares 34 links over its five seats: `delegates_to` lead -> architect, go-dev, fe-dev, reviewer and
  architect -> go-dev, fe-dev, reviewer; `escalates_to` every other seat -> lead and go-dev, fe-dev, reviewer -> architect;
  `collaborates_with` between every pair, which is what a plain `4genteam send` (intent `notice`) needs.

### Testing
- The runtime's `GetRoomLinks` answers 34 links for the room; sends then show `allowed` and `delivered` in the seats'
  audit (`4genteam activity 4genthub-min --kind send`). The two `report` sends that are still refused (lead -> fe-dev,
  architect -> reviewer) have no `escalates_to` link and are left to the owner's ruling.
