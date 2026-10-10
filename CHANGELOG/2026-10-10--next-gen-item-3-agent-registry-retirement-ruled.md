# 2026-10-10 — NEXT_GEN records the item-3 ruling: the agent registry retires and seats are the only identity

### Changed
- `agenthub_go/NEXT_GEN.md` (Checklist): one new item records the lead's ruling. `manage_agent`, the `agents` table and the 32-role registry retire, and `@<seat_key>` is the only assignee identity. Dropping only the `call_agent` field was rejected. The item carries the premise correction: `call_agent` has been absent since T6, and no production table is in the Python format. It also records who runs each step; the production `DROP TABLE agents` is the principal's under the owner's push approval.

Docs only; no code or tests changed.
