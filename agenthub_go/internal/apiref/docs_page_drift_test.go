// Package apiref_test is the WITNESS for the generated reference.
//
// THE RULE THIS TEST ENFORCES (NEXT_GEN rule 61): a route or tool that exists in code with no entry
// FAILS, and an entry with no route or tool FAILS - and it is only a check once each direction has
// been seen failing.
//
// WHY IT LIVES HERE AND WHY IT DOES NOT CALL THE PRODUCER'S PARSER. The generator and the page share
// ONE PRODUCER; this test is the INDEPENDENT WITNESS, and the two are different roles that must be
// different instruments. If this test obtained the code side by calling apiref's own parser, it would
// compare the generator TO ITSELF and could never fail. So the routes below are read by THIS FILE's
// own walk of the mount files' source, and the tools by THIS FILE's own reading of the registration
// sites rather than by calling the builder apiref calls. Two extractors are two answers; a producer
// and a witness are one answer and one check.
//
// AND THE FAILURE MODE THIS FILE EXISTS TO CATCH, recorded because it was live: an earlier version of
// the producer's parser accepted only a single string literal, so every pattern composed by
// concatenation ("POST "+base+"/") was silently skipped - no error and no count - and a 57-route
// entry set passed a guard that only refused ZERO. A guard against zero cannot see a partial skip.
// SO EVERY UNRESOLVABLE REGISTRATION HERE IS AN ERROR RATHER THAN A SKIP: silence is the defect.
package apiref_test

import (
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"testing"

	"agenthub/internal/apiref"
)

// THE PATH IS RESOLVED FROM THIS FILE'S OWN LOCATION rather than from the process working directory:
// `go test` runs with the cwd set to the package directory, so a root-relative literal silently
// resolves to nothing - which is exactly the "an instrument that reports an empty surface" failure
// this package refuses everywhere else.
func moduleRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("witness cannot locate its own source file")
	}
	// This file lives at <module>/internal/apiref, so the module root is two levels up.
	return filepath.Join(filepath.Dir(file), "..", "..")
}

// mountDir is where the one mux is built.
func mountDir(t *testing.T) string {
	return filepath.Join(moduleRoot(t), "fastmcp", "server", "httpapp")
}

// mountedFamilies is every directory whose registrations reach the mux app.go builds. It is three
// directories rather than one because the auth controllers register from their own packages: a witness
// that stopped at the mux's own directory would agree with a producer that dropped those 20
// registrations, which is the own-shadow failure this file exists to avoid.
func mountedFamilies(t *testing.T) []string {
	root := moduleRoot(t)
	return []string{
		mountDir(t),
		filepath.Join(root, "fastmcp", "auth", "interface"),
		filepath.Join(root, "fastmcp", "auth", "api"),
	}
}

// witnessRoute is what this file reads for itself: a method and a path, both taken from the source.
type witnessRoute struct{ method, path string }

func (r witnessRoute) String() string { return r.method + " " + r.path }

// normalisePath keeps the trailing slash and drops the exact-match marker.
//
// BOTH HALVES MATTER AND BOTH WERE LEARNED THE HARD WAY: "GET "+base and "GET "+base+"/" are DIFFERENT
// Go 1.22 patterns (exact versus subtree), so a trailing slash must never be normalised away - an
// earlier auditor stripped it and reported three correct entries as stale - while "{$}" marks an
// exact match and is not a path parameter.
func normalisePath(p string) string { return strings.ReplaceAll(p, "/{$}", "") }

// routesFromSource is the witness's own reading of the mount files in dir.
func routesFromSource(t *testing.T, dir string) []witnessRoute {
	t.Helper()
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatalf("witness cannot read %s: %v", dir, err)
	}
	var out []witnessRoute
	files := 0
	for _, e := range entries {
		name := e.Name()
		if e.IsDir() || !strings.HasSuffix(name, ".go") || strings.HasSuffix(name, "_test.go") {
			continue
		}
		files++
		out = append(out, routesInWitnessFile(t, filepath.Join(dir, name))...)
	}
	if files == 0 {
		t.Fatalf("witness found no Go files in %s: the directory moved, which is a failure of the judgement and not an empty surface", dir)
	}
	return out
}

