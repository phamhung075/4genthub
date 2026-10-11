### Removed

**Dead `yaml-lib` negation removed from `.gitignore`** (2026-10-05)

- `.gitignore` re-included `agenthub_main/yaml-lib/**` under a "PROTECTED DIRECTORIES" banner, but nothing excludes that path: a scratch
  repository carrying the whole file *minus* that line reports no match for a probe under it (`git check-ignore -v --no-index` -> exit 1, no
  pattern printed), while with the line present the same probe is visible in `git status` (`?? agenthub_main/yaml-lib/`) and the ignored-untracked
  listing is empty. The negation therefore reads as protection and changes nothing. `agenthub_main/yaml-lib` does not exist on disk, has no
  tracked file and no history, and no `yaml*` ignore rule exists to fight. The banner, its comment and the negation are removed rather than left
  as a rule whose intent and effect differ.
- Counts are unchanged by the removal (257861 untracked-ignored / 0 untracked-visible, identical to the reading taken for the `lib/` fix), and
  the probe path stays visible.
- Related, and not ours to fix: `.claude/.gitignore:115` carries the same unanchored `lib/` inside the hooks submodule
  (`git@github.com:phamhung075/4genthub-hooks.git`), where it can still hide a file written under `.claude/` and cannot be corrected from this
  repository.

**Three orphaned Go branch routes deleted** (2026-10-04)

- `POST /api/v2/branches/{id}/assign-agent`, `PUT /api/v2/branches/{id}` and `GET /api/v2/branches/` (`fastmcp/server/httpapp/branch_routes.go`) had no caller left after the dead frontend callers went in `c7e65486`: the live frontend calls only `GET /{id}`, `POST /` and `DELETE /{id}` plus the POST summaries routes, and nothing in the Go tests, `scripts` or `ai_docs` used them (`.swarm/` is gitignored, not part of the repo); they were not a documented contract. Their route handlers, the `BranchController` methods and the adapter methods went with them (`routes/branch_routes.go`, `httpapp/branch_wiring.go`).
- Deleting `GET /api/v2/branches/` also removes the subtree fall-through it created: measured with a routing probe, `GET /api/v2/branches/x/y` and `GET /api/v2/branches/project/p1/summaries` previously matched `GET /api/v2/branches/` (200 with all branches) and now have no match (404), while `GET /api/v2/branches/{id}` still serves a one-segment id. The same trailing-slash subtree behaviour remained for `POST /api/v2/branches/`; it is fixed now (see "The branch collection POST is an exact match" under Fixed below).

**Three unreferenced branch API controller methods removed** (2026-10-04)

- `BranchAPIController.ListBranches`, `UpdateBranch` and `AssignAgent` (`fastmcp/task_management/interface/api_controllers/branch_api_controller.go`) had no caller left once the HTTP routes and their adapter went (`f33db13a`); the package's smoke test only exercises `GetBranchPerformanceMetrics`, and a repo-wide grep found no other reference. `task_management` is otherwise untouched, per the lead's instruction: the assign capability stays alive through MCP (`git_branch_mcp_controller/handlers/agent_handler.go:88` -> facade -> `AgentAssignAgent`), and the service and repository layers keep their unit tests.

**The orphaned branch task-counts route removed** (2026-10-04)

- `GET /api/v2/branches/{id}/task-counts` had no consumer outside `agenthub_go` (the only external reference is the Python mirror, `agenthub_main/src/fastmcp/server/routes/branch_routes.py:314`; no frontend, script or doc caller), the same criterion that removed its siblings. Deleted: the mount, `routes.GetBranchTaskCounts`, the `BranchController` method, the adapter method, `BranchAPIController.GetBranchTaskCounts` and the mount-inventory row. `GET /api/v2/branches/b1/task-counts` now 404s, pinned by `TestDeletedBranchTaskCountsRouteIsNotServed`.

**The unreachable MCP-token chain is gone** (2026-10-05)

- `TokenAPIController.GenerateMCPTokenFromUser` (interface member, controller method) and `TokenApplicationFacade.GenerateMCPTokenFromUser` had no mounted caller: verified by grep over the whole Go tree (only the interface declaration, the two methods, and the tests existed) and against the Python side, whose same chain also has no route caller. No mounted route reached it, so it was unreachable code rather than a served route — the same class the frontend cleanup removed, one layer down. The two tests that existed only for it went with it (the port-test fake method and the facade test's `generate_mcp_token_from_user` block).
- Kept, deliberately: everything the mounted `/api/v2/tokens` routes still serve (`deps.tokens`, `TokenAPIController`'s other methods, the facade's other methods, and the shared `zpTokenFailure` helper) and `MCPTokenService.GenerateMCPTokenFromUserID` — see the handoff: nothing in production calls that one now either, but it is the auth domain's only minting API and the fixture its Validate/Revoke/Cleanup/Stats tests build on, so removing it would gut that coverage rather than remove a route.
