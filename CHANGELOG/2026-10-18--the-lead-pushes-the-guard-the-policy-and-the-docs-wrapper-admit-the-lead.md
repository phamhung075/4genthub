## The lead pushes: the guard, the lead's policy and the docs wrapper admit one seat

Owner ruling, 2026-10-18: the lead pushes `main` after the reviewer gate and a green test run; every
other seat still does not. The exception is the seat KEY `lead`, decided at one point per surface.

### Changed

- `scripts/team/4genthub-min/policy-lead.json`: `git push*` is `allow` (one entry, no sibling). The four
  other modules keep their single `deny`.
- `scripts/git-hooks/git_commit_capture.py`: the docs-only check exempts the lead seat, beside the
  owner's host and `OWNER_DOCS_COMMIT=1`. `session_seat` reads both spellings a runtime sets -
  `agenthub--<room>--<seat>` and the OpenRig `<room>-<seat>@<room>` - and `lead_is_committing` accepts
  the session in either, or `AGENTHUB_SEAT=lead` when the session is the one the suite carries. A name
  that merely starts with `lead` (`lead-dev`, `lead2`) is another seat and is refused.
- Client (`4genthub-min/lead-push`, `agenthub_client/internal/clientguard/guard.go`): the push refusal
  skips a session whose seat is `PushAuthoritySeat` (`lead`), in the checkout and in a linked worktree;
  the shared-checkout commit refusal skips the lead too, because the checkout is where the lead merges
  and commits `main`. `SessionFromEnv` reads the OpenRig name first and the canonical runtime name
  second, with the same `room`/`seat` shape check. The refusal now names the route out as the lead
  ("only the lead pushes", "Hand the commit hash to the lead"), not the owner.

### Tests

- `scripts/tests/test_seat_policy_commit_form.py::test_only_the_lead_module_may_push`: the lead module
  allows the push in exactly one entry, the four other modules deny it in exactly one each.
- `scripts/tests/test_git_commit_capture.py::test_the_lead_seat_lands_documentation_under_either_session_spelling`:
  real commits in a temp repository - the lead lands a doc-only commit under each spelling and under
  `AGENTHUB_SEAT=lead`, `lead-dev` is still refused. The autouse fixture now also removes
  `AGENTHUB_SEAT` and `OPENRIG_SESSION_NAME`.
- Client `guard_test.go`: the push refusal's words, the lead admitted in the checkout and in a
  worktree, every other seat (including `lead-dev`, `lead2`, empty) still refused, the lead's commit in
  the shared checkout admitted while another seat's is refused, and the canonical name parsing.
- Client `guard_e2e_test.go`: `TestTheLeadsPushAndCommitGoThrough` - real git, real hooks: the lead's
  push from a linked worktree (OpenRig spelling) and its commit and push in the checkout (canonical
  spelling) go through, and the remote's `main` is the lead's commit.

### Measured

`python3 -m pytest --noconftest -p no:cacheprovider scripts/tests/test_git_commit_capture.py -q` ->
14 passed; `scripts/tests/test_seat_policy_commit_form.py` -> 7 passed; client
`go test ./...` -> 35 packages ok; `cargo test --offline` in `rust/agenthub-runtime` -> 184 + 1 + 18 + 1
passed. `scripts/tests/test_census_audits.py` has 3 red cases in the same run, on the census instrument's
stale anchors in `ai_docs/api-integration/surface-inventory.md`; this branch touches neither `ai_docs/`
nor the schema it reads.

### Publication (`scripts/team/4genthub-min/team.json`)

The render that a seat installs is the hub's fold of its policy modules, so the policy reaches a seat
only after `4genteam team apply` publishes the module. Applying the room definition as it stood was
refused twice: the guide modules carried a version whose stored body had already moved (HTTP 409), and
the two `reviewer -> go-dev` / `reviewer -> fe-dev` links formed a launch cycle the hub now refuses.
The room definition therefore takes a version for every module whose content is the tree's - guides and
policies both, one patch step each - and drops the two cycle links. The cycle's reverse edges
(`go-dev -> reviewer`, `fe-dev -> reviewer`) stay, as `go-dev` and `fe-dev` hand their work to the
reviewer.

Measured after the publish, same command the client installs from:
`4genteam policy render --room 4genthub-min --seat lead` -> `git push*` is `approval: allow`, one
entry; the four other seats' renders keep `git push*` as `deny`.

### Landing

- Client `main` = `2ced214` (`9d95b29` + `8b7ad75` merged `--no-ff`): 35 Go packages ok, `go vet` rc 0,
  205 Rust tests passed.
- Hub `main` = `06b2e35f` + pin `421d01f0` (`agenthub_client` gitlink `4b24c15 -> 2ced214`): 138 Go
  packages ok, the two policy pytest files 19 passed.