func routesInWitnessFile(t *testing.T, path string) []witnessRoute {
	t.Helper()
	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, path, nil, 0)
	if err != nil {
		t.Fatalf("witness cannot parse %s: %v", path, err)
	}

	// Base declarations in source order, so a lookup can take the nearest PRECEDING one. TWO SHAPES
	// MATTER AND BOTH ARE IN THE TREE: routes_mount.go declares five bases as FUNCTION-SCOPED consts
	// (`const base = "/api/v2/connections"` inside each mount function), so a walk that records only
	// top-level declarations - or only assignments - misses every one of them and cannot resolve a
	// single composed pattern in the file where most of them live.
	type baseDecl struct {
		line  int
		name  string
		value string
	}
	var bases []baseDecl
	record := func(line int, name, value string) {
		if strings.Contains(name, "base") {
			bases = append(bases, baseDecl{line, name, value})
		}
	}
	ast.Inspect(file, func(n ast.Node) bool {
		switch node := n.(type) {
		case *ast.GenDecl: // const base = "..." or var base = "..." (file-scope or inside a function)
			if node.Tok != token.CONST && node.Tok != token.VAR {
				return true
			}
			for _, spec := range node.Specs {
				vs, ok := spec.(*ast.ValueSpec)
				if !ok || len(vs.Names) != len(vs.Values) {
					continue
				}
				for i, name := range vs.Names {
					if lit, ok := vs.Values[i].(*ast.BasicLit); ok && lit.Kind == token.STRING {
						if v, err := strconv.Unquote(lit.Value); err == nil {
							record(fset.Position(name.Pos()).Line, name.Name, v)
						}
					}
				}
			}
		case *ast.AssignStmt: // base := "..." or base = "..."
			if len(node.Lhs) != 1 || len(node.Rhs) != 1 {
				return true
			}
			ident, ok := node.Lhs[0].(*ast.Ident)
			if !ok {
				return true
			}
			if lit, ok := node.Rhs[0].(*ast.BasicLit); ok && lit.Kind == token.STRING {
				if v, err := strconv.Unquote(lit.Value); err == nil {
					record(fset.Position(ident.Pos()).Line, ident.Name, v)
				}
			}
		}
		return true
	})
	// The nearest PRECEDING declaration wins: routes_mount.go declares several bases in one file.
	baseAt := func(name string, line int) (string, bool) {
		best, bestLine, ok := "", -1, false
		for _, b := range bases {
			if b.name == name && b.line <= line && b.line > bestLine {
				best, bestLine, ok = b.value, b.line, true
			}
		}
		return best, ok
	}

	var out []witnessRoute
	ast.Inspect(file, func(n ast.Node) bool {
		call, ok := n.(*ast.CallExpr)
		if !ok || len(call.Args) == 0 {
			return true
		}
		sel, ok := call.Fun.(*ast.SelectorExpr)
		if !ok || (sel.Sel.Name != "HandleFunc" && sel.Sel.Name != "Handle") {
			return true
		}
		line := fset.Position(call.Pos()).Line
		pattern, ok := resolvePattern(call.Args[0], func(id string) (string, bool) { return baseAt(id, line) })
		if !ok {
			// NOT A SKIP: an unreadable registration is a defect in the code or in this witness, and
			// saying so is the whole difference between a witness and a second producer.
			t.Errorf("%s:%d: witness cannot resolve the registration pattern (a concatenation it does not "+
				"understand, or a base declared after its use): %s", path, line, exprText(call.Args[0]))
			return true
		}
		method, route, ok := splitWitnessPattern(pattern)
		if !ok {
			t.Errorf("%s:%d: witness cannot split %q into a method and a path", path, line, pattern)
			return true
		}
		out = append(out, witnessRoute{method, normalisePath(route)})
		return true
	})
	return out
}

// resolvePattern folds a pattern expression into its value: string literals contribute their text,
// identifiers are looked up, and concatenation is walked left to right.
func resolvePattern(expr ast.Expr, lookup func(string) (string, bool)) (string, bool) {
	switch e := expr.(type) {
	case *ast.BasicLit:
		if e.Kind != token.STRING {
			return "", false
		}
		v, err := strconv.Unquote(e.Value)
		return v, err == nil
	case *ast.Ident:
		return lookup(e.Name)
	case *ast.BinaryExpr:
		if e.Op != token.ADD {
			return "", false
		}
		left, ok := resolvePattern(e.X, lookup)
		if !ok {
			return "", false
		}
		right, ok := resolvePattern(e.Y, lookup)
		if !ok {
			return "", false
		}
		return left + right, true
	case *ast.ParenExpr:
		return resolvePattern(e.X, lookup)
	}
	return "", false
}

func splitWitnessPattern(pattern string) (method, route string, ok bool) {
	for _, m := range []string{"GET", "POST", "PUT", "PATCH", "DELETE"} {
		if strings.HasPrefix(pattern, m+" ") {
			return m, strings.TrimPrefix(pattern, m+" "), true
		}
	}
	return "", "", false
}

func exprText(e ast.Expr) string {
	switch v := e.(type) {
	case *ast.BasicLit:
		return v.Value
	case *ast.Ident:
		return v.Name
	case *ast.BinaryExpr:
		return exprText(v.X) + " + " + exprText(v.Y)
	case *ast.ParenExpr:
		return "(" + exprText(v.X) + ")"
	}
	return "?"
}

