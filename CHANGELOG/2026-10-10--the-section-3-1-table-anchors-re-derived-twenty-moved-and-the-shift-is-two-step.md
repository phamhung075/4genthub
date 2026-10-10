## The §3.1 table's anchors re-derived at HEAD: twenty moved, all by one commit, and the shift is two-step

### Changed
- `ai_docs/api-integration/surface-inventory.md`, line references only, nothing else: **21 values on 21 lines** — the twenty §3.1 rows plus the prose anchor that names the same registry. The species every one of them must point at is the `TableDef` entry inside `var Tables = []TableDef{` in `agenthub_go/fastmcp/task_management/infrastructure/database/models.go`, matched as `"{Name: \"<table>\","` — **never the `type <Model> struct` declaration**, which sits hundreds of lines higher in the same file.

| line | row | was | is | shift |
|---|---|---|---|---|
| `:463` (prose) | the registry sentence, "`database.Tables` (base package, `models.go:589`)" | `:589` | **`:600`** | +11 |
| `:470` | `agent_sessions` | `:590` | **`:601`** | +11 |
| `:471` | `agents` | `:605` | **`:618`** | +13 |
| `:472` | `api_tokens` | `:623` | **`:636`** | +13 |
| `:473` | `context_delegations` | `:640` | **`:653`** | +13 |
| `:474` | `context_inheritance_cache` | `:669` | **`:682`** | +13 |
| `:475` | `global_contexts` | `:693` | **`:706`** | +13 |
| `:476` | `labels` | `:712` | **`:725`** | +13 |
| `:477` | `missed_notifications` | `:723` | **`:736`** | +13 |
| `:478` | `projects` | `:738` | **`:751`** | +13 |
| `:479` | `templates` | `:750` | **`:763`** | +13 |
| `:480` | `agent_session_events` | `:771` | **`:784`** | +13 |
| `:481` | `project_contexts` | `:783` | **`:796`** | +13 |
| `:482` | `project_git_branches` | `:805` | **`:818`** | +13 |
| `:483` | `branch_contexts` | `:823` | **`:836`** | +13 |
| `:484` | `tasks` | `:844` | **`:857`** | +13 |
| `:485` | `subtasks` | `:880` | **`:893`** | +13 |
| `:486` | `task_assignees` | `:914` | **`:927`** | +13 |
| `:487` | `task_contexts` | `:927` | **`:940`** | +13 |
| `:488` | `task_dependencies` | `:952` | **`:965`** | +13 |
| `:489` | `task_labels` | `:962` | **`:975`** | +13 |

- **THE SHIFT IS TWO-STEP, AND THAT IS THE PART A UNIFORM OFFSET WOULD HAVE HIDDEN.** Eleven lines landed ABOVE the registry (`:589` -> `:600`, and the first entry with it), and two more landed BETWEEN the first and second entries (`agents` `:605` -> `:618`, and everything below it) — eleven plus two, thirteen below the first row. A re-derivation that assumed one offset for the table would have written `:601` for `agents` as well and been wrong by two from the second row onward.
- **A TWENTY-FIRST VALUE OF THE SAME SPECIES WAS OUTSIDE THE INSTRUMENT'S LIST AND IS FIXED HERE.** `S3-REDERIVE.py` tracks §3's TABLE anchors, so the prose anchor on line `:463` — the sentence that names the registry itself — was not among its twenty. `grep -n "models\.go:" ai_docs/api-integration/surface-inventory.md` returns **exactly 21 lines**: the twenty rows (470–489) and that one prose line (463). Same species, same drift, same commit; leaving it would have pointed a reader at a line that has never carried `var Tables`.

### Verified
- **TWO INDEPENDENT INSTRUMENTS, THE SAME TWENTY NUMBERS.** (a) The tracked instrument's own `HEAD` column at `14210172`; (b) a hand re-derivation that greps each table's quoted name (`grep -n "\"<table>\""` -> first match) in the same file. All twenty agree exactly, and (b)'s values at the base are the doc's old values — `agent_sessions` 590, `agents` 605, `api_tokens` 623 — so the method reproduces the state the doc was written against rather than a different one.
- **THE CONTROL THAT SAYS THE METHOD FINDS REAL DRIFT RATHER THAN INVENTING IT:** the same run reports `rows=46 anchors=66 FRESH 46` — forty-six of the sixty-six anchors in §3 were already exact, and only these twenty had moved.
- **THE ANCHOR CLASS MATTERS AND WAS MEASURED THE WRONG WAY FIRST.** A first hand-check grepped `^type <Model> struct` and returned lines 70, 92, 111 … for the models this table names. Those are declarations, not registry entries, and none of them is the line the table cites. Recorded because that mistake would "fix" twenty values to lines that never carried a table entry — the same class of error as a census that resolves a different table than the one in the row.
- **THE INSTRUMENT READS `HEAD`, NOT THE WORKTREE, SO THE FIX COULD NOT BE VERIFIED BEFORE A COMMIT — AND WAS, IN A SCRATCH WORKTREE.** With the edit in the shared worktree the instrument still printed the old values; it resolves the document at `rev=HEAD`. Pre-flight in a detached worktree at the tip (`b87abca6`), carrying only this document, committed as `27b87aeb` (discarded): **`FRESH 66 STALE->BATCH 0 STALE->EARLIER 0 UNRESOLVED 0`**, *"every anchor in section 3 is fresh at rev=HEAD"*.
- **No count moved.** The §3.1 block still lists twenty rows, the `(20)` in its heading is still true, and `models.go` is 990 lines before and after — only line references were corrected.

### The rot model's own prediction, not a surprise
- **A `file:line` drifts as a function of lines INSERTED ABOVE it, and this drift is that function showing its work.** The moving commit is `14210172` (`feat(sessions): the session carries the seat it belongs to, and a stale marker stops lying`, seven files, 200 insertions, `models.go` +17), the only commit between the base and the tip that touches this file. It added the sessions columns to the registry, so eleven lines landed above the registry and two more between the first two entries.
- **§3 previously found nothing stale because nothing had been inserted under it.** The §3.3 pass of the same day found four moved values, three of them from OTHER seats' commits; this pass finds twenty from ONE, in the direction the model predicts: the deeper the anchor sits in the file, the more insertions can land above it, so a table at the top of a block can be exact while every row beneath it is stale.

### Found by
- The census suite at the tip, not by a reader: `scripts/tests/test_census_audits.py::test_the_census_instrument_is_clean_at_head_and_says_how_much_it_read[script2-anchors=(\\d+)]` failed with `rev=HEAD base=a7990665 rows=46 anchors=66 FRESH 46 STALE->BATCH 20 ... 20 anchor(s) are NOT fresh at rev=HEAD`. Reported to the lead with the cause attributed to `14210172` in queue row `qitem-20261010121443-d92d3021b09480a1`, authorized as one documentation commit by explicit pathspec.
- **Re-derivation base: `a7990665`** (the instrument's own attribution base). **Landing tip: `b87abca6`** — the parent of this commit, measured immediately before writing, which is what makes the next drift measurable as a range rather than a guess.
