package session_stream

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"os/exec"
	"sort"
	"strings"
	"testing"

	"agenthub/fastmcp/session_stream/testdb"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TestStreamTablesMatchThePythonSchema compares the Postgres schema the Go models create for
// agent_sessions and agent_session_events with testdata/stream_tables_python_ddl.txt, the FROZEN
// snapshot of the schema Python's Base.metadata.create_all created for the same two tables: columns
// (type, length, nullability, default and ordinal position), constraints and indexes. The file's own
// header says what it is and why it can never be re-derived.
//
// The comparison is a SET comparison against the snapshot PLUS the deliberate divergences declared in
// declaredStreamSchemaDivergences, and it fails in BOTH directions: a line the database has and
// neither the snapshot nor a declaration explains is undeclared drift, while a declaration the
// database no longer holds, holds differently, or pairs with a commit this repository does not have is
// a stale claim. That is what stops this file from decaying into a snapshot of Go's own state: it
// keeps asking whether a difference was intended, which a silent overwrite could no longer ask.
//
// It needs a Postgres (AGENTHUB_TEST_PG_URL, see repository_test.go) and skips without one - the
// comparator's own logic is pinned without a database by TestTheSnapshotComparisonCatchesBothDirections.
func TestStreamTablesMatchThePythonSchema(t *testing.T) {
	sessions := testdb.NewSessions(t)
	frozen, err := os.ReadFile("testdata/stream_tables_python_ddl.txt")
	if err != nil {
		t.Fatal(err)
	}
	live, err := streamTableDDL(context.Background(), sessions)
	if err != nil {
		t.Fatal(err)
	}
	if findings := snapshotFindings(string(frozen), live, declaredStreamSchemaDivergences); len(findings) > 0 {
		t.Fatalf("the Go schema is not the frozen snapshot plus the declared divergences:\n  %s",
			strings.Join(findings, "\n  "))
	}
}

// declaredDivergence is one deliberate difference between the Go schema and the frozen snapshot. Line
// is the rendered dump line EXACTLY as the database must print it, so a declaration is a claim that
// has to keep holding rather than a comment beside it, and Commit is the change that made the
// difference - it must exist in this repository, or the declaration is stale.
type declaredDivergence struct {
	Table  string
	Kind   string // "table", "col", "con" or "idx"
	Name   string
	Line   string
	Commit string
	Why    string
}

// declaredStreamSchemaDivergences is every deliberate divergence from the frozen snapshot, which is
// the whole set the snapshot's header points at. A declaration REPLACES the snapshot's line for its
// key, so a column an insertion shifts can be declared here rather than rewritten in the snapshot.
var declaredStreamSchemaDivergences = []declaredDivergence{
	{"agent_sessions", "col", "room_slug",
		"col room_slug | character varying | 255 | YES | None | 11",
		"14210172", "the session carries the seat it belongs to (row 655227df)"},
	{"agent_sessions", "col", "seat_key",
		"col seat_key | character varying | 255 | YES | None | 12",
		"14210172", "the same pair, carried together or not at all"},
	{"agent_sessions", "con", "ck_agent_sessions_seat_pair",
		"con ck_agent_sessions_seat_pair | CHECK (((room_slug IS NULL) = (seat_key IS NULL)))",
		"14210172", "the pair rule, stated to the database"},
}

// commitExists reports whether this repository has the commit a declaration names, by git cat-file -e.
// A seam, so the comparison's own logic can be tested without a repository to ask.
var commitExists = func(hash string) bool {
	return exec.Command("git", "cat-file", "-e", hash).Run() == nil
}

// snapshotEntry is one line of a schema dump, identified within its table by kind and name. The
// rendered line carries the ordinal position of every column, so a reordering is a difference here
// like any other.
type snapshotEntry struct{ table, kind, name, line string }

func snapshotKey(table, kind, name string) string { return table + "|" + kind + "|" + name }

