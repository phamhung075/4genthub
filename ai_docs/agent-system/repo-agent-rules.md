# Repository agent rules (full detail)

> Moved out of the root `AGENTS.md` on 2026-10-05, when that file was slimmed to identity, where
> context lives, the shared hard rules and pointers. This file holds the detail behind the hard
> rules. The mapping of every moved section is in
> [`agents-md-migration-map.md`](./agents-md-migration-map.md).

## Clean code only — no compatibility, no fallbacks

Clean Code | DRY | SOLID | Single Source of Truth | Performance | Data Consistency.
Follow the prompt injection on the session-start hooks and the system prompt.

**Never add:**

- **No backward compatibility** — break cleanly, no support for old versions
- **No legacy code** — remove old code, do not preserve it
- **No fallback mechanisms** — one way only, the clean way
- **No migration helpers** — development phase, clean breaks allowed
- **No deprecation warnings** — just change it, do not warn about it
- **No version checks** — current version only, no multi-version support
- **No compatibility layers** — direct implementation only

**Why:** development phase, no production data, clean slate. Adding compatibility *is* technical
debt.

**When you see failing tests:** never add compatibility code to make them pass. Fix the code to be
clean, then update the tests to match. **Clean code > passing tests.**

## Test-fixing priority and the source of truth

### Source-of-truth hierarchy

```
1. PROMPT INPUT      (the user's explicit requirements)
   |
2. ORM MODEL         (domain entity definitions)
   |
3. DATABASE          (the actual data structure)
   |
4. TESTS             (verify behaviour, NOT define it)
   |
5. CODE              (implementation follows the above)
```

**Tests are not the source of truth.**

When a test fails: check the ORM/entity model → does the code match it? → no: fix the code to match
the model → yes: fix the test to match the model.

**ORM/entity locations (Go, the live backend):**
`agenthub_go/fastmcp/task_management/domain/entities/`. The Python path previously quoted here
(`agenthub_main/src/fastmcp/task_management/domain/entities/*.py`) is the retired backend; see
`ai_docs/api-integration/surface-inventory.md`.

### Rules

1. **The ORM model is truth** — if the model says 2000, that is the rule.
2. **Fix code first** — make the code match the model.
3. **Update tests last** — a test verifies the model's rules.
4. **No compatibility** — do not support both old and new limits.
5. **Clean break** — change directly, no transition period.

## Clean-code principles

- **Environment variables only** — no hardcoded secrets or configs.
- **Single source of truth** — one definition per concept.
- **DDD compliance** — proper domain-driven design patterns.
- **Root-cause fixes** — debug the cause, not the symptom.
- **Clean codebase** — remove legacy code immediately.

## Changelog duties

- `CHANGELOG.md` — every change that ships (Keep a Changelog format, `[Unreleased]` section).
- `TEST-CHANGELOG.md` — test-suite changes.
- A documentation change that ships gets a changelog entry too.

## Keep-out files and staging

- `.claude/` and `agenthub_go/seatcheck` never enter a commit.
- Stage by explicit path; never `git add -A`.
- The old "`CLAUDE.md` stays out of every commit" rule is **superseded**: `CLAUDE.md` was renamed
  to `AGENTS.md` (`f7a809dc`), and `AGENTS.md` is tracked. See `agenthub_go/NEXT_GEN.md`.

## Docs conventions

- Project documentation lives in `ai_docs/` (kebab-case folders, one topic per folder).
- `ai_docs/index.json` is machine-generated — never hand-edit it.
- Search existing docs before creating new ones.

## Push approval

The owner approves every push. A push to main deploys production. Never push, deploy or touch
production or another rig without the owner's explicit go-ahead.
