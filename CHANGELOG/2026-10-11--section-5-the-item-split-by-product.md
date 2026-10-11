## Section 5 splits the dev-team client features by product, with the open decisions named

### Added
- `ai_docs/operations/client-features-for-the-dev-team.md` section 5: where each of section 4's items 1-6 and the deferred set lands across 4genthub (server and frontend), 4genteam (the CLI and rigd), and 4gent-client (the `agenthub_client` library), plus the four open decisions - the base branch per room, "owner outranks lead on priorities only", the rigd loop, and whether 4genteam and 4gent-client are one repository (measured: they are one).

### Changed
- Section 5 records that `4genteam` and `4gent-client` are two surfaces of the single client repository `agenthub_client` (`4genthub-client`), not two products.

### Impact
- Documentation only. No code changed. This is the plan for step 2; the lead turns it into one board task per item.
