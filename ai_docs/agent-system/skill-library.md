# Skill library and per-seat curation

> Content for owner directive F1. The **publish** and the **drift check** are a separate
> row (go-dev); this file and its machine-readable twin `skill-library.json` are the
> inventory that row consumes. Nothing here publishes anything.

The library is the **union of two committed edges** in the OpenRig repository
(`~/__projects__/openrig`):

- `skills/_canonical/` — 35 skills in four groups: `core/` 17, `pm/` 7, `pods/` 4, `process/` 7.
- `packages/daemon/assets/plugins/openrig-core/skills/` — 19 skills, flat.
- They overlap by two names (`messaging-the-human`, `openrig-skills`), so the union is **52**.

`packages/daemon/context-packs/` is **not** a source: it is gitignored and rebuilt.

**Digest rule, stated so the number is reproducible:** each row's `sha256` is the SHA-256 of
that skill's `SKILL.md` under its committed path. A later check recomputes it and reports
DRIFT when it differs, instead of letting two copies diverge silently. `skill-library.json`
carries the same 52 rows plus the curation in a form a check can parse.

## The 52 skills

| Skill | Edge | Committed path | sha256 |
| :--- | :--- | :--- | :--- |
| `agent-browser` | canonical/process | `skills/_canonical/process/agent-browser` | `f2709bae71a8c60f6a4b80a6873560cdea9632000ed4b28d082dfae58801199b` |
| `agent-operated-software` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/agent-operated-software` | `9159d26e7884bc5205f8b06adaa65625c7d9c6bef41dc2f307d91da4cc1b424b` |
| `agent-operated-workflows` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/agent-operated-workflows` | `24e54cbfa979999f523516112670618b2926ae5d42c7aa0846c94db214857ea5` |
| `agent-starters` | canonical/core | `skills/_canonical/core/agent-starters` | `66cbaa251b05cde6a09f51b08c70ea78c6c4f75ae5db0f95baa15b8255714a1d` |
| `agent-startup-and-context-ingestion` | canonical/core | `skills/_canonical/core/agent-startup-and-context-ingestion` | `ed9a3fba75d9c53d44d3fb2a9b4703a1bdb5d13e78e4e34f18c2887c23c9d248` |
| `applying-a-permission-policy` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/applying-a-permission-policy` | `e8dbd8eec75847bfd382fb06de408c63807171d584237d1b1d7e1104c7ed4acc` |
| `backlog-capture` | canonical/pm | `skills/_canonical/pm/backlog-capture` | `345c2b47fc85e48c15c0d42bbb48fb27dd3b0ceec36bf59dc6ed20daaea47a84` |
| `claude-compaction-restore` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/claude-compaction-restore` | `ca819221c04a0479d0dc176360e69ca2aa50507451991297fb06a574aa49c111` |
| `context-builder` | canonical/pm | `skills/_canonical/pm/context-builder` | `0134c9b0a9f196565109f7f51b6ec78d5c3e4b5982a0d7105a93b29952625b3c` |
| `context-engineering` | canonical/process | `skills/_canonical/process/context-engineering` | `ef052238060410f8f49d94baaede14e569f3c943a7dba79ed98d4fc0a117af64` |
| `cross-host-rig-commands` | canonical/core | `skills/_canonical/core/cross-host-rig-commands` | `844a578d0f51cf8f02f8bfd7ffb3bbd6a37d511f721266c0d758c49157c1447a` |
| `delegating-work` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/delegating-work` | `54c061d1b28435266952d431765b40f4170581279decfffd3b10839848cd65e4` |
| `development-team` | canonical/pods | `skills/_canonical/pods/development-team` | `3d712a94a1725b543371ffc502d3f5641e3b77d9d566aa0f99a2977682241f9b` |
| `dogfood` | canonical/process | `skills/_canonical/process/dogfood` | `8addc5d22813193649e8286b354ae2282975d75f1dda6d5d4b33d6ace47f438b` |
| `exec-summary` | canonical/pm | `skills/_canonical/pm/exec-summary` | `ada0f42337920e7acdd94e24cad4f5c269b057e750f4a7fc627ea9efbc02fcb6` |
| `forming-an-openrig-mental-model` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/forming-an-openrig-mental-model` | `6e9f16191a56f87060326897d98cb3f83f00997799bc654dccc371798306d133` |
| `frontend-design` | canonical/process | `skills/_canonical/process/frontend-design` | `3897488693335f3b350292abe067e9f4a39a64af5ac6b1feb82074a36930273d` |
| `human-in-the-loop` | canonical/core | `skills/_canonical/core/human-in-the-loop` | `14cf0c4a0dc89179121465d4b8d81d40406427351adcdc34f875097d1e6e9ab2` |
| `loading-addressable-markdown` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/loading-addressable-markdown` | `104dc6a02ae6e2d0eff519387c6839cb09803945b9ee35ec3498af8feaaa8d1e` |
| `messaging-the-human` | canonical/core | `skills/_canonical/core/messaging-the-human` | `581372434f27b1994d516e144be1324c7c5981cacf64fef6f09d1a57017faa08` |
| `messaging-the-human` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/messaging-the-human` | `581372434f27b1994d516e144be1324c7c5981cacf64fef6f09d1a57017faa08` |
| `mission-slice-sop` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/mission-slice-sop` | `2cdc12b398f6d0fc05361791ec36066c44f1abd0137afd1f4f11a88b37bcc767` |
| `office-hours` | canonical/pm | `skills/_canonical/pm/office-hours` | `c09b92957e709e43b28186883aca9e73218b412a69355051b76700efac88b4cf` |
| `openrig-architect` | canonical/core | `skills/_canonical/core/openrig-architect` | `0c3f1b7ff5bf185c9da963905229e951ffe1fb6d45a3cc9247cb747fc1d9a59d` |
| `openrig-cmux` | canonical/core | `skills/_canonical/core/openrig-cmux` | `73a86eac45d68b16a38fc0a4438713c634d86061073dac96a4d9e656ea5d34dc` |
| `openrig-herdr` | canonical/core | `skills/_canonical/core/openrig-herdr` | `37508a02f50bb69ee97c22c37ccf70aa8e37dc0784061eb2a5ad813571eebd1a` |
| `openrig-operating-model` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/openrig-operating-model` | `53ec4d9c7764f5bc23616885d193b79ddb1be139fd010f4b89f143d39dfdcaa6` |
| `openrig-skills` | canonical/core | `skills/_canonical/core/openrig-skills` | `e5f47e24a4c3cb1afceb1a3a93647313e9c30830aff58faabb5fa57838d1206c` |
| `openrig-skills` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/openrig-skills` | `e5f47e24a4c3cb1afceb1a3a93647313e9c30830aff58faabb5fa57838d1206c` |
| `openrig-software-factory` | canonical/core | `skills/_canonical/core/openrig-software-factory` | `33930e72341661eaaa9d3c5ac945297926f430d643b6f279fcb7f693ac30b7f7` |
| `openrig-upgrade` | canonical/core | `skills/_canonical/core/openrig-upgrade` | `c3555c66abe0426e2990aec024849f644cf43320a65b8f1211e96d3b234f6e83` |
| `openrig-user` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/openrig-user` | `6fa8ad6e639db93a23f4d1a19d4cd446189199d5ba05c269c18ea1b8afa6e3f2` |
| `orchestration-team` | canonical/pods | `skills/_canonical/pods/orchestration-team` | `d13e08782a64b92b4db3f51d083f11fd6753f06e68052dbf2da174ab5618fa90` |
| `orienting-to-an-inherited-seat` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/orienting-to-an-inherited-seat` | `1721dfb2e66c4f1775b4d5d9a5c12340baa8042c4d26f999f85008f9a186baf3` |
| `oversight-team` | canonical/pods | `skills/_canonical/pods/oversight-team` | `a48de41350453a09b231e01a89cc1dd3d4a64e082df090a7b0e04034227d2bb4` |
| `plan-review` | canonical/pm | `skills/_canonical/pm/plan-review` | `42f1b746d9ceae32587fc754fcc96462af44ba7f0078407f505d7a30b88a1469` |
| `queue-handoff` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/queue-handoff` | `d4d7e3e8772886b3771daffd60523b5f79040309b892c8be1afd47d1f7287f7b` |
| `refocusing` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/refocusing` | `506fe68da3f127f51aeffdaec1b8859080563395585343e4a211b61328f1fab5` |
| `requirements-writer` | canonical/pm | `skills/_canonical/pm/requirements-writer` | `04cfb8853553f1538fd202e9804e14e6b259f3a4c12b5f255c30169cf66ed0af` |
| `retiring-and-inheriting-a-seat` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/retiring-and-inheriting-a-seat` | `ebe58e4db60ed963fd721a1685c4c2afe1e45d93beddd211518dfb5f0b48bdcc` |
| `review-team` | canonical/pods | `skills/_canonical/pods/review-team` | `e669a893d5bd1d01fdd5e357a0f0f56425fc2fb845705bddc629016e04c8a6da` |
| `rig-bundles-and-shareable-artifacts` | canonical/core | `skills/_canonical/core/rig-bundles-and-shareable-artifacts` | `e9d5103f419b971373e374474e6ef464e05f242f3fa25e63acfc0b2106651748` |
| `rig-lifecycle` | canonical/core | `skills/_canonical/core/rig-lifecycle` | `8346e01d532795b24c3dba63413ca662c7b44cc5eed39ee2e85568580f40adca` |
| `seat-continuity-and-handover` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/seat-continuity-and-handover` | `c08aa84aa1888b8a5d63d5e3a6d2ec8b700b8b13177fba48661ba7c7508f44ff` |
| `session-compaction-and-restore` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/session-compaction-and-restore` | `36a637b1520ff4b0a3ff2594eb4ba93340ff6794692323e95d188981aa007ab4` |
| `session-source-fork` | canonical/core | `skills/_canonical/core/session-source-fork` | `b2e650d3c89c8fb9d4ccc142c4fdbc969b5286b8141cc070565abac268decba9` |
| `software-for-agents` | plugin | `packages/daemon/assets/plugins/openrig-core/skills/software-for-agents` | `c36c6d3ae7484f477f1bd24e8ff72846f6dfbff685aef1e780f6011072a51ac7` |
| `specification-system` | canonical/core | `skills/_canonical/core/specification-system` | `5226d6e8b1362df89ba3d5afd82e4b4add355870132ca4b140d7f9f4324ffdc1` |
| `systematic-debugging` | canonical/process | `skills/_canonical/process/systematic-debugging` | `b2adbca870df5232f018a43f6715c7a97c3ddd9429aefa11f9248a859280c2c5` |
| `test-driven-development` | canonical/process | `skills/_canonical/process/test-driven-development` | `51f65d2bc71dd6fc84640bf113acf287f4e003ef325ed91cb112fce59149a298` |
| `topology-mutation-and-seat-management` | canonical/core | `skills/_canonical/core/topology-mutation-and-seat-management` | `38a7a6a4dc9f7b8c01d57ff74e72c5a07ac85a455ea580d617894ccb4364d15c` |
| `ui-mockup` | canonical/pm | `skills/_canonical/pm/ui-mockup` | `a597fad7dcdebf43e74e01a607e12eabf848c831c96be3da2f1aeeb12f82ef08` |
| `verification-before-completion` | canonical/process | `skills/_canonical/process/verification-before-completion` | `0b8cea0bb82a8ab0f015afaf84c87796e2c94eee3a83d4fa3d4461d0917950bd` |
| `watchdog` | canonical/core | `skills/_canonical/core/watchdog` | `24b2e756e3e9d067fa93a4b5fa5f48a5cce511e8b1a5b360b1c39bc09bc95d82` |

