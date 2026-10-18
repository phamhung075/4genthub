## The public-docs README states the tree is the only source and nothing syncs

### Added

- `ai_docs/public-docs/README.md` — a section saying this tree is the only source of the `/docs`
  content: `../multiple-agent-orchestration/docs` (github.com/phamhung075/multiple-agent-orchestration)
  publishes the same subjects and is a separate tree, not a mirror, so no tool copies this tree there
  and nothing flows back. A page that belongs on both is written here first and copied there by hand.

### Measured

The two trees compared on 2026-10-18: twelve page paths are shared and every one differs; this tree
carries four pages the other lacks (`00-overview.md`, `04-connect-your-machine.md`,
`01-new-project-recipe.md`, `02-troubleshooting-catalog.md`) plus `01-quickstart/architecture.svg`;
the other tree's two reference pages (`new-project-recipe.md`, `troubleshooting-catalog.md`) are its
only unnumbered files. The draft's "the architecture images it does not" and "its files are not
numbered" were corrected to these.

### Testing

- `agenthub-frontend/src/docs/docsSite.ts` globs `../../../ai_docs/public-docs/*/*.md` at build time,
  and both frontend Dockerfiles copy `ai_docs/public-docs/` to `/ai_docs/public-docs/` beside the
  app (`Dockerfile.frontend.dev:87`, `Dockerfile.frontend.production:37`) — so the markdown here is
  what `/docs` renders, with no copy step from another tree.
- `ai_docs/index.json` is untracked and deleted in `c2bf3b23` (2026-10-17); no frontend source
  references it.
