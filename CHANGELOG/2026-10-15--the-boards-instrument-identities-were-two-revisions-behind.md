# The board's instrument identities were two revisions behind, and the launcher's sha was never right

**What this changes.** Four places in `NEXT-GEN2.md` named the C4 instrument, the run tree's binaries,
or the launcher as something they no longer are: §3's provenance bullet (line 94), the
live-harness-by-content bullet (line 95), the `u3bin` bullet in the sequence block (line 329), and
the instrument-ledger bullet (line 330). Each is corrected in place, dated, keeping the measurement
that was true when taken and naming what stands now. The ledger bullet gains the revision table the
board never carried.

**Why it is not cosmetic.** These four lines are the identities a C4 run is started against. The
`u3bin` bullet said the pair on disk measured the **pre-fix** runtime — "this is the one thing that
would make a run lie" — and the rebuild it was waiting on has happened. The ledger bullet named the
live harness `5b2e15b3`, which has not been live since the stage11 install, and named the launcher
`6253f9cb`, which is not the launcher's hash now or ever measured here. A reader who takes the shas
off this board would name the wrong instrument in the run's own record.

**Measured 2026-10-15 18:1xZ at the source, every identity re-read rather than relayed** (the lead's
row `qitem-20261015180417-26431f08cb88` carried the report; the measurements are mine):

| Reading | Result |
|---|---|
| `u3bin/PROVENANCE.txt` head | client commit **`8ba0f7d`**, pair **`4genteam` `855ff5aa…` (12958462 B)** / **`agenthub-runtime` `c27b0c63…` (4623704 B)**, source `u3src-8ba0f7d347d53`, `built: 2026-10-15T06:28Z` |
| 4genteam / agenthub-runtime `sha256sum` + `stat` | `855ff5aa…d9a` 12958462 B / `c27b0c63…59c` 4623704 B — the stamp's numbers reproduce |
| `git merge-base --is-ancestor 4ada3a4 8ba0f7d` (in `agenthub_client`) | **rc 0** — the pane-pid fix is an ancestor of the build the pair was made from |
| the revision series, one `sha256sum` pass | `fe-stage6` `5b2e15b3` 157965 · `fe-stage8` `b35711cd` 167800 · `fe-stage9` `1142c831` 169481 · **`fe-stage10` `b91386d4` 170100** · **`fe-stage11` `9d32fc78` 171290** · **`fe-stage12` `d8d0b389` 174279** |
| `cmp -s u3-run/ACCEPTANCE-cutover-lab-U3.sh u3-run/fe-stage11.sh` | **rc 0** — the live path is `9d32fc78`, byte-identical to `fe-stage11.sh` |
| `sha256sum u3-run/run-c4.sh`, `stat` | `2facd3e6…`, **6032 B** |
| `run-c4.sh:47` | `ANNOUNCED_HARNESS="9d32fc78…"` — the pin names the live revision |
| `u3-run/STAGE12-2026-10-15.md` | stage12 is **STAGED, NOT INSTALLED**: "the LIVE harness `9d32fc78…` — UNTOUCHED" |

**What the ledger actually is.** Six revision files, `fe-stage6`/`8`/`9`/`10`/`11`/`12`, of which the
board had named three (`6`, `8`, `9`) plus a launcher sha that is wrong. `reviewer-stage5.sh`
(`28302b7b…`, 151731 B) is the pre-ledger live file and is not part of the six. The `5b2e15b3` bytes
survive exactly where the install rule puts them: aside under their own filename
(`ACCEPTANCE-cutover-lab-U3.sh.5b2e15b38b3c1340…`, hash-equal to `fe-stage6.sh`).

**Not in this change.** No claim about which revision closes which of the three harness faults — that
is not measured here. No test, no instrument and no rule was touched: `NEXT-GEN2.md` and this entry
only.
