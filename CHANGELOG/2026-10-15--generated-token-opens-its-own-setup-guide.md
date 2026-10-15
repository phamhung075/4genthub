## 2026-10-15 - a generated token opens its own setup guide

### Added
- `agenthub-frontend/src/components/tokens/ClientTokenGuides.tsx`: one guide per token kind (Client connector, Client MCP).
- `agenthub-frontend/src/pages/TokenManagement.tsx`: the popup after Generate matches the token kind.

### Changed
- `agenthub-frontend/src/components/help/sections/ConnectMachine.tsx` (https://www.4genthub.com/help-setup): teaches both tokens and `4genteam up`.

### Fixed
- The generated-token popup showed empty scopes because it read the form after it was reset.

### Testing
- `tsc --noEmit` clean; the two page tests are updated and were not run locally.
