package routes

import (
	"testing"

	taskdomain "agenthub/fastmcp/task_management/domain/entities"
)

// The api_tokens INTEGER columns reach the router as int64. A plain int assertion dropped them, so the
// token page showed usage_count 0 while last_used_at moved.
func TestTokenResponseFromMapKeepsInt64Counters(t *testing.T) {
	m := taskdomain.NewOrderedMap[any]()
	m.Set("usage_count", int64(42))
	m.Set("rate_limit", int64(1000))

	resp := tokenResponseFromMap(m)

	if resp.UsageCount == nil || *resp.UsageCount != 42 {
		t.Fatalf("usage_count = %v, want 42", resp.UsageCount)
	}
	if resp.RateLimit == nil || *resp.RateLimit != 1000 {
		t.Fatalf("rate_limit = %v, want 1000", resp.RateLimit)
	}
}
