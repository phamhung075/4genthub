# The room definition carries the link table the live room already had

`scripts/team/4genthub-min/team.json` declared `"links": []` while the running room's `spec.json`
declared 34 links. The file is where a room definition lives before a launch reads it, so a room started
from the committed file would be a room where no seat may send to any other — the failure this file's
own row vocabulary calls a mute room.

The 34 rows, by what they license in the client (`internal/commpolicy/policy.go`, `allowedKinds`):

- **20 `collaborates_with`** — every ordered pair of the five seats. This is what licenses
  `--intent question` and `--intent notice`, so it is the room's general channel.
- **7 `delegates_to`** — lead to each of the four seats, and architect to go-dev, fe-dev and reviewer.
  This is the only kind that licenses `--intent task`.
- **7 `escalates_to`** — the four seats to lead, and the three report edges to lead. `--intent report`
  and `--intent escalation` use it, so a report is lead-ward by construction and a peer-to-peer
  `--intent report` is refused by the policy rather than by a missing link.

Measured before committing: the file's triples and the live spec's triples both number 34 and compare
`IDENTICAL` (a `sorted` set comparison over `(from, to, kind)`), and `python3 -m pytest
scripts/tests/test_team_definition.py -q` prints `20 passed` against the modified file.

## What this commit is not

I did not author the edit. It was uncommitted in the shared working tree at 17:27:39Z, seventeen seconds
before the same table appeared in the live room's `spec.json`, which is why both the room and the file
changed within the same half-minute. It is committed here so that the room's definition and the room's
behaviour stop disagreeing; the decision the table records is not mine and is not changed by this commit.
