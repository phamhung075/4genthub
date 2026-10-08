// Package clientsync is the sync half of agenthub-client: pull, rig, bundle, switch, status and watch,
// ported test-for-test from agenthub_main/src/tests/scripts/test_openrig_seat_sync.py. Those Python
// tests are the parity spec, so a verb here is done when the Go tests assert WHAT THEY ASSERT, not when
// the Go tests pass.
//
// The pinned-snapshot rules are the part that must not soften: a seat's snapshot is pinned by hash and
// a pull never falls back to a different one.
package clientsync

import (
	"context"
	"fmt"
	"io"

	"agenthub/internal/clientcmd"
)

// Commands is what the dispatcher registers from this package. One entry per package keeps main.go
// thin and keeps this package's surface a single thing to review.
func Commands() []clientcmd.Command {
	return []clientcmd.Command{syncCommand{}}
}

// syncVerbs are the verbs this package answers under `sync`. Each is ported test-for-test; until one
// is, it REFUSES BY NAME rather than answering something plausible, which is the same rule the platform
// matrix follows.
var syncVerbs = []string{"status", "pull", "rig", "bundle", "switch", "watch", "connector"}

type syncCommand struct{}

func (syncCommand) Name() string    { return "sync" }
func (syncCommand) Summary() string { return "pull and inspect resolved seats (" + verbList() + ")" }
func (syncCommand) NeedsRig() bool  { return false }

func (syncCommand) Run(ctx context.Context, _ *clientcmd.Rig, args []string, stdout, stderr io.Writer) int {
	if len(args) == 0 {
		fmt.Fprintf(stderr, "agenthub-client sync: pick a verb: %s\n", verbList())
		return clientcmd.ExitUsage
	}
	// status and pull are ported: status compares each seat's local pin with the cloud's hash, and pull
	// writes the snapshot and moves the pin.
	switch args[0] {
	case "status":
		return RunStatusVerb(ctx, args[1:], stdout, stderr)
	case "pull":
		return RunPullVerb(ctx, args[1:], stdout, stderr)
	case "connector":
		return RunConnectorVerb(ctx, args[1:], stdout, stderr)
	}
	want := args[0]
	for _, verb := range syncVerbs {
		if verb != want {
			continue
		}
		fmt.Fprintf(stderr,
			"agenthub-client sync %s: not ported into the Go client yet, so openrig_seat_sync.py is still "+
				"the authority for it. This build refuses rather than doing something weaker.\n", want)
		return clientcmd.ExitUnavailable
	}
	fmt.Fprintf(stderr, "agenthub-client sync: unknown verb %q; the verbs are %s\n", want, verbList())
	return clientcmd.ExitUsage
}

func verbList() string {
	out := ""
	for i, verb := range syncVerbs {
		if i > 0 {
			out += ", "
		}
		out += verb
	}
	return out
}
