package httpapp

import (
	"context"
	"net/http"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

// TestNotifyRouteRefusesANotificationAddressedToAnotherUser is the regression proof for 338fe3a0.
//
// POST /api/v2/broadcast/notify resolved its offline recipients from the token's user AND from
// metadata.user_ids / metadata.user_id, so any authenticated user could store a notification into
// another user's dashboard, with the message and the sender (the frame's primary.from, which the
// dashboard renders as "from: message") chosen by the caller; the victim's next connect replayed it
// as a toast. No client presents a scope or a service identity that authorizes addressing another
// user, so a notification naming anyone but the caller is now refused and never reaches the
// broadcast.
func TestNotifyRouteRefusesANotificationAddressedToAnotherUser(t *testing.T) {
	const caller = "11111111-1111-4111-8111-111111111111"
	const other = "22222222-2222-4222-8222-222222222222"
	authenticateTestUser(t)

	var reached []string
	deps := testRouteDeps()
	deps.broadcast = func(_ context.Context, _, entityType, entityID, userID string, _, _ *entities.OrderedMap[any]) error {
		reached = append(reached, userID+" "+entityType+" "+entityID)
		return nil
	}
	mux := http.NewServeMux()
	mountBroadcastRoutes(mux, deps)

	cases := []struct {
		name     string
		metadata string
		want     int
	}{
		{"metadata.user_id names another user", `{"user_id":"` + other + `"}`, http.StatusForbidden},
		{"metadata.user_ids names another user", `{"user_ids":["` + other + `"]}`, http.StatusForbidden},
		{"metadata.user_ids names the caller and another user", `{"user_ids":["` + caller + `","` + other + `"]}`, http.StatusForbidden},
		{"metadata.user_id names the caller", `{"user_id":"` + caller + `"}`, http.StatusOK},
		{"no metadata targets", `{}`, http.StatusOK},
	}
	for _, tc := range cases {
		body := `{"event_type":"notification","entity_type":"notification","entity_id":"e1","metadata":` + tc.metadata + `}`
		rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/broadcast/notify", body)
		if rec.Code != tc.want {
			t.Fatalf("%s: status = %d, want %d (body=%s)", tc.name, rec.Code, tc.want, rec.Body)
		}
		if tc.want == http.StatusForbidden && !strings.Contains(rec.Body.String(), other) {
			t.Fatalf("%s: the refusal does not name %s: %s", tc.name, other, rec.Body)
		}
	}

	// Only the two accepted frames reached the broadcast, and every one of them was addressed to the
	// caller: a refused frame never got as far as resolving recipients.
	if len(reached) != 2 {
		t.Fatalf("broadcast invocations = %d, want 2 (%v)", len(reached), reached)
	}
	for _, got := range reached {
		if !strings.HasPrefix(got, caller+" ") {
			t.Fatalf("broadcast user = %q, want the caller %q", got, caller)
		}
	}
}

// TestNotifyRouteRefusesAnyFrameThatNamesAnotherUser is the WIDENED rule, and it replaces the case
// that pinned the old one: the guard used to fire only for entity_type "notification", so a TASK
// frame naming another user was accepted and stored for them - a cross-user write whose text and
// title the caller chose, and the dashboard toasts the task case too
// (agenthub-frontend/src/hooks/useRealtimeSync.ts:161-162). The route now refuses any client-submitted
// frame whose metadata names a user other than the caller, for every entity type, because the
// recipients `routes.BroadcastDataChange` resolves and stores for are resolved from metadata for all
// of them. The shapes that must still pass are asserted with a non-notification entity type, so this
// file cannot pass by refusing everything.
func TestNotifyRouteRefusesAnyFrameThatNamesAnotherUser(t *testing.T) {
	const caller = "11111111-1111-4111-8111-111111111111"
	const other = "22222222-2222-4222-8222-222222222222"
	authenticateTestUser(t)

	var reached []string
	deps := testRouteDeps()
	deps.broadcast = func(_ context.Context, _, entityType, entityID, userID string, _, _ *entities.OrderedMap[any]) error {
		reached = append(reached, userID+" "+entityType+" "+entityID)
		return nil
	}
	mux := http.NewServeMux()
	mountBroadcastRoutes(mux, deps)

	refused := []struct {
		name string
		body string
	}{
		{"a task frame naming another user in user_ids", `{"event_type":"updated","entity_type":"task","entity_id":"task-9","metadata":{"user_ids":["` + other + `"]}}`},
		{"a task frame naming another user in user_id", `{"event_type":"updated","entity_type":"task","entity_id":"task-9","metadata":{"user_id":"` + other + `"}}`},
		{"a project frame naming the caller and another user", `{"event_type":"updated","entity_type":"project","entity_id":"p-1","metadata":{"user_ids":["` + caller + `","` + other + `"]}}`},
	}
	for _, tc := range refused {
		rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/broadcast/notify", tc.body)
		if rec.Code != http.StatusForbidden {
			t.Fatalf("%s: status = %d, want 403 (body=%s)", tc.name, rec.Code, rec.Body)
		}
		if !strings.Contains(rec.Body.String(), other) {
			t.Fatalf("%s: the refusal does not name %s: %s", tc.name, other, rec.Body)
		}
	}

	// The same entity types, addressed to the caller alone or to nobody, still reach the broadcast -
	// and a refused frame never got as far as resolving recipients.
	allowed := []struct {
		name string
		body string
	}{
		{"a task frame naming only the caller", `{"event_type":"updated","entity_type":"task","entity_id":"task-9","metadata":{"user_id":"` + caller + `"}}`},
		{"a task frame with no metadata targets", `{"event_type":"updated","entity_type":"task","entity_id":"task-9","metadata":{}}`},
	}
	for _, tc := range allowed {
		rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/broadcast/notify", tc.body)
		if rec.Code != http.StatusOK {
			t.Fatalf("%s: status = %d, want 200 (body=%s)", tc.name, rec.Code, rec.Body)
		}
	}
	if len(reached) != len(allowed) {
		t.Fatalf("broadcast invocations = %v, want %d (one per accepted frame)", reached, len(allowed))
	}
	for _, got := range reached {
		if !strings.HasPrefix(got, caller+" task ") {
			t.Fatalf("broadcast invocation = %q, want the caller %q addressing a task", got, caller)
		}
	}
}