// toolNamesFromSource is the witness's own reading of the ADVERTISED tool names - the ones a client
// finds in `tools/list` - by reading the source of the advertised surface rather than by calling the
// builder the producer calls.
//
// THE FIRST VERSION OF THIS FUNCTION WAS WRONG AND THE WAY IT WAS WRONG IS WORTH KEEPING: it collected
// every `case "..."` label in mcp_routes.go, so it reported NINE names that are not tools at all - the
// handler's own JSON-RPC envelope (initialize, ping) and the dispatch-only names (get_mcp_status,
// check_session_health) beside the manage_* family - while missing the THREE tools dispatched outside
// that file (manage_seat, call_seat, submit_feedback, whose controllers own their dispatch). THE
// SURFACE A WITNESS MUST READ IS THE ONE THE CLIENT SEES, NOT EVERY PATH THE SERVER ACCEPTS: a dispatch
// switch answers "what can be called", which is a different question from "what is advertised".
func toolNamesFromSource(t *testing.T, moduleRoot string) map[string]bool {
	t.Helper()
	names := map[string]bool{}

	// (1) The registry tools: `Name: "manage_x"` in the file ToolDefinitions() returns.
	defsPath := filepath.Join(moduleRoot, "fastmcp/task_management/interface/ddd_compliant_mcp_tools.go")
	defs, err := os.ReadFile(defsPath)
	if err != nil {
		t.Fatalf("witness cannot read %s: %v", defsPath, err)
	}
	registryTool := regexp.MustCompile(`Name:\s*"(manage_[a-z_]+)"`)
	for _, m := range registryTool.FindAllStringSubmatch(string(defs), -1) {
		names[m[1]] = true
	}

	// (2) The controller-appended schemas: `"name": seatcontrollers.XToolName` in mcp_routes.go,
	//     resolved through the constants the controllers declare - so the reading follows the
	//     IDENTIFIER to its value rather than assuming the name.
	controllersDir := filepath.Join(moduleRoot, "fastmcp/seat_management/interface/mcp_controllers")
	consts := map[string]string{}
	entries, err := os.ReadDir(controllersDir)
	if err != nil {
		t.Fatalf("witness cannot read %s: %v", controllersDir, err)
	}
	constDecl := regexp.MustCompile(`const\s+(\w+)\s*=\s*"([^"]+)"`)
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".go") || strings.HasSuffix(e.Name(), "_test.go") {
			continue
		}
		src, err := os.ReadFile(filepath.Join(controllersDir, e.Name()))
		if err != nil {
			t.Fatalf("witness cannot read %s: %v", e.Name(), err)
		}
		for _, m := range constDecl.FindAllStringSubmatch(string(src), -1) {
			consts[m[1]] = m[2]
		}
	}
	routesPath := filepath.Join(moduleRoot, "fastmcp/server/httpapp/mcp_routes.go")
	routes, err := os.ReadFile(routesPath)
	if err != nil {
		t.Fatalf("witness cannot read %s: %v", routesPath, err)
	}
	appended := regexp.MustCompile(`"name":\s*seatcontrollers\.(\w+)`)
	for _, m := range appended.FindAllStringSubmatch(string(routes), -1) {
		value, ok := consts[m[1]]
		if !ok {
			t.Errorf("witness cannot resolve seatcontrollers.%s to a value: the controllers moved it, and an "+
				"unresolved name is reported rather than skipped", m[1])
			continue
		}
		names[value] = true
	}

	// (3) The connection tool, whose name is a literal in its own file and which is appended as a
	//     whole map rather than through a `"name":` field in the list builder.
	connPath := filepath.Join(moduleRoot, "fastmcp/server/httpapp/mcp_connection_tool.go")
	conn, err := os.ReadFile(connPath)
	if err != nil {
		t.Fatalf("witness cannot read %s: %v", connPath, err)
	}
	if m := regexp.MustCompile(`"name":\s*"([a-z_]+)"`).FindStringSubmatch(string(conn)); m != nil {
		names[m[1]] = true
	}

	if len(names) == 0 {
		t.Fatal("witness read no advertised tool names: an empty reading is a failure of the witness")
	}
	return names
}

