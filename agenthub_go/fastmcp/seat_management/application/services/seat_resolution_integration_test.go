package services_test

import (
	"context"
	"crypto/sha256"
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"

	"agenthub/fastmcp/seat_management/application/services"
	"agenthub/fastmcp/seat_management/domain/commpolicy"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/seedlibrary"
	"agenthub/fastmcp/seat_management/domain/seedmap"
	"agenthub/fastmcp/seat_management/domain/skillblock"
	seatorm "agenthub/fastmcp/seat_management/infrastructure/repositories/orm"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// TestSeatResolutionEndToEnd runs seed -> room/seat -> resolve against a real PostgreSQL
// (SEAT_TEST_DATABASE_URL) with the embedded seat library.
func TestSeatResolutionEndToEnd(t *testing.T) {
	url := os.Getenv("SEAT_TEST_DATABASE_URL")
	if url == "" {
		t.Skip("SKIPPED, NOT PASSED: SEAT_TEST_DATABASE_URL is unset, so this case did NOT run - " +
			"it applies the seat schema to a PostgreSQL it is given; bash tools/testpg/start.sh prints a URL")
	}
	db, err := sql.Open("pgx", url)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	ctx := context.Background()
	_, thisFile, _, _ := runtime.Caller(0)
	schema, err := os.ReadFile(filepath.Join(filepath.Dir(thisFile), "../../infrastructure/schema/seat_management_postgresql.sql"))
	if err != nil {
		t.Fatal(err)
	}
	// One implicit transaction holds the lock until the schema is applied, so parallel
	// test packages do not race on CREATE EXTENSION.
	if _, err := db.ExecContext(ctx, "SELECT pg_advisory_xact_lock(727274);\n"+string(schema)); err != nil {
		t.Fatalf("apply schema: %v", err)
	}
	sessions := database.NewSessionManager(&database.DatabaseConfig{Engine: &database.Engine{DB: db}})
	user := fmt.Sprintf("seat-e2e-%d", time.Now().UnixNano())

	modules, err := seatorm.NewORMModuleRepository(sessions)
	must(t, err)
	seatTypes, err := seatorm.NewORMSeatTypeRepository(sessions)
	must(t, err)
	rooms, err := seatorm.NewORMRoomRepository(sessions)
	must(t, err)
	seats, err := seatorm.NewORMSeatRepository(sessions)
	must(t, err)
	overlays, err := seatorm.NewORMOverlayRepository(sessions)
	must(t, err)
	links, err := seatorm.NewORMSeatLinkRepository(sessions)
	must(t, err)
	resolved, err := seatorm.NewORMResolvedSeatRepository(sessions)
	must(t, err)

	seeds, err := seedlibrary.Load()
	must(t, err)
	seedFixtureCatalogRefs(t, ctx, user, seeds, modules)
	must(t, services.SeedSeatTypes(ctx, user, seeds, modules, seatTypes))
	must(t, services.SeedSeatTypes(ctx, user, seeds, modules, seatTypes)) // idempotent

	svc := &services.SeatResolutionService{
		SeatTypes: seatTypes, Rooms: rooms, Seats: seats, Overlays: overlays, Links: links, Resolved: resolved,
		NewCatalog: func(userID string) services.CheckedCatalog { return seatorm.NewDBCatalog(modules, userID) },
		MCPURL:     "https://api.example.test/mcp",
	}

	room, err := rooms.Save(ctx, user, repositories.Room{Slug: "dev", Name: "Dev room"})
	must(t, err)
	coder := mustSeat(t, ctx, seats, user, room.ID, "coder", seatTypes, "developer")
	reviewer := mustSeat(t, ctx, seats, user, room.ID, "reviewer", seatTypes, "reviewer")

	first, err := svc.ResolveSeat(ctx, user, "dev", "coder")
	must(t, err)
	again, err := svc.ResolveSeat(ctx, user, "dev", "coder")
	must(t, err)
	if first.Hash != again.Hash || first.ID != again.ID {
		t.Fatalf("same definition produced two snapshots: %s vs %s", first.Hash, again.Hash)
	}
	guidance := fileContent(t, first, "guidance/role.md")
	t.Logf("guidance head: %.300q", guidance)
	if !strings.Contains(guidance, "## developer-role") {
		t.Errorf("role guidance missing the role module")
	}
	if first.Runtime != "claude-code" {
		t.Errorf("runtime = %s", first.Runtime)
	}

	// A seat overlay that removes the output-format document changes the snapshot.
	_, err = overlays.Upsert(ctx, user, repositories.Overlay{
		Scope: repositories.ScopeSeat, SeatID: coder.ID,
		Ops: []resolver.Op{{Kind: resolver.OpRemove, Slug: "developer-output-format"}},
	})
	must(t, err)
	changed, err := svc.ResolveSeat(ctx, user, "dev", "coder")
	must(t, err)
	if changed.Hash == first.Hash {
		t.Fatal("overlay did not change the snapshot")
	}
	if strings.Contains(fileContent(t, changed, "guidance/role.md"), "Document: developer-output-format") {
		t.Error("removed module still rendered")
	}

	// A link changes the policy and therefore the snapshot; the policy parses strictly.
	_, err = links.Upsert(ctx, user, repositories.SeatLink{FromSeatID: coder.ID, ToSeatID: reviewer.ID, Kind: "escalates_to", Allow: true})
	must(t, err)
	withLink, err := svc.ResolveSeat(ctx, user, "dev", "coder")
	must(t, err)
	if withLink.Hash == changed.Hash {
		t.Fatal("link did not change the snapshot")
	}
	policy := commpolicy.Policy{Seat: "coder", Links: []commpolicy.Link{{From: "coder", To: "reviewer", Kind: commpolicy.KindEscalatesTo, Allow: true}}}
	if got := withLink.Policy["Seat"]; got != "coder" {
		t.Errorf("policy seat = %v", got)
	}
	if d := commpolicy.Decide(policy, "reviewer", commpolicy.IntentEscalation); !d.Allowed {
		t.Errorf("decision = %+v", d)
	}

	// Switching the runtime of a pinned seat resolves to a new snapshot of the same pinned version.
	latest, err := seatTypes.LatestVersion(ctx, user, "developer")
	must(t, err)
	pinned, err := seats.Create(ctx, user, repositories.Seat{
		RoomID: room.ID, SeatKey: "pinned", SeatTypeID: latest.SeatTypeID, PinnedVersion: &latest.Version,
		Runtime: "claude-code", Model: "sonnet", PermissionPolicy: "standard",
	})
	must(t, err)
	beforeSwitch, err := svc.ResolveSeat(ctx, user, "dev", "pinned")
	must(t, err)
	must(t, seats.UpdateOccupant(ctx, user, pinned.ID, "codex", "gpt-5.1"))
	afterSwitch, err := svc.ResolveSeat(ctx, user, "dev", "pinned")
	must(t, err)
	if afterSwitch.Runtime != "codex" || afterSwitch.Hash == beforeSwitch.Hash {
		t.Fatalf("runtime switch of a pinned seat: runtime %s, hash unchanged = %v", afterSwitch.Runtime, afterSwitch.Hash == beforeSwitch.Hash)
	}

	// A deleted seat cannot be resolved.
	must(t, links.DeleteBySeat(ctx, user, reviewer.ID))
	must(t, resolved.DeleteBySeat(ctx, user, reviewer.ID))
	must(t, seats.Delete(ctx, user, reviewer.ID))
	if _, err := svc.ResolveSeat(ctx, user, "dev", "reviewer"); err == nil {
		t.Error("deleted seat resolved")
	}
	// Tenant isolation: another user sees nothing.
	if _, err := svc.ResolveSeat(ctx, user+"-other", "dev", "coder"); err == nil {
		t.Error("other tenant resolved the seat")
	}
}

func must(t *testing.T, err error) {
	t.Helper()
	if err != nil {
		t.Fatal(err)
	}
}

// seedFixtureCatalogRefs stores a module version for every ref the embedded library carries that
// the library does not author itself.
//
// Those refs are the curated OpenRig catalog skills (queue-handoff@1.0.0,
// test-driven-development@1.0.0, ...): they live in the OpenRig catalog, published there by
// `scripts/openrig_team_setup.py publish-skills`, not in this repository. The seeder refuses a ref
// it cannot resolve, so without them this test cannot seed at all.
//
// The bodies are FIXTURES, not product data: one valid skill block per ref, so the seed and the
// resolve can be exercised end to end on a machine with no OpenRig checkout. The slug and version
// are the library's own, so what resolves is the ref the catalog would really satisfy.
func seedFixtureCatalogRefs(t *testing.T, ctx context.Context, user string, seeds []seedmap.Seed, modules repositories.ModuleRepository) {
	t.Helper()
	authored := map[string]bool{}
	for _, seed := range seeds {
		for _, module := range seed.Modules {
			authored[module.Slug] = true
		}
	}
	done := map[string]bool{}
	for _, seed := range seeds {
		for _, ref := range seed.ModuleRefs {
			if authored[ref.Slug] || done[ref.Slug] {
				continue
			}
			done[ref.Slug] = true
			body := "# " + ref.Slug + "\n\nFixture skill body: this ref is satisfied so the seat renders a complete spec.\n"
			block, err := skillblock.Marshal(skillblock.Block{
				Content:    body,
				SourcePath: "skills/" + ref.Slug + "/SKILL.md",
				SHA256:     fmt.Sprintf("%x", sha256.Sum256([]byte(body))),
			})
			if err != nil {
				t.Fatalf("fixture skill block %s: %v", ref.Slug, err)
			}
			if _, err := modules.SaveModule(ctx, user, ref.Slug, resolver.KindSkill); err != nil {
				t.Fatalf("fixture module %s: %v", ref.Slug, err)
			}
			if _, err := modules.AddVersion(ctx, user, ref.Slug, ref.Version, block); err != nil {
				t.Fatalf("fixture module version %s@%s: %v", ref.Slug, ref.Version, err)
			}
		}
	}
}

func mustSeat(t *testing.T, ctx context.Context, seats repositories.SeatRepository, user, roomID, key string, seatTypes repositories.SeatTypeRepository, typeSlug string) *repositories.Seat {
	t.Helper()
	version, err := seatTypes.LatestVersion(ctx, user, typeSlug)
	must(t, err)
	if version == nil {
		t.Fatalf("seat type %s not seeded", typeSlug)
	}
	seat, err := seats.Create(ctx, user, repositories.Seat{
		RoomID: roomID, SeatKey: key, SeatTypeID: version.SeatTypeID, Runtime: "claude-code", Model: "sonnet", PermissionPolicy: "standard",
	})
	must(t, err)
	return seat
}

func fileContent(t *testing.T, seat *repositories.ResolvedSeat, path string) string {
	t.Helper()
	for _, f := range seat.Files {
		if f.Path == path {
			return f.Content
		}
	}
	t.Fatalf("file %s missing", path)
	return ""
}
