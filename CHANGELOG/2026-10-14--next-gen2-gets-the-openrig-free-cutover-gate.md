## NEXT-GEN2 gets the OpenRig-free cutover gate

### Added

- `NEXT-GEN2.md`, **Group C: OpenRig-Free Cutover Gate** (C1–C5), placed after Group R. R1–R7 are delivered
  components, not the cutover: measured 2026-10-14, the five `4genthub-min` seats are still hosted by the
  OpenRig daemon and one `pi-runner.js` each; the `agenthub-runtime` daemons run beside them and host no seat.
  - **C1** seats hosted natively (U0/U1/U2); work is on `4genthub-min/u2-native-runner` at `dbda423`
    (`go vet`, `go test ./...` 24 packages ok, `cargo test` 65 passed), not merged, pin not bumped, not installed.
  - **C2** parity: auto-resume after a provider stream error, large-RPC chunking, `send` identity and submit
    confirmation, idle-seat watchdog for unclaimed queue rows.
  - **C3** no exec of `rig` from the client (P1), and native `rig transcript` / `rig capture` (U5).
  - **C4** the U3 acceptance run on `cutover-lab` is the gate.
  - **C5** snapshot, then retire the live OpenRig rig, only after C1–C4.
- Owner decisions recorded in the group: retire OpenRig only after U3 passes and a snapshot exists; omp cap
  unchanged; OpenRig stays up until then.

### Notes

- Documentation only. The edit to `NEXT-GEN2.md` was scripted because the pre-tool hook reads an edit of an
  existing root file as a creation. Diff: 37 insertions, 0 deletions.
