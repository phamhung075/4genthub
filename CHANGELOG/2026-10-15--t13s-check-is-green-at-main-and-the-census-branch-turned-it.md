# T13's check is green at main, and the commits that turned it are the census branch's

**What this adds.** One measured bullet under T13 on the board, beside the red one already there:
the check is **green at main `acf916c8`**, and the commits that made it green are named with it.

**The measurement.** At `acf916c8`, in a clean detached export (`git worktree add --detach`):

- `CI= python3 scripts/CITATION-AUDIT.py` → **rows 148, stale 0, unresolved 0, exit 0**
- `python3 -m pytest scripts/tests -q` → **91 passed**, 3 warnings
- `cd agenthub_go && go test ./...` → **rc 0**, measured at `658ba0fd` (26 s): `658ba0fd..acf916c8`
  carries no `.go` byte — `48d0cfdd` touches two files, `acf916c8` two docs files

**What turned it.** The red at `80e51824` was **seven stale rows** in
`agenthub_go/fastmcp/server/httpapp/app.go`, and **`7360008e`** repointed them at the source rather
than incrementing them. **`b114d0ae`** repointed the same file's four prose citations and the setup
guide's copies of them; **`48d0cfdd`** corrected the 2026-10-13 note's attribution. The instrument
measures the first of the three and **neither of the other two** — it reads the table's rows, not
the sentences beside them.

**Not in this change.** No instrument, no code, no citation: `NEXT-GEN2.md` plus this entry. The
prose class stays open, and the item that states it is the next commit on this lane.
