# The pin carries the code-edit target move, and its record awaits a carrier

The hub's gitlink moves db06fed -> a4bacb1: the report-metric lane 9c9f4f8 (gated PASS,
qitem-20261017065832-8b4120f5f3ba), with the post-gate comment commit a4bacb1 on top, fast-forwarded.
The code-edit target now holds the two editing seats (> 40% each for go-dev and fe-dev, reported on
their own lines), the room line prints as diagnostic and never PASS/FAILs, a turn counts as code-edit
when ANY of its calls edits code (the first-tool-call reading is kept for comparison), and the report
reads the room spec to know which seats are developer seats. Decision:
seats/architect/RULING-code-edit-share-target.md. At the merged tip: go test -count=1 ./... 32
packages rc 0; `4genteam room report 4genthub-min --since 1h` prints the two per-seat targets, the diag
room line, and both readings (any-call 12.9%, first-call 12.0%).
