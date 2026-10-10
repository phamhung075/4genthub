## The render can emit an allowance, so the `rig whoami` exemption survives the first client install

- **Why it was needed, in the renderer's own words:** the client merges a SERVER-RENDERED document into the
  seat's `config.yml` with the `bash.patterns` list replaced wholesale, and the guard accepted only `deny` —
  so the exemption landed in the hand-written generator (`d9d93182`) would have **vanished at the first
  install while its own check still passed**. A fix that works today and disappears silently tomorrow is
  worse than one that fails.
- **The guard keeps the property that makes it worth having.** `parsePolicyRules` now expresses `deny` and
  `allow`, and still refuses anything else **BY NAME** — *"an unknown approval would silently not apply"* —
  so this is one more expressible value rather than a hole. The message names both values it can express,
  so a publisher who sees only the error knows what to write.
- **The SIBLING is required of a denial and not of an allowance, and the asymmetry is the rule:** a denial
  without a sanctioned alternative is a trap, while an allowance **is** the alternative, so a sibling would
  be a second voice saying the same thing.
- **The fields now say what they carry:** `BashDeny`/`ToolDeny` became `BashRules`/`ToolRules` on both the
  parsed module and the folded set, because each list holds both approvals.
- **The fold refuses a contradiction rather than picking a winner:** one match declared as both `deny` and
  `allow` fails the fold by name. The union's rationale is restated where it now applies — a deny unions
  safely, because adding one can only make a seat safer; an allowance **grants**, so its safety comes from
  elsewhere: a seat cannot compose itself, and every block in its stack was put there by whoever owns the
  room. The collision rule is what keeps that honest.
- **The words emission splits allowed from refused.** `RenderPolicyLimits` gives allowances their own
  section: a seat reading an allowance under a `### Refused shell commands` heading would be told the
  opposite of what its policy says, and it reads these words rather than the document. The `— instead:`
  count stays one per denial, which is the check that no denial was written without a sibling.
- **The ten room policy modules carry the entry FIRST** (`scripts/team/4genthub-min/policy-<seat>.json`), so
  the exemption reaches the rendered document from the same table that produces the denials — one source,
  not two. Publishing them is what puts the entry in the catalogue, and that step is the owner's.
- Files: `agenthub_go/fastmcp/seat_management/domain/seatrenderer/{policy.go,policy_fold.go,policy_test.go,policy_fold_test.go}`,
  `scripts/team/4genthub-min/policy-<seat>.json` (ten).
