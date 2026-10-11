## Pin citations name the live pin again — `9666de68` → `80cc766`

### Changed
- `README.md` and `agenthub_go/NEXT_GEN.md` — **four clauses** said "at the pinned client commit `9666de68`". The pin
  moved to **`80cc766`** when the six client commits were pushed, so "pinned" was false of that hash. Each clause now
  names the live pin and maps the earlier one, and the two reproducible `ls-tree` commands point at `80cc766`.

### Verified
- The claims hold **at both hashes**, re-read rather than relayed: `git -C agenthub_client ls-tree -r --name-only
  <hash>` yields no `.py` and no `pyproject.toml`, and `src/agenthub_client/` — the subtree the corrected clauses
  retired — is gone at `80cc766`.
- `agenthub_go/NEXT_GEN.md:449` already named the live pin; that is what exposed the inconsistency.
