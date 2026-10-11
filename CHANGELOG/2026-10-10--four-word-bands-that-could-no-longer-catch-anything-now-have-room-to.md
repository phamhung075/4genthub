## Four word bands that could no longer catch anything now have room to

### Fixed
- `scripts/tests/test_team_definition.py`, `ROOM_WORD_LIMITS`: four of the ten bands sat within **five words** of their ceiling, so they had stopped doing the two things a band exists for — catching bloat and catching truncation. Each ceiling moves to a round number above the file's own length, with the floors untouched:

  | room / file | words | band before | band after | headroom |
  |---|---|---|---|---|
  | `4genthub-client/client-go-mission` | 518 | 350–520 | **350–560** | 2 → 42 |
  | `4genthub/mission-4genthub` | 516 | 350–520 | **350–560** | 4 → 44 |
  | `4genthub/area-docs` | 147 | 80–150 | **80–190** | 3 → 43 |
  | `4genthub/area-quality` | 195 | 100–200 | **100–240** | 5 → 45 |

  The other six bands are unchanged (project-4genthub 132, delegate-deepseek 32, area-web-frontend 54, area-go-backend 74, ab-terse 24, ab-verify 28). The pattern is what makes this one change rather than four: three different ceilings had all been filled to within five words, which is what a ceiling that was fitted to its file looks like.

### Not changed, deliberately
- **No module text grew.** The commit touches the band table and its comment only: `git status --porcelain -- scripts/team/` shows nothing, and every banded file is byte-identical to its parent commit. A module that needs to grow is a different row with its own reason.
- **The floors are untouched.** They are the truncation check, not a style bound.
- **The min room's table stays empty, and the comment now says why**: every instruction module `4genthub-min` names resolves into the Go seed library, whose content the seed owns, so it has no room-local file to band. An empty table copied as a convention would be copying an absence.
- **The rule is now written above the table**, so the next band is justified rather than fitted: the ceiling is a round number above the file's length with about two sentences of room; both ends bite.

### Verified
- **Green at the new numbers:** `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` → **90 passed**, 3 warnings, with every banded module byte-identical to its parent (the band check alone: 3 passed, one per room).
- **Old versus new headroom, computed with the guard's own rule** (bands parsed from the table, words = `len(text.split())`): the four moved lines read 2/4/3/5 words before and 42/44/43/45 after; the six others are unchanged.
- **Bloat side, by effect:** appending filler to a real mission → `AssertionError: 4genthub-client/client-go-mission: 638 words, expected 350-560`, one failed and two passed, then the file restored and the module diff back to zero lines.
- **Floor side, by effect:** truncating a real instruction file → `AssertionError: 4genthub/area-docs: 30 words, expected 80-190`, one failed and two passed, then restored byte-identical to `HEAD` and green again.
