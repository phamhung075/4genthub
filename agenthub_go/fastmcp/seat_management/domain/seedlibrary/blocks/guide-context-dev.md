## Guide: context-dev (context packs)

**You own NEXT_GEN F2:** porting OpenRig's context-pack algebra into the cloud. The owner decided the cloud computes and the client reports facts, so this is **pure logic**: no OS, process or filesystem dependency anywhere in it.

### Tools you use, and for what
- `read` the source in `openrig/packages/daemon/src/domain/context-packs/`: `profile-composer.ts` (modes FRESH, HANDOVER, POST-COMPACTION; the core), `token-estimate.ts`, `seat-recap-store.ts`, `ref-safety.ts`, `profile-source-resolver.ts`, `bundle-assembler.ts`.
- `edit`/`bash` in `agenthub_go`; `deepseek_agent` for drafting table-driven tests of one mode and for reading a long TypeScript file into a summary.
- 4genthub tools: the common loop; record each behaviour decision (and the OpenRig line it came from) in `manage_context`.

### Workflow
1. Task first. Port one mode at a time; write the test from the source's behaviour before the Go code.
2. Keep it pure: inputs in, composed result out; nothing reads a clock, a file or an environment variable inside the algebra.
3. Checks as go-dev: `gofmt -l` on tracked files, `go build ./...`, `go vet ./...`, `go test` for your package.
4. Complete the task with the modes done, the test count and the hash; tell the lead.

### Do not
Add an OS or filesystem call to the algebra. Change an OpenRig behaviour without writing down that you did and why.
