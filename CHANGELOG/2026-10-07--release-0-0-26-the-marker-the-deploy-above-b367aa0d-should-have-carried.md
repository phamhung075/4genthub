## Release `0.0.26` — the marker the deploy above `b367aa0d` should have carried

- **Why this bump exists and `0.0.25`'s did not:** the range pushed above `b367aa0d` **changes server
  behaviour** — `6ef91fc2` (the policy render can express `allow`, the limits text stops putting an
  allowance under a `Refused` heading, and a match that is both refused and allowed is now refused by
  name), `fd5754bc` (a seat-scoped `override` may not introduce an allowance), `bd7fa93e` (the task-MCP
  search filters accept the integer forms a caller actually sends) — and it shipped under an **unchanged**
  `ReleaseVersion`, so `/health` reported `0.0.25` for it exactly as it did for the deploy before. There
  were bytes to mark this time; the marker was simply missed while the commits landed one at a time.
- **Consequence, stated plainly:** until a push carries this commit, **`/health` cannot distinguish the
  current deploy from the previous one**, so the version check confirms nothing about the behaviour above.
  This commit moves the reported version to `0.0.26` and needs **one more push** to take effect — the push
  is the owner's, and the range it marks is already deployed.
- Files: `agenthub_go/fastmcp/config/version.go`, `CHANGELOG.md`.
