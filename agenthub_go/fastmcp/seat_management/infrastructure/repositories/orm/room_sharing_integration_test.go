package orm

// The D5 sharing wiring, end to end against a real PostgreSQL: a room shared with a team is
// readable by that team's members under the OWNER's rows, the strict lookups every write path uses
// keep returning only the caller's own room, a viewer cannot re-share, and a team id that names no
// team is refused by the foreign key.

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"os"
	"testing"
	"time"

	domainrepo "agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

func TestRoomSharingVisibilityIntegration(t *testing.T) {
	url := os.Getenv("SEAT_TEST_DATABASE_URL")
	if url == "" {
		t.Skip("SEAT_TEST_DATABASE_URL not set")
	}
	db, err := sql.Open("pgx", url)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	if err := db.PingContext(ctx); err != nil {
		t.Fatalf("ping: %v", err)
	}
	if _, err := db.ExecContext(ctx, seatIntegrationSchema(t)); err != nil {
		t.Fatalf("apply schema: %v", err)
	}
	sessions := database.NewSessionManager(&database.DatabaseConfig{Engine: &database.Engine{DB: db}})

	rooms, err := NewORMRoomRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}

	// A unique tenant per run; the integration database is shared between tests.
	stamp := time.Now().UnixNano()
	owner := fmt.Sprintf("share-owner-%d", stamp)
	member := fmt.Sprintf("share-member-%d", stamp)
	stranger := fmt.Sprintf("share-stranger-%d", stamp)

	// The team and its two memberships are written directly: this test is about the ROOM
	// repository's visibility, and the teams repository has its own integration test. The ids are
	// generated in Go, EXACTLY as the application does (ColumnDef.Default = DefaultUUIDv4), because
	// neither creation path declares a server default on id — an insert that omitted it would pass
	// on a database the schema FILE made and fail on one the RUNTIME path made.
	teamID := database.GenerateUUIDString()
	if _, err := db.ExecContext(ctx,
		`INSERT INTO teams (id, user_id, slug, name) VALUES ($1, $2, 'eng', 'Engineering')`,
		teamID, owner); err != nil {
		t.Fatal(err)
	}
	for _, m := range []struct{ user, role string }{{owner, "owner"}, {member, "viewer"}} {
		if _, err := db.ExecContext(ctx,
			`INSERT INTO team_members (id, team_id, user_id, role) VALUES ($1, $2, $3, $4)`,
			database.GenerateUUIDString(), teamID, m.user, m.role); err != nil {
			t.Fatal(err)
		}
	}

	shared, err := rooms.Save(ctx, owner, domainrepo.Room{Slug: "dev", Name: "Dev"})
	if err != nil {
		t.Fatal(err)
	}
	other, err := rooms.Save(ctx, owner, domainrepo.Room{Slug: "dev-unshared", Name: "Dev unshared"})
	if err != nil {
		t.Fatal(err)
	}
	if shared.TeamID != "" {
		t.Fatalf("a fresh room carries a team: %q", shared.TeamID)
	}

	// Before sharing: only the owner sees the room, and nobody's list carries it.
	if got, err := rooms.GetVisibleBySlug(ctx, member, "dev"); err != nil || got != nil {
		t.Fatalf("member saw an unshared room: %+v, %v", got, err)
	}
	if got, err := rooms.GetVisibleBySlug(ctx, stranger, "dev"); err != nil || got != nil {
		t.Fatalf("stranger saw an unshared room: %+v, %v", got, err)
	}
	if list, err := rooms.List(ctx, member); err != nil || len(list) != 0 {
		t.Fatalf("member list before sharing = %+v, %v", list, err)
	}
	if got, err := rooms.GetBySlug(ctx, owner, "dev"); err != nil || got == nil || got.ID != shared.ID {
		t.Fatalf("owner lookup = %+v, %v", got, err)
	}

	if err := rooms.SetTeam(ctx, owner, shared.ID, teamID); err != nil {
		t.Fatalf("SetTeam: %v", err)
	}

	// After sharing: the member reads the OWNER's room and the owner's row is unchanged.
	got, err := rooms.GetVisibleBySlug(ctx, member, "dev")
	if err != nil || got == nil {
		t.Fatalf("member lookup after sharing = %+v, %v", got, err)
	}
	if got.ID != shared.ID || got.UserID != owner || got.TeamID != teamID {
		t.Fatalf("member lookup = %+v, want the owner's room %s", got, shared.ID)
	}
	// The strict lookup every write path uses still refuses the member.
	if strict, err := rooms.GetBySlug(ctx, member, "dev"); err != nil || strict != nil {
		t.Fatalf("member strict lookup = %+v, %v, want nil", strict, err)
	}
	list, err := rooms.List(ctx, member)
	if err != nil || len(list) != 1 || list[0].ID != shared.ID {
		t.Fatalf("member list after sharing = %+v, %v", list, err)
	}
	if ownerList, err := rooms.List(ctx, owner); err != nil || len(ownerList) != 2 {
		t.Fatalf("owner list = %+v, %v (the owner's own path must be unchanged)", ownerList, err)
	}
	// A stranger still sees nothing.
	if got, err := rooms.GetVisibleBySlug(ctx, stranger, "dev"); err != nil || got != nil {
		t.Fatalf("stranger lookup after sharing = %+v, %v", got, err)
	}
	if list, err := rooms.List(ctx, stranger); err != nil || len(list) != 0 {
		t.Fatalf("stranger list = %+v, %v", list, err)
	}
	// The unshared room stays private to the owner.
	if got, err := rooms.GetVisibleBySlug(ctx, member, "dev-unshared"); err != nil || got != nil {
		t.Fatalf("member saw the unshared room: %+v, %v", got, err)
	}

	// A slug is unique per owner, not globally: when the member owns a room with the same slug,
	// the member's own room wins over the one shared with them.
	memberRoom, err := rooms.Save(ctx, member, domainrepo.Room{Slug: "dev", Name: "Member dev"})
	if err != nil {
		t.Fatal(err)
	}
	preferred, err := rooms.GetVisibleBySlug(ctx, member, "dev")
	if err != nil || preferred == nil || preferred.ID != memberRoom.ID || preferred.UserID != member {
		t.Fatalf("member's own room did not win: %+v, %v", preferred, err)
	}

	// A viewer cannot re-share, and cannot unshare either.
	if err := rooms.SetTeam(ctx, member, shared.ID, teamID); !errors.Is(err, domainrepo.ErrRoomNotOwned) {
		t.Fatalf("viewer SetTeam = %v, want ErrRoomNotOwned", err)
	}
	if err := rooms.SetTeam(ctx, member, shared.ID, ""); !errors.Is(err, domainrepo.ErrRoomNotOwned) {
		t.Fatalf("viewer unshare = %v, want ErrRoomNotOwned", err)
	}

	// The foreign key refuses a team id that names no team.
	if err := rooms.SetTeam(ctx, owner, shared.ID, "00000000-0000-0000-0000-000000000000"); err == nil {
		t.Fatal("SetTeam accepted a team_id that references no team")
	}

	// Unsharing ends the member's access: their list holds only their own room again, and the
	// owner's other room is untouched.
	if err := rooms.SetTeam(ctx, owner, shared.ID, ""); err != nil {
		t.Fatalf("unshare: %v", err)
	}
	list, err = rooms.List(ctx, member)
	if err != nil || len(list) != 1 || list[0].ID != memberRoom.ID {
		t.Fatalf("member list after unsharing = %+v, %v, want only their own room", list, err)
	}
	reloaded, err := rooms.GetBySlug(ctx, owner, "dev-unshared")
	if err != nil || reloaded == nil || reloaded.ID != other.ID || reloaded.TeamID != "" {
		t.Fatalf("owner's other room = %+v, %v", reloaded, err)
	}
}
