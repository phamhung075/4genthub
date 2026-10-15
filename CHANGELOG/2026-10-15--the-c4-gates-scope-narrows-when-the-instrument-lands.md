## The C4 gate's scope narrows when the instrument lands

### Changed

- `NEXT-GEN2.md`: two clauses under the C4 gate, both classified by fe-dev, adopted by the lead
  (rail `qitem-20261015062016-c760e7b68e78`) and re-read by the architect at the source in
  `fe-stage11.sh` rather than cited:
  - **B2's no-artifact verdict becomes NOT MEASURED, so C4 does not cover parity 2 at all.** The
    harness counts skips in their own ledger (`fe-stage11.sh:417` `PASSES=0; FAILS=0; SKIPS=0`,
    `:425` `skip(){ SKIPS=$((SKIPS+1)); … }`, its own words *"a skip is not evidence of success"*)
    and computes its exit code from `FAILS` alone (`:2397` for `--check`, `:2414` for `--all`;
    summary `:2413` *"TOTAL: … pass, … fail, … skip (a SKIP is never a pass)"*). A skipped leg can
    neither redden the run nor green the property, so a green C4 must not be read as covering
    parity 2; the existing bullet's *PARITY 2 STAYS UNPROVEN* remains that parity's standing state.
  - **Q1's route-2 baseline stays a FAIL after the instrument lands**, because the leg drives the
    product's own launch path (`fe-stage11.sh:2166-2168`: `"$FOURGENTEAM" up "$slug" --team …
    --room-only` under its own HOME, socket and state dir), so no instrument revision can
    reclassify its red. Re-measuring it is worth doing against the product half that landed after
    it, `4ada3a4` (the pane-pid start path).
