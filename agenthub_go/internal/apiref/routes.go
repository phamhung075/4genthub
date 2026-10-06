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
// TWO INSTRUMENTS, AND THE DIFFERENCE IS DELIBERATE. ROUTES come from the SOURCE TEXT of every
// non-test Go file in the mount directory AND in each package that directory mounts routes from,
// because a http.ServeMux cannot be enumerated: the method and the pattern are string literals and
// are therefore certain, while the handler name is present only when the mount registers a named
// function and is empty for an inline closure. TOOLS come from CALLING
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

// testFileSuffix marks the files whose registrations are not part of the surface: a registration in a
// test is a test's own mux, not the server's.
const testFileSuffix = "_test.go"

// routesFromTree reads EVERY directory whose registrations reach the one mux app.go builds: the mount
// directory itself and each package whose RegisterRoutes that directory calls with the mux. The auth
// controller and the supabase controller register from their own packages, so a scan of the mount
// directory alone dropped their 20 registrations silently - the same partial skip as a
// string-literal-only parser, one scope wider, and one the empty-artefact guard cannot see.
func routesFromTree(dir string) ([]RouteEntry, error) {
	dirs, err := routeDirs(dir)
	if err != nil {
		return nil, err
	}
	var routes []RouteEntry
	for _, found := range dirs {
		entries, err := routesFromDir(found)
		if err != nil {
			return nil, err
		}
		routes = append(routes, entries...)
	}
	sortRoutes(routes)
	return routes, nil
}

// goFilesIn lists the non-test Go files in dir, sorted. A test's own mux is not the server's surface,
// and every other .go file is: the family used to be *_mount.go, which dropped 29 registrations that
// lived in app.go and the per-family *_routes.go files.
func goFilesIn(dir string) ([]string, error) {
	names, err := filepath.Glob(filepath.Join(dir, "*.go"))
	if err != nil {
		return nil, fmt.Errorf("cannot list the Go files in %s: %w", dir, err)
	}
	files := make([]string, 0, len(names))
	for _, name := range names {
		if strings.HasSuffix(name, testFileSuffix) {
			continue
		}
		files = append(files, name)
	}
	if len(files) == 0 {
		return nil, fmt.Errorf("no Go files in %s: the route surface cannot be empty", dir)
	}
	sort.Strings(files)
	return files, nil
}

