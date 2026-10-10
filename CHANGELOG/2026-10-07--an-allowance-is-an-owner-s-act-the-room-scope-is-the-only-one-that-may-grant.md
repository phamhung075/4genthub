## An allowance is an owner's act: the room scope is the only one that may grant

- **The rule, and where it is enforced:** a policy block may DENY from any scope, because adding a denial
  can only make a seat safer — but it may not GRANT from a **seat-scoped `override`**, because that content
  is the overlay's own and at the seat scope it is the seat's own act. `FoldPolicies` refuses it **by name**,
  with the way out in the message ("move the block to the room scope, or make this a denial") — the same
  form as the guard's refusal of an approval it cannot express.
- **The scope travels from where it is known:** `ResolvedModule.ContentScope` records the scope of the
  `override` that supplied a module's content (empty when the content came from the catalogue), set in
  `resolver.applyOp`, which is the one place the scope and the content are both in hand. `computeHash`
  deliberately does **not** read it: provenance is not content, the rendered bytes are the same wherever the
  same text came from, so no seat re-resolves and no hash moves.
- **`resolver.ScopeSeat` is exported** because the renderer has to name the scope this rule turns on; the
  other two scopes stay unexported, because naming them has no production reader.
- **AND THE LINE THE RULING NEEDED REFINING AT, named rather than passed over: the ruling reads "never a
  seat-scoped block", but the ten room policy modules are delivered by SEAT-scoped `add` ops.** An `add`
  carries a version and **no content**, and a room-scoped op applies to *every* seat in the room, so a
  per-seat module cannot be attached any other way — refusing seat-scoped blocks outright would refuse the
  very modules that carry the `rig whoami` exemption. What is enforced is the narrower, sufficient rule: a
  seat-scoped **override** may not introduce an allowance. That closes the self-grant vector — the only path
  by which a seat's own act supplies content — and leaves the ten modules folding, which the test's second
  positive control pins.
- Files: `seat_management/domain/resolver/{resolver.go,resolver_test.go}`,
  `seat_management/domain/seatrenderer/{policy_fold.go,policy_fold_test.go}`.
