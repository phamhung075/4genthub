# The index guard folds case only outside the literal, and reads whole statements

The reviewer's re-gate MINOR on the index comparison added in `a4ff5306`: the normalization lower-cased
the WHOLE statement, a single-quoted literal included, so the baseline's `uq_team_members_one_owner ...
WHERE role = 'owner'` and a case-only change to `WHERE role = 'Owner'` normalized to the same text and
the guard stayed green. Measured by the reviewer; reproduced here before the fix.

Two defects, one root: the normalization treated layout as the only difference, and the migration side
was parsed **line by line**.

- **Case is folded outside literals only.** `goDefNormalizeStatement` now folds through
  `goDefFoldOutsideLiterals`: SQL's words are case-insensitive layout, a string literal's case is its
  value. For a partial index that literal IS the invariant's scope, so two indexes that filter on
  different values are different indexes. An unterminated literal leaves the remainder as written.
- **A statement is read whole.** `goDefStepIndexes` iterated `strings.Split(step.SQL, "\n")` and read
  each line, so a `CREATE INDEX` split across two lines was compared as a truncated first line - a
  statement that could not be read whole was silently compared as a fragment. It now iterates
  `goDefStatements(step.SQL)`, the same whole-statement unit the runtime side is parsed in. The
  scanner respects single-quoted literals, parentheses and `--` line comments, so neither a semicolon
  inside a literal nor one inside a column list ends a statement; a final statement without a trailing
  semicolon is kept, and anything that still looks like an index but cannot be parsed remains a
  FAILURE (`goDefParseError`), never a skip.
- **Comments are dropped, not scanned.** The migration's prose carries apostrophes ("registry's"), and
  a comment whose text reached the scanner as SQL would open a bogus literal and swallow every
  statement after it. The file's own header comment does exactly that, which is how that behaviour was
  found.

## Verified

- `go test -count=1 -run TestSchemaMatchesGoDefinitions ./fastmcp/task_management/infrastructure/database/`
  green; `gofmt -l` clean.
- MEASURED RED, re-run here: with the baseline's partial index changed to `WHERE role = 'Owner'` the
  guard fails naming `uq_team_members_one_owner` and printing both sides - `migrations: ... where role =
  'Owner'` against `runtime: ... where role = 'owner'`. Reverted, green.
- MEASURED: with `ix_modules_user_id` split across two lines (the statement still whole) the guard
  stays green, because the statement is compared, not its first line.
