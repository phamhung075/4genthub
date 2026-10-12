# The test-changelog entry that was narrower than its diff

2026-10-12. The two post-gate minors from the frontend gate's APPROVE at `414ca2e7` (task `40af6a98`).
No product code and no test changed, so the shipped bundle is untouched.

## The entry now describes the whole diff

`TEST-CHANGELOG.md`'s `componentTypes.test.ts` entry said the file "loses one line". The change it
describes also trims trailing whitespace on two lines and adds the file's missing final newline, so the
entry names those too: three more touched lines, with no case added, removed or re-pinned. A changelog line
is read against the diff, and a line narrower than its diff cannot be checked against it.

## The panel test's stubbed message is the one the client produces - measured, not changed

The second minor asked whether the panel test's stubbed list-error string is the string the code produces.
It is. `apiV2.ts`'s non-ok branch falls back to `Request failed: HTTP ${response.status}` exactly when the
body is not JSON; the Go mux answers a route it does not hold with the plain text `404 page not found`; and
the browser run on the OF4 local stack rendered `Request failed: HTTP 404` in the panel's `role="alert"`.
The test keeps the string and keeps the comment recording that it is the measured message, so this minor is
recorded as verified rather than changed.

## Checks

From `agenthub-frontend`: `npx vitest run src/tests/services/apiV2.test.ts
src/tests/components/RoomDecisionPanel.test.tsx` -> exit 0, 2 files / 40 tests passed; `npx tsc --noEmit -p .`
-> exit 0, 0 `error TS` lines. Neither file changed, so the runs confirm that both pinned messages still
hold at this tip.
