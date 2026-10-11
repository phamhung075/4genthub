## The three facade factories blamed a Python port that already exists

### Changed
- `agenthub_go/fastmcp/task_management/application/factories/{project,git_branch,task}_facade_factory.go`: the unwired-builder guard now names the missing wiring instead of claiming the facade has no Go port. All three application facades ARE ported - project, git branch and task - and the guard fires when `ProjectFacadeBuilder` / `GitBranchFacadeBuilder` / `TaskFacadeBuilder` was never assigned at composition time. `ProjectApplicationFacade is not ported` therefore sent a reader after a port that exists and hid the actual cause; the messages now read `ProjectFacadeBuilder is not wired: set it at server composition`, with the GitBranch and Task equivalents.

### Verified
- **FAIL-first, by putting the three files back to HEAD and re-running the pinning case rather than arguing from the diff.** `fastmcp/task_management/application/factories/facade_builder_guard_test.go`'s `TestFacadeBuilderGuardNamesTheMissingWiring` at HEAD: **FAIL on all three subtests**, each printing the old string verbatim (`ProjectApplicationFacade is not ported`, `GitBranchApplicationFacade is not ported`, `TaskApplicationFacade is not ported`). With the change: `go test ./fastmcp/task_management/application/factories/... -run TestFacadeBuilderGuardNamesTheMissingWiring -count=1` -> **ok**. The three files were then restored and checked **byte-identical** with `md5sum -c` against hashes taken before the revert.

### Found by
- Row `b14b7dee` (the "not ported" marker sweep).
