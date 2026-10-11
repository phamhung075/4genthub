// The fixture-bring-up guard: a _test.go file brings a database schema up through testdb.CreateSchema
// (or not at all), and the only _test.go sites allowed to call CreateTables DIRECTLY are the three
// named below, each of which is ABOUT the boot itself.
//
// WHY IT EXISTS, with the cost attached. The gated carry step 0003_progress_history_carry_and_drop
// refuses on any database whose applied_migrations ledger holds no 0001_baseline row, and createAll
// populates the catalogue BEFORE the runner runs, so a fresh fixture database skips the frozen
// baseline without recording it and a bare cfg.CreateTables refuses with `SQLSTATE P0001`. Four
// shared helpers were brought up that way and took the suite down with 126 reds; the repair
// (92d3e825, c6392354) adopted testdb.CreateSchema - expect the refusal, record the operator's mark,
// boot again - and a hand-chosen battery of packages then missed three more fixtures, which stayed
// red with 12. That is the failure this check catches: every package can look green in review while
// one package's bring-up is the old shape, because the red only appears under a database URL.
//
// NO DATABASE AND NO CLUSTER: it is a SOURCE scan of the module, so it runs in the default
// `go test` on a machine with no Postgres. That is the point - the defect it catches is invisible in
// exactly that run.
//
// SILENCE IS THE DEFECT, which is why a tree with no call site at all FAILS rather than passes, and
// why an allowlist entry whose call site is gone FAILS too. A guard that finds nothing must not read
// as a clean tree.
//
// WHAT IT CANNOT SEE, stated so the blind spots are not mistaken for coverage:
//   - a call through a VARIABLE or a differently-named wrapper (`boot := cfg.CreateTables`): there is
//     no identifier `CreateTables` at the call site, so there is nothing to match. The direct call is
//     the shape every fixture here uses.
//   - a call the PREFILTER does not recognize, which is why the prefilter is an optimization and not the
//     rule. Before parsing, the scan asks whether the file's bytes contain `CreateTables(`, so the name
//     and its opening parenthesis must be ADJACENT in the raw bytes: `cfg.CreateTables (ctx)` (a space
//     before the parenthesis, which gofmt removes) or `CreateTables` followed by a newline and then `(`
//     never reaches the AST pass, and that file is treated as if it held no call at all. Two
//     consequences, in opposite directions: an unlisted call in such a file is NOT reported, and an
//     allowlist entry for that file's function would read as STALE, because the scan never recorded the
//     call the entry names. A split after the dot, or a receiver on its own line, is still seen - only
//     the name-to-parenthesis adjacency defeats the prefilter.
//   - whether a fixture that does call CreateSchema also asserts anything: this check is about the
//     bring-up path, not about the cases built on it.
//   - a violation in a file another seat writes while the walk runs: the walk can MISS a call site (a
//     file stashed or edited away mid-scan is simply not scanned) but it can never INVENT one, because
//     every finding cites a call this check actually read.
//   - anything under a DOT DIRECTORY, because the walk skips those: they hold the toolchain's own corpus
//     and this project's caches. The 3120 _test.go files with 2631 of them under
//     .gomodcache/.gocache/.gotmp/.claude are a count of the SHARED CHECKOUT the count was taken in, not
//     of this commit: in a clean worktree of the same commit the module measures 490 _test.go files and
//     NONE of them under those directories, so that pair cannot be cross-checked from a checkout. What IS
//     reproducible is the count the guard itself REPORTS on every run - 490 in that clean worktree - so
//     that a walk which skipped the real tree as well as the corpus is visible rather than silent.
package database_test

import (
	"bytes"
	"go/ast"
	"go/parser"
	"go/token"
	"io/fs"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"testing"
)

