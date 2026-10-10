## The served frontend is checkable in one command, and the two measures that made the old census read clean are the ones it refuses

### Added
- `scripts/check_served_frontend.py`: the deploy acceptance as a command. It fetches the index CACHE-BUSTED (a cached index can hide a rebuild behind a stale reference), takes the CLOSURE — the index's refs, then the refs found inside those, to a fixpoint — and asserts both halves: at least one `4genteam` verb is served (`sync pull`, `sync switch`, `bridge`) and ZERO `openrig_<name>.py` names, matched as a PATTERN rather than a closed list of four so the next retirement is covered without editing the census. It prints the index's AND the entry's `Last-Modified`, because a bare pass/fail loses the date — and the date is what dated this drift. Exit 0 fresh, 1 stale or mismatched, 2 cannot measure, where **2 is never a pass**: a 404 inside the closure yields `INCOMPLETE`, since a stale chunk could be hiding in the part that did not arrive.
- `--expect-dist` / `--expect-entry`: identity instead of a two-token census. The census alone is satisfied by ANY build after the rename landed (`75f81494`) — on 2026-10-10 a window of 21 commits touching `agenthub-frontend/src`. Given the build a deploy just made, the assertion becomes "the served entry chunk IS this build's entry chunk, and every file the served app is composed of exists in it". A directory holding nothing but the token passes the census and FAILS identity: that is the difference between "newer than 08 Oct" and "is this build".
- `scripts/tests/test_check_served_frontend.py`: 13 cases over a threaded `http.server` and temp docroots; no case reaches production, and every case goes through the same HTTP path the deploy uses.

### Changed
- `check-served-frontend.sh` — the seat-area interim instrument — **RETIRES**: the tested script supersedes it, so there is one instrument rather than two. It earned its place by catching the live defect first, and that is the credit it gets here rather than being left beside a second mechanism.

### Verified
- **Against production, 2026-10-10 07:03Z**, exit **1 STALE**, and naming WHERE: `/assets/SeatDetailPage-BpUArPYK.js` carries `openrig_seat_sync.py` twice and `/assets/SeatsPage-DRldE7DQ.js` carries `openrig_bridge.py` once; 0 verbs, 92 assets / 1,762,641 bytes; index and entry both `Thu, 08 Oct 2026 19:26:51 GMT`.
- **Against a fresh local serve of a HEAD build** (`agenthub-frontend/build`, 127.0.0.1:8765): exit 0; `--expect-dist` MATCH; a wrong `--expect-entry` exit 1; a token-only directory censused 0 and refused by identity; an unreachable origin exit 2.
- `python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` → **49 passed, 0 failed**, the six pre-existing files included.
- **Two cases caught bugs in the census itself while it was written**, which is the evidence they are not decoration: a JS-only build inventory reported a stylesheet as `absent from the build` (a false mismatch that failed a correct build), and the report counted the files carrying a stale name without naming them.

### Found by
- Row `b70278f2`, and the two independent censuses that agreed before either had an instrument: feedback-dev at 06:56Z and fe-dev at 06:57Z, on a production bundle whose index and entry both date to 2026-10-08 19:26:51Z.
