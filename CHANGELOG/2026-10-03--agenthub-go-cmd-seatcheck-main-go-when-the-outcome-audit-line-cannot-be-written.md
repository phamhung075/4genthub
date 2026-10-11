### Fixed

**seatcheck no longer reports failure for a message it delivered** (2026-10-03)

- `agenthub_go/cmd/seatcheck/main.go`: when the outcome audit line cannot be written after delivery, seatcheck prints a warning on stderr and keeps the delivery's own exit code (0 delivered, 5 not delivered) instead of exit 1, so a caller that retries on a non-zero exit cannot send the message twice. The decision line before delivery is still mandatory (exit 1, nothing sent).
- Documented in the package comment and `commpolicy.AuditRecord.Outcome`: an allowed decision line with no outcome line means the delivery outcome is unknown (the message may have been delivered).
- Reviewer minors on 951a4136. Verified: gofmt, go vet, `go test ./cmd/seatcheck ./fastmcp/seat_management/domain/commpolicy`.
