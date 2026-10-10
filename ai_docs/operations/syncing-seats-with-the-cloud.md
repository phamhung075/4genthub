# Syncing local OpenRig seats with the 4genthub cloud

The cloud owns what a seat is and resolves it to a snapshot named by a hash. The local client
compares each seat's pinned hash with the cloud's, adopts a newer snapshot, and can restart the
seat so it loads it. Tool: `agenthub_client/src/agenthub_client/seat_client.py`, run as
`4genteam seat` (it calls `4genteam sync rig ROOM --update` to adopt, so the pinning rules live in
one place: never fall back to another snapshot; a missing pin is an error).

```
cloud room  --hash per seat-->  4genteam seat  --4genteam sync rig ROOM --update-->  <store>/<room>/rig
                                      |                                                      |
                                      +-- relaunch (when quiet) -->  seat loads it at start
```

**The `scripts/openrig_*.py` paths this document used to instruct are gone, and the port they were
waiting on has happened.** `scripts/openrig_seat_client.py` and `scripts/openrig_seat_sync.py`
moved into the client package as `seat_client.py` and `seat_sync.py`; both are absent from the
working tree and the index (the deletion is staged with the pending line decision, not yet
committed, so `git show HEAD:scripts/openrig_seat_client.py` still resolves while the file on disk
does not). The console script is `4genteam` (also installed as `agenthub-client`), which runs
`agenthub_client.cli:main`. **Two older instructions are therefore dead and must not be followed:**
`python3 scripts/openrig_seat_client.py …`, and `agenthub-client sync status <room>` — the latter
was never a verb, because `sync` is `seat_sync` (`pull`, `rig`, `bundle`, `offline-install`,
`respawn`, `install-checker`, `switch`), while per-seat `status` lives under `4genteam seat`.

Environment: `AGENTHUB_URL` (for production `https://api.4genthub.com`) and `AGENTHUB_TOKEN`. The
token is passed on in the environment and never printed or written. The store is
`~/.openrig/agenthub-seats` (`--out`).

## Commands

```bash
4genteam seat status 4genthub-dev                    # pinned vs cloud, per seat
4genteam seat sync 4genthub-dev                      # adopt newer snapshots only
4genteam seat sync 4genthub-dev --relaunch quiet     # adopt, then restart changed seats
4genteam seat watch 4genthub-dev --interval 60 --relaunch quiet
4genteam sync rig 4genthub-dev --update              # materialize the room: rig.yaml plus links
```

`--seat NAME` (repeatable) limits the work; `--rig NAME` when the rig name differs from the room.
`4genteam seat sync` is the per-seat loop; `4genteam sync` is the module that pulls, pins and
materializes (`--help` lists its seven subcommands).

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
- **The cloud's copy of a room's module text can lag the repo, and a resolved hash does not say
  otherwise** (measured 2026-10-10, `4genthub-min`). The room serves a copy of `project-4genthub`
  (version 1.0.0) that differs from its source `scripts/team/4genthub/project-4genthub.txt` in three
  hunks - the `PROJECT.` line still reads "being ported from the Python backend in `agenthub_main`"
  although the tree retired that backend (`python-backend-final`); the LAYOUT bullet
  "`agenthub_main`: legacy Python backend; its script tests live in `agenthub_main/src/tests/scripts`."
  still exists although the repo deleted it; and TESTS still carries that pre-move pytest command plus
  a TypeScript-error baseline the tree removed on 2026-10-03 - and the guide block itself differs the
  same way (`guide-reviewer` still names the pre-move pytest command, `shared-modules/guide-common.md`
  still says to `git add -- <path>` and stage first where the settled form at `guide-common.md:22` is a
  pathspec commit with no pre-stage). `4genthub-min/lead` resolved to the same snapshot hash on
  2026-10-08 21:23Z and on 2026-10-10, which rules out a stale cache but not a publish that landed
  **unreferenced**, because an unreferenced version changes nothing a seat sees; the one command that
  separates the two is `GET /api/v2/openrig/modules` (latest per module, with `sha256`) or `GET /api/v2/openrig/modules/{slug}/versions/{version}`. **No corrected body had reached a
  seat in the two days before 2026-10-10.** The corrections are committed in the repo (`0ea06c77`,
  `1f0b177a`, `d1114170`) and publishing them is the principal's token, not a seat's; a corrected body
  must also go out as a NEW version and the refs must name it, because a module version is immutable
  (`modulecontent.go:4`) and the manifests name literal versions, so an unreferenced publish renders the
  old row and looks exactly like a publish that never happened. Until it lands, a seat that needs the
  current text reads the repo source, not the served render.
- **Not yet built:** the frontend "Apply" button. When the cloud records apply requests, `watch`
  will act on them; today `watch` compares hashes by polling.
