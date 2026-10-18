# Pin: the client names the replay rule and the login refusal (client 5582628)

The hub gitlink moves `2ffd265 -> 5582628`, which carries three landed client changes:

- `cb7e81f` - a 409 stops the completion, an identical replay is the hub's 200. The amended head of
  the complete-failure surface; the 2ffd265 "continue once" branch is gone.
- `b266f0f` - the clientroom dispatched-verb test clears its ambient `AGENTHUB_ROOM`, so the suite is
  green in a seat shell as well as outside one.
- `5582628` - the merge that carries both above `2ffd265`.

Hub side landed first, as the architect's ruling requires: `0824c331` (an identical replay answers
200 with the stored entry) is on hub main, merged as part of `19d4f43c`.

Measured at this pin: `AGENTHUB_ROOM=4genthub-min go test ./... -count=1` in `agenthub_client` - rc 0;
`env -u AGENTHUB_ROOM go test ./internal/clientroom/` - ok.
