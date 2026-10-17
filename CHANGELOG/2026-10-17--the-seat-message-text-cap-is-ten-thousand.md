## 2026-10-17 — the seat message text cap is ten thousand

### Changed
- `agenthub_go/fastmcp/seat_management/application/services/seat_message_service.go`: `SeatMessageMaxText`
  2000 → 10000. The owner's send to a seat was refused at 2000 characters (07:30Z, rail row
  `qitem-20261017073214-9e74e1f65ff6`), so the one bound the message path applies moves; the store column is
  TEXT and no migration is involved.
- The const's comment said the bound IS the friction channel's own, so the two seat-keyed channels could not
  answer differently. That is no longer true and the comment now says so: the message path moved and the
  friction channel (`SeatFeedbackMaxText`, and the `maxLength` its tool schema renders) did not.

### Tested
- `go test -count=1 ./fastmcp/seat_management/...` — every package ok. The refusal case
  (`TestSeatMessageSendRefusesBadNamesAndBadText`, "text past the bound") derives its input from the const
  (`strings.Repeat("x", SeatMessageMaxText+1)`) rather than a literal, so it follows the move and passes
  unchanged; no test was edited.
- Measured for the "one cap" claim before the change: the message controller renders no `maxLength`, and the
  only `maxLength` in the seat controllers is the friction channel's (`submit_feedback_controller.go`, from
  `SeatFeedbackMaxText`); no client cap, no frontend `maxLength`, stream limit 1 MB, `seat_messages.text` TEXT.

### Notes
- The deploy is the owner's: the cap is live only after the hub is rebuilt and restarted.
