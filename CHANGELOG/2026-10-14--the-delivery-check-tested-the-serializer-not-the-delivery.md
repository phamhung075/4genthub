# The delivery check tested the serializer, not the delivery

## What was wrong
The lead's send-verification instrument decided whether a message had landed by grepping the
**recipient's** transcript for a marker inside a JSON entry, and it looked for the **spaced** form:

```
grep -F -- "$MARK" "$tr" | grep -q '"role": "user"'
```

The transcript writes **compact** JSON. Measured in go-dev's transcript:
`grep -c '"role":"user"'` → **16**; `grep -c '"role": "user"'` → **0**. The pattern could therefore
never match, so **every send was judged "refused/dropped"**, and the loop re-sent messages that had
already landed.

Two consequences, both on the record before they were understood:
1. **Seven duplicate arrivals of one body.** Body sha256 `10a812bba32810b2…`, 2734 chars, received at
   `20:28:42.236Z`, `20:29:42.255Z`, `20:30:12.283Z`, `20:30:42.322Z`, `20:31:12.359Z`, `20:31:42.392Z`,
   `20:32:12.415Z` — one per re-send window, each one a send the instrument had called a failure.
   The recipient (go-dev) caught it, not the sender: **the evidence lives only in the receiving
   transcript**, and a job that "lands" identically on every attempt is not credible.
2. **Every rate figure drawn from this instrument is void.** An earlier form of the same check also
   produced false **"already present"** landings, by using as its marker a hash the recipient had
   printed itself. So the evening's numbers about sending in both directions ("9 of 10 sends dropped",
   "two replies never landed") are products of a broken detector, not measurements of the channel.

## Evidence
- go-dev's transcript: 7 inbound copies of that body, timestamps above; the sender's own transcript shows
  **no** duplicate bodies (11 inbound messages, all distinct), which is exactly why the sender could not
  see its own duplicate from its own side.
- The job logs for the two delivery loops: `attempt N: refused/dropped (send rc=0 :: Sent to
  agenthub--4genthub-min--go-dev)` for sends that had, in fact, landed.
- The predicate, dry-tested after the fix against that same transcript: mark `22696` → **8 entries**
  (LANDED); a fabricated marker → **0**; the old spaced pattern → **0** (the defect, reproduced).

## Fix
- **The detector is a JSON reader, not a grep**: it parses each line and accepts only `type=message` with
  `message.role=user` whose text **begins with a sender envelope**, then searches *that entry's* text for
  the marker. No substring elsewhere in the file (the recipient's own `sha256sum`/`wc -c` output lives in
  `toolResult` entries) can count as a delivery.
- **It refuses to send at all when the marker is not a literal substring of the body.** The second lie
  was a marker: `"three arrivals, not two"` against a body that says `"THREE arrivals, not two"` — a
  correct detector would still have re-sent a landed message. The check now runs before the first send.
- The runaway loops were killed (two concurrent `deliver-to-godev.sh` processes, ~4 minutes of repeating
  sends) and nothing was re-sent after `20:32Z`.

## Rules this defect produced
1. **A delivery check written as a string pattern against another program's file tests that program's
   serializer, not the delivery.** Parse, or state the form you matched.
2. **A re-send loop with a broken detector manufactures the duplicates it reports.**
3. **The rail is the durable channel.** Every row it carried arrived; the chat sends both dropped and
   duplicated. Anything that must not be lost goes on the rail, and the fix above is what makes the
   chat channel's own confirmation trustworthy again.

## Limits
- The fixed instrument is verified by a **dry predicate test** against a real transcript (known-present
  and known-absent markers), and its first live use **immediately afterwards** did what the broken version
  could not: the message to `architect` reported **`LANDED on attempt 1 (check 1)`** — one send,
  detected on the first 3-second check, no re-send. That single line is also the direct refutation of the
  window theory: with a detector that matches, a landing is visible within seconds, so the earlier
  seven-copy storm was never a latency problem.
- The body-hash dedupe adopted from go-dev (skip a body already answered, `/tmp/lead-answered-bodies.txt`)
  is a **reading** rule only: a body sha must never serve as a **delivery marker**, because the lead's own
  outgoing text sits in the lead's own transcript — the same trap in a new place.