// TestReferenceMatchesTheMountedRoutes is the drift rule, both directions, each reported separately.
func TestReferenceMatchesTheMountedRoutes(t *testing.T) {
	reference, err := apiref.Entries(mountDir(t))
	if err != nil {
		t.Fatalf("Entries(%q): %v", mountDir(t), err)
	}
	if len(reference.Routes) == 0 {
		t.Fatal("Entries returned no routes: an empty result is a failure, not a document")
	}

	families := mountedFamilies(t)
	var witnessed []witnessRoute
	for _, dir := range families {
		witnessed = append(witnessed, routesFromSource(t, dir)...)
	}
	t.Logf("witness reads %d registrations across %d mounted families", len(witnessed), len(families))
	inCode := map[string]bool{}
	for _, r := range witnessed {
		inCode[r.String()] = true
	}
	inReference := map[string]bool{}
	for _, r := range reference.Routes {
		inReference[r.Method+" "+normalisePath(r.Path)] = true
	}

	// DIRECTION 1: in the code, no entry. This is the omission direction, and it is the one that
	// produced tonight's 57-versus-144.
	compareBothDirections(t, "registration", inCode, inReference)
}

// TestReferenceToolsMatchTheRegistrationSite is the same rule for the tool surface, read from the
// source rather than from the builder apiref calls.
func TestReferenceToolsMatchTheRegistrationSite(t *testing.T) {
	reference, err := apiref.Entries(mountDir(t))
	if err != nil {
		t.Fatalf("Entries(%q): %v", mountDir(t), err)
	}
	if len(reference.Tools) == 0 {
		t.Fatal("Entries returned no tools: an empty result is a failure, not a document")
	}
	inSource := toolNamesFromSource(t, moduleRoot(t))
	inReference := map[string]bool{}
	for _, tool := range reference.Tools {
		inReference[tool.Name] = true
	}
	compareBothDirections(t, "tool", inSource, inReference)
}

// compareBothDirections is THE RULE, in one place so that the two real tests and the self-test below
// exercise the same code: an entry in the code with no reference entry FAILS, and a reference entry
// with nothing in the code FAILS. Each direction is reported separately so a failure names which one.
func compareBothDirections(t *testing.T, what string, inCode, inReference map[string]bool) {
	t.Helper()
	if missing := setDifference(inCode, inReference); len(missing) > 0 {
		t.Errorf("DIRECTION 1 FAILS: %d %s(s) exist in the code and are absent from the reference:\n  %s",
			len(missing), what, strings.Join(missing, "\n  "))
	}
	if phantom := setDifference(inReference, inCode); len(phantom) > 0 {
		t.Errorf("DIRECTION 2 FAILS: %d reference %s(s) have nothing in the code:\n  %s",
			len(phantom), what, strings.Join(phantom, "\n  "))
	}
}

// TestTheDriftComparisonCanFailBothWays is this file's OWN falsifiability, and it is the criterion rule
// 61 carries: a document check that has only ever passed is a claim about a document, not a check on
// one. It perturbs the world by one item in each direction, calls the SAME comparison function the real
// tests call - not a copy of the logic - and requires each direction to fire and to NAME the perturbed
// item rather than merely to fail.
//
// BOTH DIRECTIONS HAVE ALSO BEEN SEEN FAILING ON THE REAL TREE, which is what makes this file a check
// rather than a demonstration: direction 1 fired with 29 routes when the producer walked only the
// `_mount.go` family, and direction 1 likewise fired with nine non-tool names plus a three-name gap
// when this witness read the dispatch switch instead of the advertised surface.
func TestTheDriftComparisonCanFailBothWays(t *testing.T) {
	code := map[string]bool{"GET /a": true, "GET /b": true}
	reference := map[string]bool{"GET /a": true}

	if d := setDifference(code, reference); len(d) != 1 || d[0] != "GET /b" {
		t.Errorf("direction 1 did not name the perturbed item: got %v, want [GET /b]", d)
	}
	if d := setDifference(reference, code); len(d) != 0 {
		t.Errorf("direction 2 fired on a clean set: got %v, want none", d)
	}

	// The phantom set is a SUPERSET of the code, so direction 1 is genuinely clean: the first version of
	// this self-test used {"GET /a","GET /c"} and asserted direction 1 was clean, which was wrong - /b
	// was in the code and absent from that set, so direction 1 fired correctly and the SELF-TEST was the
	// thing that failed. A perturbed world must isolate one direction or it tests two things at once.
	phantomReference := map[string]bool{"GET /a": true, "GET /b": true, "GET /c": true}
	if d := setDifference(phantomReference, code); len(d) != 1 || d[0] != "GET /c" {
		t.Errorf("direction 2 did not name the perturbed item: got %v, want [GET /c]", d)
	}
	if d := setDifference(code, phantomReference); len(d) != 0 {
		t.Errorf("direction 1 fired on a set that contains everything in the code: got %v, want none", d)
	}
}

func setDifference(a, b map[string]bool) []string {
	var out []string
	for k := range a {
		if !b[k] {
			out = append(out, k)
		}
	}
	sort.Strings(out)
	return out
}
