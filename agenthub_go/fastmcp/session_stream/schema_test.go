package session_stream

import (
	"context"
	"database/sql"
	"fmt"
	"os"
	"strings"
	"testing"

	"agenthub/fastmcp/session_stream/testdb"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TestStreamTablesMatchThePythonSchema compares the Postgres schema the Go models create
// for agent_sessions and agent_session_events with testdata/stream_tables_python_ddl.txt,
// the schema Python's Base.metadata.create_all creates for the same two tables: columns
// (type, length, nullability, default), constraints and indexes.
//
// It needs a Postgres (AGENTHUB_TEST_PG_URL, see repository_test.go) and skips without one.
// To regenerate the golden file, create the two tables from the Python models in an empty
// database and print them with the same catalog queries as streamTableDDL:
//
//	cd agenthub_main/src && PYTHONPATH=. ../venv/bin/python -c "
//	import sqlalchemy
//	from fastmcp.task_management.infrastructure.database.models import AgentSession, AgentSessionEvent
//	e = sqlalchemy.create_engine('postgresql+psycopg2://postgres@127.0.0.1:54329/<empty db>')
//	AgentSession.metadata.create_all(e, tables=[AgentSession.__table__, AgentSessionEvent.__table__])"
func TestStreamTablesMatchThePythonSchema(t *testing.T) {
	sessions := testdb.NewSessions(t)
	want, err := os.ReadFile("testdata/stream_tables_python_ddl.txt")
	if err != nil {
		t.Fatal(err)
	}

	got, err := streamTableDDL(context.Background(), sessions)
	if err != nil {
		t.Fatal(err)
	}

	if got != string(want) {
		t.Fatalf("Go schema differs from the Python schema\n--- python\n%s\n--- go\n%s", want, got)
	}
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
