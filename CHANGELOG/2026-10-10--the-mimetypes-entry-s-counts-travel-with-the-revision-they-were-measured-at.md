# The mimetypes entry's counts travel with the revision they were measured at

Corrects two sentences in `CHANGELOG/2026-10-10--the-mimetypes-table-marker-cited-a-generator-that-was-never-in-this-tree.md`
(commit `ddd3db26`, row `eeb62d07`, verdict `GATE-ddd3db26-mimetypes-header-2026-10-10.md`). A new entry
rather than an amend, by rule 5; the corrected entry is left exactly as it landed.

### Corrected
- **`git log --all -S mimeTypesMap` — the count travels with its moment.** The entry states the search
  returns exactly one commit. It returned one when the entry was written and returns **two** the moment
  that entry lands, because its own commit `ddd3db26` names the symbol. Measured 2026-10-10 13:00Z over all
  refs: `ddd3db26` and `6b0bdd5f` (*feat: migrate backend to Go FastMCP and update CapRover definition*, the
  Go port that added both `mimetypes.go` and `mimetypes_table.go`). The substance the count was carrying is
  unchanged — **`6b0bdd5f` is the only commit other than the correction itself that has ever touched the
  symbol** — and every entry that writes `mimeTypesMap` down joins the list, this one included.
- **`git grep -l mimetypes_table` — counted over the tree, not asserted of it.** The entry states the
  pattern matches only a CHANGELOG entry. Measured at HEAD `157f14e3`: **two** files, both changelog prose
  — the corrected entry, and `CHANGELOG/2026-10-10--the-session-carries-the-seat-it-belongs-to.md`, which
  cites the file in a list. The substance holds: **no `.go` file in the tree names `mimetypes_table`**
  (`git grep -l mimetypes_table -- '*.go'` is empty), so nothing generates it and nothing consumes it. This
  entry adds itself to that list on landing, which is why the count is stated with its revision rather than
  as a property of the tree.

### Verified
- Both searches were run in the repository root on 2026-10-10 at 13:00Z, HEAD `157f14e3`:
  `git log --all -S mimeTypesMap --oneline` printed `ddd3db26` and `6b0bdd5f`; `git grep -l mimetypes_table`
  printed the two changelog paths named above; `git grep -l mimetypes_table -- '*.go'` printed nothing.
- Nothing else changed: this file is the whole change. No code, no test, no route and no other count.

### Note
- The corrected sentences sit in the other entry's body, which is why the fix is a second entry citing the
  first instead of an edit of it. That entry's own substance — one comment line replaced by a header block,
  numstat 17/1, not one data line in the diff — is not restated here as a new claim and is unaffected.