// parseSchemaDump reads a dump, and reports every line it cannot read: a comparator that quietly
// ignores what it does not understand is how a snapshot stops being a snapshot. Lines starting with
// "#" are the frozen file's header and blank lines are nothing.
func parseSchemaDump(dump string) (map[string]snapshotEntry, []string) {
	entries := make(map[string]snapshotEntry)
	var unreadable []string
	table := ""
	for _, raw := range strings.Split(strings.TrimRight(dump, "\n"), "\n") {
		line := strings.TrimRight(raw, "\r")
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		kind, rest, found := strings.Cut(line, " ")
		if !found {
			unreadable = append(unreadable, line)
			continue
		}
		if kind == "==" {
			name, ok := strings.CutPrefix(rest, "table ")
			if !ok || name == "" {
				unreadable = append(unreadable, line)
				continue
			}
			table = name
			entries[snapshotKey(table, "table", table)] = snapshotEntry{table, "table", table, line}
			continue
		}
		if kind != "col" && kind != "con" && kind != "idx" {
			unreadable = append(unreadable, line)
			continue
		}
		name, _, found := strings.Cut(rest, " | ")
		if table == "" || !found || name == "" {
			unreadable = append(unreadable, line)
			continue
		}
		entries[snapshotKey(table, kind, name)] = snapshotEntry{table, kind, name, line}
	}
	return entries, unreadable
}

// snapshotFindings returns every difference between the live schema and the frozen snapshot that the
// declarations do not explain, in both directions, sorted so a failure reads the same twice. Empty
// means the schema is exactly the snapshot plus the declared divergences.
func snapshotFindings(frozen, live string, declared []declaredDivergence) []string {
	frozenEntries, frozenUnreadable := parseSchemaDump(frozen)
	liveEntries, liveUnreadable := parseSchemaDump(live)
	var findings []string
	for _, line := range frozenUnreadable {
		findings = append(findings, "the frozen snapshot has a line this comparison cannot read: "+line)
	}
	for _, line := range liveUnreadable {
		findings = append(findings, "the database printed a line this comparison cannot read: "+line)
	}

	covered := make(map[string]bool, len(declared))
	for _, d := range declared {
		key := snapshotKey(d.Table, d.Kind, d.Name)
		if covered[key] {
			findings = append(findings, "the declaration for "+key+" is stated twice")
			continue
		}
		covered[key] = true
		if !commitExists(d.Commit) {
			findings = append(findings, fmt.Sprintf(
				"STALE COMMIT: the declaration for %s names %s, which this repository does not have", key, d.Commit))
		}
		if was, inSnapshot := frozenEntries[key]; inSnapshot && was.line == d.Line {
			findings = append(findings, "REDUNDANT: the declaration for "+key+" repeats a line the snapshot already has")
			continue
		}
		got, inLive := liveEntries[key]
		if !inLive {
			findings = append(findings, fmt.Sprintf(
				"STALE: the declaration for %s claims %q, and the database has no such line", key, d.Line))
			continue
		}
		if got.line != d.Line {
			findings = append(findings, fmt.Sprintf(
				"STALE: the declaration for %s claims %q, and the database has %q", key, d.Line, got.line))
		}
	}

	for key, want := range frozenEntries {
		if covered[key] {
			continue
		}
		got, inLive := liveEntries[key]
		switch {
		case !inLive:
			findings = append(findings, fmt.Sprintf("MISSING: the snapshot has %q and the database does not", want.line))
		case got.line != want.line:
			findings = append(findings, fmt.Sprintf("CHANGED: the snapshot has %q and the database has %q", want.line, got.line))
		}
	}
	for key, got := range liveEntries {
		if covered[key] {
			continue
		}
		if _, inSnapshot := frozenEntries[key]; inSnapshot {
			continue
		}
		findings = append(findings, fmt.Sprintf(
			"UNDECLARED: the database has %q, and neither the snapshot nor a declaration explains it", got.line))
	}
	sort.Strings(findings)
	return findings
}

