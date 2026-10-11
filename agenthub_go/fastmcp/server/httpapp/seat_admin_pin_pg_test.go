package httpapp

// R1's acceptance against the REAL store, which is the half the committed case beside this one
// cannot show.
//
// `seat_admin_pin_test.go` drives the route -> handler -> service -> version-check seam through
// `newFakeSeatAdmin()`, so the ORM statement
//
//	UPDATE "seats" SET "pinned_version" = $1, "updated_at" = $2 WHERE "user_id" = $3 AND "id" = $4
//
// (`fastmcp/seat_management/infrastructure/repositories/orm/seat_repository.go:109`-`:117`) is
// executed by NO committed test. The reviewer's post-hoc approve on `42de79c2` and the architect's
// finding both said so, and the only proof was a scratch run against a real PostgreSQL that did not
// survive its session. This case seeds rows in a real database and mounts the route with the real
// session manager, so the statement runs and the ROW is what the assertions read.
//
// It needs AGENTHUB_TEST_PG_URL (see tools/testpg/start.sh) and skips loudly without it, through the
// harness in missed_notification_replay_test.go.

import (
	"context"
	"net/http"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func TestSeatAdminPinSeatVersionAgainstTheRealStore(t *testing.T) {
	sessions := newMissedNotificationAppEnv(t) // real PostgreSQL; skips loudly without it
	authenticateTestUser(t)
	// The id authenticateTestUser's stubbed user carries, so the seeded rows belong to the caller
	// the handler sees.
	const user = "11111111-1111-4111-8111-111111111111"
	ctx := context.Background()

	// Seeded directly, because the subject here is the pin seam: a room, a seat type with two
	// versions, and a seat pinned to the older one. The versions ARE the check's input - 1.4.2 is
	// accepted and 9.9.9 is refused - and they are rows, not a constant, which is why the check can
	// be exercised at all.
	var roomID, seatTypeID, seatID string
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		if err := s.QueryRowContext(ctx, `INSERT INTO rooms (id, user_id, slug, name, created_at, updated_at)
			VALUES (gen_random_uuid(), $1, 'dev', 'Dev', now(), now()) RETURNING id`, user).Scan(&roomID); err != nil {
			return err
		}
		if err := s.QueryRowContext(ctx, `INSERT INTO seat_types (id, user_id, slug, name, description, created_at)
			VALUES (gen_random_uuid(), $1, 'coder', 'Coder', '', now()) RETURNING id`, user).Scan(&seatTypeID); err != nil {
			return err
		}
		for _, version := range []string{"0.9.0", "1.4.2"} {
			if _, err := s.ExecContext(ctx, `INSERT INTO seat_type_versions
					(id, user_id, seat_type_id, version, default_runtime, module_refs, created_at)
				VALUES (gen_random_uuid(), $1, $2, $3, 'claude-code', '[]'::jsonb, now())`,
				user, seatTypeID, version); err != nil {
				return err
			}
		}
		return s.QueryRowContext(ctx, `INSERT INTO seats
				(id, user_id, room_id, seat_key, seat_type_id, runtime, model, permission_policy,
				 pinned_version, created_at, updated_at)
			VALUES (gen_random_uuid(), $1, $2, 'alice', $3, 'claude-code', 'sonnet', $4, '0.9.0', now(), now())
			RETURNING id`, user, roomID, seatTypeID, resolver.DefaultPermissionPolicy).Scan(&seatID)
	}); err != nil {
		t.Fatalf("seeding the room, the type, its versions and the seat failed: %v", err)
	}

	// pinnedInStore reads the COLUMN, so every assertion below is about the row rather than about a
	// response that could have been composed from the request.
	pinnedInStore := func() string {
		t.Helper()
		var pinned string
		if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
			return s.QueryRowContext(ctx, `SELECT pinned_version FROM seats WHERE id = $1::uuid`, seatID).Scan(&pinned)
		}); err != nil {
			t.Fatalf("reading the seat's row failed: %v", err)
		}
		return pinned
	}

	// sessions, not nil: the second argument is what the mount resolves its real source from, so the
	// package-level seams the fake case overrides stay default here and the store IS the database.
	// Both mounts, in the order app.go mounts them, because the acceptance's last claim is what the
	// RESOLVED seat renders, and that route lives in seat_mount.go rather than in the admin mount.
	mux := http.NewServeMux()
	mountSeatRoutes(mux, sessions)
	mountSeatAdminRoutes(mux, sessions)

	// (1) A version the seat's type does not have is refused, and the row is untouched: the refusal
	// must happen BEFORE the UPDATE, which is exactly the half a fake that never runs the statement
	// cannot show.
	rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/pin",
		`{"pinned_version":"9.9.9"}`)
	if rec.Code != http.StatusBadRequest {
		t.Errorf("pin to a version the type does not have: status = %d, want 400: %s", rec.Code, rec.Body.String())
	}
	if got := pinnedInStore(); got != "0.9.0" {
		t.Errorf("the refused pin changed the row to %q, want it still 0.9.0: the version check must run "+
			"before the UPDATE", got)
	}

	// (2) A version the type has is written, and the ORM UPDATE is what changed the row.
	rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/pin",
		`{"pinned_version":"1.4.2"}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("pin to 1.4.2: status = %d, want 200: %s", rec.Code, rec.Body.String())
	}
	if got := pinnedInStore(); got != "1.4.2" {
		t.Errorf("the row is %q after a 200, want 1.4.2: UPDATE \"seats\" did not reach it", got)
	}

	// (3) The next read of the room's seats reports the ROW, not the request.
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/rooms/dev/seats", "")
	if rec.Code != http.StatusOK {
		t.Fatalf("listing the room's seats: %d %s", rec.Code, rec.Body.String())
	}
	if !strings.Contains(rec.Body.String(), `"pinned_version":"1.4.2"`) {
		t.Errorf("the room's seats read back without the pin: %s", rec.Body.String())
	}

	// (4) The resolve renders the pinned version, which is the claim the row's own acceptance makes.
	rec = doTestRequest(t, mux, http.MethodGet, "/api/v2/openrig/seats/dev/alice", "")
	if rec.Code != http.StatusOK {
		t.Errorf("resolving the pinned seat: status = %d, want 200: %s", rec.Code, rec.Body.String())
	} else if !strings.Contains(rec.Body.String(), "1.4.2") {
		t.Errorf("the resolved seat does not render the pinned version: %s", rec.Body.String())
	}

	// (5) A seat that does not exist is a 404, so a typo in the seat key cannot pin nothing - and the
	// refusal comes from the store, not from a fake's table.
	rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/nobody/pin",
		`{"pinned_version":"1.4.2"}`)
	if rec.Code != http.StatusNotFound {
		t.Errorf("pin on a seat the store does not hold: status = %d, want 404: %s", rec.Code, rec.Body.String())
	}
}
