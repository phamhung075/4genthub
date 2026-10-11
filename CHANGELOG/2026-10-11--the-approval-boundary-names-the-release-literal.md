## The approval boundary names the release literal, not the derived health constant

### What changed
`scripts/team/4genthub/mission.md:21` — the Approval boundary paragraph of the standing mission, the file that
renders into every seat — told a seat to bump the health version "in
`agenthub_go/fastmcp/server/httpapp/http.go`". That is the wrong file, and has been since the port:
`httpapp/http.go:160` reads `const healthVersion = config.ReleaseVersion`, so the value a seat must move is the
literal in `agenthub_go/fastmcp/config/version.go` (`ReleaseVersion`, line 25). A seat that followed the old
sentence edited a file that holds no value and believed it had bumped the release — the belief is the failure
mode, because the deploy's confirmability through `/health` depends on that literal.

The sentence now reads:

> The release version in agenthub_go/fastmcp/config/version.go must be bumped in the same commit set so the
> deploy can be confirmed: healthVersion in agenthub_go/fastmcp/server/httpapp/http.go derives from it and is
> what /health reports.

One line changed; nothing else in that file was touched, and the neighbouring lines were current when measured.

### Where the value actually moves, as the tree proves it
The certified release batch is the evidence for the mechanism: `294f432b` (the `0.0.37` deploy marker, the
batch's last commit) set `config/version.go:25` and left `http.go` untouched. At this tip the literal reads
`"0.0.36"` on `4genthub-min/go-dev` and `"0.0.37"` on `4genthub-min/batch-0.0.37`; `http.go:160` is identical on
both, which is the point.

### What this does NOT do
It fixes the repo-side file only. The same wrong file is named in two seat-context guide sources —
`scripts/team/4genthub/area-go-backend.txt:18` ("Bump healthVersion in fastmcp/server/httpapp/http.go with each
release") and `scripts/team/4genthub/project-4genthub.txt:1` — and those are the cloud brain's rendered context,
so they are corrected through the seat-context channel (feedback `eecc8a97-200b-43b8-bd73-7e14304008f8`) rather
than by editing files here. `area-go-backend` is the block the go-dev seat itself reads, so those two reach seats
ahead of this file.

No test accompanies this change: it is prose in a rendered context file, and a test would have to pin that
prose, which is the source-text assertion the testing contract forbids. The check that the file says what it
should is the read-back below.

### Verified
- the new sentence read back from `scripts/team/4genthub/mission.md:21`, and `git diff --stat` shows one
  insertion and one deletion in that single file;
- `agenthub_go/fastmcp/server/httpapp/http.go:160` reads `const healthVersion = config.ReleaseVersion` and
  `agenthub_go/fastmcp/config/version.go:25` carries the literal, both grepped at this tip;
- nothing else is touched: no Go, test or frontend file, so no package suite is affected by this commit.

Row: `qitem-20261011010830` (filed by the lead from the reviewer's finding, both of whom measured the sentence
independently).
