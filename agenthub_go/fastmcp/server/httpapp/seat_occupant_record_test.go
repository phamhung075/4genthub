package httpapp

// The occupant record on the HTTP surface: the actor is the authenticated caller and never a
// request field, and GET .../occupant-history answers with what was recorded. The record itself
// is written in the repository's transaction (occupant_change_repository_test.go).

import (
	"context"
	"net/http"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/seat_management/domain/repositories"
)

const occupantHistoryPath = "/api/v2/rooms/dev/seats/alice/occupant-history"

// A body naming the actor is refused as an unknown field: the actor cannot be chosen by the caller.
func TestSeatAdminSetOccupantRefusesAnActorField(t *testing.T) {
	_, mux := occupantFixture(t, "claude-code")
	rec := doTestRequest(t, mux, http.MethodPut, occupantPath, `{"runtime":"codex","actor":"someone-else"}`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("actor field: status = %d, want 400: %s", rec.Code, rec.Body.String())
	}
}

// The record names the authenticated caller, and the previous pair the seat held before the change.
func TestSeatAdminSetOccupantPassesTheAuthenticatedActor(t *testing.T) {
	fake, mux := occupantFixture(t, "claude-code")
	rec := doTestRequest(t, mux, http.MethodPut, occupantPath, `{"runtime":"codex","model":"gpt-5.1"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("set occupant: status = %d: %s", rec.Code, rec.Body.String())
	}
	if len(fake.occupantChanges) != 1 {
		t.Fatalf("recorded changes = %d, want 1", len(fake.occupantChanges))
	}
	change := fake.occupantChanges[0]
	if change.Actor != mountTestUser || change.UserID != mountTestUser {
		t.Errorf("recorded actor/user = %q/%q, want the authenticated caller %q", change.Actor, change.UserID, mountTestUser)
	}
	if change.FromRuntime != "claude-code" || change.FromModel != "sonnet" ||
		change.ToRuntime != "codex" || change.ToModel != "gpt-5.1" {
		t.Errorf("recorded change = %s/%s -> %s/%s, want claude-code/sonnet -> codex/gpt-5.1",
			change.FromRuntime, change.FromModel, change.ToRuntime, change.ToModel)
	}
}

// One seat's changes are read newest first, a team viewer reads them through the room owner's
// rows, and the read route emits no frame.
func TestSeatAdminOccupantHistoryReturnsOneSeatsChanges(t *testing.T) {
	fake := newSharingSeatAdmin()
	seedSharedRoom(fake)
	at := time.Date(2026, 10, 20, 19, 1, 34, 0, time.UTC)
	fake.occupantChanges = append(fake.occupantChanges, &repositories.OccupantChange{
		ID: "occ-1", UserID: "owner-user", SeatID: "seat-a", Actor: "owner-user", At: at,
		FromRuntime: "claude-code", FromModel: "sonnet", ToRuntime: "codex", ToModel: "gpt-5.1",
	})
	mux := sharingTestMux(t, fake)

	frames := 0
	before := seatBroadcastFn
	seatBroadcastFn = func(context.Context, string, string, string, string, string, string) error {
		frames++
		return nil
	}
	defer func() { seatBroadcastFn = before }()

	fake.scopes = nil
	rec := doTestRequest(t, mux, http.MethodGet, occupantHistoryPath, "")
	if rec.Code != http.StatusOK {
		t.Fatalf("occupant history: status = %d: %s", rec.Code, rec.Body.String())
	}
	if frames != 0 {
		t.Errorf("the read route emitted %d frame(s), want 0", frames)
	}
	assertScopeIsOwner(t, fake, "owner-user")
	if success := sharingTestField(t, rec.Body.Bytes(), "success"); success != true {
		t.Fatalf("success = %v, want true", success)
	}
	if changes, ok := sharingTestField(t, rec.Body.Bytes(), "changes").([]any); !ok || len(changes) != 1 {
		t.Fatalf("changes = %v, want one row", sharingTestField(t, rec.Body.Bytes(), "changes"))
	}
	for _, field := range []string{"actor", "at", "seat", "from_runtime", "from_model", "to_runtime", "to_model"} {
		if value := sharingTestField(t, rec.Body.Bytes(), "changes", "0", field); value == nil {
			t.Errorf("change field %q missing from the response: %s", field, rec.Body.String())
		}
	}
	if got := sharingTestField(t, rec.Body.Bytes(), "changes", "0", "actor"); got != "owner-user" {
		t.Errorf("actor = %v, want owner-user", got)
	}
	if got := sharingTestField(t, rec.Body.Bytes(), "changes", "0", "at"); got != "2026-10-20T19:01:34Z" {
		t.Errorf("at = %v, want 2026-10-20T19:01:34Z", got)
	}
	if got := sharingTestField(t, rec.Body.Bytes(), "changes", "0", "to_runtime"); got != "codex" {
		t.Errorf("to_runtime = %v, want codex", got)
	}
	if !strings.Contains(rec.Body.String(), `"from_model":"sonnet"`) {
		t.Errorf("from_model missing: %s", rec.Body.String())
	}
}
