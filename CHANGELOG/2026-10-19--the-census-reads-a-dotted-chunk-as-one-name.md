# The census reads a dotted chunk as one name

## Changed

- `scripts/check_served_frontend.py`: `HASHED_REF` keeps an asset name carrying a vite plugin
  prefix (`./mermaid.core-PVSKwLbE.js`) as ONE reference. It gains `(?:[A-Za-z0-9_-]+\.)*` for the
  dotted prefix and a `(?<![A-Za-z0-9_.-])` left boundary. Without the boundary the match began after
  the dot - `core-PVSKwLbE.js` - so the closure fetched `/assets/core-PVSKwLbE.js` (404) and reported
  INCOMPLETE on a clean surface. `ASSET_REF`, `census`, and `walk_closure` are unchanged.

## Tested

- `scripts/tests/test_check_served_frontend.py::test_a_dotted_chunk_name_is_one_ref_not_a_phantom`
  (new): RED before the fix (`discover_refs` returned the phantom `core-PVSKwLbE.js`), green after -
  the served dotted asset is walked to its real path and the verdict is OK with no fetch failure.
- `cd scripts && python3 -m pytest tests/test_check_served_frontend.py -q` -> 14 passed.
- Live census at 19:12Z: `verdict OK`, `fetch_failures []`, 153 assets, 6864632 bytes against
  `https://www.4genthub.com`.
