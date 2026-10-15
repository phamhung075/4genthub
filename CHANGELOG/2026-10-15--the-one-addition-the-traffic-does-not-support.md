# The one addition the traffic does not support, named, before the ff

One clause of the link bullet was false as written. The reviewer measured it; this is the correction,
landed before the fast-forward rather than after it.

## Changed

- **Item (ii) of the link bullet no longer says "every addition carries the measured traffic that
  justifies it".** Ten of the eleven do. **`reviewer collaborates_with fe-dev` has ZERO rows at every
  cutoff** — measured by the reviewer across 227 rail rows and re-checked against my own 171-row
  grouping, where the pair is simply absent — and it is kept on the **class** argument instead: a gate
  verdict returns work to its author, and a reviewer that cannot return a frontend verdict fails the
  same way as one that cannot return a Go verdict (`reviewer → go-dev` has 5 measured rows and the same
  shape).
- **Why it is named rather than quietly dropped:** the traffic claim is what justifies the other ten. A
  successor reading "every addition carries its traffic" would take the sentence for more than it is.
- **The rule for the next addition keeps its one exception, stated:** a class argument may add a link
  where traffic is absent, and when it does, the absent measurement is written beside it.

## Instruments

- The reviewer's measurement, in its own gate row `qitem-20261015053452-7a53fe146711`: 227 rail rows,
  every added pair carries traffic except `reviewer → fe-dev`.
- My own 171-row grouping in this same bullet lists no `reviewer → fe-dev` pair — the error was in the
  sentence, not in the instrument, and the sentence is what is fixed.
- The reviewer's verdict on both deltas is APPROVE ON CONTENT at the two identities the gate row
  `qitem-20261015053042-ad2717febc86` names; nothing in either patch was required to change.

## Not in this change

No code, no test, no pin. `NEXT-GEN2.md` plus this entry: a sixth commit, so the docs delta's tip and
patch-id move once more and the lead asserts the new pair at the ff. The definition delta is untouched
at `16f0032f` / `ae899a1a`.
