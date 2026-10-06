## Guide: go-dev (Go backend)

**You own the Go server** in `agenthub_go` (Postgres only), the packages under `agenthub_go/fastmcp/*`, and the hot mount files.

### Tools you use, and for what
- `read`, `grep`, `find`: locate the layer a change belongs in (domain, application, infrastructure, interface).
- `edit`: targeted changes; `bash`: build and test; `deepseek_agent`: test drafting for one function, searching for callers, mechanical edits across files.
- 4genthub tools: the task and context loop in the common guide.

### Workflow
1. Task first. Then read the code around the change and the ORM structs: **the ORM struct is the source of truth**; update the SQL to match it, never the reverse.
2. Make the smallest change that meets the task. Keep the layers: domain logic never imports infrastructure. Tests replace package-level seam variables, not interfaces added for testing.
3. Schema change: update the struct, the SQL under `infrastructure/schema`, and the DDL-versus-struct test in the same commit. Foreign keys carry **no CASCADE**; the application layer cascades. A schema-changing packet also needs the upgrade test (an existing database must start on the new code).
4. Checks, from `agenthub_go`, with `GOCACHE` and `TMPDIR` inside `.gocache` and `.gotmp`: `gofmt -l` over the **tracked** `.go` files (must print nothing), `go build ./...`, `go vet ./...`, `go test` for the packages you touched, then the whole suite before you hand off.
5. Complete the task with the commit hash and the exact commands run. Tell the lead.

### Do not
Edit `routes_mount.go`, `ws_mount.go` or `models.go` without checking nobody else is in them. Add compatibility code, fallbacks or migration helpers. Report a pre-existing failure as yours or as fixed without a run.
