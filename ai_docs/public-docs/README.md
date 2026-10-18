# Public docs

This tree is the content of the public `/docs` site. Everything here is published to anyone, so it holds no internal notes, hostnames or credentials.

- One folder per subject: `NN-<subject>/`. The folder name, without its number, becomes the sidebar group and the URL segment (`01-quickstart` → `/docs/quickstart`).
- One file per page: `NN-<page>.md`. The number sets the order; the first `# ` heading is the page title (`02-five-minute-team.md` → `/docs/quickstart/five-minute-team`).
- Link to another page by its relative path, for example `[Jev](../03-production-performance/05-jev-decisions.md)`. Numbers are ignored when the link is resolved, so renumbering a file does not break links to it.
- Images sit next to the pages that use them and are referenced by relative path.
- `{{API_ORIGIN}}`, `{{MCP_URL}}` and `{{VERSION}}` are replaced with the deployment's values when the page renders.

The frontend reads this tree at build time (`agenthub-frontend/src/docs/docsSite.ts`); the frontend Dockerfiles copy it beside the app.

## This tree is the only source; nothing syncs

`../multiple-agent-orchestration/docs` (github.com/phamhung075/multiple-agent-orchestration) publishes the same subjects, and it is a separate tree, not a mirror. Measured 2026-10-18: every one of the twelve shared pages differs, this tree carries four pages and `01-quickstart/architecture.svg` it does not, and its two reference pages are the only ones without numbers. So a change made there does not reach the `/docs` site, and no tool copies this tree there.

The rule: a page that belongs on both is written here first and copied there by hand. Nothing flows back, and a diff between the two trees is not a defect.

The internal docs tree keeps its own index as its tracked files (`git ls-files 'ai_docs/**/*.md'`); the generated `ai_docs/index.json` was retired on 2026-10-17, and nothing ever read it for `/docs`.
