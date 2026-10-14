## The decision ladder (seat, lead, owner) is added to NEXT-GEN2

### Added

- `NEXT-GEN2.md` Group C, item **C6**: a seat decides itself at Jev confidence of 0.8 or more, else asks the
  lead with its recommendation; the lead decides at 0.8 or more, else asks the owner. The owner tier already
  exists (`room_decisions`, `jev-1.13.0`, `JEV_DECISION_THRESHOLD`); C6 adds the two lower tiers.
- Owner ruling recorded: credentials and tokens, spend, and the omp cap always reach the owner whatever the
  confidence. Below 0.8 a question escalates one level with its recommended option. Built by the lead after C3.

### Notes

- Documentation only; no code written. The edit was scripted because the hook reads an edit of an existing
  root file as a creation.
