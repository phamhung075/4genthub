## The served census reads a dotted chunk name whole

### Fixed

- `scripts/check_served_frontend.py`: the closure's two ref patterns now start on a boundary
  (`(?<![\\w.-])`) and the hashed-name stem carries dots, so `mermaid.core-CGIcD27U.js` is one name
  instead of the tail `core-CGIcD27U.js`. Measured 2026-10-18 at https://www.4genthub.com on build
  2026-10-18 23:33:27Z: the census closed INCOMPLETE (exit 2) with every assertion passing, because
  its closure had fetched `/assets/core-CGIcD27U.js` and `/assets/esm-CkK8FqzY.js`, neither of which
  the build ever had; the served names are `/assets/mermaid.core-CGIcD27U.js` and
  `/assets/cytoscape.esm-CkK8FqzY.js`, both 200. A fresh deploy could not be certified OK by the one
  instrument built for that claim.

### Testing

- `python3 -m pytest scripts/tests/test_check_served_frontend.py -q` -> 15 passed. New: a dotted-stem
  sibling discovered whole and carried through the closure to an OK verdict, and `assets/` inside a
  longer word not treated as a ref. `python3 scripts/check_served_frontend.py --json` against
  production -> `OK`, 153 assets / 6,861,354 bytes, 0 fetch failures, entry `index-C9y0WCTp.js`,
  verbs 1/1/1, deleted names 0.
- The 3 failures in `scripts/tests/test_census_audits.py` (`S3-REDERIVE.py`) predate this change;
  re-run with it stashed, the same 3 fail.

### Impact

- Read-only instrument, no production code touched. The verdict now reflects the served surface
  rather than the census's own ref extraction.