// routesFromDir reads every non-test Go file in dir and returns their routes, sorted.
//
// Unexported on purpose: this is the producer's instrument, and the witness must parse the same
// source text with its own code rather than call this.
func routesFromDir(dir string) ([]RouteEntry, error) {
	files, err := goFilesIn(dir)
	if err != nil {
		return nil, err
	}
	routes := make([]RouteEntry, 0, len(files))
	for _, name := range files {
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
	sortRoutes(routes)
	return routes, nil
}

// sortRoutes orders routes by path and then method, so the artefact has one stable order whatever
// directory order the read produced.
func sortRoutes(routes []RouteEntry) {
	sort.Slice(routes, func(i, j int) bool {
		if routes[i].Path != routes[j].Path {
			return routes[i].Path < routes[j].Path
		}
		return routes[i].Method < routes[j].Method
	})
}

// routeDirs returns dir plus every package directory whose RegisterRoutes dir calls with the mux. The
// traversal follows the mount calls rather than a list someone maintains, so a family that registers
// from its own package is read where it lands; a package already visited is not visited twice.
func routeDirs(dir string) ([]string, error) {
	moduleRoot, modulePath, err := moduleFor(dir)
	if err != nil {
		return nil, err
	}
	dirs := []string{dir}
	seen := map[string]bool{dir: true}
	for index := 0; index < len(dirs); index++ {
		files, err := goFilesIn(dirs[index])
		if err != nil {
			return nil, err
		}
		for _, name := range files {
			source, err := os.ReadFile(name)
			if err != nil {
				return nil, fmt.Errorf("cannot read %s: %w", name, err)
			}
			file, err := parser.ParseFile(token.NewFileSet(), name, source, 0)
			if err != nil {
				return nil, fmt.Errorf("%s does not parse: %w", filepath.Base(name), err)
			}
			imports := importPaths(file)
			for _, call := range registerRoutesMounts(file) {
				path, ok := imports[packageQualifier(call.Fun)]
				if !ok {
					continue
				}
				target := filepath.Join(moduleRoot, strings.TrimPrefix(path, modulePath+"/"))
				if !seen[target] {
					seen[target] = true
					dirs = append(dirs, target)
				}
			}
		}
	}
	return dirs, nil
}

// registerRoutesMounts returns the `pkg.RegisterRoutes(mux)` calls in file: a package-qualified
// RegisterRoutes call is a route family joining the mux from its own package, which is the package
// routeDirs then reads.
func registerRoutesMounts(file *ast.File) []*ast.CallExpr {
	var calls []*ast.CallExpr
	ast.Inspect(file, func(node ast.Node) bool {
		call, ok := node.(*ast.CallExpr)
		if !ok || len(call.Args) != 1 {
			return true
		}
		selector, ok := call.Fun.(*ast.SelectorExpr)
		if !ok || selector.Sel.Name != "RegisterRoutes" {
			return true
		}
		calls = append(calls, call)
		return true
	})
	return calls
}

// packageQualifier reports the package identifier an expression is rooted at, so
// `authinterface.NewAuthController()` and a plain `pkg.Func()` both name their package.
func packageQualifier(expr ast.Expr) string {
	switch value := expr.(type) {
	case *ast.Ident:
		return value.Name
	case *ast.CallExpr:
		return packageQualifier(value.Fun)
	case *ast.SelectorExpr:
		return packageQualifier(value.X)
	}
	return ""
}

// importPaths maps each import's local qualifier to its path: the alias when one is declared and the
// path's last segment otherwise.
func importPaths(file *ast.File) map[string]string {
	imports := map[string]string{}
	for _, spec := range file.Imports {
		path, err := strconv.Unquote(spec.Path.Value)
		if err != nil {
			continue
		}
		name := filepath.Base(path)
		if spec.Name != nil {
			name = spec.Name.Name
		}
		imports[name] = path
	}
	return imports
}

// moduleFor walks up from dir to the go.mod that owns it and returns the module root and path, so an
// import path can be turned into the directory it names.
func moduleFor(dir string) (root, path string, err error) {
	current, err := filepath.Abs(dir)
	if err != nil {
		return "", "", fmt.Errorf("cannot resolve %s: %w", dir, err)
	}
	for {
		data, readErr := os.ReadFile(filepath.Join(current, "go.mod"))
		if readErr == nil {
			for _, line := range strings.Split(string(data), "\n") {
				fields := strings.Fields(line)
				if len(fields) >= 2 && fields[0] == "module" {
					return current, fields[1], nil
				}
			}
			return "", "", fmt.Errorf("%s/go.mod declares no module path", current)
		}
		parent := filepath.Dir(current)
		if parent == current {
			return "", "", fmt.Errorf("no go.mod above %s: cannot resolve a mounted package", dir)
		}
		current = parent
	}
}

// routesInSource parses one mount file and returns the routes it registers.
//
// THE FIRST ARGUMENT IS AN EXPRESSION, NOT A LITERAL, and this is the fix for a silent skip that the
// witness caught: accepting only a string literal skipped every concatenated registration - 38 of
// them in this package alone - with no error and no count, which the empty-artefact guard cannot
// detect because the artefact was not empty, it was short. So the pattern is EVALUATED here, and ANY
// CALL SITE THAT CANNOT BE RESOLVED IS AN ERROR: a skip is the defect, and the count below is only
// its symptom.
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

	// bases is LEXICAL AND SEQUENTIAL: the value in force is the nearest preceding assignment, because
	// one mount file declares several bases and a single file-level base produces wrong paths. The
	// walk below is in source order, so setting the map as assignments are met is exactly that rule.
	bases := map[string]string{}
	candidates := 0
	routes := []RouteEntry{}
	var walkErr error
	ast.Inspect(file, func(node ast.Node) bool {
		if walkErr != nil {
			return false
		}
		switch typed := node.(type) {
		case *ast.AssignStmt:
			recordBase(typed, bases)
			return true
		case *ast.GenDecl:
			recordBases(typed, bases)
			return true
		case *ast.CallExpr:
			selector, ok := typed.Fun.(*ast.SelectorExpr)
			if !ok || (selector.Sel.Name != "HandleFunc" && selector.Sel.Name != "Handle") {
				return true
			}
			if len(typed.Args) == 0 {
				walkErr = fmt.Errorf("%s: a %s call with no pattern", filename, selector.Sel.Name)
				return false
			}
			candidates++
			pattern, ok := resolvePattern(typed.Args[0], bases)
			if !ok {
				// THE REFUSAL MUST BE A STARTING POINT RATHER THAN A PUZZLE: the file and the LINE,
				// then what this parser can read and therefore what shape it just met. A guard whose
				// output does not say where costs the next reader the same hunt twice.
				walkErr = fmt.Errorf(
					"%s: cannot resolve the pattern of the %s call at %s: this parser reads string "+
						"literals, + concatenations of them, and identifiers declared by const, var or "+
						"assignment EARLIER IN THE SAME FILE - so the shape here is a helper call, a "+
						"value declared elsewhere, or a declaration this walk does not record",
					filename, selector.Sel.Name, fileSet.Position(typed.Pos()))
				return false
			}
			method, path, params, err := splitPattern(pattern)
			if err != nil {
				walkErr = fmt.Errorf("%s: %w", filename, err)
				return false
			}
			entry := RouteEntry{Method: method, Path: path, PathParams: params}
			if len(typed.Args) > 1 {
				entry.Handler = handlerName(typed.Args[1])
			}
			if doc, ok := docs[entry.Handler]; ok {
				entry.Description = doc
			}
			routes = append(routes, entry)
		}
		return true
	})
	if walkErr != nil {
		return nil, walkErr
	}
	// THE COUNT IS THE SYMPTOM CHECK: every registration call site must have produced an entry, so a
	// call the walk never recognized cannot pass as a smaller surface.
	if candidates != len(routes) {
		return nil, fmt.Errorf("%s: %d registration call sites but %d entries: a call site the parser "+
			"did not read is a missing route, not a smaller surface", filename, candidates, len(routes))
	}
	return routes, nil
}

