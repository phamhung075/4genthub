## The third retirement now names the architect as its first step (team flow, 2026-10-08)

- The team flow changed: a change that touches **structure, an interface, a boundary or the data model** goes to the
  **architect** first — it reads the code, compares at least two options, writes a short decision note and recommends
  one — and the lead then assigns the work with that decision attached. **The third retirement is that kind of
  change**: it removes a writer of `config.yml` and the source of the eleven guide blocks, so its note now says so
  in both places a would-be deleter reads — `guides.lock.json`'s `_deletion` and
  `ai_docs/operations/openrig-seat-limits.md` — beside the trigger, which has **not** fired (all ten seats still
  carry the generator's header, and `go-dev2`'s removal and the architect's arrival were verified against the live
  rig rather than taken from the brief). No code changed and nothing was deleted; the gate for this commit is the
  seed library's own load test, because the file it edits is read at load.
