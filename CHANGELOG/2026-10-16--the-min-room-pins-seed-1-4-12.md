# The min room pins seed 1.4.12

### Changed

- `scripts/team/4genthub-min/team.json`: the five seat pins go 1.4.3 -> 1.4.12 (short guide, reviewer verdict in
  the task, no `GATE-*.md`, no `vite build`). The room was restarted off-peak on the rebuilt client with this pin.

### Testing

- JSON parses; all five pins read 1.4.12. `4genteam heal 4genthub-min --check`: clean. All five seats `running`.
