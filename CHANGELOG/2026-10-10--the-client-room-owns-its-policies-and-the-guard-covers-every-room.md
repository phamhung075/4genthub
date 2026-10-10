## The client room owns its policies, and the guard covers every room

### Fixed
- `scripts/team/4genthub-client/mission.md`: the Rules block told every seat to `Push to the client repo main`, while all four policies the same room pins carry `match: git push*` with an approval `deny` - an instruction each seat's own policy refuses, and this module sits in EVERY seat overlay, the lead's included. The sentence now reads NO SEAT PUSHES - the PRINCIPAL pushes the hashes to the client repo `main` once the lead has seen the phase green. **The policy is untouched: the mission was what was wrong.** 518 words, inside the mission's 350-520 band.
- `scripts/team/4genthub-client/team.json`: its four policy modules pointed at `../4genthub-min/policy-*.json`, so the new room broke silently the moment its sibling renamed, edited or deleted one. The room now OWNS its policies - `policy-lead.json`, `policy-go-dev.json`, `policy-reviewer.json`, `policy-writer.json` copied beside it, byte-identical to the min room's at this commit - and the module `file` fields are local.

### Changed
- `scripts/tests/test_team_definition.py`: the definition guard now runs for EVERY room under `scripts/team`, DISCOVERED rather than listed (`ROOMS = sorted(p.name for p in TEAM_ROOT.iterdir() if (p / "team.json").is_file())`). Before this, `TEAM_DIR` hard-coded `scripts/team/4genthub`, so `4genthub-min`, `4genthub-ab` and the new `4genthub-client` room were gated by nothing at all - the reviewer of `0a0d3795` had to verify the client room's invariants by hand.
  - Per room: every module file resolves, is non-empty and (for a policy) parses as one JSON object; the modules and the union of the overlays' slugs are equal in both directions; the `seat_overlays` keys EQUAL the seat keys (a seat with no overlay would start with no context whatever); every link endpoint is a seat; every seat type is one of the nine; the room's runtimes match `ROOM_RUNTIMES`, and an omp seat names its model and the seat-type version it pinned.
  - The word bands are per room now (`ROOM_WORD_LIMITS`), and a room-local instruction file with no band FAILS instead of passing unnoticed; a band no file uses is stale.
  - `test_dry_run_makes_no_requests_and_needs_no_env` is parametrized over every room, so the client has to load and plan each room's definition and not only the dev room's.
  - `MODULE_FILES` is deleted: a module's own `file` field is the source of truth, and `_context_file` reads it.
  - A room that exists with no entry in `ROOM_RUNTIMES` or `ROOM_WORD_LIMITS` fails here, so a room added tomorrow is gated the moment it lands. (The check is one-directional on purpose: an entry for a room a given checkout does not have costs nothing, and a room can sit in a working tree before it is committed - `4genthub-ab` does.)

### Verified
- `PYTHONPATH=agenthub_client/src python3 -m pytest --noconftest -p no:cacheprovider scripts/tests/test_team_definition.py scripts/tests/test_seatcheck_guard.py -q` -> **46 passed** (35 before the change); the collected set carries 5 parametrized cases for each of the four rooms.
- **THE RED, SHOWN RATHER THAN ARGUED:** `cp -r scripts/team/4genthub-client scripts/team/zz-broken-room`, then delete the copy's `mission.md`, then the same command -> **5 failed, 46 passed**, every failure naming the copy: `zz-broken-room/client-go-mission: mission.md does not resolve`; `zz-broken-room ships ['omp'], the expectation says []`; `the bands and the room's own instruction files disagree - a file with no band would pass unnoticed`; `a room with no runtime expectation would be ungated`; and the dry-run case exiting 2. The copy was removed (`shutil.rmtree`) and the same command is green at 46.
- The client mission's word count after the sentence change: 518, read with the same `len(text.split())` the guard uses.

### Found by
- Lead row `55e30624`, from the reviewer's gate on `0a0d3795`.

### Not taken here
- `scripts/team/4genthub-ab/team.json` carries the SAME borrowing pattern (`ab-policy-lead` and `ab-policy-go-dev` point at `../4genthub-min/policy-*.json`). It resolves, so the new guard is green on it, and the row named only the client room: it is reported to the lead rather than swept into this commit.
