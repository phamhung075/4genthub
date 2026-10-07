// Command apirefgen writes the generated API reference the docs page renders.
//
// IT IS THE ONLY CALLER OF apiref.WriteModule, and that is the point of having a command: the package
// can render a reference, but until something writes it into agenthub-frontend/src/docs the artefact
// does not exist and the page has nothing real to show.
//
// It refuses with a non-zero exit when the reference cannot be produced, and NOTHING IS WRITTEN in
// that case: no routes or no tools is a failure rather than a file, because a module asserting that
// the platform has nothing is worse than no module. Run it from agenthub_go:
//
//	go run ./cmd/apirefgen
//
// The invocation is deliberately not hidden behind go:generate: a generator that writes into a
// different tree is a step a reader should see named when it runs.
package main

import (
	"flag"
	"fmt"
	"io"
	"os"

	"agenthub/internal/apiref"
)

// defaultMountDir is the SEED directory of the route walk: the *_mount.go files live here, and the walk
// follows each RegisterRoutes call from them into the package that owns it, so this path is where the
// reading starts rather than the whole scope it covers.
const defaultMountDir = "fastmcp/server/httpapp"

// defaultOut is the artefact the page imports. It must live inside agenthub-frontend, because the
// production image copies only that tree.
const defaultOut = "../agenthub-frontend/src/docs/apiReference.ts"

func main() {
	mountDir := flag.String("mount-dir", defaultMountDir, "SEED directory of the route walk (the *_mount.go files; the packages they mount routes from are followed too)")
	out := flag.String("out", defaultOut, "the TypeScript module to write")
	flag.Parse()

	if code := run(*mountDir, *out, os.Stderr); code != 0 {
		os.Exit(code)
	}
}

// run is the whole command, with stderr passed in so a refusal is testable without exiting.
func run(mountDir, out string, stderr io.Writer) int {
	reference, err := apiref.Entries(mountDir)
	if err != nil {
		_, _ = fmt.Fprintf(stderr, "apirefgen: %v\n", err)
		return 1
	}
	if err := apiref.WriteModule(out, reference); err != nil {
		_, _ = fmt.Fprintf(stderr, "apirefgen: %v\n", err)
		return 1
	}
	_, _ = fmt.Fprintf(stderr, "wrote %s: %d routes, %d tools\n",
		out, len(reference.Routes), len(reference.Tools))
	return 0
}
