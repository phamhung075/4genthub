## Unreleased — fe-dev carries the browser e2e duty; the test-account file is ignored

### Added
- `scripts/team/4genthub-min/guide-e2e-dev.md` (module `guide-e2e-dev@1.1.0`): an addendum to the `fe-dev` guide. `fe-dev` runs Playwright against `https://www.4genthub.com` with the account in `/e2e-test-account`, reads it inside the test process only, and never prints, copies or commits it. There is no separate `e2e-dev` seat.
- `scripts/team/4genthub-min/policy-fe-dev.json` (`policy-fe-dev@1.2.0`): five denies (`cat`, `grep`, `head`, `tail`, `sed` on `*e2e-test-account*`). The cloud overlay of `fe-dev` pinned `policy-fe-dev@1.0.0`, so this version also brings the repo's 1.1.0 content to that seat.
- `team.json`: the `guide-e2e-dev` module and the `fe-dev` overlay `[guide-fe-dev, guide-e2e-dev, policy-fe-dev]`.
- Applied to the cloud: both module versions through `4genteam team apply` on a subset definition; the `fe-dev` seat overlay and the removal of a first, standalone `e2e-dev` seat (created and deleted the same day) through the room API. A running `fe-dev` keeps what it loaded; the change applies at its next launch.

### Changed
- `.gitignore`: `/e2e-test-account` (USERNAME/PASSWORD for the frontend e2e account; untracked and never committed; mode 600).

### Not done
- The full `team.json` apply stops at `guide-fe-dev@1.0.0`: the cloud holds that version with different content from `seedlibrary/blocks/guide-fe-dev.md` (HTTP 409, versions are immutable). Before the stop it applied `guide-lead@1.0.0` and `guide-go-dev@1.0.0`. The drift needs a version bump of the changed guides.
- The orphan cloud modules `guide-e2e-dev@1.0.0` and `policy-e2e-dev@1.1.0` (from the removed seat) remain; module versions cannot be deleted.
- No Playwright config or spec exists yet; it is `fe-dev`'s first task. Nothing was run against the live site.
