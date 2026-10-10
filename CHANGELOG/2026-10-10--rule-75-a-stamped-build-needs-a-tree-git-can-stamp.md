## Rule 75: a build a gate judges by its vcs stamp has to come from a tree git can stamp

Filed from `qitem-20261010185322-02a9cfc29de69270`, beside rule 74 — the pair is deliberate: 74 says **which object** to measure, 75 says **how the object must be built** for the measurement to be possible at all.

### Fixed
- `agenthub_go/NEXT_GEN.md`, the numbered rule series: **rule 75** — *a build a gate must judge by its VCS stamp has to come from a tree git can stamp; a linked worktree stamps nothing, so it produces an artefact the gate cannot read.* It carries the instance in the order it was found (the client's own checkout one commit **past** the pin at `f9ebec81`, so a build there stamps a non-pin revision; a detached worktree **at the pin** stamping **no** `vcs.revision`/`vcs.modified` at all, because Go does not stamp where `.git` is a file; and the contrast — the main-checkout build at 16:05 stamps `84bd0343`/`false`), the working route (**a real clone at the pin**), the honest reading of a missing stamp (**a FAIL against a gate that requires it, and it hides exactly the staleness the check exists to catch**), and the method point (the build tree is part of the artefact, since the gate reads it only through the binary).

### Verified
- The three measured positions are context-dev's and the lead's, each cited in the rule: `f9ebec81` (the client checkout past the pin), the worktree build with no stamps, and `84bd0343`/`false` from the main checkout. This seat did not run a build.
- **What this seat did check, because the rule's remedy depends on it:** the pin is a gitlink (`git ls-tree HEAD agenthub_client` → `bae2c86d`), so a build's stamped revision is comparable to it at all only from a tree git can stamp — which is why "clone at the pin" and not "checkout at the pin" is the instruction.

### Not run
- No build, no clone, and no `go version -m` run by this seat: the A0 artefact and its stamps are other seats' measurements, attributed rather than re-derived. Nothing was edited outside `NEXT_GEN.md` in this repository.
