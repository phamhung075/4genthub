package httpapp

import (
	"context"
	"testing"
)

func TestRecordToolCallKeysByToolAndAction(t *testing.T) {
	var got []string
	a := &App{tokenOperations: func(_ context.Context, tokenID, operation string) {
		got = append(got, tokenID+"|"+operation)
	}}
	id := "tok_1"

	a.recordToolCall(context.Background(), &id, "manage_task", map[string]any{"action": "create"})
	a.recordToolCall(context.Background(), &id, "get_mcp_status", map[string]any{})
	a.recordToolCall(context.Background(), nil, "manage_task", map[string]any{"action": "list"})

	want := []string{"tok_1|manage_task.create", "tok_1|get_mcp_status"}
	if len(got) != len(want) || got[0] != want[0] || got[1] != want[1] {
		t.Fatalf("recorded %v, want %v", got, want)
	}
}
