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

// TestNotifyRouteLeavesOtherEntityTypesAddressedToSeveralUsers pins the other half of 338fe3a0: the
// guard is for notifications. routes.BroadcastDataChange is the common fan-out, and its metadata
// targeting is how an entity type that is legitimately addressed to several users reaches them, so
// the route must keep forwarding that metadata unchanged for those types.
func TestNotifyRouteLeavesOtherEntityTypesAddressedToSeveralUsers(t *testing.T) {
	const other = "22222222-2222-4222-8222-222222222222"
	authenticateTestUser(t)

	var gotMetadata *entities.OrderedMap[any]
	deps := testRouteDeps()
	deps.broadcast = func(_ context.Context, _, _, _, _ string, _, metadata *entities.OrderedMap[any]) error {
		gotMetadata = metadata
		return nil
	}
	mux := http.NewServeMux()
	mountBroadcastRoutes(mux, deps)

	body := `{"event_type":"updated","entity_type":"task","entity_id":"task-9","metadata":{"user_ids":["` + other + `"]}}`
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/broadcast/notify", body)
	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body=%s)", rec.Code, rec.Body)
	}
	if gotMetadata == nil {
		t.Fatal("the broadcast did not receive the metadata")
	}
	list, _ := gotMetadata.Get("user_ids")
	ids, ok := list.([]any)
	if !ok || len(ids) != 1 || ids[0] != other {
		t.Fatalf("metadata.user_ids reaching the fan-out = %v, want [%s]", list, other)
	}
}
