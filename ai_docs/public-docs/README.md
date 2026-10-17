# Public docs

This tree is the content of the public `/docs` site. Everything here is published to anyone, so it holds no internal notes, hostnames or credentials.

- One folder per subject: `NN-<subject>/`. The folder name, without its number, becomes the sidebar group and the URL segment (`01-quickstart` → `/docs/quickstart`).
- One file per page: `NN-<page>.md`. The number sets the order; the first `# ` heading is the page title (`02-five-minute-team.md` → `/docs/quickstart/five-minute-team`).
- Link to another page by its relative path, for example `[Jev](../03-production-performance/05-jev-decisions.md)`. Numbers are ignored when the link is resolved, so renumbering a file does not break links to it.
- Images sit next to the pages that use them and are referenced by relative path.
- `{{API_ORIGIN}}`, `{{MCP_URL}}` and `{{VERSION}}` are replaced with the deployment's values when the page renders.

The frontend reads this tree at build time (`agenthub-frontend/src/docs/docsSite.ts`); the frontend Dockerfiles copy it beside the app.
