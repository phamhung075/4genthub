package httpapp

import (
	"context"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// TestContextLedgerAppenderRefusesWithoutAResolvedCaller pins the rule the 2026-10-15 defect forced:
// the context event is written under the CALLER's resolved id, so an append that cannot resolve one is
// REFUSED rather than written under an empty id - which is what the appender did for every caller
// before the fix (`NewTaskEventRepository(sessions, "", "")`, built once in NewApp).
//
// An empty id is not a harmless default here. The ledger's reads are scoped by user_id, so a row under
// the empty id is a row the caller's own history does not show; and the empty id shares the TASK's seq
// space with the caller's rows, because `uq_task_event_seq` is UNIQUE (task_id, seq) - which is how a
// freshly created task's first update came to answer 23505 and never recover.
func TestContextLedgerAppenderRefusesWithoutAResolvedCaller(t *testing.T) {
	// The auth chain falls back to a configured test user when the mode is `testing`, so the mode is
	// pinned: the case under test is the request that names no caller at all.
	t.Setenv("AUTH_ENABLED", "true")
	t.Setenv("MCP_AUTH_MODE", "production")

	appender := contextLedgerAppender{sessions: nil}
	_, err := appender.Append(context.Background(), entities.AppendTaskEvent{
		TaskID: "0d0f5f2a-0000-4000-8000-000000000000",
		Kind:   entities.TaskEventKindContextUpdated,
	})
	if err == nil {
		t.Fatal("an append with no caller in the context must be refused, not written under an empty id")
	}
}
