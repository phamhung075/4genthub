## 2026-10-15 - a long token wraps in the setup command box

### Fixed
- `agenthub-frontend/src/components/help/shared/CommandBox.tsx`: the `AGENTHUB_CONNECTOR_TOKEN=...` and `AGENTHUB_TOKEN=...` lines in the token popups broke out of the box. The text now wraps at the box edge; Copy still copies one line.

### Testing
- `tsc --noEmit` clean; no test covers layout.
