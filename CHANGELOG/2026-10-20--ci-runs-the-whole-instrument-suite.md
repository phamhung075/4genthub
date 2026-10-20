# CI runs the whole instrument suite

The `scripts` job added with the citation instrument ran one file:
`scripts/tests/test_doc_citations.py`. `scripts/tests/test_census_audits.py` — which runs
`COUNTS-AUDIT.py`, `S3-REDERIVE.py` and `CITATION-AUDIT.py` against the committed tree — ran in no
gate at all, and neither did any hook. That is how `2b89edfc` (main) sat four tests red: the occupant
record added a route, a registered table and a DDL statement, and nothing told anyone the inventory
no longer matched the tree.

## Change

- `.github/workflows/ci.yml`: the `scripts` job runs `python3 -m pytest scripts/tests -q`, the whole
  instrument suite, and checks out with `fetch-depth: 0` — `S3-REDERIVE.py` attributes a stale anchor
  by reading the same file at a base revision, and the census cases export HEAD with `git`, so a
  shallow checkout cannot answer.
- `python3 scripts/DOC-CITATIONS.py` stays as its own step, so a citation failure names itself even
  when another case in the suite is the first to fail.

## Verified

`python3 -m pytest scripts/tests -q` -> `130 passed`, exit 0 at `3e62c924`. The workflow file parses
(`yaml.safe_load`). The suite is the same one the census repair had to make green, so this job would
have failed at `2b89edfc` on exactly the four cases it now runs.
