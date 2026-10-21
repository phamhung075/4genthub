package httpapp

// The ledger's READ half answered a flat 500 with nothing anywhere naming the cause: routes.GetTaskEvents
// drops the error, as its write sibling drops the writer's, and only the write path logged. Measured on
// the deployed server 2026-10-21 - every task's events answered 500 while the same ledger's writes and
// its progress-number read succeeded - the only record of which statement broke would have been this
// line, and it did not exist. The test forces the read to fail the cheapest way available without
// touching a database: a manager with no configuration cannot hand out a session.

import (
	"bytes"
	"context"
	"log"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/infrastructure/database"
)

func TestTheEventsReadLogsWhyItFailed(t *testing.T) {
	var logged bytes.Buffer
	previous := log.Writer()
	log.SetOutput(&logged)
	t.Cleanup(func() { log.SetOutput(previous) })

	reader := taskEventReaderAdapter{sessions: database.NewSessionManager(&database.DatabaseConfig{})}
	found, err := reader.ListTaskEvents(context.Background(), "b7a2c44c", 0, "b7a2c44c-90f4-464f-8596-de450ffe2a6b")
	if err == nil {
		t.Fatal("a manager with no configuration handed out a session")
	}
	if found != nil {
		t.Fatalf("a failed read returned rows: %d", len(found))
	}

	line := logged.String()
	for _, want := range []string{"events: task b7a2c44c: ListTaskEvents failed:", err.Error()} {
		if !strings.Contains(line, want) {
			t.Fatalf("the log line does not carry %q; it holds %q", want, line)
		}
	}
}
