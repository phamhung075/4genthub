package httpapp

// The occupant pair is asymmetric by design: CREATE inherits the seat type version's
// default_runtime when the request omits runtime (handleCreateSeat), while CHANGE keeps the
// seat's current runtime when the same field is blank (SeatAdminService.SetOccupant). A blank
// runtime NEVER changes a runtime — inheriting a type default on change would silently reset a
// live seat's runtime, which is a destructive surprise, and rejecting it would leave the pair
// inconsistent for no gain. An explicit runtime still wins and is still validated on both paths.

import (
	"net/http"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
)

const occupantPath = "/api/v2/openrig/rooms/dev/seats/alice/occupant"

func occupantFixture(t *testing.T, runtime string) (*fakeSeatAdmin, *http.ServeMux) {
	t.Helper()
	fake := newFakeSeatAdmin()
	room := fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	pinned := "1.0.0"
	fake.seats = append(fake.seats, &repositories.Seat{
		ID: "seat-a", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder",
		PinnedVersion: &pinned, Runtime: runtime, Model: "sonnet", PermissionPolicy: "standard",
	})
	return fake, seatAdminTestMux(t, fake)
}

// The case that would fail if a blank runtime went back to a 400.
func TestSeatAdminSetOccupantBlankRuntimeKeepsTheRuntime(t *testing.T) {
	fake, mux := occupantFixture(t, "claude-code")
	rec := doTestRequest(t, mux, http.MethodPut, occupantPath, `{"runtime":"","model":"opus"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("blank runtime: status = %d, want 200 (a blank runtime must not change the runtime): %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `"runtime":"claude-code"`) || !strings.Contains(rec.Body.String(), `"model":"opus"`) {
		t.Errorf("blank runtime did not keep the runtime while changing the model: %s", rec.Body.String())
	}
	if got := fake.seats[0]; got.Runtime != "claude-code" || got.Model != "opus" {
		t.Errorf("stored seat = %+v (runtime must stay claude-code, model must be opus)", got)
	}
}

func TestSeatAdminSetOccupantOmittedRuntimeKeepsTheRuntime(t *testing.T) {
	fake, mux := occupantFixture(t, "omp")
	rec := doTestRequest(t, mux, http.MethodPut, occupantPath, `{"model":"deepseek/deepseek-flash"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("omitted runtime: status = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `"runtime":"omp"`) {
		t.Errorf("omitted runtime did not keep omp: %s", rec.Body.String())
	}
	if got := fake.seats[0]; got.Runtime != "omp" || got.Model != "deepseek/deepseek-flash" {
		t.Errorf("stored seat = %+v", got)
	}
}

func TestSeatAdminSetOccupantExplicitRuntimeWins(t *testing.T) {
	fake, mux := occupantFixture(t, "claude-code")
	rec := doTestRequest(t, mux, http.MethodPut, occupantPath, `{"runtime":"codex","model":"gpt-5.1:high"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("explicit runtime: status = %d: %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `"runtime":"codex"`) {
		t.Errorf("an explicit runtime did not win: %s", rec.Body.String())
	}
	if got := fake.seats[0]; got.Runtime != "codex" || got.Model != "gpt-5.1:high" {
		t.Errorf("stored seat = %+v", got)
	}
}

func TestSeatAdminSetOccupantExplicitBogusRuntimeIsRejected(t *testing.T) {
	fake, mux := occupantFixture(t, "claude-code")
	rec := doTestRequest(t, mux, http.MethodPut, occupantPath, `{"runtime":"not-a-runtime","model":"opus"}`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("bogus explicit runtime: status = %d, want 400: %s", rec.Code, rec.Body.String())
	}
	if got := fake.seats[0]; got.Runtime != "claude-code" || got.Model != "sonnet" {
		t.Errorf("a rejected request changed the seat: %+v", got)
	}
}

// The change path must never inherit the type version's default runtime: a seat running
// claude-code whose type default is codex keeps claude-code when the request omits runtime.
func TestSeatAdminSetOccupantBlankRuntimeDoesNotInheritTheTypeDefault(t *testing.T) {
	fake, mux := occupantFixture(t, "claude-code")
	fake.seatTypes["coder"].DefaultRuntime = "codex" // the version default differs from the seat

	rec := doTestRequest(t, mux, http.MethodPut, occupantPath, `{"model":"opus"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("omitted runtime with a differing type default: status = %d: %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `"runtime":"claude-code"`) {
		t.Errorf("the change path inherited the type default instead of keeping the seat runtime: %s", rec.Body.String())
	}
	if got := fake.seats[0]; got.Runtime != "claude-code" {
		t.Errorf("stored seat = %+v, want the runtime unchanged at claude-code (never the codex type default)", got)
	}
}
