package httpapp

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// TestBroadcastNotifyIsAuthedAndIgnoresBodyUser is the regression proof for the unauthenticated
// write path: POST /api/v2/broadcast/notify had no auth wrapper and took the target user from the
// request body, so anyone could forge a notification for any user. The ingress takes the user
// token and the target user is that token's user; a user_id in the body cannot move the write.
func TestBroadcastNotifyIsAuthedAndIgnoresBodyUser(t *testing.T) {
	const owner = "11111111-1111-4111-8111-111111111111"
	authenticateTestUser(t)

	var gotUser string
	broadcasts := 0
	deps := testRouteDeps()
	deps.broadcast = func(_ context.Context, _, _, _, userID string, _, _ *entities.OrderedMap[any]) error {
		broadcasts++
		gotUser = userID
		return nil
	}
	mux := http.NewServeMux()
	mountBroadcastRoutes(mux, deps)

	// The forged user_id is the whole point: it must never reach the broadcast.
	body := `{"event_type":"notification","entity_type":"notification","entity_id":"e1","user_id":"22222222-2222-4222-8222-222222222222"}`

	cases := []struct {
		name string
		auth string
		want int
	}{
		{"no Authorization header", "", http.StatusForbidden},
		{"valid user token", "Bearer test-token", http.StatusOK},
	}
	for _, tc := range cases {
		req := httptest.NewRequest(http.MethodPost, "/api/v2/broadcast/notify", strings.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		if tc.auth != "" {
			req.Header.Set("Authorization", tc.auth)
		}
		rec := httptest.NewRecorder()
		mux.ServeHTTP(rec, req)
		if rec.Code != tc.want {
			t.Fatalf("%s: status = %d, want %d (body=%s)", tc.name, rec.Code, tc.want, rec.Body)
		}
	}

	if broadcasts != 1 {
		t.Fatalf("broadcast invocations = %d, want 1 (only the authenticated request)", broadcasts)
	}
	if gotUser != owner {
		t.Fatalf("broadcast user = %q, want the token's user %q (the body said the other user)", gotUser, owner)
	}
}