## Per-seat curation

Roughly six skills per seat type, chosen from the 52. Every skill a role text already
names is in that seat's set (the mandated inclusions); the rest are chosen for the role,
and each row states the reason in one clause.

### lead

| Skill | Why it is in the set |
| :--- | :--- |
| `delegating-work` | named in the role text; deciding WHO does a task is the lead's core act |
| `queue-handoff` | named in the role text; durable handoffs are how the lead moves work |
| `orchestration-team` | the pod skill for coordinating assignments and blocked work across a rig |
| `mission-slice-sop` | the lead runs work as missions and slices, the unit this skill describes |
| `human-in-the-loop` | the lead routes real decisions to the operator rather than deciding alone |
| `messaging-the-human` | the lead is the seat that escalates and reports to the human |

### architect

| Skill | Why it is in the set |
| :--- | :--- |
| `queue-handoff` | named in the role text; decisions are handed on durably |
| `openrig-architect` | the role's own craft: authoring RigSpec/AgentSpec and topology content |
| `specification-system` | specs are the architect's deliverable form |
| `plan-review` | decisions must survive multi-perspective review before build |
| `topology-mutation-and-seat-management` | the architect changes a live rig rather than only drawing one |
| `agent-starters` | named per-seat starting points are what an architect publishes |

### planner

