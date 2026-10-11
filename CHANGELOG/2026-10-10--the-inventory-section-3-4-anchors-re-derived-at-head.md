## The inventory's §3.4 anchors re-derived at HEAD — six rows, one uniform shift

Writer seat, 2026-10-10. Found by running the section-3 instrument rather than by reading the document:
`python3 scripts/S3-REDERIVE.py HEAD` reported **`FRESH 60  STALE->BATCH 6  STALE->EARLIER 0  UNRESOLVED 0`** and exited non-zero.

### Changed
- Six `Declaration` anchors in `ai_docs/api-integration/surface-inventory.md` §3.4 (`ProductionTables`), each a `models_prod.go:NN` pointer, moved to where the TableDef entry actually is at HEAD:

| table | was | is |
|---|---|---|
| `agent_import_history` | `:97` | `:105` |
| `applied_migrations` | `:118` | `:126` |
| `token_transactions` | `:135` | `:143` |
| `user_agent_configurations_md` | `:162` | `:170` |
| `user_api_tokens` | `:182` | `:190` |
| `user_sessions` | `:217` | `:225` |

**All six moved by exactly +8, and that is the finding rather than a coincidence:** one insertion above them in `agenthub_go/fastmcp/task_management/infrastructure/database/models_prod.go` moved every following entry. The instrument classifies them `STALE->BATCH` — stale between its base `a7990665` and HEAD — so the batch moved them, not an earlier commit, and not this seat. 66 anchors are read across §3.1-§3.4; the other 60 were fresh.

### Verified
- `python3 scripts/S3-REDERIVE.py HEAD` -> **`FRESH 66  STALE->BATCH 0  STALE->EARLIER 0  UNRESOLVED 0`**, exit 0.
- `python3 scripts/COUNTS-AUDIT.py` -> exit 0, and `python3 scripts/CITATION-AUDIT.py` -> `rows 145  stale 0  unresolved 0`: this edit touches no count and no §1 citation.
- `python3 -m pytest scripts/tests -q` -> the `[script2-anchors]` failure is gone.

### Not fixed here, named instead
`test_s3_rederive_says_its_base_is_missing_instead_of_passing_quietly` still fails, and it is a behaviour gap in `scripts/S3-REDERIVE.py` rather than a document defect: handed a rev it cannot read, the instrument does not say so in the form the test requires. It is a separate change to the instrument and is reported rather than bundled here.
