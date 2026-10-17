# The sitemap route check accepts a splat route

CI on `main` failed on `LandingPage.head.test.tsx` ("lists only routes that exist in the app"): the sitemap lists `/docs`, which `App.tsx` serves through `path="/docs/*"`, and the test only matched an exact `path="/docs"`.

## Fixed

- `agenthub-frontend/src/tests/pages/LandingPage.head.test.tsx`: a sitemap path counts as served when the app has its exact route or its `/*` route. No production code changed.

## Tested

- `npx tsc --noEmit` is clean. The vitest run is left to CI (local frontend runs are not allowed).