| Skill | Why it is in the set |
| :--- | :--- |
| `queue-handoff` | named in the role text; the plan is handed to the requester durably |
| `requirements-writer` | turning intake into an observable SPEC.md is the planner's output |
| `plan-review` | a plan is reviewed from strategy, design and engineering angles before build |
| `backlog-capture` | the planner captures incoming ideas before they become requirements |
| `mission-slice-sop` | planning happens in missions and slices under the lightweight SDLC |
| `exec-summary` | the planner orients leadership with a single-page summary |

### developer

| Skill | Why it is in the set |
| :--- | :--- |
| `test-driven-development` | named in the role text; the red-green loop is how the developer changes code |
| `queue-handoff` | named in the role text; durably handing the change to review |
| `verification-before-completion` | named in the role text; do not say done before running the checks |
| `context-engineering` | the developer must fill and prune the context window around the change |
| `specification-system` | implementation follows a spec, and this is how specs are authored/read |
| `development-team` | the pod skill for implementation/QA/design handoff inside a team |

### tester

| Skill | Why it is in the set |
| :--- | :--- |
| `test-driven-development` | named in the role text; the red-green loop when tests come first |
| `verification-before-completion` | the tester's whole job is verified completion, not claimed completion |
| `dogfood` | systematically exploring the real app is how the tester finds what tests miss |
| `agent-browser` | the tester drives the real UI, which needs browser automation |
| `review-team` | the tester works to the review boundary the pod skill defines |
| `queue-handoff` | findings are handed on durably rather than only reported in chat |

