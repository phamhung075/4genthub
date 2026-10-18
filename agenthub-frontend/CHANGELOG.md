# Frontend Changelog

## [Unreleased]

### Changed
- **Client routes move to `/api/v2/*` and the feedback layer is `client`** - 2026-10-15
  - Every API call, the generated `src/` route reference and the tests use `/api/v2/...` without the old client sub-prefix; the server and client change in the same release, so deploy the frontend with the backend.
  - `src/types/feedback.ts`, `src/pages/FeedbackPage.tsx` (label "Client") and its test: the layer value is `client`.
  - Page copy (`index.html`, `manifest.json`, landing, seats, connect-machine, prose) names the 4genteam client. NOT run (no local test run); `tsc --noEmit` is the check.

### Fixed
- **The ledger's context-update row names the level and version it recorded** - 2026-10-18
  - `src/lib/taskTimeline.ts` `describeEvent`: a `context_updated` row reads the payload's `{level, version}` and prints "Context updated: task context, version 7" instead of the bare kind label; an empty level keeps "Context updated". What it may NOT print is which field changed or which seat wrote: both writers send only `{level, id, version}` with `actor_id` the literal `"context"` (`agenthub_go/.../use_cases/update_context.go:83`, `.../services/unified_context_service.go:474`), so a row claiming a field or a seat would invent it. Asked in row `qitem-20261018171212-02987299f1e2` for the payload to carry the changed keys and the acting seat key.
  - `src/tests/lib/taskTimeline.test.ts`: four payload cases in one new case (task level with version, branch level with version 0, level only, empty level). `npx tsc --noEmit -p .` clean; the file's 21 tests pass.
- **The dashboard drawer's row actions work on a phone** - 2026-10-18
  - `src/components/ProjectList/components/ProjectItem.tsx` and `BranchItem.tsx`: the action cluster was `opacity-0 group-hover:opacity-100`, which no touch device can reach. It is now visible by default and fades only where hover exists (`[@media(hover:hover)]:opacity-0` plus group-hover), with `group-focus-within` so a keyboard reaches it too.
  - The same rows overflowed the 375px drawer (actions measured at right=419): the project name's container gains `min-w-0`, its badges and both icons `shrink-0`, and the branch's button `min-w-0`, so the name truncates instead of setting the row's width.
  - NOT verified in a browser yet: it needs the owner's deploy. `npx tsc --noEmit -p .` clean; the ProjectList tests (6 files, 91 tests) pass.
- **Every page fits a 375px and a 320px phone** - 2026-10-18
  - Measured on https://www.4genthub.com at iPhone SE size (375x667) and 320 wide, signed in: 7 of the 10 signed-in pages carried a fault (horizontal drag, clipped text, unreadable labels, collapsed table columns). Fixed per page:
  - `/token-management` (`src/pages/TokenManagement.tsx`): the three tab labels shrink to `text-xs` with the icons hidden below `sm`, so the active pill no longer overlaps its neighbour; each scope tile stacks its resource name above the verb chip, so a 110px tile holds "MCP Profile" and "Delegate" without crushing them.
  - `/profile` (`src/pages/Profile.tsx`): the header row wraps and the name/email truncate, so the card's minimum width no longer exceeds the phone; the tab row scrolls instead of clipping.
  - `/seats` (`src/pages/SeatsPage.tsx`, `src/components/seats/MachinesPanel.tsx`): the page header wraps, the machine table scrolls inside its card, and a seat card's long model name breaks instead of setting a 526px minimum width.
  - `/seats/authoring` (`src/pages/SeatAuthoringPage.tsx`, `src/components/seats/SeatPreview.tsx`, `src/components/seats/SeatComposer.tsx`): the 64-character snapshot hash and the pull command break, so the page stops being 592px wide inside a 375px viewport; the Level select keeps its width.
  - `/topology` (`src/components/topology/TopologyGraph.tsx`): the graph scrolls inside its card instead of being scaled to a 7px font by `max-w-full`.
  - `/sessions` (`src/components/sessions/SessionList.tsx`): the meta row wraps, so the project name is no longer squeezed to 7px.
  - `/feedback` (`src/pages/FeedbackPage.tsx`) and `/docs` (`src/pages/DocsPage.tsx`): a long unbroken word breaks instead of overflowing, and the header fits 320px.
  - NOT verified in a browser yet: the fixes exist only on the branch until the owner deploys. `npx tsc --noEmit -p .` is clean.
