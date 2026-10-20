# The pin carries the deny-list fix, and its record awaits a carrier

The hub's gitlink moves `50b97132 -> dae76a98` (hub `6a458a24`, gitlink only), after client main took
`4genthub-min/openrig-deny` as a merge: `50b9713` + `e157cd6` -> `dae76a9`.

## Changed (client e157cd6, 2 files +39/-1)

- **`rust/agenthub-runtime/src/main.rs`.** `ENV_DENY_PREFIXES` is `["OPENRIG_", "RIGGED_"]` again: the
  prior client's variables (`OPENRIG_HOME`, `OPENRIG_URL`, the activity-hook token, session/node ids -
  nine measured in an agent's environ) address a rig, so an agent carrying them out of an inherited
  environment could reach a room that is not its own. The deny test asserts `OPENRIG_URL` and
  `OPENRIG_ACTIVITY_HOOK_TOKEN` are denied; the comment names why the new name alone does not retire
  the old one from environments that still export it.
- U3 defect: `338f192` had dropped `OPENRIG_`, which the cutover-lab run measured as a real failure.

## Evidence

- At the lane tip `e157cd6` and at the merged client main `dae76a9`:
  `cargo test the_deny_list_covers_every_prefix_that_addresses_a_rig` -> `test ... ok`, 1 passed;
  `cargo build` clean; `go build ./...` rc 0.
- The merged tip is a merge because client main had moved (the commit-form skill half); the two
  lanes share no path.

## Held

Held record: a pin commit cannot carry its docs from a seat (pre-commit drops the gitlink, so a
pin+docs commit arrives as docs-only and the docs-only guard refuses it; no hook was bypassed). It
rides any commit that touches a non-doc file, or the owner's `types_or: [file, directory]` one-liner
(`qitem-20261017002819-8e1c6aff25f2`).

The push is not authorized and waits for the owner's word.
