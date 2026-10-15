## Seat friction loop — design (step 1)

### Added
- `ai_docs/operations/seat-friction-loop.md`: the dedupe of the owner's 7-skill friction loop against the 16 skills
  on disk. Verdicts: `share/friction-report` **EXTEND** — the friction channel already ships end-to-end
  (`submit_feedback` MCP + `4genteam feedback` -> `POST /api/v2/feedback`, closed `layer` vocabulary, owner
  reads by layer; `internal/clientfeedback/feedback.go`); `share/self-check-while-working` **MERGE** — worktree,
  branch, changelog, tests and skills each already have an owner, including the `F1`-`F5` launch check (specified,
  not yet landed); `lead/friction-triage`, `lead/architect-ecosystem-review`, `architect/system-improvement-analysis`,
  `lead/autonomy-charter` and `reviewer/improvement-review` are **NEW** (the charter is owner-gated).
- Also records: each skill's level in the `share/` / `rooms/<room>/` / `rooms/<room>/<seat>/` tree; the report ->
  triage -> fix -> close routing (reusing the queue, the feedback channel and the reviewer verdict path); the triage
  rules; the lead+architect review inputs and cadence; the owner digest shape (capped at the top 3); the cost rules;
  and the open decisions split into lead-ratify versus owner-only.

### Impact
- Documentation only. No skill text, no code, no board task. Design for the lead to ratify (step 2).
