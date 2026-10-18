# The pin carries the human's reply hint, and its record awaits a carrier

The hub's gitlink moves `6667de3 -> 81d2bdb` (hub pin, gitlink only): a fast-forward of
`4genthub-min/comm-guard-unaudited-routes`, whose tip is the merge `81d2bdb` (reply-hint `1801abd` +
main `6667de3`, both kept).

Client `1801abd` `fix(send): the reply hint names the rail for a human, not a send that refuses`: a send
addresses a runtime session, and a human has none, so `replyLine` for a `human@kernel` sender now emits
the rail row command for `agenthub--<room>--lead`, deriving the room from the recipient (`<room>` when
unreadable); a blank sender gets no command, and `@external` and session labels keep their lines.
`HumanSender` moves to `clientruntime`. Tests: `TestTheReplyHintNamesOnlyRoutesThatReachTheSender` plus the
clientsync delivery seam (`internal/clientruntime/sendline_test.go`,
`internal/clientsync/messagesverb_test.go`).

Reviewer PASS at `81d2bdb` (`qitem-20261017075041`): all 32 client packages pass
`go test -count=1 ./...`, `go vet ./internal/...` rc 0. Lead's own smoke at the same sha:
`go test -count=1 ./internal/clientsync ./internal/clientruntime` rc 0; the landing diff is the lane's
5 files (+121/-11). Nothing pushed.
