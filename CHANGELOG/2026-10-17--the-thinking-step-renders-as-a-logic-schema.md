## The thinking step renders as the four-field schema it carries

The queue-row schema 3/8 ruled (`facts`, `rule`, `decision`, `next`: four fixed lines, pinned order,
per-field caps 280/110/100/78) exists so a reader finds the one thing to act on. A seat's thinking is
where that logic is formed, but the Sessions viewer showed it as one collapsed block of prose, so the
schema had to be read out of the raw text by eye.

### Added
- `agenthub-frontend/src/utils/sessionSteps.ts`: `logicSchema(text)` reads the schema from the LAST four
  lines of a thinking step - the literal keys `facts: `, `rule: `, `decision: `, `next: ` in that order,
  values of 1..cap chars each (the caps are the ruling's). Reasoning above the four lines is allowed and
  kept whole in the step's `body`; a step that mentions a key mid-prose, orders them differently, or
  exceeds a cap is not a schema step. `SessionStep.logic` carries the result on `thinking` steps only.
- `agenthub-frontend/src/components/sessions/SessionLiveView.tsx`: a thinking step carrying the fields
  renders them as a compact four-row list (`facts`, `rule`, `decision`, `next`) with the raw thinking
  collapsed beneath under the existing "Show reasoning" toggle. A step without the fields renders exactly
  as before - one component, two sources.

### Testing
- NEW `agenthub-frontend/src/tests/components/SessionLiveView.test.tsx`: one render with a schema step and
  a raw step. It asserts the four keys in the schema's order with their values, the raw thinking present
  and collapsed (`<details>` with no `open`), and that the control card shows no schema.
- `agenthub-frontend/src/tests/utils/sessionSteps.test.ts`: four `logicSchema` cases - values read with the
  reasoning kept, exactly-four-lines and trailing blanks accepted, order/completeness/prefix refusals, and
  every field's cap accepted at the limit and refused one past it.
- Red first: with the parser wired as `logic: undefined`, both new cases fail (`expected undefined to
  deeply equal {...}` and no `<dl>` in the card); restored, they pass.
- RUN: `npx vitest run src/tests/utils/sessionSteps.test.ts
  src/tests/components/SessionLiveView.test.tsx` = 2 files, 9 tests, 0 failed. `npx tsc --noEmit -p .`
  exits 0 with no `error TS`. No local vite build (the owner's 3 GB rule); the visual check on a running
  stack is not taken here, the component render is the surface this commit can prove.
- Full suite: `npx vitest run` = 126 files / 1922 tests passed, 1 failed. The failure is
  `ApiReferenceView.real.test.tsx:87`, red on main since `8e706e18` renders tool descriptions as markdown
  (the first `<pre>` in the tool article is now the description's code fence, not the parameters JSON);
  it is unrelated to this change and filed on the rail (`qitem-20261017140123-543b9c3967c2`).
