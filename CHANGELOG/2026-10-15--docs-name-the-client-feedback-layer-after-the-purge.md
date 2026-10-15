## The docs name the feedback layer `client` and the frontend changelog records the route move

### Fixed
- `ai_docs/operations/seat-friction-loop.md` and `agenthub_go/NEXT_GEN.md`: the bulk rename had written the layer as a prose phrase; the closed vocabulary is `runtime | client | cloud | seat-context | workspace | other`.

### Added
- `agenthub-frontend/CHANGELOG.md`: entry for the `/api/v2/*` route move, the `client` layer and the 4genteam copy.

### Testing
- Docs only; `git grep` shows no remaining phrase in a layer position outside historical changelog entries.
