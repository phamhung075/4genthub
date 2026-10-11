## The progress note goes where the entity reads it

`manage_context add_progress` wrote `progress_updates` at the **top level** of the context dict. The entity's own
load — `createContextEntity` and `updateContextEntity`, which both read the top-level `implementation_notes` key
into `t.ImplementationNotes` — never looked at that key, so **the write and the read never met**: the note was
persisted faithfully and was invisible to every reader that goes through the entity. That is the incident's own
shape at one more site, and it is why the verb appeared to work while nothing downstream could see its output.

`UnifiedContextService.AddProgress` now reads the note list out of `implementation_notes` and writes it back
inside the same map, which is where the entity's load and the entity's own `UpdateProgress` both look.

**One property worth naming, derived from the merge rule rather than observed in the old code**: at the top level
the key was append-merged, because `mergeContextData`'s `replaceListFields` holds only `insights` and `next_steps`
— so a caller that already included the previous entries in its update would have had them appended again, and the
top-level location would accumulate duplicates on every call. Inside `implementation_notes` the value is a map and
the merge replaces the `progress_updates` key wholesale, so the list is exactly what the verb built.

**Evidence.** New test `TestZucsAddProgressLandsWhereTheEntityLoadsItsNotes` in
`application/services/unified_context_service_test.go` writes two notes through the verb and asserts the read-back
**through the entity the service itself built from the saved dict** (not the response shape): red before the change
— `ImplementationNotes[progress_updates]=<nil>` — and green after, with exactly the two notes in order and no
duplicates. `gofmt` clean, `go vet` clean on the package, and module-wide `go test ./... -count=1` green.

The live path is unchanged in shape: the handler and the facade still call `service.AddProgress`
(`application/facades/unified_context_facade.go:249`); only the key the note is stored under moves. Nothing was
pushed.
