# The commit form is pathspec fleet-wide, by the owner's word

The commit-form escalation (queue rows `qitem-20261017011935` and its 02:32Z relay) is answered:
**PATHSpec FLEET-WIDE** is the standing rule - commit with an explicit pathspec in the shared repo.
`270765d1`'s flip of the guide and its test to the staged form is reverted; nothing else of that
commit retires.

## Changed

- **`guide-common.md`, the loop's step 4.** A seat is told to commit by pathspec and *not* stage
  first: `git commit -m "<type(scope): subject>" -- <paths>`, with `git add -N -- <new>` only for a
  new file. The never-rules (`git add .`, `-A`, `commit -a`, `--amend`) and the changelog sentence
  are unchanged.
- **`guide_commit_form_test.go`, its two constants and their A1/A2 wording.** `newCommitRule` is
  `do not stage first` again and `oldCommitForm` is the staged prescription; the assertions'
  comments and messages name the shared index as the reason, so the file's header comment and its
  assertions state one form.
- **`guides.lock.json` and `seedcontent.lock.json` re-recorded, `seedVersion` 1.4.12 -> 1.4.13.**
  The guide's bytes moved, so the pairing's `sha256` and `source_sha256` carry the new digest (the
  shape `270765d1` used) and the content set is recorded under the raised version; the record was
  appended with the package's own `-update-seedcontent-lock` flag, not by hand.
- **`seedmap.go`'s version ledger gains the 1.4.13 sentence** the gate nit found missing: the ledger
  describes each version's change and 1.4.13 had no line, so the comment now names the restored step-4
  commit form beside 1.4.12's.

## Evidence

- `gofmt -l` on the two changed Go files: empty, rc 0.
- `go vet ./fastmcp/seat_management/domain/seedlibrary/ ./fastmcp/seat_management/domain/seedmap/ ./fastmcp/seat_management/domain/seatrenderer/`: rc 0.
- `go test` the same three packages, `-count=1`: all ok.
- `TestGuideCommonPrescribesTheCurrentCommitForm`, `TestGuidePairingRefusesTheGuideChangedUnderTheOldLock`
  and `TestSeedVersionNamesOneContentSet` pass with the re-recorded lock and content set.
- The same three checks re-ran at the tip that carries the ledger sentence: `gofmt -l` empty, `go vet` rc 0,
  `go test -count=1` all ok.

## Not mine to move

`AGENTS.md` rule 4 and the ten `scripts/team/*/policy-*.json` already state the pathspec form, so
they need no edit under this ruling; the push is not authorized and waits for the owner's word.
