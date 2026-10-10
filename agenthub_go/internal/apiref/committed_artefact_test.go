package apiref_test

// THIS FILE GATES THE COMMITTED ARTEFACT, and it exists because nothing else did.
//
// THE GAP, MEASURED: the artefact agenthub-frontend/src/docs/apiReference.ts is consumed by the page,
// and the only Go code that NAMED it was the writer (cmd/apirefgen/main.go's defaultOut), a comment in
// reference.go, and reference_test.go:103 - which renders into t.TempDir() and therefore never reads
// the file on disk. The drift witness in docs_page_drift_test.go is a real check, but BOTH OF ITS SIDES
// COME FROM THE CODE: its own walk of the mount files against apiref.Entries, the producer. It proves
// the producer agrees with an independent extractor; it cannot see whether the committed file matches
// either of them, because it never opens it. So a stale artefact would be served to users with every
// test green - and the note in agenthub-frontend/src/docs/api-reference-prose.en.md asserting that
// reference_test.go checks the artefact is describing an intent this file now implements.
//
// WHY THE COMPARISON IS STRUCTURAL RATHER THAN TEXTUAL, which is the trap the same note records: the
// artefact is compared entry by entry against the producer's own output, so NO path is ever normalised
// or matched as a substring. That matters twice over. `{$}` is Go's end-anchor for a trailing slash and
// not a parameter, so a normaliser rewriting `{...}` would report /api/v2/branches/{$} as missing while
// the tables are right; and a path parameter absorbs a literal segment, so
// /api/v2/openrig/seats/{room}/{seat} also serves /api/v2/openrig/seats/{room}/messages. A gate built
// on either would be red on correct code and would be disabled rather than fixed.
//
// AND WHY IT COMPARES AGAINST THE PRODUCER RATHER THAN A SECOND EXTRACTOR: this is not the witness.
// The witness's job is to disagree with the producer by reading the code its own way, and it does that.
// This gate's job is the different one the producer cannot do for itself - to say whether the FILE the
// frontend imports is the file the producer would write today - so it must compare the producer to the
// artefact, not to a third opinion.
//
// AND IT COMPARES THE SERVED PAYLOAD, NOT ONLY THE IDENTITY: the page renders the descriptions, the path
// parameters, the handler names and the tool parameter schemas, so an artefact whose text has drifted is
// a stale serve even when every route is present and every name matches. routeFingerprints states why
// that comparison is on the encoded entry rather than field by field.

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"testing"

	"agenthub/internal/apiref"
)

// artefactPath resolves the committed file FROM THIS FILE'S OWN LOCATION, the discipline the witness
// states for itself: `go test` runs with the cwd set to the package directory, so a root-relative
// literal resolves to nothing and an instrument that reports an empty surface is the failure this
// package refuses everywhere else.
func artefactPath(t *testing.T) string {
	t.Helper()
	return filepath.Join(moduleRoot(t), "..", "agenthub-frontend", "src", "docs", "apiReference.ts")
}

// readCommittedArtefact parses the header the renderer writes and returns the JSON body as a Reference.
// It refuses rather than returning a zero value at every step, because an empty reference compared
// against a full one would report every route as missing and look like a finding.
func readCommittedArtefact(t *testing.T, path string) apiref.Reference {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		if errors.Is(err, fs.ErrNotExist) {
			// ABSENT IS NOT DRIFTED, and a reader who cannot tell them apart spends a seat on a
			// defect that does not exist: this is what a checkout WITHOUT agenthub-frontend, or a
			// deleted artefact, looks like, and it is not a statement about any route. The drift
			// failures below name routes and entries; none of them can produce this message.
			t.Fatalf("THE COMMITTED ARTEFACT IS ABSENT, NOT DRIFTED: %s does not exist, so no "+
				"comparison was made and no route is missing. A checkout that omits "+
				"agenthub-frontend, or an artefact deleted from one, looks exactly like this.", path)
		}
		t.Fatalf("cannot read the committed artefact at %s: %v - this gate is about the file the "+
			"frontend imports, so a path that no longer resolves is a failure of the judgement rather "+
			"than an empty surface", path, err)
	}
	text := string(raw)

	marker := "export const apiReference: ApiReference = "
	start := strings.Index(text, marker)
	if start < 0 {
		t.Fatalf("the committed artefact has no %q line: the renderer's envelope changed and this gate "+
			"would otherwise compare nothing", marker)
	}
	body := strings.TrimSpace(text[start+len(marker):])
	body = strings.TrimSuffix(body, ";")
	body = strings.TrimSpace(body)

	var reference apiref.Reference
	if err := json.Unmarshal([]byte(body), &reference); err != nil {
		t.Fatalf("the committed artefact's body is not the JSON the renderer writes: %v", err)
	}
	if len(reference.Routes) == 0 || len(reference.Tools) == 0 {
		t.Fatalf("the committed artefact carries %d routes and %d tools: an artefact that says this "+
			"server mounts nothing is the failure mode, not a comparison", len(reference.Routes), len(reference.Tools))
	}
	return reference
}

