# Syncing local OpenRig seats with the 4genthub cloud

The cloud owns what a seat is and resolves it to a snapshot named by a hash. The local client
compares each seat's pinned hash with the cloud's, adopts a newer snapshot, and can restart the
seat so it loads it. Tool: `scripts/openrig_seat_client.py` (it calls `openrig_seat_sync.py rig`
to adopt, so the pinning rules live in one place: never fall back to another snapshot).

```
cloud room  --hash per seat-->  openrig_seat_client.py  --rig ROOM --update-->  <store>/<room>/rig
                                         |                                              |
                                         +-- relaunch (when quiet) -->  seat loads it at start
```

**`openrig_seat_client.py` is retiring into `agenthub-client sync`.** `status` is already ported —
`agenthub-client sync status <room>` is the same check. `sync` and `watch` stay on this script until
`agenthub-client sync rig` and `sync watch` are ported; **the script and its test are deleted in that
commit.** (Architect decision: `ai_docs/core-architecture/agenthub-system-architecture.md D4`.)

Environment: `AGENTHUB_URL` (for production `https://api.4genthub.com`) and `AGENTHUB_TOKEN`. The
token is passed on in the environment and never printed or written. The store is
`~/.openrig/agenthub-seats` (`--out`).

## Commands

```bash
python3 scripts/openrig_seat_client.py status 4genthub-dev                    # pinned vs cloud, per seat
python3 scripts/openrig_seat_client.py sync 4genthub-dev                      # adopt newer snapshots only
python3 scripts/openrig_seat_client.py sync 4genthub-dev --relaunch quiet     # adopt, then restart changed seats
python3 scripts/openrig_seat_client.py watch 4genthub-dev --interval 60 --relaunch quiet
```

`--seat NAME` (repeatable) limits the work; `--rig NAME` when the rig name differs from the room.

| Mode | Effect |
|---|---|
| `--relaunch none` (default) | adopt only; a running seat keeps what it loaded and changes at its next launch |
| `--relaunch quiet` | restart each changed seat after it has been idle 30 s; a seat that is not quiet within 25 min is reported and left running |

Exit codes: 0 ok (`status`: all in sync), 2 usage or environment, 3 a cloud, sync or relaunch step
failed, 4 `status` found a seat behind or not pulled.

## Know before you use it

- **Only cloud rooms sync.** The cloud has the rooms `4genthub-dev` and `smoke`. A rig that exists
  only locally (the `4genthub-min` team) has no room, so `status 4genthub-min` answers `room not found`.
  It becomes syncable once the cloud has a room for it, which is part of
  `SEAT-CONTEXT-AS-BLOCKS.md`.
- **A running seat never changes live.** Adopting changes the files; the seat reads them at launch.
- **Not yet built:** the frontend "Apply" button. When the cloud records apply requests, `watch`
  will act on them; today `watch` compares hashes by polling.
