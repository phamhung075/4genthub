## The files that named the root CHANGELOG.md now name the directory

### Changed

- `AGENTS.md` — the changelog duty read "Update `CHANGELOG.md` for changes that ship"; it now reads "Update the changelog for changes that ship (one new file `CHANGELOG/<date>--<title>.md`)".
- `ai_docs/core-architecture/agenthub-system-architecture.md` — the **Commits** bullet said to update `CHANGELOG.md` in the same commit; it now says the changelog is ONE new file under `CHANGELOG/`. The **Documentation** bullet below it already stated the directory form, so the two no longer disagree.
- `ai_docs/api-integration/surface-inventory.md` — a citation that resolved to the deleted flat file now names `CHANGELOG/`, and the two quotations of its line numbers are marked pre-split. A quotation is a dated record, so its numbers stay rather than being repaired.
- `agenthub_go/NEXT_GEN.md` — a pointer to the flat file now names `CHANGELOG/`; the dated measurements that named it are marked pre-split and keep their numbers; the stale reproduce command now reads `grep -rn "slug-derived" CHANGELOG/`; and rule 64's live sentence now says `CHANGELOG/` above all, because that rule's hazard moved with the split.

### Not changed, and why

- `TEST-CHANGELOG.md` and `agenthub-frontend/CHANGELOG.md` are real files; every reference to them was left alone.
- The three seat guides already state the live convention, so no guide changed — and therefore no lock digest needed re-recording.
- History that is still true was left as history: a past commit's file list, a measurement taken at named past tips, the "old single `CHANGELOG.md`" in `repo-agent-rules.md`, and the "NEVER create a CHANGELOG.md … in other directories" prohibitions, which forbid a file rather than pointing a reader at one.

### Testing

- Read, not run: no suite asserts this prose. The check is the sweep — `git grep -n "CHANGELOG\.md" -- <the in-scope paths>` — with every remaining hit opened and classified, and the classification is the section above.
