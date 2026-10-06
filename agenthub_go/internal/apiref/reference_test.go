package apiref

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// sampleMountFile is a mount file in the shape the extractor reads: a named handler with a doc
// comment, an inline closure with no name, a path parameter, and a method-less registration.
const sampleMountFile = `package httpapp

// handleThing answers one thing.
// It is documented, so the route carries that text.
func handleThing(w http.ResponseWriter, r *http.Request) {}

func mountSample(mux *http.ServeMux) {
	mux.HandleFunc("GET /api/v1/things/{thing_id}", handleThing)
	mux.HandleFunc("POST /api/v1/things", func(w http.ResponseWriter, r *http.Request) {})
	mux.HandleFunc("/api/v1/legacy", handleThing)
}
`

func writeSampleMount(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "sample_mount.go"), []byte(sampleMountFile), 0o644); err != nil {
		t.Fatal(err)
	}
	return dir
}

// TestRoutesInSourceReadsTheShapesWeDependOn pins the four things the artefact claims about a route:
// the method and the pattern exactly as registered, the parameters from the pattern, the handler name
// when the mount names a function, and the doc comment when that function has one. The closure is the
// case worth pinning: an empty handler is a FACT about the source, not missing data.
func TestRoutesInSourceReadsTheShapesWeDependOn(t *testing.T) {
	routes, err := routesInSource("sample_mount.go", []byte(sampleMountFile))
	if err != nil {
		t.Fatalf("routesInSource: %v", err)
	}
	if len(routes) != 3 {
		t.Fatalf("routes = %d, want 3: %+v", len(routes), routes)
	}
	byPath := map[string]RouteEntry{}
	for _, route := range routes {
		byPath[route.Path] = route
	}
	named, ok := byPath["/api/v1/things/{thing_id}"]
	if !ok {
		t.Fatalf("the parameterised route is missing: %+v", routes)
	}
	if named.Method != "GET" || len(named.PathParams) != 1 || named.PathParams[0] != "thing_id" {
		t.Errorf("parameterised route = %+v, want GET with the thing_id parameter", named)
	}
	if named.Handler != "handleThing" || !strings.Contains(named.Description, "documented") {
		t.Errorf("named handler = %+v, want the name and its doc comment", named)
	}
	closure := byPath["/api/v1/things"]
	if closure.Handler != "" || closure.Description != "" {
		t.Errorf("closure route = %+v, want an empty handler and description", closure)
	}
	legacy := byPath["/api/v1/legacy"]
	if legacy.Method != "" {
		t.Errorf("method-less registration = %+v, want an empty method", legacy)
	}
}

// TestEntriesRefusesAnEmptySurface is the second guard's own test: pointing the producer at input that
// yields nothing must REFUSE, because a module that asserts the platform mounts nothing is worse than
// no module. Both directions are covered: no mount file at all, and a mount file that registers no
// routes.
func TestEntriesRefusesAnEmptySurface(t *testing.T) {
	if _, err := Entries(t.TempDir()); err == nil {
		t.Fatal("Entries refused nothing for a directory with no mount file")
	}
	dir := t.TempDir()
	empty := "package httpapp\n\nfunc mountNothing(mux *http.ServeMux) {}\n"
	if err := os.WriteFile(filepath.Join(dir, "nothing_mount.go"), []byte(empty), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := Entries(dir); err == nil {
		t.Fatal("Entries refused nothing for a mount file that registers no route")
	}
}

// TestRenderModuleRefusesAnEmptyReference pins the same rule one layer down, where it protects the
// disk rather than the caller: the renderer refuses, so WriteModule cannot write an artefact that
// says the platform has nothing.
func TestRenderModuleRefusesAnEmptyReference(t *testing.T) {
	cases := map[string]Reference{
		"no routes": {Tools: []ToolEntry{{Name: "t", Parameters: map[string]any{}}}},
		"no tools":  {Routes: []RouteEntry{{Method: "GET", Path: "/x"}}},
		"neither":   {},
	}
	for name, reference := range cases {
		t.Run(name, func(t *testing.T) {
			if _, err := RenderModule(reference); err == nil {
				t.Fatal("an empty reference rendered instead of refusing")
			}
			path := filepath.Join(t.TempDir(), "apiReference.ts")
			if err := WriteModule(path, reference); err == nil {
				t.Fatal("WriteModule wrote an empty reference")
			}
			if _, err := os.Stat(path); err == nil {
				t.Fatal("an empty reference reached the disk")
			}
		})
	}
}

// TestRenderModuleImportsThePageTypeAndExportsData pins the artefact's shape: it imports the type from
// src/types (the page owns it), exports ONE const, and its body is the reference verbatim.
func TestRenderModuleImportsThePageTypeAndExportsData(t *testing.T) {
	reference := Reference{
		Routes: []RouteEntry{{Method: "GET", Path: "/api/v1/things/{id}", PathParams: []string{"id"}, Handler: "handleThing"}},
		Tools:  []ToolEntry{{Name: "manage_thing", Description: "does a thing", Parameters: map[string]any{"type": "object"}, Actions: []string{"list"}}},
	}
	module, err := RenderModule(reference)
	if err != nil {
		t.Fatalf("RenderModule: %v", err)
	}
	text := string(module)
	if !strings.Contains(text, `import type { ApiReference } from "../types/apiReference";`) {
		t.Errorf("the module does not import the page type:\n%s", text)
	}
	if strings.Count(text, "export const") != 1 || !strings.Contains(text, "export const apiReference: ApiReference =") {
		t.Errorf("the module does not export exactly one typed const:\n%s", text)
	}
	body := text[strings.Index(text, "= ")+2:]
	body = strings.TrimSuffix(strings.TrimSpace(body), ";")
	var roundTrip Reference
	if err := json.Unmarshal([]byte(body), &roundTrip); err != nil {
		t.Fatalf("the module body is not the reference: %v\n%s", err, body)
	}
	if len(roundTrip.Routes) != 1 || roundTrip.Routes[0].PathParams[0] != "id" || roundTrip.Tools[0].Actions[0] != "list" {
		t.Errorf("the module body lost data: %+v", roundTrip)
	}
}
