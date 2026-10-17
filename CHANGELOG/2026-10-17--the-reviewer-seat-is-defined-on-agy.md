## Changed

- `scripts/team/4genthub-min/team.json`: the reviewer seat is defined on `agy` with `gemini-3.8-flash-low` (owner brief item 5). The definition is the room's source of record; the LIVE room still runs the reviewer on `omp` until the owner applies it, because the live `spec.json` is written by the launcher and lies outside a seat's write scope.

### Measured, so the applying step is one command

- ONE seat can be moved without cycling the room: the runtime's `restart_seat` RE-READS `<room>/spec.json` from disk, so the owner writes that file and runs `4genteam room reseat 4genthub-min reviewer` - the reviewer alone restarts, on agy.
- The runtime has no set-runtime verb (`IpcRequest` carries `StopSeat`, `RestartSeat` and `SetSeatModel`, and nothing that changes a runtime), so a runtime is fixed by the spec; and `4genteam up RIG --team DIR` on a live room is READ, not restarted, in its own help.
- `agy` 1.4.0 is alive on this box and the seat's own launch shape reaches it: `agy --model gemini-3.8-flash-low --print` answered in 5.3 s, and `agy --model 'gemini-3.8-flash-low'` in a tmux pane answered a typed message in about 20 s. `sync switch` answers `applied=manual` for a runtime change and names the reseat; its manual text says whether a restart carries a changed runtime "is not established" - it is established here: the restart carries whatever `spec.json` holds.
