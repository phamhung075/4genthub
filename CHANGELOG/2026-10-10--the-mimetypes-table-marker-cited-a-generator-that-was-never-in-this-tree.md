## The mimetypes table's DO-NOT-EDIT marker cited a generator that was never in this tree
### Changed
- `agenthub_go/fastmcp/utilities/mimetypes_table.go`, **the file header only** — one comment line replaced by a header block, numstat **17/1**, and **no data line appears in the diff** (`git diff -U0 -- <path> | grep -E '^[+-]\s*"'` is empty), so no entry in `mimeTypesMap`, `mimeSuffixMap` or `mimeEncodingsMap` changed and the served answers are identical. Nothing else in the file, and no other path, moved.
- The marker read `// Code generated from CPython 3.14 mimetypes.MimeTypes() built-in tables (host mime files are not read). DO NOT EDIT.` — an instruction no seat could follow (there is no generator to run) or verify (there is no generator to find), which is the same defect the `models.go` header carried until `14210172`.
- The header now states ORIGIN (transcribed by hand during the port, from the standard library the Python side called), the **verified** provenance, that **NO GENERATOR EXISTS AND NONE EVER DID**, that the file is **HAND-MAINTAINED**, and **DO NOT REGENERATE**, with the reason: the data is deliberately the built-ins, so re-deriving it from a host or from a different CPython silently changes which content types the server accepts.
### Verified
- **The provenance is exact rather than paraphrased, at the same minor version the marker names (CPython 3.14.0):** `mimeTypesMap` is `MimeTypes().types_map[True]` — **the strict table `guess_type` uses by default** — with **198 entries and zero differences**; `mimeSuffixMap` (6 entries) equals its `suffix_map` and `mimeEncodingsMap` (5) its `encodings_map`. Reproduce from the repo root:

```python
import mimetypes, re
s = open('agenthub_go/fastmcp/utilities/mimetypes_table.go').read()
i = s.index('var mimeTypesMap = map[string]string{')
go = dict(re.findall(r'^\t"([^"]+)":\s+"([^"]+)",$', s[i:s.index('\n}', i)], re.M))
tm = mimetypes.MimeTypes().types_map
print(len(go), sum(1 for k, v in go.items() if tm[True].get(k) != v))
```
  → prints **`198 0`**.
- **"Host mime files are not read" is measured rather than repeated:** the module-level tables — which `init()` populates from the host's known files at import — hold **1571** entries on this machine and differ from the Go map in **1420** keys. Treat that as a direction rather than a figure: the Go side deliberately carries the built-ins, and any host carrying a different database still must not change these answers.
- **The no-generator claim comes from history, not from a directory listing:** `git log --all -S mimeTypesMap` returns **exactly one commit**, `6b0bdd5f` (*feat: migrate backend to Go FastMCP and update CapRover definition*), which added both `mimetypes.go` and `mimetypes_table.go`; `git log --all --diff-filter=A -- '*mimetype*'` adds no other file ever; and `git grep -l mimetypes_table` matches **only a CHANGELOG entry** in the whole tree.
- **The Python side did not generate them either:** at the port commit's parent, `agenthub_main/src/fastmcp/utilities/types.py` imported the standard library and called `mimetypes.guess_type(self.path)` — which is why these tables have to exist in Go at all.
- **Not a code change and not a behaviour change:** `gofmt -l` clean; `go test -count=1 ./fastmcp/utilities/...` → **ok** (both packages); `go build ./...` → rc=0; `go vet ./fastmcp/utilities/...` → rc=0.
### Found by
- The marker audit run for the `models.go` ruling, reported in `CHANGELOG/2026-10-10--the-session-carries-the-seat-it-belongs-to.md:22` as *"its own row, not this one"*; landed as row `eeb62d07`, lead-dispatched. **The audit's second marker gets no row and needs none:** `agenthub-frontend/public/env-config.js` is accurate, because it is replaced at container startup.
- **Low priority by construction:** the file is data, the edit is a comment, and it rides **above** the sealed `7fe3b837` rather than touching it.
