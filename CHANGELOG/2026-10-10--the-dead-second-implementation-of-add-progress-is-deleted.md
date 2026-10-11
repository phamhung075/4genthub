## The dead second implementation of `add_progress` is deleted

Two implementations of one live verb sat in the tree, and the one a reader was most likely to find first
wrote **nothing at all**: it checked that the context existed and then returned an error **by design**, faithfully
reproducing a Python quirk (`'AddProgressRequest' object has no attribute 'content'`). That ambiguity is what made
the `user_seq` incident hard to bound — a reader following the wrong implementation files the wrong defect.

### Removed
- `agenthub_go/fastmcp/task_management/application/use_cases/add_context_progress.go` — the no-op use case, with the
  test cases that pinned its preserved bug (`TestSmallUCAddContextProgressMissingContext`,
  `TestSmallUCAddContextProgressKeepsAttributeBug`) and their section in `small_use_cases_draft_test.go`. They
  asserted the quirk rather than a behaviour the product wants, which is exactly the class of test the mission
  says to delete rather than preserve.
- `AddProgressRequest` and `NewAddProgressRequest` in `dtos/context/context_request.go` — **orphaned by that
  deletion**, so in scope as code made obsolete by the cutover: the only references in the module were their own
  definition and the use case that is now gone.

### Why the deletion is the fix rather than a behaviour change
- **The verb was never served by that code.** The handler for `manage_context add_progress`
  (`unified_context_controller/handlers/context_operation_handler.go:99`) calls
  `facade.AddProgress(...)` → `UnifiedContextService.AddProgress` (`unified_context_service.go:558`), which is
  what actually appends the note to the context row and calls `UpdateContext`. The deleted path was unreachable
  from it, which is why nothing user-visible changes.
- **Caller check first, established by reading, not assumed**: module-wide, `AddContextProgressUseCase` appears
  only in its own file and the two test cases above — **no non-test caller anywhere**. No rerouting was needed,
  so none was invented.

### Verified
- **Acceptance, read rather than asserted**: `grep -rn "AddContextProgressUseCase\|AddProgressRequest" --include=*.go`
  over `agenthub_go` returns **nothing** — the second implementation and its request type are gone, so the
  ambiguity cannot be filed against again.
- **The live path is intact**: `UnifiedContextService.AddProgress` still defines the verb servlet-side, and the
  handler → facade → service chain is untouched.
- `gofmt` clean on every touched file; `go vet` clean; the DTO and use-case packages ok; module-wide
  `go test ./... -count=1` → **exit 0, 140 ok, 38 no-test, 0 FAIL**.