// recordBases remembers const and var declarations whose value resolves, under the same
// nearest-preceding rule as assignments. A base declared with const or var is invisible to a walk that
// reads only assignments, and THAT IS THE SHAPE THIS PARSER REFUSED A REAL SITE ON: the witness
// resolver matches the declaration forms alike, which is why it read the sites this one refused.
func recordBases(decl *ast.GenDecl, bases map[string]string) {
	for _, spec := range decl.Specs {
		value, ok := spec.(*ast.ValueSpec)
		if !ok {
			continue
		}
		for index, name := range value.Names {
			if name.Name == "_" || index >= len(value.Values) {
				continue
			}
			if text, ok := resolvePattern(value.Values[index], bases); ok {
				bases[name.Name] = text
			}
		}
	}
}

// recordBase remembers a single-identifier assignment whose right-hand side resolves, so a pattern
// built from it can be evaluated. Anything else is left out rather than guessed, and a pattern that
// needs it then fails loudly at the call site.
func recordBase(assign *ast.AssignStmt, bases map[string]string) {
	if len(assign.Lhs) != 1 || len(assign.Rhs) != 1 {
		return
	}
	name, ok := assign.Lhs[0].(*ast.Ident)
	if !ok || name.Name == "_" {
		return
	}
	if value, ok := resolvePattern(assign.Rhs[0], bases); ok {
		bases[name.Name] = value
	}
}

// resolvePattern evaluates a registration's first argument under the witness's convention: a string
// literal is its own text, a concatenation is its parts in order, and an identifier is the value
// assigned to it earlier in the same file. ANYTHING ELSE - a computed pattern, a call, a constant this
// file does not assign - does not resolve, and the caller turns that into an error rather than a
// silently missing route.
func resolvePattern(expr ast.Expr, bases map[string]string) (string, bool) {
	switch value := expr.(type) {
	case *ast.BasicLit:
		if value.Kind != token.STRING {
			return "", false
		}
		text, err := strconv.Unquote(value.Value)
		if err != nil {
			return "", false
		}
		return text, true
	case *ast.ParenExpr:
		return resolvePattern(value.X, bases)
	case *ast.BinaryExpr:
		if value.Op != token.ADD {
			return "", false
		}
		left, ok := resolvePattern(value.X, bases)
		if !ok {
			return "", false
		}
		right, ok := resolvePattern(value.Y, bases)
		if !ok {
			return "", false
		}
		return left + right, true
	case *ast.Ident:
		text, ok := bases[value.Name]
		return text, ok
	}
	return "", false
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
	// AN EMPTY LIST, NOT A NIL ONE: a nil slice marshals to JSON null, and the page's type declares
	// pathParams as an array, so a route with no parameters would arrive as null and fail the
	// frontend's type check. A route with no parameters has an EMPTY list of them, and that is what
	// the artefact says.
	params = []string{}
	for _, match := range pathParam.FindAllStringSubmatch(path, -1) {
		if match[1] == "$" {
			// `{$}` is Go 1.22's exact-match marker rather than a parameter. The path keeps it, because
			// the artefact reports the pattern as registered; the parameter list does not, because the
			// marker names no value a handler receives.
			continue
		}
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