// createTablesSites are the only _test.go sites allowed to call CreateTables directly, keyed by file
// and enclosing function. Each carries the reason CreateSchema cannot serve it, because the reason is
// what makes an entry legitimate - an entry added to silence this check is the hand-chosen-list
// failure this check exists to stop.
var createTablesSites = []createTablesSite{
	{
		File:     "fastmcp/server/httpapp/migration_idempotence_test.go",
		Function: "TestSchemaMigrationIsIdempotentInProcess",
		Reason: "boots the same migration path a SECOND time, in-process, against a database that ALREADY " +
			"holds the schema; that re-run being a no-op is the property under test, and CreateSchema asserts " +
			"the FIRST boot refuses, so it cannot be used here",
	},
	{
		File:     "fastmcp/task_management/infrastructure/database/integration_test.go",
		Function: "TestRealPostgresCreateTablesAndSessions",
		Reason: "calls CreateTables a SECOND time immediately after testdb.CreateSchema, and the " +
			"checkfirst idempotence of that second boot is what the case asserts",
	},
	{
		File:     "fastmcp/task_management/infrastructure/database/progress_history_drop_integration_test.go",
		Function: "TestTheBootRefusesTheCarryStepOnAPopulatedDatabaseWithoutTheMark",
		Reason: "the case that MEASURES the refusal itself: it boots on a populated database holding no " +
			"0001_baseline row and asserts the error, so it must make the boot that refuses",
	},
}

// createTablesSite is one allowed direct call: the file, the function that encloses it, and why.
type createTablesSite struct {
	File     string
	Function string
	Reason   string
}

// createTablesCall is one call the scan found.
type createTablesCall struct {
	File     string
	Function string
	Line     int
}

func (c createTablesCall) String() string {
	return c.File + ":" + strconv.Itoa(c.Line) + " in " + c.Function
}

func TestFixturesBringUpTheSchemaThroughCreateSchema(t *testing.T) {
	root := moduleRoot(t)
	var (
		calls  []createTablesCall
		walked int
		naming int
	)
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			// A directory removed or renamed while the walk is inside it - another seat's checkout, a
			// branch switch - is tolerated: the entry was part of the tree when the walk listed it, and
			// a walk cannot be run against a tree several seats are editing without expecting it to move.
			if os.IsNotExist(err) {
				if entry != nil && entry.IsDir() {
					return fs.SkipDir
				}
				return nil
			}
			return err
		}
		if entry.IsDir() {
			name := entry.Name()
			if name == "testdata" || name == "node_modules" || strings.HasPrefix(name, ".") {
				return fs.SkipDir
			}
			return nil
		}
		if !strings.HasSuffix(entry.Name(), "_test.go") {
			return nil
		}
		walked++
		source, err := os.ReadFile(path)
		if err != nil {
			if os.IsNotExist(err) {
				return nil
			}
			return err
		}
		// Cheap prefilter: most test files never boot a schema.
		if !bytes.Contains(source, []byte("CreateTables(")) {
			return nil
		}
		naming++
		relative, relErr := filepath.Rel(root, path)
		if relErr != nil {
			relative = path
		}
		relative = filepath.ToSlash(relative)
		calls = append(calls, createTablesCallsIn(t, path, relative, source)...)
		return nil
	})
	if err != nil {
		t.Fatalf("scan %s: %v", root, err)
	}
	t.Logf("walked %d _test.go file(s) under %s (dot-directories skipped), %d of them naming CreateTables, "+
		"and found %d call site(s) in %d file(s)", walked, root, naming, len(calls), len(uniqueFiles(calls)))
	if walked == 0 {
		t.Fatal("the walk visited no _test.go file at all: the module root resolved to nothing, so this check " +
			"is reading an empty tree and its verdict would be silence rather than a check")
	}
	if len(calls) == 0 {
		t.Fatal("the scan found no CreateTables call site at all. The three sites this check allowlists are " +
			"still in the tree, so this is the scan failing to see the tree - a moved root, a renamed " +
			"predicate - and it is reported as a failure rather than as a clean tree, because silence is the " +
			"defect a guard against a missing bring-up must not have")
	}

	allowed := map[string]string{}
	for _, site := range createTablesSites {
		allowed[site.File+"|"+site.Function] = site.Reason
	}
	matched := map[string]bool{}
	sort.Slice(calls, func(i, j int) bool {
		if calls[i].File != calls[j].File {
			return calls[i].File < calls[j].File
		}
		return calls[i].Line < calls[j].Line
	})
	for _, call := range calls {
		key := call.File + "|" + call.Function
		if _, ok := allowed[key]; ok {
			matched[key] = true
			continue
		}
		t.Errorf("%s calls CreateTables directly. A fixture database needs the operator's 0001_baseline "+
			"mark, or the gated carry step refuses it with SQLSTATE P0001 - adopt testdb.CreateSchema(t, cfg), "+
			"which expects that refusal, records the mark and boots again. If the call is ABOUT the boot and "+
			"cannot use it, add %q with that function to createTablesSites in this file, with the reason.",
			call, call.File)
	}
	for _, site := range createTablesSites {
		if matched[site.File+"|"+site.Function] {
			continue
		}
		t.Errorf("createTablesSites still lists %s in %s, but no CreateTables call is there any more: remove "+
			"the entry, so the list keeps naming only the sites that are still the exception - and has a "+
			"stated reason for each.", site.Function, site.File)
	}
}