// routeFingerprints reduces entries to everything the two sides must agree on: the identity AND the
// payload the page serves. NO normalisation happens on the identity - the method and the path are used
// exactly as written, which is the whole point, because a {$} stays a {$} and a parameter stays a
// parameter and neither trap in the package note can fire.
//
// THE PAYLOAD IS PART OF THE PROJECTION BECAUSE THE PAGE SERVES IT: the description, the path parameters
// and the handler name reach users, so an artefact whose text has drifted serves what the server no
// longer carries, and a keys-only projection reports that file as matching. That is the hole this
// projection closes, and it is the one the page's own prose note cannot close for itself.
//
// THE COMPARISON IS ON THE ENCODED ENTRY RATHER THAN FIELD BY FIELD, for a reason this package measured:
// ToolEntry.Parameters is map[string]any, built in memory on the producer's side and unmarshalled from
// JSON on the artefact's, so one schema arrives as int on one side and float64 on the other and a
// field-wise comparison disagrees on a file that is correct. The renderer's own encoding maps those two
// forms to one document, and it normalises nothing else: no path is rewritten and no field is dropped.
func routeFingerprints(reference apiref.Reference) []string {
	fingerprints := make([]string, 0, len(reference.Routes))
	for _, route := range reference.Routes {
		fingerprints = append(fingerprints, encodedEntry(route))
	}
	sort.Strings(fingerprints)
	return fingerprints
}

// toolFingerprints is the same projection for the tool list, and it is where the encoding above earns
// its keep: every tool carries a parameters schema, and Parameters is exactly the field that does not
// survive a naive field-wise comparison.
func toolFingerprints(reference apiref.Reference) []string {
	fingerprints := make([]string, 0, len(reference.Tools))
	for _, tool := range reference.Tools {
		fingerprints = append(fingerprints, encodedEntry(tool))
	}
	sort.Strings(fingerprints)
	return fingerprints
}

// encodedEntry is the projection's one primitive. A value that cannot be encoded yields a marker naming
// the failure rather than an empty string, because an entry dropped silently here reads as a difference
// in the other direction and would blame the committed file for the encoder's problem.
func encodedEntry(entry any) string {
	encoded, err := json.Marshal(entry)
	if err != nil {
		return fmt.Sprintf("unencodable %T: %v", entry, err)
	}
	return string(encoded)
}

// TestTheCommittedArtefactMatchesTheProducer is the gate. Both directions fail, because both are
// defects: an artefact MISSING a registered route serves a page that understates the API, and an
// artefact CARRYING a route that is gone serves a page that advertises something the server does not
// answer.
func TestTheCommittedArtefactMatchesTheProducer(t *testing.T) {
	committed := readCommittedArtefact(t, artefactPath(t))
	produced, err := apiref.Entries(mountDir(t))
	if err != nil {
		t.Fatalf("Entries(%q): %v", mountDir(t), err)
	}

	fromCode := routeFingerprints(produced)
	inFile := routeFingerprints(committed)
	if missing := difference(fromCode, inFile); len(missing) > 0 {
		t.Errorf("DIRECTION 1 FAILS: %d route(s) are registered in the code and absent from the "+
			"committed artefact, so the page understates the API. Re-run the generator and commit the "+
			"result:\n  %s", len(missing), strings.Join(missing, "\n  "))
	}
	if stale := difference(inFile, fromCode); len(stale) > 0 {
		t.Errorf("DIRECTION 2 FAILS: %d route(s) are in the committed artefact and registered nowhere, "+
			"so the page advertises what the server does not answer:\n  %s", len(stale), strings.Join(stale, "\n  "))
	}

	codeTools := toolFingerprints(produced)
	fileTools := toolFingerprints(committed)
	if missing := difference(codeTools, fileTools); len(missing) > 0 {
		t.Errorf("DIRECTION 1 FAILS for tools: %d tool(s) exist in the server and are absent from the "+
			"committed artefact:\n  %s", len(missing), strings.Join(missing, "\n  "))
	}
	if stale := difference(fileTools, codeTools); len(stale) > 0 {
		t.Errorf("DIRECTION 2 FAILS for tools: %d tool(s) are in the artefact and offered by nothing:"+
			"\n  %s", len(stale), strings.Join(stale, "\n  "))
	}
}

// difference returns the sorted members of want that are absent from have.
func difference(want, have []string) []string {
	present := make(map[string]bool, len(have))
	for _, h := range have {
		present[h] = true
	}
	out := make([]string, 0)
	for _, w := range want {
		if !present[w] {
			out = append(out, w)
		}
	}
	sort.Strings(out)
	return out
}

