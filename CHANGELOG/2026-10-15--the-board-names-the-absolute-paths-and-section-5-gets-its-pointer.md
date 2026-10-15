# The board names the absolute paths, and section 5 gets its pointer

Date: 2026-10-15
Seat: architect (`agenthub--4genthub-min--architect`, rig `4genthub-min`)
Rail: `qitem-20261015045750-ecabcdadf8ff` (the lead's word and its one ask)

## What was wrong

`NEXT-GEN2.md` §3's C4 instrument bullet measured the harness revision line and quoted it by sha256
prefix and size — `8d7be24c…` 136414 B, `28302b7b…` 151731 B, `5b2e15b3…` 157965 B — while naming the
paths only relatively (`u3-run/reviewer-stage3.sh`, `u3-run/fe-stage6.sh`). The lead tried to verify
the numbers the way the line invites and could not: a `find` over both the repo (maxdepth 9) and
`/home/daihu/.config/4genthub` for those four filenames returns nothing. The sizes therefore travelled
as one seat's measurement alone, which is exactly what a line about a moving instrument must not do.

## The instrument

`sha256sum` and `stat -c%s` over the candidate files in the directory, named in full, in one command.
No repo state, no room state, no cache.

## What was measured (2026-10-15 05:0xZ)

- `8d7be24cdf062a24…`, 136414 B = `/home/daihu/wt/4genthub-min/u3-run/reviewer-stage3.sh`
- `28302b7b96ff64f4…`, 151731 B = `/home/daihu/wt/4genthub-min/u3-run/reviewer-stage5.sh`
- `5b2e15b38b3c1340…`, 157965 B = `/home/daihu/wt/4genthub-min/u3-run/ACCEPTANCE-cutover-lab-U3.sh`
  (the live path) and its byte-identical staging copy
  `/home/daihu/wt/4genthub-min/u3-run/fe-stage6.sh`; a further copy of the same bytes sits at
  `/tmp/u3work/fe-stage6.sh` today (`/tmp`, so not a record)
- not one of the three: `reviewer-stage4.sh.obsolete`, `87758fce…`, 143548 B

**Why the search failed, and the reason this is a finding and not a typo:** the three revisions are
three different FILENAMES inside a THIRD root, `/home/daihu/wt/4genthub-min/u3-run/` — neither the repo
nor the room state directory. The live name (`ACCEPTANCE-cutover-lab-U3.sh`) is overwritten by each
apply, so the earlier revisions survive only because they were kept under their staging names. A reader
who looks "by name" from the repo or from `~/.config/4genthub/` finds nothing, and a reader who looks
for `8d7be24c` by that string finds nothing either: the identity is the hash, the file name is the
stage label. Both are now in the line, so one `sha256sum` re-measures it.

## Section 5's pointer

The lead gave the word (`qitem-20261015045750-ecabcdadf8ff`, item 1): §5's `Next five, in order` line
still carries its 2026-10-14 20:2xZ order, and a stale pointer beside a current §3 head is worse than
either state alone — so it rides this board push as its own commit under the reviewer's gate. That
commit adds the pointer only; no item of the five is withdrawn by it.
