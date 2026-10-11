## Unreleased — ai_docs cut from 57 files to 21

### Removed
- `ai_docs/_workplace/`, `ai_docs/claude-code/`, `ai_docs/reports-status/`: dated scratch, retired-model records and two dated reports.
- The three `cleanup-analysis-*` pages, `token-optimization-complete-summary-2025-11-03.md`, `mcp-crud-all-layers-report.md`, `mcp_test_issues.md`, `testing-qa/mcp-comprehensive-test-report-2025-11-29.md`: analyses and generated reports of the retired Python tree.
- Vendor reference copies: the four `anthropic_*.md`, `openai_quick_start.md`, `cc_hooks_docs.md`, `user_prompt_submit_hook.md`, `uv-single-file-scripts.md`; their five `Read` lines in `.gemini/commands/prime.toml` and `prime_tts.toml` go with them.
- Python-era guides the architecture doc and the surface inventory supersede: `development-guides/{ddd-architecture,development-workflow,development-infrastructure}-complete.md`, `ui-patterns/toast-notification-architecture.md`, `testing-qa/{qa-strategy-planning,contract-integration,mcp-tools-validation}-complete.md`, `testing-qa/e2e/End_to_End_Testing_Guidelines.md` (an unfilled template), `api-behavior/api-parameter-handling-complete.md`, `agent-system/agents-md-migration-map.md`; the pointers to the last two in `AGENTS.md`, `ai_docs/agent-system/*.md` and `ai_docs/api-integration/surface-inventory.md` are reworded.

### Added
- `ai_docs/development-guides/development.md`: one page of the commands that run the project and where each kind of fact lives.

### Changed
- `ai_docs/index.json` regenerated (20 indexed files).
- Validated: `go test ./...`, `scripts/tests` (49 passed) and the client suite.
- Not changed: `operations/complete-operations-guide.md`, `setup-guides/`, `troubleshooting-guides/` and `authentication/` still carry dated "struck" and "earlier revisions" notes; rewriting them needs the real production deploy path, which no file in the tree states.
