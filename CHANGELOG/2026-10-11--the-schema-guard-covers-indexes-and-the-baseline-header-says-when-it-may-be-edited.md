# The schema guard covers indexes, and the baseline's header says when the file may be edited

Two follow-ups the reviewer raised on `a4ff5306`, both closed here. Neither is a gate finding; both are
the same kind of thing - a guard with a blind spot, and a rule that contradicted another rule.

## The blind spot: indexes were outside TestSchemaMatchesGoDefinitions

The guard compared columns, referenced tables, CHECK expressions and column defaults, and stopped there.
The registry declares its indexes in the SAME `TableDef.DDL` slice as the `CREATE TABLE` - 60 statements
in the baseline, two of them `UNIQUE` - and a unique index IS the invariant for the tables that carry
one: `uq_overlays_target` (one overlay per target per user) and `uq_team_members_one_owner` (one owner
per team) are not decoration, they are the rule. A drifted or lost unique index kept every other
comparison in that guard green.

It now compares them too: the statements are read from each side, normalized (whitespace collapsed,
letter case folded, `IF NOT EXISTS` and the trailing semicolon removed - the runtime DDL writes the
statement bare and the migration writes it re-runnable, and those are the only two differences that
exist by design), and compared as sets per table, in both directions: a statement in the baseline whose
table nobody registers is a failure too.

**Measured red, both directions, in one run:** with `UNIQUE` dropped from `uq_overlays_target` in the
baseline and `ix_email_tokens_email`'s column list drifted in the registry, the guard fails naming both
tables and printing which side says what. Reverted, it is green.

**How the first attempt failed, because the failure mode is the point.** The parses were written as one
regex - `^(?i)create (unique )?index (?:if not exists )"?([a-z0-9_]+)"? on "?([a-z_]+)"?` - and it
matched the migration's text and NOT the runtime's, whose only difference is the absent `IF NOT EXISTS`.
The runtime side therefore compared as an empty list, which is a guard reporting agreement about
statements it never read. It is replaced by a word-by-word parse of the statement's fixed shape, whose
input is collapsed first; the statement text is still what gets compared.

## The rule that contradicted another rule

The header said the file must "never be renamed, reordered or edited once it has been applied anywhere",
while the guard requires the file to EQUAL the registry. Before the owner marks a live database the two
cannot both hold. The header now says which wins and when: while no database has recorded this step in
`applied_migrations`, the file tracks the registry and a definition change edits it (safe - nothing has
executed it); once a database has recorded it, the file is frozen and the change goes into a new step.

## Verified

- `go test -count=1 -run TestSchemaMatchesGoDefinitions ./fastmcp/task_management/infrastructure/database/`
  green; the same command red under the two mutations above.
- The two mutated files are back at HEAD (`git status --porcelain` empty for them) and the guard is
  green again.
