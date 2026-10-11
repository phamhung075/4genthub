## The seat guide asks for a plain writing style, not the caveman voice

### Changed
- `agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/guide-common.md`: the section "Reply voice (caveman)" becomes "Writing style": answer first, literal wording, no greeting, recap, closing offer or metaphor, one idea per sentence, negations, numbers, code and paths exact, full sentences for warnings, irreversible actions, ordered steps and questions. It no longer points at `scripts/caveman`. `guides.lock.json` records the new digest.
- The `scripts/caveman` submodule and `scripts/caveman-proxy.sh` stay as reference for the input-side trial. No voice skill is applied to any seat.

### Verified
- `go test ./fastmcp/seat_management/domain/seedlibrary/` ok.