### debugger

| Skill | Why it is in the set |
| :--- | :--- |
| `systematic-debugging` | named in the role text; reproduce, hypothesise, root-cause before fixing |
| `refocusing` | a long hunt loses the product outcome without a refocus step |
| `agent-browser` | reproducing a UI defect needs browser automation |
| `dogfood` | the fastest reproduction is often exploratory use of the real product |
| `verification-before-completion` | a fix is not a fix until the checks are run and read |
| `context-engineering` | diagnosis is an evidence-gathering and pruning exercise |

### reviewer

| Skill | Why it is in the set |
| :--- | :--- |
| `review-team` | the reviewer's role boundary and what an authored review covers |
| `verification-before-completion` | the reviewer checks the claims, not the summary of them |
| `plan-review` | the reviewer reviews plans and requirements as well as code |
| `specification-system` | code is reviewed against the spec it implements |
| `dogfood` | review includes running the real thing, not only reading the diff |
| `queue-handoff` | review findings return durably to the author |

### researcher

| Skill | Why it is in the set |
| :--- | :--- |
| `queue-handoff` | named in the role text; findings are handed to the requester durably |
| `agent-browser` | reading live surfaces and citations needs browser automation |
| `context-builder` | distilling sources into background.md is the researcher's output |
| `verification-before-completion` | every claim is labelled verified/uncertain, which this skill enforces |
| `refocusing` | research drifts off the question without a refocus step |
| `messaging-the-human` | the researcher escalates what only the human can answer |

### writer

| Skill | Why it is in the set |
| :--- | :--- |
| `queue-handoff` | named in the role text; the finished document is handed to review durably |
| `context-builder` | a document is only as good as the context distilled for it |
| `exec-summary` | summary documents are a writer's standard output |
| `loading-addressable-markdown` | documents reference sections as path#slug, which this skill defines |
| `requirements-writer` | the writer authors SPEC.md-style documents from intake |
| `openrig-operating-model` | the writer must place a document correctly, which this skill decides |

## In the library but in no default set

Naming the remainder is what makes each default set a choice rather than everything. These
26 skills are available and a user adds them by hand:

- `agent-operated-software`
- `agent-operated-workflows`
- `agent-startup-and-context-ingestion`
- `applying-a-permission-policy`
- `claude-compaction-restore`
- `cross-host-rig-commands`
- `forming-an-openrig-mental-model`
- `frontend-design`
- `office-hours`
- `openrig-cmux`
- `openrig-herdr`
- `openrig-skills`
- `openrig-software-factory`
- `openrig-upgrade`
- `openrig-user`
- `orienting-to-an-inherited-seat`
- `oversight-team`
- `retiring-and-inheriting-a-seat`
- `rig-bundles-and-shareable-artifacts`
- `rig-lifecycle`
- `seat-continuity-and-handover`
- `session-compaction-and-restore`
- `session-source-fork`
- `software-for-agents`
- `ui-mockup`
- `watchdog`

## Provenance

Generated from the OpenRig repository HEAD at the time of writing; the 35 canonical skills
are mirrored to `packages/daemon/specs/agents/shared/skills/` upstream, and OpenRig guards its
own mirrors with pinned digests (`scripts/skill-edge-digests.generated.json`). This file applies
the same idea to the copy 4genthub seeds from.
