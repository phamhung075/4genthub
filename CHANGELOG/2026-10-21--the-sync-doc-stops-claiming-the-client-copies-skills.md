# The sync doc stops claiming the client copies a seat's skills

Task: none - a ruling the architect handed the lead (row `qitem-20261021153745-eac1fb7c60da`).

`ai_docs/operations/syncing-seats-with-the-cloud.md:69-74` said, present tense, that before each restart the
client replaces the omp seat's own skill directory with the skills the room root holds for that seat, "because
nothing else copies them there". That is false: `clientseat/deliverSkills` is deleted and the runtime installs a
seat's skills at every start (`install_seat_skills`, in `rust/agenthub-runtime/src/supervisor/mod.rs`), so the
document now carries the skill copy in the past tense with a dated note, and names the runtime as the writer.

The paragraph comes from the parked branch `4genthub-min/pin-and-the-two-sentences` (`54d0164c`), whose hunk no
longer applies (its context named the `rig` root, main the `room` root); its `AGENTS.md` half is superseded by
main's newer §2 and did not land.
