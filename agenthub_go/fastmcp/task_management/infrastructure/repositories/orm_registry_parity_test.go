package repositories_test

// The registry parity check: every table name a repository constructor asks the shared ORM
// registry for must exist in database.Tables.
//
// WHY IT EXISTS, with the cost attached. NewORMRepository (base_orm_repository.go:52-66) resolves
// a table BY NAME from the registry at RUNTIME, and the composition root constructs repositories
// while the process starts. So a repository whose TableDef is missing - or was held back in a
// serialized commit - does not fail the build, does not fail any test that does not construct it,
// and kills the process with `unknown table "<name>"` before it can serve anything. That is what
// happened on 2026-10-06: `go build`, `go vet` and the package tests were all green while
// cmd/agenthub exited 1 (`app: unknown table "seat_feedback"`). The only test that called NewApp
// skips without a database URL, so nothing in the DEFAULT run constructed the app.
//
// This check therefore runs in the default run: no database, no environment variable, no
// construction. It is a SOURCE scan of the constructor call sites, which is the honest form here -
// the alternative (calling every constructor) needs a database and a hand-maintained list, and a
// hand-maintained list is exactly how the defect slipped past the existing constructor test.
//
// WHAT IT CANNOT SEE, stated so the blind spots are not mistaken for coverage:
//   - a table name that is not a string literal at the call site. The check FAILS on one instead
//     of skipping it, so the gap cannot open silently; forwarding constructors are an explicit
//     allowlist below, and a new one must be added deliberately.
//   - a repository that reaches its table by raw SQL instead of asking the registry: it never
//     asks, so there is nothing to compare. Its own runtime failure is a different class.
//   - whether the TableDef's COLUMNS match the row struct: TestSeatTableMetadataMatchesStructs
//     and the seat DDL guard own that.
//   - whether the table exists in a LIVE database: that is the migration's business. A migrated
//     schema is what app_boot_test.go checks, and it needs a database to do it.

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

	taskdb "agenthub/fastmcp/task_management/infrastructure/database"

	// The registry is filled by init() functions in the packages that own tables, so every such
	// package has to be linked in for this check to see the whole registry - otherwise its tables
	// look unregistered and this test fails with a message that names the wrong cause. The three
	// below are the ones that append to the shared registry today; a new one must be added here,
	// and the failure is loud (the table is reported missing) rather than silent.
	_ "agenthub/fastmcp/auth/infrastructure/database"            // users, user_token_balances
	_ "agenthub/fastmcp/auth/infrastructure/repositories"        // email_tokens
	_ "agenthub/fastmcp/seat_management/infrastructure/database" // the seat_management tables
)

// tableNameConstructors are the constructors whose FIRST argument is a table name. The two
// forwarding ones are included so their call sites are checked too.
var tableNameConstructors = map[string]bool{
	"NewORMRepository":           true,
	"NewUserScopedORMRepository": true,
	"NewBaseTimestampRepository": true,
}

// forwardingSites are the only call sites allowed to pass a table name THROUGH from their caller
// instead of writing a literal. Their callers pass literals and are checked here; a new forwarding
// site must be added deliberately rather than being invisible to this check.
var forwardingSites = map[string]bool{
	"fastmcp/task_management/infrastructure/repositories/base_timestamp_repository.go":  true,
	"fastmcp/task_management/infrastructure/repositories/user_scoped_orm_repository.go": true,
}

func TestORMRepositoriesAskForRegisteredTables(t *testing.T) {
	root := moduleRoot(t)
	registered := map[string]bool{}
	for _, def := range taskdb.Tables {
		registered[def.Name] = true
	}
	if len(registered) == 0 {
		t.Fatal("the shared registry is empty: the check would pass vacuously")
	}

	asked := map[string][]string{}
	err := filepath.WalkDir(root, func(path string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if entry.IsDir() {
			// Test data and vendored trees hold no constructor the server runs.
			if name := entry.Name(); name == "testdata" || name == "node_modules" || name == ".git" {
				return fs.SkipDir
			}
			return nil
		}
		if !strings.HasSuffix(entry.Name(), ".go") || strings.HasSuffix(entry.Name(), "_test.go") {
			return nil
		}
		source, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		// Cheap prefilter: most files declare no repository at all.
		if !bytes.Contains(source, []byte("NewORMRepository[")) &&
			!bytes.Contains(source, []byte("NewUserScopedORMRepository[")) &&
			!bytes.Contains(source, []byte("NewBaseTimestampRepository[")) {
			return nil
		}
		relative, relErr := filepath.Rel(root, path)
		if relErr != nil {
			relative = path
		}
		relative = filepath.ToSlash(relative)
		fset := token.NewFileSet()
		parsed, parseErr := parser.ParseFile(fset, path, source, 0)
		if parseErr != nil {
			return parseErr
		}
		ast.Inspect(parsed, func(node ast.Node) bool {
			call, ok := node.(*ast.CallExpr)
			if !ok || len(call.Args) == 0 {
				return true
			}
			if !tableNameConstructors[calleeName(call.Fun)] {
				return true
			}
			literal, isLiteral := call.Args[0].(*ast.BasicLit)
			if !isLiteral || literal.Kind != token.STRING {
				if !forwardingSites[relative] {
					t.Errorf("%s:%d calls %s with a table name that is not a string literal: this check cannot verify it, so make it a literal or add the file to forwardingSites with the reason",
						relative, fset.Position(call.Pos()).Line, calleeName(call.Fun))
				}
				return true
			}
			name, unquoteErr := strconv.Unquote(literal.Value)
			if unquoteErr != nil {
				t.Errorf("%s: unreadable table name literal %s", relative, literal.Value)
				return true
			}
			asked[name] = append(asked[name], relative)
			return true
		})
		return nil
	})
	if err != nil {
		t.Fatalf("scan %s: %v", root, err)
	}
	if len(asked) == 0 {
		t.Fatal("the scan found no repository constructor call site: the check would pass vacuously")
	}

	names := make([]string, 0, len(asked))
	for name := range asked {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		if registered[name] {
			continue
		}
		sites := asked[name]
		sort.Strings(sites)
		t.Errorf("table %q has no TableDef in the shared registry, but a repository asks for it by name (%s). "+
			"NewORMRepository resolves the name at RUNTIME, so this compiles, passes every test that does not "+
			"construct the repository, and kills the process at startup with `unknown table %q`. Register the "+
			"table's TableDef and DDL in the same commit as the repository.",
			name, strings.Join(unique(sites), ", "), name)
	}
}

// calleeName is the identifier a call goes through, ignoring a package qualifier.
func calleeName(fun ast.Expr) string {
	switch typed := fun.(type) {
	case *ast.Ident:
		return typed.Name
	case *ast.SelectorExpr:
		return typed.Sel.Name
	case *ast.IndexExpr:
		return calleeName(typed.X)
	case *ast.IndexListExpr:
		return calleeName(typed.X)
	}
	return ""
}

// moduleRoot walks up from this file to the directory holding go.mod.
func moduleRoot(t *testing.T) string {
	t.Helper()
	_, thisFile, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime.Caller(0) failed")
	}
	dir := filepath.Dir(thisFile)
	for {
		if _, err := os.Stat(filepath.Join(dir, "go.mod")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			t.Fatalf("no go.mod above %s", filepath.Dir(thisFile))
		}
		dir = parent
	}
}

func unique(items []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(items))
	for _, item := range items {
		if seen[item] {
			continue
		}
		seen[item] = true
		out = append(out, item)
	}
	return out
}
