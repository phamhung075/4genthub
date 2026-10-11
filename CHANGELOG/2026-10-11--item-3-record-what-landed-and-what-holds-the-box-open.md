## Item 3's box records what landed, and what still holds it open

### Changed
`agenthub_go/NEXT_GEN.md:455` (PLAN item 3, retire `manage_agent`, the `agents` table and the role
registry): the plan's step 9 record is appended to the box. Board row `1133eeb8`.

- **Landed:**
  - `b0d441bd`, `e0338f54` and `76b800b9` (steps 1-2), with the server's absence guard
    `TestMCPToolsListDoesNotPublishManageAgent`.
  - `fd3e5581` (step 6, the served API prose).
  - Client commit `1fec5bc5` (step 5), which the reviewer approved in `qitem-20261011064422`.
- **The reviewer's coverage note, kept so it stays visible:** the client's suite stays green if the retired
  entry is put back into `nonLeadToolDeny`. Only the server guard backs that list's correctness.
- **Still open:**
  - the pin bump, after the owner's client push;
  - step 4, the hint block in the owner's `.claude` submodule;
  - step 7, the owner's push approval;
  - step 8, the principal's export and `DROP TABLE agents`.

### Not changed
The box stays `[ ]`. The plan's step 9 closes it "with the commit hashes and the step-8 read-back", and no
read-back exists yet. Ticking it now would claim a production drop nobody has made. No code changed.
