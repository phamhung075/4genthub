# The real-artefact schema test reads the schema block

CI on `main` failed in `ApiReferenceView.real.test.tsx`: the docs now render tool descriptions as markdown, and the test took the first `<pre>` of a tool article, which is a code block of the description, as the schema.

## Fixed

- `agenthub-frontend/src/tests/components/ApiReferenceView.real.test.tsx`: the test reads the last `<pre>` of the article, which is the schema that `ApiReferenceView` prints after the description. No production code changed.

## Tested

- `npx tsc --noEmit` is clean. The vitest run is left to CI (local frontend runs are not allowed).
