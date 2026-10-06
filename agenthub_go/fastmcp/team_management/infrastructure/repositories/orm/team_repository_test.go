package orm

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"net/url"
	"os"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/infrastructure/database"
	domainrepo "agenthub/fastmcp/team_management/domain/repositories"
)

// newTeamTestEnv creates a throwaway database (AGENTHUB_TEST_PG_URL, see tools/testpg),
// creates every registered table through the runtime path (cfg.CreateTables, which runs the
// TableDef DDL - the same path production uses), and returns a session manager over it.
func newTeamTestEnv(t *testing.T) *database.SessionManager {
	t.Helper()
	admin := os.Getenv("AGENTHUB_TEST_PG_URL")
	if admin == "" {
		t.Skip("AGENTHUB_TEST_PG_URL not set")
	}
	adm, err := sql.Open("pgx", admin)
	if err != nil {
		t.Fatal(err)
	}
	name := fmt.Sprintf("agenthub_team_%d", time.Now().UnixNano())
	if _, err := adm.Exec("CREATE DATABASE " + name); err != nil {
		t.Fatal(err)
	}
	adm.Close()
	u, _ := url.Parse(admin)
	u.Path = "/" + name
	env := map[string]string{"DATABASE_TYPE": "postgresql", "DATABASE_HOST": "x", "DATABASE_PASSWORD": "x"}
	database.ResetInstance()
	deps := database.Deps{
		Getenv: func(k string) (string, bool) { v, ok := env[k]; return v, ok },
		Sleep:  func(time.Duration) {},
		Open: func(string, database.EngineOptions) (*sql.DB, error) {
			return database.PgxOpener(u.String(), database.EngineOptions{PoolSize: 4, MaxOverflow: 4, PoolRecycle: 60})
		},
	}
	cfg, err := database.GetInstance(context.Background(), deps)
	if err != nil {
		t.Fatal(err)
	}
	if err := cfg.CreateTables(context.Background()); err != nil {
		t.Fatal(err)
	}
	database.SetupTimestampEvents()
	t.Cleanup(func() {
		database.ResetInstance()
		if adm, err := sql.Open("pgx", admin); err == nil {
			_, _ = adm.Exec("DROP DATABASE IF EXISTS " + name + " WITH (FORCE)")
			adm.Close()
		}
	})
	return database.NewSessionManager(cfg)
}

