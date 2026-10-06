// Package apiref produces the generated reference tier of the docs page: every mounted HTTP route and
// every MCP tool, taken from the code rather than from a list someone maintains.
//
// ONE PRODUCER, ONE WITNESS. Entries() is the producer and the only thing a consumer calls. The drift
// test is the WITNESS and must read the code independently - a separate parse of the *_mount.go source
// for routes, and the dispatch entries for tools - which is why THE ROUTE PARSER IN THIS FILE IS
// UNEXPORTED. Exporting it would let the witness call the producer and compare the generator to
// itself, passing forever: two readings of one artefact is the whole value, and one reading twice is
// no evidence at all.
//
// TWO INSTRUMENTS, AND THE DIFFERENCE IS DELIBERATE. ROUTES come from the SOURCE TEXT of the
// *_mount.go files, because a http.ServeMux cannot be enumerated: the method and the pattern are
// string literals and are therefore certain, while the handler name is present only when the mount
// registers a named function and is empty for an inline closure. TOOLS come from CALLING
// (*httpapp.App).MCPToolsList(), so the tool surface is reproduced by RUNNING the code rather than by
// counting lines - and the ten tools (six definitions plus four schemas appended inside that function)
// reach this package only because they reach the wire.
package apiref

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// RouteEntry is one mounted HTTP route, in the shape the page renders and the drift test checks.
//
// Handler is the name of the function the mount registers. It is EMPTY when the mount passes an
// inline closure, which is a fact about the source rather than a gap to fill in: a route whose
// registration is a closure has no name to report, and inventing one would be a second source.
type RouteEntry struct {
	Method      string   `json:"method"`
	Path        string   `json:"path"`
	PathParams  []string `json:"pathParams"`
	Handler     string   `json:"handler"`
	Description string   `json:"description"`
}

// pathParam matches one {name} segment of a Go 1.22 route pattern.
var pathParam = regexp.MustCompile(`\{([^}]*)\}`)

// mountFileSuffix is the file family that registers routes on the mux.
const mountFileSuffix = "_mount.go"

// routesFromDir reads every mount file in dir and returns their routes, sorted, deduplicated.
//
// Unexported on purpose: this is the producer's instrument, and the witness must parse the same
// source text with its own code rather than call this.
func routesFromDir(dir string) ([]RouteEntry, error) {
	names, err := filepath.Glob(filepath.Join(dir, "*"+mountFileSuffix))
	if err != nil {
		return nil, fmt.Errorf("cannot list the mount files in %s: %w", dir, err)
	}
	if len(names) == 0 {
		return nil, fmt.Errorf("no %s files in %s: the route surface cannot be empty", mountFileSuffix, dir)
	}
	sort.Strings(names)

	routes := make([]RouteEntry, 0, len(names))
	for _, name := range names {
		source, err := os.ReadFile(name)
		if err != nil {
			return nil, fmt.Errorf("cannot read %s: %w", name, err)
		}
		found, err := routesInSource(filepath.Base(name), source)
		if err != nil {
			return nil, err
		}
		routes = append(routes, found...)
	}
	sort.Slice(routes, func(i, j int) bool {
		if routes[i].Path != routes[j].Path {
			return routes[i].Path < routes[j].Path
		}
		return routes[i].Method < routes[j].Method
	})
	return routes, nil
}

// routesInSource parses one mount file and returns the routes it registers. A file that does not parse
// is an error rather than an empty result: a silent zero here would become a document that says the
// platform mounts nothing.
func routesInSource(filename string, source []byte) ([]RouteEntry, error) {
	fileSet := token.NewFileSet()
	file, err := parser.ParseFile(fileSet, filename, source, parser.ParseComments)
	if err != nil {
		return nil, fmt.Errorf("%s does not parse: %w", filename, err)
	}

	// The doc comment of every named function, so a route whose handler is named can carry its
	// documentation. A doc comment is code, which is why it is a legitimate source here.
	docs := map[string]string{}
	for _, decl := range file.Decls {
		fn, ok := decl.(*ast.FuncDecl)
		if !ok || fn.Doc == nil {
			continue
		}
		docs[fn.Name.Name] = strings.TrimSpace(fn.Doc.Text())
	}

	routes := []RouteEntry{}
	var walkErr error
	ast.Inspect(file, func(node ast.Node) bool {
		call, ok := node.(*ast.CallExpr)
		if !ok || walkErr != nil {
			return true
		}
		selector, ok := call.Fun.(*ast.SelectorExpr)
		if !ok || (selector.Sel.Name != "HandleFunc" && selector.Sel.Name != "Handle") {
			return true
		}
		if len(call.Args) == 0 {
			return true
		}
		pattern, ok := stringLiteral(call.Args[0])
		if !ok {
			return true
		}
		method, path, params, err := splitPattern(pattern)
		if err != nil {
			walkErr = fmt.Errorf("%s: %w", filename, err)
			return false
		}
		entry := RouteEntry{Method: method, Path: path, PathParams: params}
		if len(call.Args) > 1 {
			entry.Handler = handlerName(call.Args[1])
		}
		if doc, ok := docs[entry.Handler]; ok {
			entry.Description = doc
		}
		routes = append(routes, entry)
		return true
	})
	if walkErr != nil {
		return nil, walkErr
	}
	return routes, nil
}

// splitPattern turns `GET /api/v2/openrig/rooms/{room}` into its method, its path and its parameters.
// The method may be absent (a mux registers the handler for every method then), and the path is
// reported as registered so the drift test can compare literals rather than reconstructions.
func splitPattern(pattern string) (method, path string, params []string, err error) {
	fields := strings.Fields(pattern)
	switch len(fields) {
	case 1:
		path = fields[0]
	case 2:
		method, path = fields[0], fields[1]
	default:
		return "", "", nil, fmt.Errorf("route pattern %q is neither a path nor a method and a path", pattern)
	}
	if !strings.HasPrefix(path, "/") {
		return "", "", nil, fmt.Errorf("route pattern %q does not start with a slash", pattern)
	}
	for _, match := range pathParam.FindAllStringSubmatch(path, -1) {
		params = append(params, match[1])
	}
	return method, path, params, nil
}

// stringLiteral returns the value of a plain string literal, and false for anything else (a
// concatenation, a constant, a variable): an unstated pattern is not a route this package can report.
func stringLiteral(expr ast.Expr) (string, bool) {
	literal, ok := expr.(*ast.BasicLit)
	if !ok || literal.Kind != token.STRING {
		return "", false
	}
	value, err := strconv.Unquote(literal.Value)
	if err != nil {
		return "", false
	}
	return value, true
}

// handlerName reports the name a registration passes, and empty for a closure or any expression that
// is not a plain function name.
func handlerName(expr ast.Expr) string {
	switch value := expr.(type) {
	case *ast.Ident:
		return value.Name
	case *ast.SelectorExpr:
		return value.Sel.Name
	}
	return ""
}
