## The assembled tip's section 3.1 anchors are re-derived, and the architect's 12/76 texts are applied

### Fixed
`ai_docs/api-integration/surface-inventory.md` section 3.1 — **all nineteen `models.go` declaration
anchors were stale at the assembled tip `e42160c2`**, and each row now cites the instrument's own HEAD
value at that tip.

The oracle is `scripts/S3-REDERIVE.py`, which is read-only by design. At the assembled tip it said
`rev=HEAD base=0e9746c0 rows=45 anchors=65` with **`FRESH 46  STALE->BATCH 19  STALE->EARLIER 0
UNRESOLVED 0`**, naming every one of the nineteen as a `def` anchor into
`agenthub_go/fastmcp/task_management/infrastructure/database/models.go`. Its baseline was zero not-fresh
before this work, so its own three cases in `scripts/tests/test_census_audits.py` went red:
`test_the_census_instrument_is_clean_at_head_and_says_how_much_it_read[script2]`,
`test_the_census_instrument_can_fail[script2]` (its `--self-test` cannot isolate a one-anchor perturbation
against a nineteen-anchor baseline) and
`test_s3_rederive_says_its_base_is_missing_instead_of_passing_quietly`.

**The cause is the fold, measured rather than inferred.** `git diff --numstat 66fee74d^ 66fee74d --
…/models.go` deletes 8 lines above these declarations (0 added / 8 deleted), so the anchors shifted by
**4 lines for the sixteen rows from `agent_sessions` to `tasks`, 6 for `subtasks`, and 8 for the four from
`task_assignees` to `task_labels`**. Neither the take, the cherry-pick of the 12/76 withdrawal, the
`4genthub-min/go-dev` branch merge nor the docs commit touches `models.go` or any cited document: the docs
commit's six files are `CHANGELOG/`, `TEST-CHANGELOG.md` and the migrations `README.md`, and the branch's
eight are `NEXT_GEN.md`, the seat-pin test, `rigd-boundaries.md` and their entries.

**The mapping applied, cited -> new** (`git rev-parse`-independent, read off the instrument's own columns):
`agent_sessions` 596->592, `api_tokens` 615->611, `context_delegations` 632->628,
`context_inheritance_cache` 661->657, `global_contexts` 685->681, `labels` 704->700,
`missed_notifications` 715->711, `projects` 730->726, `templates` 742->738,
`agent_session_events` 763->759, `project_contexts` 775->771, `project_git_branchs` 797->793,
`branch_contexts` 815->811, `tasks` 836->832, `subtasks` 874->868, `task_assignees` 910->902,
`task_contexts` 923->915, `task_dependencies` 948->940, `task_labels` 958->950.

The record paragraph below the table is stamped with this third re-derivation rather than rewritten: it is
the measurement of the previous two.

### Changed
The same commit applies the architect's ARCH RULING texts (1a-1d and the guard README sentence) that were
landed as `e42160c2`: the take keeps its `12 failed / 76 passed` figure and **every site is stamped with the
revision it belongs to** — the figure is the SEALED revision `708e3131`'s own clean-tree result, and this
batch's own `7c358c4b` and `5150f16d` are what fixed the twelve before `e0e75084^` — while the withdrawal's
two explanation sentences are rewritten so the difference is a revision, not a damaged environment. The
merged migrations `README.md`, taken verbatim from the fold, now names **both** guards now that the tree
carries both.

### Verified
- `env -u GIT_DIR python3 -m pytest --noconftest -p no:cacheprovider scripts/tests -q` at the tip after the
  re-derivation: see the handoff for the exact line; acceptance is the suite going green.
- `python3 scripts/S3-REDERIVE.py HEAD 0e9746c0` is the oracle for every number above and reports
  `STALE->BATCH 0` once the rows cite the HEAD column.
- Docs only: no `.go`, no `.sql`, no test file changed, so no Go build or gate is required for this entry.
