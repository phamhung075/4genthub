## Guide: skills-dev (skill library)

**You own NEXT_GEN F1:** bringing OpenRig's skill library into the cloud as published blocks. This is content work with a digest guard, not a code port.

### Tools you use, and for what
- `read`/`find`/`grep` over the two source edges: `openrig/skills/_canonical/` (35 skills) and `openrig/packages/daemon/assets/plugins/openrig-core/skills/` (19 skills; the only edge with `delegating-work` and `queue-handoff`). The two overlap by two names, so the union is **52**.
- `bash` for the publish and digest commands; `deepseek_agent` for reading and summarising batches of skills in parallel (give each worker a disjoint list).
- 4genthub tools: the common loop; record the digest and counts in `manage_context`.

### Workflow
1. Task first. List both edges and compute the union yourself; the number must be 52 before you publish.
2. Publish each skill as a block of the right kind; the tool kind's content rule is parsed by the renderer, so a publish the renderer cannot read is refused. Fix the content, not the rule.
3. Digest guard: compare what you published against the committed source, never against a rebuilt tree.
4. Complete the task with the counts (published, skipped, why) and the commit hash; tell the lead.

### Do not
Read `openrig/packages/daemon/context-packs/` (gitignored, assembled at package time). Treat a count you did not recompute as true.
