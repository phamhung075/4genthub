## The /docs site replaces /help-setup and renders ai_docs/public-docs

`/help-setup` was a hand-built React page (2,491 lines in `components/help`) that still taught the Python client, the hooks submodule and the Docker menu. `/docs` showed only the API reference. `/docs` is now a docs site in the style of platform.claude.com/docs: subject groups in a left sidebar, the page in the middle, "On this page" on the right, and previous and next links at the bottom. Its content is Markdown in `ai_docs/public-docs`, so a docs change is a Markdown edit with no frontend code.

### Added
- `ai_docs/public-docs/`: one folder per subject (`01-quickstart`, `02-architecture-and-mental-model`, `03-production-performance`, `04-reference-and-playbooks`) and one numbered file per page, seeded from `multiple-agent-orchestration/docs` at `43f026c`. Each copy loses only its `Next:` footer and the number in its title, because the site renders both itself. `00-overview.md` is that repo's README without the docs map, which the sidebar replaces. `04-connect-your-machine.md` is the one current section of the old help page (two tokens, `.env`, `up`, `heal --check`, `sync connector`). `README.md` holds the layout contract. Everything in the tree is published publicly.
- `agenthub-frontend/src/docs/docsSite.ts`: reads the tree at build time with `import.meta.glob`, groups the pages into sections ordered by their numbers, and resolves relative `.md` links and images by slug, so renumbering a file does not break a link to it.
- `agenthub-frontend/src/pages/DocsPage.tsx`: the site at `/docs/*`. `/docs` opens the first page, and `/docs/api-reference` renders the existing API reference, lazy-loaded, inside the same layout. An unknown path shows "Page not found" with the sidebar still visible.
- `src/lib/headingToc.ts` (`slugifyHeading`, `collectHeadings`) and `src/lib/docTokens.ts` (`applyTokens`, `useDocTokenValues`): moved out of `ApiDocsPage.tsx` so both pages share them. `src/lib/markdownHtml.ts` adds `rewriteUrls`, and `Markdown` takes an optional `rewriteUrl`. The rewrite happens after sanitizing, inside an inert `<template>`.

### Changed
- `docker-system/docker/Dockerfile.frontend.production` and `.dev` copy `ai_docs/public-docs/` to `/ai_docs/public-docs/`, one level above the app's workdir. The relative glob therefore resolves in both the image and a checkout. `vite.config.ts` adds the tree to `server.fs.allow` for the dev server.
- `Header.tsx`: the Help & Setup link is gone, and the remaining `/docs` link is titled Docs. `LandingPage.tsx`: all six `/help-setup` links point to `/docs`. `public/sitemap.xml` drops `/help-setup`. `App.tsx`: `/help-setup` is removed (the catch-all sends it to `/`) and `/docs/*` renders `DocsPage`.
- `CommandBox.tsx` moves from `components/help/shared` to `components/tokens`, next to its only remaining user, `ClientTokenGuides.tsx`.

### Removed
- `src/pages/HelpSetup.tsx`, `src/components/help/**` and `src/tests/pages/HelpSetup.test.tsx`.

### Testing
- `npx tsc --noEmit` is clean. The new tests (`src/tests/docs/docsSite.test.ts`, `src/tests/pages/DocsPage.test.tsx`) and the edited `ApiDocsPage.test.tsx` were not run, because local frontend test and build runs are not allowed. A scratch tsconfig over those three files reported no errors in them; the only errors were the missing node and jest-dom ambient types. No image was built, so the Dockerfile `COPY` is untested until the deploy builds it.
- `ai_docs/index.json` was not regenerated, because `.claude/hooks/utils/docs_indexer.py` is not present in this checkout.
