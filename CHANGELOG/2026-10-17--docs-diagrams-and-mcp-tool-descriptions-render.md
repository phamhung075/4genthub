# Docs diagrams and MCP tool descriptions render

Three faults on the `/docs` site. The `sequenceDiagram` on *The durable work queue* showed as a code block. On `/docs/api-reference`, each MCP tool's description (which the server writes in markdown) showed as a single paragraph of pipes and fences. And *Self-compaction* listed the client's built-in limits instead of the ones the team runs.

## Added

- `agenthub-frontend/src/lib/mermaidDiagrams.ts`: draws the ```` ```mermaid ```` fences of a rendered document. Mermaid is imported only when a page has a fence, so it builds as its own chunk. It uses `securityLevel: 'strict'` and follows the light/dark theme. The source `<pre>` stays in the page, hidden, so a theme change can redraw from it, and a fence that fails to parse stays visible as code.
- `agenthub-frontend/package.json`, `pnpm-lock.yaml`: `mermaid` 12.1.0.
- `agenthub-frontend/pnpm-workspace.yaml`: override `@types/d3-dispatch` to 3.0.6. Mermaid's types pull in 3.0.7, which uses TypeScript 5 syntax and does not parse under this app's TypeScript 4.9. The override affects types only.

## Fixed

- `agenthub-frontend/src/pages/DocsPage.tsx`: the article draws its diagrams after rendering, and again when the theme changes.
- `agenthub-frontend/src/components/docs/ApiReferenceView.tsx`: tool descriptions render through `Markdown`, the same sanitizer as the docs pages. A wide table scrolls inside its card.
- `agenthub-frontend/src/index.css`: `.mermaid-diagram` spacing.
- `ai_docs/public-docs/03-production-performance/02-self-compaction.md`: the limits table now shows the values this team runs: 150,000, 200,000 and 250,000. These were read from the running supervisor's `COMPACT_*_TOKENS`. The table names each variable and states the built-in defaults used when one is unset (150,000, 250,000 and 300,000). Each tier's action now matches the client: the seat is told to find a safe point; compacted without waiting for quiet; turn aborted and compaction forced.

## Tested

- `npx tsc --noEmit` is clean. `pnpm install --frozen-lockfile --offline` accepts the lockfile.
- New tests: `src/tests/lib/mermaidDiagrams.test.ts`, and the markdown-description case in `src/tests/components/ApiReferenceView.test.tsx`. Not run locally (local frontend runs are not allowed); CI runs them.
- The CSP in `Dockerfile.frontend.production` allows `style-src 'unsafe-inline'`, which mermaid's SVG `<style>` needs.