// TestTheArtefactGateCanFailBothWays proves the gate above is an instrument rather than a decoration,
// in the form the package's own rule requires: a check is only a check once each direction has been
// seen failing. It perturbs the PARSED artefact rather than the file, so it needs no scratch copy and
// cannot leave the tree modified.
func TestTheArtefactGateCanFailBothWays(t *testing.T) {
	committed := readCommittedArtefact(t, artefactPath(t))
	if len(committed.Routes) == 0 {
		t.Fatal("the committed artefact has no routes to perturb")
	}

	// DIRECTION 1: a route the code has and the artefact does not.
	missingOne := apiref.Reference{
		Routes: append(append([]apiref.RouteEntry{}, committed.Routes[1:]...), committed.Routes[0]),
		Tools:  committed.Tools,
	}
	missingOne.Routes = missingOne.Routes[:len(missingOne.Routes)-1]
	fromCode := routeFingerprints(committed)
	inFile := routeFingerprints(missingOne)
	if got := difference(fromCode, inFile); len(got) != 1 {
		t.Errorf("direction 1 did not name exactly the dropped route: got %v", got)
	}
	if got := difference(inFile, fromCode); len(got) != 0 {
		t.Errorf("direction 2 fired on a set that is only missing an entry: got %v", got)
	}

	// DIRECTION 2: an entry the artefact has and the code does not. Built from the PRISTINE set rather
	// than from the perturbed one above, because a set that is already missing an entry makes direction
	// 1 fire for the earlier reason and proves nothing about this one.
	extraRoute := apiref.RouteEntry{Method: "GET", Path: "/a/route/that/is/registered/nowhere"}
	inFile = routeFingerprints(committed)
	inFile = append(inFile, extraRoute.Method+" "+extraRoute.Path)
	if got := difference(inFile, fromCode); len(got) != 1 || got[0] != extraRoute.Method+" "+extraRoute.Path {
		t.Errorf("direction 2 did not name exactly the invented route: got %v", got)
	}
	if got := difference(fromCode, inFile); len(got) != 0 {
		t.Errorf("direction 1 fired on a set that only gained an entry: got %v", got)
	}

	// DIRECTION 3: THE STALE-TEXT CASE - an entry whose identity is untouched and whose SERVED TEXT has
	// drifted. The method and the path are identical on both sides, so the keys-only projection this
	// replaced reported the two sets as EQUAL; that is the hole, and these assertions are what show the
	// value projection closes it. Both sides are named exactly as the renderer encodes them, which is
	// also what keeps this assertion free of any assumption about how a description is spelled.
	stale := apiref.Reference{
		Routes: append([]apiref.RouteEntry{}, committed.Routes...),
		Tools:  append([]apiref.ToolEntry{}, committed.Tools...),
	}
	stale.Routes[0].Description = committed.Routes[0].Description + " (text that is not what the server serves)"
	dropped := difference(routeFingerprints(committed), routeFingerprints(stale))
	if len(dropped) != 1 || dropped[0] != encodedEntry(committed.Routes[0]) {
		t.Errorf("the pristine route did not leave the set as the named entry: got %v", dropped)
	}
	added := difference(routeFingerprints(stale), routeFingerprints(committed))
	if len(added) != 1 || added[0] != encodedEntry(stale.Routes[0]) {
		t.Errorf("the route whose text drifted did not arrive as the named entry, text included: got %v", added)
	}
	stale.Tools[0].Description = committed.Tools[0].Description + " (text that is not what the server serves)"
	if got := difference(toolFingerprints(committed), toolFingerprints(stale)); len(got) != 1 || got[0] != encodedEntry(committed.Tools[0]) {
		t.Errorf("the value projection did not name exactly the tool whose text drifted: got %v", got)
	}

	// AND THE PARSER ITSELF: a body that is not the renderer's envelope must be refused rather than
	// silently compared as empty, which is the failure the module comment above names.
	dir := t.TempDir()
	broken := filepath.Join(dir, "apiReference.ts")
	if err := os.WriteFile(broken, []byte("export const somethingElse = {};\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := readArtefactForTest(broken); err == nil {
		t.Errorf("a file without the renderer's envelope was accepted: %s", fmt.Sprint(broken))
	}
}

// readArtefactForTest is the refusal path of readCommittedArtefact without the t.Fatalf, so the
// perturbation case above can assert a refusal instead of ending the test.
func readArtefactForTest(path string) (apiref.Reference, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return apiref.Reference{}, err
	}
	text := string(raw)
	marker := "export const apiReference: ApiReference = "
	start := strings.Index(text, marker)
	if start < 0 {
		return apiref.Reference{}, fmt.Errorf("no %q line", marker)
	}
	body := strings.TrimSpace(text[start+len(marker):])
	body = strings.TrimSpace(strings.TrimSuffix(body, ";"))
	var reference apiref.Reference
	if err := json.Unmarshal([]byte(body), &reference); err != nil {
		return apiref.Reference{}, err
	}
	if len(reference.Routes) == 0 || len(reference.Tools) == 0 {
		return apiref.Reference{}, fmt.Errorf("empty reference")
	}
	return reference, nil
}