// streamTableDDL prints the two tables as catalog rows, one line per column, constraint
// and index, in the format of the golden file.
func streamTableDDL(ctx context.Context, sessions *database.SessionManager) (string, error) {
	var lines []string
	err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		for _, table := range []string{"agent_sessions", "agent_session_events"} {
			lines = append(lines, "== table "+table)
			rows, err := s.QueryContext(ctx, `select column_name, data_type, character_maximum_length, is_nullable, column_default, ordinal_position
				from information_schema.columns where table_schema='public' and table_name=$1 order by ordinal_position`, table)
			if err != nil {
				return err
			}
			for rows.Next() {
				var name, dataType, nullable string
				var maxLen, def sql.NullString
				var position int
				if err := rows.Scan(&name, &dataType, &maxLen, &nullable, &def, &position); err != nil {
					rows.Close()
					return err
				}
				lines = append(lines, fmt.Sprintf("col %s | %s | %s | %s | %s | %d", name, dataType, orNone(maxLen), nullable, orNone(def), position))
			}
			rows.Close()

			rows, err = s.QueryContext(ctx, `select conname, pg_get_constraintdef(oid) from pg_constraint where conrelid=$1::regclass order by conname`, table)
			if err != nil {
				return err
			}
			for rows.Next() {
				var name, def string
				if err := rows.Scan(&name, &def); err != nil {
					rows.Close()
					return err
				}
				lines = append(lines, "con "+name+" | "+def)
			}
			rows.Close()

			rows, err = s.QueryContext(ctx, `select indexname, indexdef from pg_indexes where schemaname='public' and tablename=$1 order by indexname`, table)
			if err != nil {
				return err
			}
			for rows.Next() {
				var name, def string
				if err := rows.Scan(&name, &def); err != nil {
					rows.Close()
					return err
				}
				lines = append(lines, "idx "+name+" | "+def)
			}
			rows.Close()
		}
		return nil
	})
	return strings.Join(lines, "\n") + "\n", err
}

func orNone(v sql.NullString) string {
	if !v.Valid {
		return "None"
	}
	return v.String
}

