# The docs architecture image shows the current runtime

The image on the `/docs` overview was the old demo picture (copied from `multiple-agent-orchestration/demo2.png`). It showed an OpenRig daemon as the local tier, "Claude 3.7", a "qitems" queue and garbled labels. The client no longer uses OpenRig.

## Changed

- `ai_docs/public-docs/01-quickstart/architecture.svg` (new): the 3-tier model redrawn from the text diagram on the same page. The tiers are: the 4genthub cloud brain; the 4genteam Go client (worktree per seat, compaction, live feeds, Jev); and agenthub-runtime (Rust) with seats in headless PTYs, `queue.sqlite` and message routing.
- `ai_docs/public-docs/01-quickstart/00-overview.md`: the image reference points to `architecture.svg`.

## Removed

- `ai_docs/public-docs/01-quickstart/architecture.png` (563 KB).

## Tested

- Rendered the SVG with Playwright Chromium and checked the result: all text fits its boxes. `docsSite.ts` already globs `*.svg`, so no code changed.
