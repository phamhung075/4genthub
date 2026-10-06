package apiref

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// Reference is the whole generated surface: every mounted route and every advertised MCP tool.
//
// The shape is web-dev's type in agenthub-frontend/src/types/apiReference.ts; this struct is the Go
// side of that one definition, and the emitted module imports the type rather than declaring one.
type Reference struct {
	Routes []RouteEntry `json:"routes"`
	Tools  []ToolEntry  `json:"tools"`
}

// Entries is THE PRODUCER: the routes read from the mount directory and every package it mounts
// routes from, plus the tools read by calling the server's own builder. The drift test is the WITNESS
// and must read the code independently rather than call this - see the package doc.
//
// AN EMPTY RESULT IS A FAILURE, NOT A DOCUMENT. Zero routes or zero tools returns an error and no
// value, because a module that says the platform mounts nothing or offers no tools is worse than no
// module at all: it asserts a fact that the failure of an instrument can produce. That is the second
// layer, and it holds whatever the first one did - a mount directory that moved, a parse that matched
// nothing and a registry that was never composed all reach this point as nothing.
func Entries(mountDir string) (Reference, error) {
	routes, err := routesFromTree(mountDir)
	if err != nil {
		return Reference{}, err
	}
	if len(routes) == 0 {
		return Reference{}, fmt.Errorf(
			"no routes were found in %s, so the reference cannot be generated: an artefact with no "+
				"routes would assert that this server mounts nothing", mountDir)
	}
	tools, err := toolsFromServer()
	if err != nil {
		return Reference{}, err
	}
	if len(tools) == 0 {
		return Reference{}, fmt.Errorf(
			"no MCP tools came back, so the reference cannot be generated: an artefact with no tools " +
				"would assert that this server offers none")
	}
	return Reference{Routes: routes, Tools: tools}, nil
}

// RenderModule renders the artefact: one typed TypeScript module for agenthub-frontend/src/docs.
//
// DATA, NOT A DEFINITION. The module exports ONE const and imports its type from src/types, which is
// the page's own file: the generator declares no type, because two definitions of one concept let the
// artefact drift from the page silently.
func RenderModule(reference Reference) ([]byte, error) {
	if len(reference.Routes) == 0 || len(reference.Tools) == 0 {
		return nil, fmt.Errorf(
			"refusing to render an empty reference: %d routes and %d tools (an artefact that asserts "+
				"the platform has nothing is worse than no artefact)",
			len(reference.Routes), len(reference.Tools))
	}
	body, err := json.MarshalIndent(reference, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("cannot encode the reference: %w", err)
	}
	header := strings.Join([]string{
		"// GENERATED - do not edit by hand.",
		"//",
		"// Produced by agenthub/internal/apiref from the running code: every mounted route read from the",
		"// *_mount.go source text, and every MCP tool read by calling the server's own builder, so an",
		"// entry reaches this file only because it reaches the wire.",
		"//",
		"// THE DRIFT TEST IS THE WITNESS and reads the code independently; if this file and the code",
		"// disagree, the artefact is wrong rather than the test.",
		"",
		"import type { ApiReference } from \"../types/apiReference\";",
		"",
		"export const apiReference: ApiReference = ",
	}, "\n")
	return []byte(header + string(body) + ";\n"), nil
}

// WriteModule writes the artefact, and it is the only writer: it renders FIRST and writes nothing when
// rendering refuses, which is what keeps an empty reference off the disk rather than merely out of the
// return value.
func WriteModule(path string, reference Reference) error {
	module, err := RenderModule(reference)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return fmt.Errorf("cannot create %s: %w", filepath.Dir(path), err)
	}
	if err := os.WriteFile(path, module, 0o644); err != nil {
		return fmt.Errorf("cannot write %s: %w", path, err)
	}
	return nil
}