// createTablesCallsIn reads one file's CreateTables calls, each with the function that encloses it.
// The enclosing function is found by containment rather than by a stack: a call inside a closure reports
// the NAMED function it is written in, which is the unit an allowlist can name, and a call outside every
// function reports "<outside any function>" instead of hiding.
func createTablesCallsIn(t *testing.T, path, relative string, source []byte) []createTablesCall {
	t.Helper()
	fset := token.NewFileSet()
	parsed, parseErr := parser.ParseFile(fset, path, source, 0)
	if parseErr != nil {
		// ONE RE-READ, because a concurrent writer can present a TRUNCATED file: a genuine syntax error
		// survives a re-read, a truncated read does not.
		refreshed, readErr := os.ReadFile(path)
		if readErr != nil {
			if os.IsNotExist(readErr) {
				return nil
			}
			t.Fatalf("re-reading %s: %v", relative, readErr)
		}
		fset = token.NewFileSet()
		if parsed, parseErr = parser.ParseFile(fset, path, refreshed, 0); parseErr != nil {
			t.Fatalf("%s does not parse, so this check cannot read it: %v", relative, parseErr)
		}
	}
	type span struct {
		name       string
		start, end token.Pos
	}
	var functions []span
	for _, decl := range parsed.Decls {
		fn, ok := decl.(*ast.FuncDecl)
		if !ok || fn.Body == nil {
			continue
		}
		functions = append(functions, span{name: fn.Name.Name, start: fn.Body.Pos(), end: fn.Body.End()})
	}
	enclosing := func(pos token.Pos) string {
		name, innermost := "<outside any function>", token.NoPos
		for _, fn := range functions {
			if pos >= fn.start && pos <= fn.end && fn.start > innermost {
				name, innermost = fn.name, fn.start
			}
		}
		return name
	}
	var calls []createTablesCall
	ast.Inspect(parsed, func(node ast.Node) bool {
		call, ok := node.(*ast.CallExpr)
		if !ok || createTablesCallee(call.Fun) != "CreateTables" {
			return true
		}
		calls = append(calls, createTablesCall{
			File: relative, Function: enclosing(call.Pos()), Line: fset.Position(call.Pos()).Line,
		})
		return true
	})
	return calls
}

// createTablesCallee is the identifier a call goes through, ignoring a package qualifier.
func createTablesCallee(fun ast.Expr) string {
	switch typed := fun.(type) {
	case *ast.Ident:
		return typed.Name
	case *ast.SelectorExpr:
		return typed.Sel.Name
	case *ast.IndexExpr:
		return createTablesCallee(typed.X)
	case *ast.IndexListExpr:
		return createTablesCallee(typed.X)
	}
	return ""
}

// uniqueFiles is the number of files the calls were found in, for the count this check reports.
func uniqueFiles(calls []createTablesCall) []string {
	seen := map[string]bool{}
	var out []string
	for _, call := range calls {
		if seen[call.File] {
			continue
		}
		seen[call.File] = true
		out = append(out, call.File)
	}
	return out
}

// moduleRoot is THE PATH RESOLVED FROM THIS FILE'S OWN LOCATION rather than from the process working
// directory: `go test` runs with the cwd set to the package directory, so a root-relative literal
// resolves to nothing and the scan would report an empty tree. This file lives at
// <module>/fastmcp/task_management/infrastructure/database, so the root is four levels up.
func moduleRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("this guard cannot locate its own source file")
	}
	return filepath.Join(filepath.Dir(file), "..", "..", "..", "..")
}
