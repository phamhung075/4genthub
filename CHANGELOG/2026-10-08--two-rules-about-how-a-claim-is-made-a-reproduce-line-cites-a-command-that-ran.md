## Two rules about how a claim is made: a reproduce line cites a command that ran here, and a citation says which part of its sentence it supports

### Added
- `agenthub_go/NEXT_GEN.md` process lessons 62 and 63, from the writer's two findings. Rule 62: a reproduce line cites a command that was run in this environment. The environment is per seat: `rg` has no binary on PATH, but in the claude-code seat's shell it is a function that runs the harness's embedded copy, while a plain login shell does not find it. Rule 63: a citation can resolve and still support only half its sentence, as `PROD_READINESS_REPORT.md:179` → `MIGRATION.md:951` shows. The instance where it was applied is `782302f1`.
