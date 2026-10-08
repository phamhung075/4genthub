// Command blockdrift runs the seed library's block-provenance check against a repository tree.
//
// WHY IT EXISTS: seedlibrary.CheckBlockDrift had NO caller outside its own tests — every test call
// passes a temporary directory — so the pairing between the library blocks, the lock and the interim
// source files was asserted against a synthetic copy and never measured against a tree. A check that
// nothing runs is a check that cannot fail, which is the failure this whole provenance family exists
// to prevent. A block that is hand-edited in one copy and not the other is exactly the silent
// divergence the one-source property forbids, and nothing else in the tree compares the two copies.
//
// WHAT A GREEN RUN MEANS, AND WHAT IT DOES NOT — the two halves differ, and a reader who takes them
// as one instrument will believe more than the run shows:
//
//   - the MIGRATION half is anchored in guides.lock.json and is meaningful in ANY tree: the lock
//     records the digest each interim file had when the block was copied out of it, so a hand-edit to
//     ai_docs/operations/seat-guides/* is visible even here.
//   - the LIBRARY half compares the tree's block files against the bytes EMBEDDED in this binary.
//     Under `go run` from the build tree the rebuild makes those bytes identical and it reports
//     nothing — a thing compared to its own shadow. It is meaningful only for a binary pointed at a
//     tree it was not built from.
//
// SOURCE-GONE IS NOT A FAILURE. After the migration deletes the interim files an absent source is the
// intended state, and CheckBlockDrift reports it in the same slice as a real divergence. Treating it
// as a failure would produce a check that can never pass again — a gate somebody has to disable,
// which is worse than having no gate. It is counted and printed, and it does not set the exit status.
//
// Exit status is the contract a hook reads: 0 nothing diverges, 1 a divergence, 2 usage, 3 the check
// could not run at all (a root that does not hold the library is a refusal, not a pass).
//
// The root is REQUIRED and is never guessed: a check that picks its own root can silently examine the
// wrong tree, and the library's own refusal would then be the only thing standing between a wrong
// root and a clean bill.
//
// Run it from agenthub_go:
//
//	go run ./cmd/blockdrift -root ..
package main

import (
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"agenthub/fastmcp/seat_management/domain/seedlibrary"
)

const usage = `blockdrift - check the seed library's blocks against the tree and the lock

    blockdrift -root <repository root>

	-root   the repository root that holds agenthub_go/ (required). The block paths in the library
	        and in guides.lock.json are recorded against that root.`

func main() {
	root := flag.String("root", "", "repository root holding agenthub_go/ (required)")
	flag.Usage = func() { _, _ = fmt.Fprintln(os.Stderr, usage) }
	flag.Parse()

	if strings.TrimSpace(*root) == "" {
		_, _ = fmt.Fprintln(os.Stderr, "blockdrift: -root is required; "+strings.SplitN(usage, "\n", 2)[0])
		_, _ = fmt.Fprintln(os.Stderr, usage)
		os.Exit(2)
	}
	os.Exit(run(*root, os.Stdout, os.Stderr))
}

// run is the whole command, with its writers passed in so both the report and the refusal are
// testable without exiting.
func run(root string, stdout, stderr io.Writer) int {
	abs, err := filepath.Abs(root)
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "blockdrift: %v\n", err)
		return 3
	}

	table, err := seedlibrary.BlockProvenanceTable()
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "blockdrift: the library cannot describe itself: %v\n", err)
		return 3
	}

	divergences, err := seedlibrary.CheckBlockDrift(abs)
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "blockdrift: %v\n", err)
		return 3
	}

	failures, gone := partition(divergences)
	for _, d := range gone {
		_, _ = fmt.Fprintf(stdout, "expected: %s\n", d)
	}
	for _, d := range failures {
		_, _ = fmt.Fprintf(stdout, "divergence: %s\n", d)
	}
	if len(failures) > 0 {
		_, _ = fmt.Fprintf(stderr,
			"blockdrift: %d divergence(s) under %s — one edit reached one copy and not the other\n",
			len(failures), abs)
		return 1
	}
	_, _ = fmt.Fprintf(stdout,
		"blockdrift: %d block(s) in step under %s; %d source file(s) already gone (expected after the migration)\n",
		len(table), abs, len(gone))
	return 0
}

// partition splits what CheckBlockDrift returns into the states that are a failure and the one that
// is not. It is a function rather than a branch inside run so the distinction can be asserted
// directly: `source-gone` is the intended state after the migration and every other problem is a
// divergence, and a caller that conflates them has a gate that fails forever.
func partition(divergences []seedlibrary.BlockDivergence) (failures, gone []seedlibrary.BlockDivergence) {
	for _, d := range divergences {
		if d.Problem == "source-gone" {
			gone = append(gone, d)
			continue
		}
		failures = append(failures, d)
	}
	return failures, gone
}
