## The served API page stops naming the retired agent registry

### Fixed
PLAN item 3, step 6 (board `1133eeb8`). `agenthub-frontend/src/docs/api-reference-prose.en.md` is the
written part of the API page the frontend serves (`ApiDocsPage.tsx:17`). Two of its sentences still
described the agent registry that `76b800b9` retired:

- `:4` listed "a live registry of agents (the `manage_agent` surface)" among what agenthub stores. The
  tool, the `agents` table and the role registry are gone, and
  `agenthub_go/fastmcp/server/httpapp/manage_agent_absent_test.go` guards that absence. The clause is
  removed, so the sentence goes straight from the context hierarchy to the seat model.
- `:74` said assignees are written as `@<seat-key>` "(or a known role)". `NormalizeAssignees`
  (`agenthub_go/fastmcp/task_management/domain/entities/task.go`) accepts only `@<seat_key>` and
  rejects every bare name, a retired role included. The line now says so.

### Verified
`go test ./internal/apiref/ -count=1` -> ok; `committed_artefact_test.go` is the Go test that names this
file. `ApiDocsPage.test.tsx` mocks the file, so no frontend assertion reads its text. Prose only; no
code changed.
