## Trivy CRITICAL/HIGH: both lockfiles upgraded, and the one finding upgrading cannot fix

- The Production Deployment Pipeline's Trivy step (`severity: CRITICAL,HIGH`, `exit-code: 1`)
  scans the FILESYSTEM (`scan-type: fs`), and NEITHER workflow runs pnpm - so the LOCKFILES are
  the artefact that must change, and every change below is visible in them rather than only in a
  manifest.
- UPGRADED, each the minimum that clears its finding: react-router 7.9.1 -> 7.18.4 (frontend; the
  RCE plus six other React Router advisories, and a MINOR within v7 rather than the major the
  brief anticipated), js-cookie 3.0.5 -> 3.0.8 (CVE-2026-46625), immutable 5.1.3/5.1.4 -> 5.1.9
  (prototype pollution and a List trie-overflow DoS), picomatch 2.3.1 -> 2.3.2 and 4.0.3 -> 4.0.4
  (ReDoS, both majors), source-map-js 1.2.1 -> 1.2.2 (path traversal).
- `braces@3.0.3` IS GONE FROM THE ROOT LOCK, and it could not have been fixed by pinning braces:
  no released version is outside its advisory. The chain was sass -> @parcel/watcher@2.5.1 ->
  micromatch -> braces, and @parcel/watcher 2.6.0 REPLACED micromatch with picomatch, so
  overriding that one package shed braces without touching braces at all.
- `braces@3.0.3` REMAINS IN THE FRONTEND LOCK AND IS NOT FIXABLE BY UPGRADING IN RANGE: its only
  consumer there is `tailwindcss@3.4.17` -> `micromatch@4.0.8` (already the latest), so clearing it
  means a tailwindcss MAJOR, which is a migration rather than a bump. Reported as the blocking
  finding rather than worked around, and `.trivyignore` is deliberately untouched: this repository
  fixes findings by upgrading.
- The overrides live in each package.json's `pnpm.overrides`, which is the home that MEASURABLY
  takes effect: an identical block added to `agenthub-frontend/pnpm-workspace.yaml` was INERT (the
  lock recorded the package.json set and not that one), so it was removed rather than left as a
  second voice - the same rule this week applied to the docs page's two copies of one surface.
- Verified: `npx tsc --noEmit -p .` exit 0 with 0 errors; `npx vitest run` 105 files / 1795 tests
  passed; `npx vite build` green. Both lockfiles keep `lockfileVersion: '9.0'` - the upgrades ran
  with pnpm 9 at the root and pnpm 10 in the frontend, the versions that write that format and
  that read that workspace file respectively.