func TestTeamRepositoryIntegration(t *testing.T) {
	sessions := newTeamTestEnv(t)
	repo, err := NewORMTeamRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	owner := fmt.Sprintf("team-it-owner-%d", time.Now().UnixNano())
	viewer := owner + "-viewer"
	other := owner + "-other"

	team, err := repo.Create(ctx, "eng", "Engineering", owner)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if team.ID == "" || team.UserID != owner || team.Slug != "eng" || team.Name != "Engineering" {
		t.Fatalf("Create = %+v", team)
	}

	// The owner membership is written in the same transaction.
	m, err := repo.Membership(ctx, team.ID, owner)
	if err != nil || m == nil || m.Role != domainrepo.RoleOwner {
		t.Fatalf("owner membership = %+v, %v", m, err)
	}

	if _, err := repo.Create(ctx, "eng", "Again", owner); !errors.Is(err, domainrepo.ErrTeamExists) {
		t.Fatalf("duplicate slug = %v, want ErrTeamExists", err)
	}

	bySlug, err := repo.FindForMember(ctx, owner, "eng")
	if err != nil || bySlug == nil || bySlug.ID != team.ID {
		t.Fatalf("FindForMember = %+v, %v", bySlug, err)
	}
	if miss, err := repo.FindForMember(ctx, other, "eng"); err != nil || miss != nil {
		t.Fatalf("FindForMember non-member = %+v, %v", miss, err)
	}

	// Membership scoping: the owner sees the team, a non-member does not.
	memberships, err := repo.ListForMember(ctx, owner)
	if err != nil || len(memberships) != 1 || memberships[0].Role != domainrepo.RoleOwner {
		t.Fatalf("ListForMember owner = %+v, %v", memberships, err)
	}
	if ms, err := repo.ListForMember(ctx, other); err != nil || len(ms) != 0 {
		t.Fatalf("ListForMember non-member = %+v, %v", ms, err)
	}
	if m, err := repo.Membership(ctx, team.ID, other); err != nil || m != nil {
		t.Fatalf("non-member Membership = %+v, %v", m, err)
	}

	// A second user may reuse the same slug: the unique key is (user_id, slug).
	otherTeam, err := repo.Create(ctx, "eng", "Other Engineering", other)
	if err != nil {
		t.Fatalf("second owner same slug: %v", err)
	}
	if otherTeam.ID == team.ID {
		t.Fatal("two owners' teams share an id")
	}
	if own, _ := repo.FindForMember(ctx, other, "eng"); own == nil || own.ID != otherTeam.ID {
		t.Fatalf("FindForMember other = %+v", own)
	}

	// Owner adds and removes a viewer; ListMembers keeps the owner first.
	if _, err := repo.AddMember(ctx, team.ID, viewer, domainrepo.RoleViewer); err != nil {
		t.Fatalf("AddMember: %v", err)
	}
	if _, err := repo.AddMember(ctx, team.ID, viewer, domainrepo.RoleViewer); !errors.Is(err, domainrepo.ErrMemberExists) {
		t.Fatalf("duplicate AddMember = %v, want ErrMemberExists", err)
	}
	// The DB itself refuses a second owner (partial unique index uq_team_members_one_owner),
	// so the single-owner rule holds for a caller that bypasses the service and against the
	// ErrLastOwner trap: with one owner row, demoting "the" owner cannot leave the team
	// ownerless behind a second owner. A distinct user is used so the only possible
	// conflict is the one-owner index, not the (team_id, user_id) key.
	if _, err := repo.AddMember(ctx, team.ID, "team-it-second-owner", domainrepo.RoleOwner); !errors.Is(err, domainrepo.ErrTeamHasOwner) {
		t.Fatalf("second owner = %v, want ErrTeamHasOwner from the DB", err)
	}
	members, err := repo.ListMembers(ctx, team.ID)
	if err != nil || len(members) != 2 {
		t.Fatalf("ListMembers = %+v, %v", members, err)
	}
	if members[0].Role != domainrepo.RoleOwner || members[1].UserID != viewer {
		t.Fatalf("ListMembers order = %+v", members)
	}
	if err := repo.UpdateRole(ctx, team.ID, viewer, domainrepo.RoleViewer); err != nil {
		t.Fatalf("UpdateRole: %v", err)
	}
	if err := repo.UpdateRole(ctx, team.ID, "no-such-user", domainrepo.RoleViewer); !errors.Is(err, domainrepo.ErrTeamNotFound) {
		t.Fatalf("UpdateRole unknown member = %v, want ErrTeamNotFound", err)
	}
	if removed, err := repo.RemoveMember(ctx, team.ID, viewer); err != nil || !removed {
		t.Fatalf("RemoveMember = %v, %v", removed, err)
	}
	if removed, err := repo.RemoveMember(ctx, team.ID, viewer); err != nil || removed {
		t.Fatalf("second RemoveMember = %v, %v", removed, err)
	}

	// Delete cascades to the member rows in the application layer.
	if err := repo.Delete(ctx, team.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if gone, err := repo.FindForMember(ctx, owner, "eng"); err != nil || gone != nil {
		t.Fatalf("FindForMember after Delete = %+v, %v", gone, err)
	}
	if member, err := repo.Membership(ctx, team.ID, owner); err != nil || member != nil {
		t.Fatalf("member rows after Delete = %+v, %v", member, err)
	}
}

// TestTeamDeleteClearsRoomSharingIntegration covers the D5 wiring half of the delete: rooms.team_id
// references teams (id) with NO ON DELETE CASCADE (the cascade is application-layer), so without
// the clearing inside Delete this delete would be REFUSED by the foreign key and a shared room
// could never be released. The room must survive, private to its owner again.
func TestTeamDeleteClearsRoomSharingIntegration(t *testing.T) {
	sessions := newTeamTestEnv(t)
	repo, err := NewORMTeamRepository(sessions)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	owner := fmt.Sprintf("team-del-owner-%d", time.Now().UnixNano())
	viewer := owner + "-viewer"

	team, err := repo.Create(ctx, "eng", "Engineering", owner)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if _, err := repo.AddMember(ctx, team.ID, viewer, domainrepo.RoleViewer); err != nil {
		t.Fatalf("AddMember: %v", err)
	}

	// A room shared with the team. The id is a literal because the runtime DDL creates rooms
	// without a database default for it; the seat room repository has its own integration test.
	const roomID = "8a4f2f2e-6f2b-4a1e-9d5c-2b8f0a7c1d3e"
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		_, err := s.ExecContext(ctx,
			`INSERT INTO rooms (id, user_id, slug, name, team_id) VALUES ($1, $2, 'dev', 'Dev', $3)`,
			roomID, owner, team.ID)
		return err
	}); err != nil {
		t.Fatal(err)
	}

	if err := repo.Delete(ctx, team.ID); err != nil {
		t.Fatalf("Delete with a shared room: %v", err)
	}

	var sharedTeam *string
	if err := sessions.WithSession(ctx, func(ctx context.Context, s database.DBTX) error {
		return s.QueryRowContext(ctx, `SELECT team_id::text FROM rooms WHERE id = $1`, roomID).Scan(&sharedTeam)
	}); err != nil {
		t.Fatalf("room after Delete: %v", err)
	}
	if sharedTeam != nil {
		t.Fatalf("room still points at the deleted team: %q", *sharedTeam)
	}
	if members, err := repo.ListMembers(ctx, team.ID); err != nil || len(members) != 0 {
		t.Fatalf("member rows after Delete = %+v, %v", members, err)
	}
}
