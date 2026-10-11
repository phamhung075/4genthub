## Rule 74: a gate asks about the artefact as its consumer invokes it

Filed from `qitem-20261010185322-02a9cfc29de69270` (the lead's handoff, on `context-dev`'s point: two facts this room paid for tonight would otherwise be rediscovered by the next occupant, because the seats directory is scoped to this boot).

### Fixed
- `agenthub_go/NEXT_GEN.md`, the numbered rule series (`:912`): **rule 74** — *a gate asks about the artefact as its consumer invokes it, not as it sits on disk.* It carries the instance with both binaries in hand (the clean artefact at the pin, `artifacts/seatcheck-bae2c86d`, correct and running, and A0 failed anyway because the invoked path is the retired server copy `8a7598ec` with `modified=true`), the measurement that is the whole rule (`go version -m $(readlink -f ~/.local/bin/seatcheck)`), the general question (*which object did the gate measure, and is that the object the consumer crosses?*), and the non-cosmetic consequence (the stale binary breaks the guard for every seat whose `HOME` is a seat state directory — the lead's A/B).

### Verified
- The two binaries are as context-dev's A0 file and the lead's A/B report them: the artefact at `~/.openrig/agenthub-seats/4genthub-min/artifacts/seatcheck-bae2c86d` and the invoked path `~/.local/bin/seatcheck -> ~/.openrig/agenthub-seats/bin/seatcheck`. Not re-measured by this seat; the rule is filed on two seats' independent measurements and says whose they are.
- The rule's place in the family was checked against the neighbouring rules before writing: 72 (the database the ORM actually reaches), 73 (the seam the case actually drives), 74 (the binary the consumer actually invokes).

### Not run
- No build and no install: A0 is the operator's install, as the record says. Nothing was edited outside `NEXT_GEN.md` in this repository.
