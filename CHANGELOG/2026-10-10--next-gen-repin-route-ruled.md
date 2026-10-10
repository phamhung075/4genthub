# 2026-10-10 — NEXT_GEN records the re-pin ruling for the guide-common rollout

### Changed
- `agenthub_go/NEXT_GEN.md` (Checklist, guide-common item): the lead ruled R1. A new `PUT /api/v2/openrig/rooms/{room}/seats/{seat}/pin` route re-pins existing seats, and it ships with seedVersion 1.4.2. DELETE + re-create was rejected. This change does not gate the 0.0.35 board-fix push.

Docs only; no code or tests changed.
