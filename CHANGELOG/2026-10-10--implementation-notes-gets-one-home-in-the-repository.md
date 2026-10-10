## `implementation_notes` gets one home: the entity's own field

The gate on the previous commit refused it, and the refusal was right. Its cause, measured by the architect against
testpg with the real `TaskContextRepository`: `AddProgress` twice both reported `success=true`, and `repo.Get` then
returned `ImplementationNotes=map[]` **and** `Metadata[implementation_notes]=map[]` — **both notes lost**.

The repository owned that column from two directions that never met:

- `Create` and `Update` wrote the column **from `entity.Metadata["implementation_notes"]`**;
- `Get` loaded the column **into `Metadata` only**, never into `ImplementationNotes`.

The service writes the entity's own field, so the write went to a place the column never read, and the read came
back to a place the service never asked. It was the incident's shape one layer down, and the service-level test was
green **only because its fake stores the entity in memory** — it never crossed the mapping where the notes were
being lost.

**The fix, in the two directions**: `Create`/`Update` take the column from `entity.ImplementationNotes` (with the
same empty-map default the neighbouring context maps get), and `Get` sets `ImplementationNotes` from the column
while `implementation_notes` stops travelling through `Metadata` at all. One home, in and out.

**Evidence, through the real repository on testpg**: `TestTaskContextRepositoryImplementationNotesRoundTrip`
creates a task context carrying a note and reads it back. Red on the pre-fix repository — with the source stashed
and the test left in place, `ImplementationNotes[progress_updates]` comes back **nil**, the architect's own
measurement reproduced here. Green after: the note is present and its text survives the column, and the test also
asserts the `Metadata` route is gone. `gofmt` clean; the repositories package green, PG-gated cases included.

**What this test is not**: it drives the repository rather than the service's `AddProgress`, so the service path is
covered by the service-level test (whose fake cannot cross the mapping) plus this one, which crosses it without the
service. A single test doing both would need this package's foreign-key fixtures, which the services package cannot
see — named here rather than left as a gap for a reader to discover.
