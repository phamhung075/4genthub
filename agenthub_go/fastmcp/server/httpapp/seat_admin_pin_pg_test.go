package httpapp

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"testing"

	authdomain "agenthub/fastmcp/auth/domain/entities"
	authinterface "agenthub/fastmcp/auth/interface"
	seatorm "agenthub/fastmcp/seat_management/infrastructure/repositories/orm"
)

// THE STORE THE FAKE STANDS IN FOR, AGAINST REAL SQL. This is the follow-on both of R1's gates named:
// the architect's GATE-42de79c2 ("committed pin test uses a fake store; add a SEAT_TEST_DATABASE_URL
// case") and the reviewer's post-hoc GATE-42de79c2-r1-seat-pin-POSTHOC, which confirmed the finding as
// non-blocking. `TestSeatAdminPinSeatVersion` in seat_admin_pin_test.go drives the real route, the
// handler and the service - but through a SUBSTITUTED seatAdminSource, so every assertion it makes
// about the store is the fake's answer, and `UpdatePinnedVersion` is a plain UPDATE whose behaviour
// (does it move the row? is it scoped to the caller's tenant?) no fake can fail. BOTH of those are
// measured below: the moved row is read back from the table, and the case ends by making the same
// calls as ANOTHER user, which must neither see the seat nor move its pin.
//
// This case mounts the SAME routes over the PRODUCTION source - `newSeatAdminSource(sessions)`, built
// by seat_mount/seat_admin_mount's own wiring, no seam swapped - on a real PostgreSQL, and reads the
// row back through the repository rather than through the response, so the pin is proven to have
// reached the table. The refusals are asserted with the row read AFTER them: a version check that
// refuses in the response but writes anyway would pass the fake-store test and fail this one.
//
// GATED EXACTLY LIKE ITS NEIGHBOURS: without AGENTHUB_TEST_PG_URL it SKIPS LOUDLY and nothing below
// runs, so a green line from this file means nothing unless the skip did not appear. To run it:
//
//	bash tools/testpg/start.sh
//	AGENTHUB_TEST_PG_URL=postgresql://agenthub_user@127.0.0.1:55451/postgres go test -count=1 \
//	  -run TestSeatAdminPinReachesTheRowOnARealDatabase ./fastmcp/server/httpapp/
func TestSeatAdminPinReachesTheRowOnARealDatabase(t *testing.T) {
	sessions := newMissedNotificationAppEnv(t) // skips loudly when AGENTHUB_TEST_PG_URL is unset
	t.Setenv("AUTH_ENABLED", "false")
	authenticateTestUser(t)

	// The broadcast is not this case's subject and this mux has no broker behind it, so it is stubbed
	// exactly as the fake-store route test stubs it: the subject here is the row.
	previousBroadcast := seatBroadcastFn
	seatBroadcastFn = func(context.Context, string, string, string, string, string, string) error { return nil }
	t.Cleanup(func() { seatBroadcastFn = previousBroadcast })

	mux := http.NewServeMux()
	mountSeatAdminRoutes(mux, sessions) // the production source, not a substituted one

	ctx := context.Background()
	const user = "11111111-1111-4111-8111-111111111111" // the id authenticateTestUser resolves

	// Two module versions, because a pin needs two versions of the seat's type to move between.
	for _, version := range []string{"1.0.0", "2.0.0"} {
		rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/pgpinmod/versions/"+version,
			`{"kind":"instruction","content":"c"}`)
		if rec.Code != http.StatusOK {
			t.Fatalf("seeding module version %s: %d %s", version, rec.Code, rec.Body.String())
		}
	}

	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types", `{"slug":"pgpin","name":"PgPin"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("creating the seat type: %d %s", rec.Code, rec.Body.String())
	}
	// The service appends the next patch version, so these are 1.0.0 then 1.0.1 - read from the
	// responses rather than assumed, because the point of this case is that the numbers are the
	// database's and not a fixture's.
	firstVersion := createSeatTypeVersion(t, mux, "pgpinmod@1.0.0")
	secondVersion := createSeatTypeVersion(t, mux, "pgpinmod@2.0.0")
	if firstVersion == secondVersion {
		t.Fatalf("the two versions are both %q; this case cannot pin between them", firstVersion)
	}

	rec = doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms", `{"slug":"pgpinroom","name":"PgPin room"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("creating the room: %d %s", rec.Code, rec.Body.String())
	}
	rec = doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/rooms/pgpinroom/seats",
		`{"seat_key":"alice","seat_type":"pgpin","pinned_version":"`+firstVersion+`","runtime":"claude-code"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("creating the seat pinned to %s: %d %s", firstVersion, rec.Code, rec.Body.String())
	}

	// THE ROW, read through the repository: the route's own rendering is what the fake-store test
	// already covers, and it is not what this case exists for.
	rooms, err := seatorm.NewORMRoomRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	room, err := rooms.GetBySlug(ctx, user, "pgpinroom")
	if err != nil || room == nil {
		t.Fatalf("reading the room back: %v (%v)", room, err)
	}
	seats, err := seatorm.NewORMSeatRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	storedPin := func(what string) string {
		t.Helper()
		seat, err := seats.FindByRoomAndKey(ctx, user, room.ID, "alice")
		if err != nil || seat == nil {
			t.Fatalf("%s: reading the seat back = %v (%v)", what, seat, err)
		}
		if seat.PinnedVersion == nil {
			return ""
		}
		return *seat.PinnedVersion
	}
	if got := storedPin("after the create"); got != firstVersion {
		t.Fatalf("the seat was created pinned to %q, want %q", got, firstVersion)
	}

	rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/pgpinroom/seats/alice/pin",
		`{"pinned_version":"`+secondVersion+`"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("pinning to %s: %d %s", secondVersion, rec.Code, rec.Body.String())
	}
	if got := storedPin("after the pin"); got != secondVersion {
		t.Fatalf("the row reads %q after the pin, want %q - the response is not the store", got, secondVersion)
	}

	// THE REFUSALS, each followed by a read of the row: a check that refuses in the body and writes
	// anyway is exactly the failure a fake-store test cannot see.
	for _, refusal := range []struct {
		name string
		body string
		want int
	}{
		{"a version the seat type does not have", `{"pinned_version":"9.9.9"}`, http.StatusBadRequest},
		{"an omitted version", `{}`, http.StatusBadRequest},
	} {
		rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/pgpinroom/seats/alice/pin", refusal.body)
		if rec.Code != refusal.want {
			t.Errorf("pin with %s: status = %d, want %d: %s", refusal.name, rec.Code, refusal.want, rec.Body.String())
		}
		if got := storedPin("after " + refusal.name); got != secondVersion {
			t.Fatalf("%s moved the row to %q, want it unchanged at %q", refusal.name, got, secondVersion)
		}
	}
	if rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/pgpinroom/seats/nobody/pin",
		`{"pinned_version":"`+secondVersion+`"}`); rec.Code != http.StatusNotFound {
		t.Errorf("pin on an absent seat: status = %d, want 404: %s", rec.Code, rec.Body.String())
	}

	// THE TENANT SCOPE, measured rather than claimed. Every request above is made as the OWNING
	// user, so a store that dropped `AND user_id = $n` from either statement would pass all of them.
	// The resolver is swapped mid-case (as token_mount_wiring_test.go does) to make the SAME calls
	// as another user, which must not see the room's seat and must not move its pin.
	const otherUser = "22222222-2222-4222-8222-222222222222"
	previousResolve := authinterface.GetCurrentUserUniversal
	authinterface.GetCurrentUserUniversal = func(context.Context, string) (*authdomain.User, error) {
		id := otherUser
		return &authdomain.User{ID: &id, Email: "other@example.com", Username: "other"}, nil
	}
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/pgpinroom/seats", "")
	listCode := rec.Code
	if body := rec.Body.String(); strings.Contains(body, "alice") || listCode >= http.StatusInternalServerError {
		t.Errorf("another tenant's seat list: status %d, body %s - want the owner's seat absent and no server error",
			listCode, body)
	}
	rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/pgpinroom/seats/alice/pin",
		`{"pinned_version":"`+firstVersion+`"}`)
	if rec.Code == http.StatusOK {
		t.Errorf("another tenant pinned the owner's seat: status %d, body %s", rec.Code, rec.Body.String())
	}
	t.Logf("another tenant: seat list %d, pin %d (want the owner's seat absent and the pin refused)", listCode, rec.Code)
	authinterface.GetCurrentUserUniversal = previousResolve

	if got := storedPin("at the end"); got != secondVersion {
		t.Fatalf("the row moved to %q on a refused pin, want %q", got, secondVersion)
	}
}

// createSeatTypeVersion adds one version to the seat type and returns the version the SERVICE
// assigned, taken from the response body rather than from this file.
func createSeatTypeVersion(t *testing.T, mux *http.ServeMux, moduleRef string) string {
	t.Helper()
	rec := doTestRequest(t, mux, http.MethodPost, "/api/v2/openrig/seat-types/pgpin/versions",
		`{"module_refs":["`+moduleRef+`"],"default_runtime":"claude-code"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("adding version from %s: %d %s", moduleRef, rec.Code, rec.Body.String())
	}
	var body struct {
		SeatTypeVersion struct {
			Slug    string `json:"slug"`
			Version string `json:"version"`
		} `json:"seat_type_version"`
	}
	if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
		t.Fatalf("parsing the version response: %v: %s", err, rec.Body.String())
	}
	if body.SeatTypeVersion.Slug != "pgpin" || body.SeatTypeVersion.Version == "" {
		t.Fatalf("the version response carries slug %q version %q; want pgpin and a version",
			body.SeatTypeVersion.Slug, body.SeatTypeVersion.Version)
	}
	return body.SeatTypeVersion.Version
}
