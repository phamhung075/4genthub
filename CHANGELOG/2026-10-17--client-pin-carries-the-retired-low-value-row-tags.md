# The pin carries the retired low-value row tags, and its record awaits a carrier

The hub's gitlink moves `7e01b65 -> 2a316a0` (hub pin `b3e4db1e`, gitlink only). Client `2a316a0`
`feat(rail): the four low-value row tags retire, and the refusal names the list`: the allowed set is now
14 tags, and a refused tag's message names the list instead of the word "invalid" alone. Tests:
`internal/clientroom/queue_test.go` (+23) pins the refusal and the count; `internal/clientruntime/queue.go`
and `rust/agenthub-runtime/src/queue/mod.rs` carry the set. On client main through `61fce91`. Nothing
pushed; the push is the owner's.
