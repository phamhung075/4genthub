package httpapp

// The seat creation route falls back to the chosen version's default_runtime when the request
// omits runtime, because the schema documents default_runtime as "the runtime of a seat that sets
// none". An explicit runtime wins and is validated exactly as before; when no version resolves
// there is nothing to inherit, so the request is refused rather than given an invented default.

import (
	"net/http"
	"strings"
	"testing"
)

func TestSeatAdminCreateSeatInheritsVersionDefaultRuntime(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0") // the seeded version's default_runtime is claude-code
	mux := seatAdminTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"alice","seat_type":"coder"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("omitted runtime: status = %d: %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `"runtime":"claude-code"`) {
		t.Errorf("omitted runtime did not inherit the version default: %s", rec.Body.String())
	}
}

func TestSeatAdminCreateSeatExplicitRuntimeWins(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0") // version default is claude-code
	mux := seatAdminTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"bob","seat_type":"coder","runtime":"codex","model":"gpt"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("explicit runtime: status = %d: %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `"runtime":"codex"`) {
		t.Errorf("an explicit runtime did not win over the version default: %s", rec.Body.String())
	}
}

func TestSeatAdminCreateSeatRejectsBadExplicitRuntime(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	mux := seatAdminTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"alice","seat_type":"coder","runtime":"not-a-runtime"}`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("invalid explicit runtime: status = %d, want 400: %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminCreateSeatNoDefaultRuntimeRefuses(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	fake.seatTypes["coder"].DefaultRuntime = "" // a version that sets no default
	mux := seatAdminTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"alice","seat_type":"coder"}`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("no default and no explicit runtime: status = %d, want 400: %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminCreateSeatOmittedRuntimeRefusesUnknownType(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	mux := seatAdminTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"alice","seat_type":"ghost"}`)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("unknown seat type: status = %d, want 404: %s", rec.Code, rec.Body.String())
	}
}

func TestSeatAdminCreateSeatInheritedRuntimeStillValidatesModel(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedRoom("dev")
	fake.seedSeatType("coder", "1.0.0")
	fake.seatTypes["coder"].DefaultRuntime = "codex" // inherited, and codex cannot run a claude model
	mux := seatAdminTestMux(t, fake)

	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/dev/seats",
		`{"seat_key":"alice","seat_type":"coder","model":"claude-3"}`)
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("inherited runtime with an incompatible model: status = %d, want 400: %s", rec.Code, rec.Body.String())
	}
}
