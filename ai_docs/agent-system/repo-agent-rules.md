# Repository agent rules (full detail)

> The detail behind the hard rules in the root `AGENTS.md`.

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

- `CHANGELOG/<date>--<title>.md` — one new file per change that ships (Keep a Changelog subsections; see `CHANGELOG/README.md`).
- `TEST-CHANGELOG.md` — test-suite changes.
- A documentation change that ships gets a changelog entry too.

## Keep-out files and staging

- `.claude/` and `agenthub_go/seatcheck` never enter a commit.
- **Commit by pathspec and do not stage first: `git commit -m "<type(scope): subject>" -- <paths>`.** A new
  file is the one exception and is marked with `git add -N -- <new>` (intent-to-add, nothing enters the index)
  before the same pathspec commit. The index is shared with every other seat working in this worktree, so a
  staged line can be taken by another seat's commit. Just before committing, read
  `git status --porcelain -- <paths>` and `git diff HEAD -- <paths>` and name every line; if a line is not
  yours, do not commit that file — commit your other paths and hold it until its owner has committed.
  Never `git add .`, `-A` or `--amend`. **Expect the hooks to rewrite a path you named:** the config's
  `trailing-whitespace` and `end-of-file-fixer` run on a commit's own files and re-add their fix, so read
  `git show --numstat --format=` after committing to learn what the commit actually carries — `7b198a15`
  gained nine whitespace-only lines in `agenthub_main/src/tests/README.md` that way.
- **A removal is attributed by the COMMIT that carries it, never by the staging area.** `git status` and
  `git diff` answer *what* changed and never *who* changed it — an uncommitted deletion has no author to
  find, because `git log -S` and `git blame` see nothing until it is committed — and the index records no
  seat. Read the author per path with `git show --numstat --format= <sha> -- <path>`. So a commit that
  names a path takes **every** line in it under its own message, and a sibling's line can ride a commit it
  is not part of: `0565da9f` is titled as a frontend fix and carried a staged `TEST-CHANGELOG.md` entry,
  17/0, taken from the shared tree (`agenthub_go/NEXT_GEN.md:703`).
- **If the pre-commit framework refuses a pathspec commit with "Your pre-commit configuration is
  unstaged,"** the config file differs from **the index that commit builds** — not from the shared index —
  and the guard's predicate is `git diff --quiet --no-ext-diff scripts/git-hooks/pre-commit-config.yaml`
  (pre-commit 4.4.0, `pre_commit/commands/run.py:339-345`). **The remedy, in order, and the order is the
  point:**
  1. **If the config is yours to commit, commit it by itself, by explicit pathspec.** Naming it puts that
     file's worktree content into the commit's temporary index, so the predicate is clean, the guard passes
     by itself, and **the whole hook chain runs** — measured 2026-10-08: `6ded99e2`, config alone, every hook
     ran and passed, no `--no-verify`. **Staging it in the shared index is what does not work**, because the
     temporary index then holds the config at HEAD: committing it is not a workaround, it is the fix.
  2. **If it is not yours, ask its owner to commit it alone first** — that is what unblocked this queue.
  3. **`--no-verify` is the last resort**, for a config that cannot be the committed path: run the config's
     own hooks over **your own** paths (`pre-commit run --config <config> --files <your paths>`; passing
     `--files` or `--all-files` is also what skips the guard, `run.py:347`), report the exit code, and name
     in the body exactly what the flag then skipped. The same flag with no hooks run is a defect.
  **Expect the run to stash what is not being committed:** on the same condition (`run.py:347`), a commit
  that is not given `--files` or `--all-files` makes the framework stash **every** unstaged file to a patch
  and restore it afterwards — so a sibling seat's uncommitted work exists as a patch file in the working tree
  for the length of your commit, and a crash between the stash and the restore leaves it there, in a file its
  author never made (measured on `da07c9db`, whose output read `Stashing unstaged files` … `Restored changes`;
  it restored cleanly, and this tree has already lost a fleet to a tmux death once). The hazard is the window,
  not the mechanism: prefer `--files <your paths>` when the tree is crowded.
- **A changelog entry is one new file, so it cannot carry a peer's entry.** The changelog is the `CHANGELOG/`
  directory: one file `CHANGELOG/<date>--<title>.md` per change, added with `git add -N` and committed by
  pathspec with the change it describes. Do not read the whole directory; `ls CHANGELOG | tail` lists the newest.
  The old single `CHANGELOG.md` took the WHOLE file under `git commit -- CHANGELOG.md` and carried every peer's
  uncommitted entry (measured 2026-10-08, `0ea06c77`); that hazard now applies only to the other shared files
  (the backlog, the guides): before naming one, check it is clear of other seats' lines, sequence with that
  seat, or **name what you carry** in the message, and check the commit with `git show <sha> -- <path>`
  for removals, the entries you carry and the headings added.
- **The earlier rule here — "stage by explicit path; never `git add -A`" — is RETIRED rather than restated:**
  the pre-stage form is the one that puts a line into the shared index, which is the window the fleet's
  commit form was changed to close. See `ai_docs/core-architecture/agenthub-system-architecture.md D8`
  (`b059b863`, 2026-10-08).
- The old "`CLAUDE.md` stays out of every commit" rule is **superseded**: `CLAUDE.md` was renamed
  to `AGENTS.md` (`f7a809dc`), and `AGENTS.md` is tracked. See `agenthub_go/NEXT_GEN.md`.

## Docs conventions

- Project documentation lives in `ai_docs/` (kebab-case folders, one topic per folder).
- `ai_docs/index.json` is machine-generated — never hand-edit it.
- Search existing docs before creating new ones.

## Push approval

The owner approves every push. A push to main deploys production. Never push, deploy or touch
production or another rig without the owner's explicit go-ahead.