// The comparison's own logic, pinned WITHOUT a database: the gated test above skips by default, and a
// comparator nobody exercises is a claim rather than a check. Each case is one way a schema stops
// agreeing with the snapshot, and both directions have to fire - a line nobody explains, a snapshot
// line the database lost, a column whose position moved, a declaration the database has differently or
// not at all, a declaration repeating the snapshot, a declaration naming a commit this repository does
// not have, and a line the comparison cannot read.
func TestTheSnapshotComparisonCatchesBothDirections(t *testing.T) {
	col := func(name, rest string) string { return "col " + name + " | " + rest }
	twoColumns := "== table t\n" + col("a", "integer | None | NO | None | 1") + "\n" +
		col("b", "integer | None | NO | None | 2") + "\n"

	prev := commitExists
	defer func() { commitExists = prev }()
	commitExists = func(hash string) bool { return hash == "abcdef1" }

	cases := []struct {
		name     string
		frozen   string
		live     string
		declared []declaredDivergence
		want     []string
	}{
		{name: "an identical schema is no finding", frozen: twoColumns, live: twoColumns},
		{name: "a column nobody declared", frozen: twoColumns,
			live: twoColumns + col("c", "integer | None | NO | None | 3") + "\n",
			want: []string{`UNDECLARED: the database has "col c | integer | None | NO | None | 3", and neither the snapshot nor a declaration explains it`}},
		{name: "a snapshot column the database lost", frozen: twoColumns,
			live: "== table t\n" + col("a", "integer | None | NO | None | 1") + "\n",
			want: []string{`MISSING: the snapshot has "col b | integer | None | NO | None | 2" and the database does not`}},
		{name: "a column whose position moved", frozen: twoColumns,
			live: "== table t\n" + col("a", "integer | None | NO | None | 1") + "\n" +
				col("b", "integer | None | NO | None | 3") + "\n",
			want: []string{`CHANGED: the snapshot has "col b | integer | None | NO | None | 2" and the database has "col b | integer | None | NO | None | 3"`}},
		{name: "a declared column the database has, differently", frozen: twoColumns, live: twoColumns,
			declared: []declaredDivergence{{"t", "col", "b", "col b | integer | None | NO | None | 9", "abcdef1", "a wrong claim"}},
			want:     []string{`STALE: the declaration for t|col|b claims "col b | integer | None | NO | None | 9", and the database has "col b | integer | None | NO | None | 2"`}},
		{name: "a declared column the database does not have", frozen: twoColumns, live: twoColumns,
			declared: []declaredDivergence{{"t", "col", "z", "col z | integer | None | NO | None | 9", "abcdef1", "gone"}},
			want:     []string{`STALE: the declaration for t|col|z claims "col z | integer | None | NO | None | 9", and the database has no such line`}},
		{name: "a declaration repeating the snapshot", frozen: twoColumns, live: twoColumns,
			declared: []declaredDivergence{{"t", "col", "a", "col a | integer | None | NO | None | 1", "abcdef1", "nothing new"}},
			want:     []string{"REDUNDANT: the declaration for t|col|a repeats a line the snapshot already has"}},
		{name: "a declaration naming a commit this repository does not have", frozen: twoColumns, live: twoColumns,
			declared: []declaredDivergence{{"t", "col", "a", "col a | integer | None | NO | None | 1", "deadbee", "no such commit"}},
			want: []string{
				"REDUNDANT: the declaration for t|col|a repeats a line the snapshot already has",
				"STALE COMMIT: the declaration for t|col|a names deadbee, which this repository does not have",
			}},
		{name: "a declared column is explained", frozen: twoColumns,
			live:     twoColumns + col("c", "integer | None | NO | None | 3") + "\n",
			declared: []declaredDivergence{{"t", "col", "c", "col c | integer | None | NO | None | 3", "abcdef1", "deliberate"}}},
		{name: "a mid-table insert needs the new column AND the shifted one declared", frozen: twoColumns,
			live: "== table t\n" + col("a", "integer | None | NO | None | 1") + "\n" +
				col("c", "integer | None | NO | None | 2") + "\n" + col("b", "integer | None | NO | None | 3") + "\n",
			declared: []declaredDivergence{
				{"t", "col", "c", "col c | integer | None | NO | None | 2", "abcdef1", "the new column"},
				{"t", "col", "b", "col b | integer | None | NO | None | 3", "abcdef1", "pushed down by the new column"},
			}},
		{name: "the same insert with only the shifted column declared is not enough", frozen: twoColumns,
			live: "== table t\n" + col("a", "integer | None | NO | None | 1") + "\n" +
				col("c", "integer | None | NO | None | 2") + "\n" + col("b", "integer | None | NO | None | 3") + "\n",
			declared: []declaredDivergence{{"t", "col", "b", "col b | integer | None | NO | None | 3", "abcdef1", "pushed down by the new column"}},
			want:     []string{`UNDECLARED: the database has "col c | integer | None | NO | None | 2", and neither the snapshot nor a declaration explains it`}},
		{name: "a line the comparison cannot read", frozen: twoColumns + "garbage\n", live: twoColumns,
			want: []string{"the frozen snapshot has a line this comparison cannot read: garbage"}},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			got := snapshotFindings(c.frozen, c.live, c.declared)
			if strings.Join(got, "\n") != strings.Join(c.want, "\n") {
				t.Errorf("findings:\n  %s\nwant:\n  %s", strings.Join(got, "\n  "), strings.Join(c.want, "\n  "))
			}
		})
	}
}
