## The metrics citation in the Monitoring block was off by one line

### Fixed
- `ai_docs/operations/complete-operations-guide.md:276`: the Monitoring block cited `misc_mount.go:72` for `GET /ws/metrics`; the registration is at `:73`, and `:72` is the closing `})` of the registration above it. One line, no adjacent sweep. **In scope now rather than merely reported, because that block is the citation for the Prometheus correction landed in `12006c50`.**

### Verified
- `misc_mount.go` read at lines 55–80: `:72` is `})`, `:73` is `mux.HandleFunc("GET /ws/metrics", handleWebSocketMetrics)`, and the handler is defined at `:238`.
- `grep -n 'misc_mount\.go:' ai_docs/operations/complete-operations-guide.md` -> one line, the Monitoring block, now `:73`.
