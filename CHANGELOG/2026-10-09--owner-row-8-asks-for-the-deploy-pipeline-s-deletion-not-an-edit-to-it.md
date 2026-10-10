## Owner row 8 asks for the deploy pipeline's deletion, not an edit to it

### Changed
- `ai_docs/core-architecture/agenthub-system-architecture.md`, section 6 row 8: the question becomes "approve DELETING the production-deployment workflow and the four scripts only it calls". 50 of 50 runs failed (2025-11-22 to 2026-10-08), build and deploy never ran, and the Security Scan, the only Trivy gate, goes with it. Recommendation: yes.
- D2 stage 3: the `test_coverage.yml` instruction stays; the `skip-dirs` edit to `production-deployment.yml` is struck with a dated note. The deletion is prepared in `48c0bf71`, which is not on `main`, and lands only with the owner's answer to row 8.
