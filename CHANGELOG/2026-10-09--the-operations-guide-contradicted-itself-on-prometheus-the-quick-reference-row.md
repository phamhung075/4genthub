## The operations guide contradicted itself on Prometheus; the Quick Reference row now names the surface that exists

### Fixed
- `ai_docs/operations/complete-operations-guide.md`: the Quick Reference said *Monitor metrics* -> `http://localhost:9090 (Prometheus)`, while the same file's Infrastructure note and Monitoring note both state that this repository defines no `monitoring/`, no Prometheus and no Grafana. **One file disagreeing with itself is worse than a stale path — the reader cannot tell which half is stale, so neither can be trusted.** The row now names the in-repo surface: `GET /ws/metrics` on the Go server, emitted in Prometheus text format from its in-process registry, with the Infrastructure note carrying the dated correction.
- **No monitoring target was invented**, per the same discipline as the deployment-script row: `git grep -n 9090` returns the CHANGELOG history entry that removed the old Prometheus row plus numeric coincidences inside test fixtures — **nothing in the tree defines a listener on 9090**.

### Verified
- `git ls-files monitoring/ | wc -l` -> `0`. The endpoint is a plain HTTP GET registered at `agenthub_go/fastmcp/server/httpapp/misc_mount.go:73` (`handleWebSocketMetrics`, `:238`), whose body writes `# HELP`/`# TYPE` lines from `metrics.GetMetricsSummary()` (`fastmcp/server/metrics`) with `Content-Type: text/plain; version=0.0.4; charset=utf-8` (`:37`).
- **Adjacent defect REPORTED, not fixed, because this row's scope was the contradiction alone:** the same file's Monitoring block cites that registration as `misc_mount.go:72` where the tree has `:73`.
