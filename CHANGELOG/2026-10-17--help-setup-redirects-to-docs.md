## /help-setup redirects to /docs instead of the landing page

The /docs commit (`aa9d15aa`) removed the Help & Setup page and its route without a redirect, so a link that
still says `/help-setup` fell through the catch-all and opened the landing page. That path was in the header,
on the landing page and in the sitemap for months, so links to it exist outside the app (bookmarks, search
results, other sites' posts).

### Changed
- `agenthub-frontend/src/App.tsx`: `/help-setup` renders `<Navigate to="/docs" replace />`. Nothing links to
  it - `Header.tsx`, `LandingPage.tsx` and `public/sitemap.xml` name only `/docs`, as `aa9d15aa` left them.
- The reader lands inside the same layout on the docs site's first page: `DocsPage` canonicalises `/docs` to
  `/docs/quickstart/overview` with its own replace, so that is the URL after the redirect.

### Testing
- `agenthub-frontend/src/tests/App.test.tsx`, new case `sends the retired /help-setup route to the docs
  site`: it pushes `/help-setup`, the docs body opens on `Overview`, and the URL ends at
  `/docs/quickstart/overview`. Before this change the catch-all sent the path to `/`.
- RUN: `npx vitest run src/tests/App.test.tsx src/tests/docs/docsSite.test.ts
  src/tests/pages/DocsPage.test.tsx src/tests/pages/ApiDocsPage.test.tsx` = 4 files, 36 tests, 0 failed.
  `npx tsc --noEmit` exits 0. This is also the first run of the three /docs test files added at `aa9d15aa`
  (18 of the 36); the rule against local frontend runs is the 3 GB vite build, and `npx vitest run` is on
  the seat guard's allow list (the guard passed it).

### Not in this commit
- `ai_docs/index.json` is NOT regenerated. Its generator is `.claude/hooks/utils/docs_indexer.py`, from the
  hooks repository, which this checkout does not carry; and the tree holds an untracked
  `ai_docs/reports-status/` that a fresh run would index as content this commit does not carry - the defect
  `CHANGELOG/2026-10-09--the-regenerated-docs-index-lands-without-the-byte-its-own-gate-would-have-added.md`
  records. Nothing consumes the index for `/docs`: `docsSite.ts` reads the tree with `import.meta.glob`.
- The production image build, which is what proves the Dockerfile `COPY ai_docs/public-docs/`: that is the
  owner's deploy step.
