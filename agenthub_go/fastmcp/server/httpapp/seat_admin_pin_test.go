package httpapp

import (
	"net/http"
	"strings"
	"testing"
)

// R1's acceptance, driven through the production seam: the request goes over the real route
// mounted by mountSeatAdminRoutes, through the handler, the service and the service's version
// check - not around them. A version the seat's type does not have is refused with 400 (the same
// refusal handleCreateSeat produces for a create that pins an unknown version), an existing
// version is written, and the next read of the room's seats reports what was written rather than
// echoing the request.
func TestSeatAdminPinSeatVersion(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0", "0.9.0", "1.4.2")
	mux := seatAdminTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"alice","seat_type":"coder","pinned_version":"0.9.0","runtime":"claude-code","model":"sonnet"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("seeding the seat: %d %s", rec.Code, rec.Body.String())
	}

	// A version that does not exist for the seat's type is refused.
	rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/pin",
		`{"pinned_version":"9.9.9"}`)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("pin to a version that does not exist: status = %d, want 400: %s", rec.Code, rec.Body.String())
	}

	// The version this release seeds with is accepted.
	rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/pin",
		`{"pinned_version":"1.4.2"}`)
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"pinned_version":"1.4.2"`) {
		t.Errorf("pin to 1.4.2: %d %s", rec.Code, rec.Body.String())
	}

	// The write is in the store, not only in the response.
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/seats", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("listing the room's seats: %d %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `"pinned_version":"1.4.2"`) {
		t.Errorf("the pin never reached the store; the room's seats read back as %s", rec.Body.String())
	}

	// An omitted version is the same refusal, not a silent unpin.
	rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/pin", `{}`)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("pin with no version: status = %d, want 400: %s", rec.Code, rec.Body.String())
	}

	// A seat that does not exist is a 404, so a typo in the seat key cannot pin nothing.
	rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/nobody/pin",
		`{"pinned_version":"1.4.2"}`)
	if rec.Code != http.StatusNotFound {
		t.Errorf("pin on an absent seat: status = %d, want 404: %s", rec.Code, rec.Body.String())
	}
}
