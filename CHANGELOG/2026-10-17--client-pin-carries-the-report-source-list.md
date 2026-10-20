# The pin carries the report's fifth source name

The hub's gitlink moves a4bacb1 -> 06ab07a: the help-text delta the reviewer confirmed PASS on the report
lane (reviewer delta 07:01Z, qitem-20261017070052). reportUsage said "Five sources" and listed four; the
paragraph now names the room's spec.json, which says which seats are developer seats and so which carry the
code-edit target. One hunk; gofmt clean, go test -count=1 ./... rc 0, and `4genteam room report --help`
prints the five-source list. Code sha unchanged at 9c9f4f8.
