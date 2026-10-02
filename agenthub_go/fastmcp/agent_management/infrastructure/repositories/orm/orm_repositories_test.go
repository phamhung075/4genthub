package orm

import (
	"context"
	"database/sql"
	"fmt"
	"net/url"
	"os"
	"testing"
	"time"

	"agenthub/fastmcp/agent_management/domain/entities"
	"agenthub/fastmcp/agent_management/domain/enums"
	amvo "agenthub/fastmcp/agent_management/domain/value_objects"
	"agenthub/fastmcp/task_management/infrastructure/database"
)

// newAgentRepoEnv creates a throwaway database with all tables (agent models included via
// their init registration) and returns a session manager over it.
func newAgentRepoEnv(t *testing.T) *database.SessionManager {
	t.Helper()
	admin := os.Getenv("AGENTHUB_TEST_PG_URL")
	if admin == "" {
		t.Skip("AGENTHUB_TEST_PG_URL not set")
	}
	adm, err := sql.Open("pgx", admin)
	if err != nil {
		t.Fatal(err)
	}
	name := fmt.Sprintf("agenthub_agent_%d", time.Now().UnixNano())
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
		adm, err := sql.Open("pgx", admin)
		if err == nil {
			_, _ = adm.Exec("DROP DATABASE IF EXISTS " + name + " WITH (FORCE)")
			adm.Close()
		}
	})
	return database.NewSessionManager(cfg)
}

func agentTestTemplate(t *testing.T, slug, name, category string) *entities.AgentTemplate {
	t.Helper()
	id := amvo.GenerateNewAgentTemplateId()
	cfg, err := amvo.NewAgentConfigurationDefaults("You are " + name)
	if err != nil {
		t.Fatal(err)
	}
	tmpl := entities.DefaultAgentTemplate()
	tmpl.ID, tmpl.Slug, tmpl.Name, tmpl.Category, tmpl.Description = &id, slug, name, category, "desc"
	tmpl.DefaultConfiguration = &cfg
	out, err := entities.NewAgentTemplate(tmpl)
	if err != nil {
		t.Fatalf("NewAgentTemplate: %v", err)
	}
	return out
}

func TestAgentTemplateRepositoryCRUD(t *testing.T) {
	env := newAgentRepoEnv(t)
	repo, err := NewORMAgentTemplateRepository(env)
	if err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()

	saved, err := repo.Save(ctx, agentTestTemplate(t, "zeta", "Zeta", "b"))
	if err != nil {
		t.Fatalf("Save: %v", err)
	}
	if saved.ID == nil {
		t.Fatal("Save did not keep the id")
	}
	got, err := repo.FindByID(ctx, *saved.ID)
	if err != nil || got == nil || got.Slug != "zeta" || got.Name != "Zeta" {
		t.Fatalf("FindByID = %v, %v", got, err)
	}
	if got.DefaultConfiguration == nil || got.DefaultConfiguration.SystemPrompt != "You are Zeta" {
		t.Fatalf("configuration = %+v", got.DefaultConfiguration)
	}
	bySlug, err := repo.FindBySlug(ctx, "zeta")
	if err != nil || bySlug == nil {
		t.Fatalf("FindBySlug = %v, %v", bySlug, err)
	}
	if ok, _ := repo.ExistsBySlug(ctx, "zeta"); !ok {
		t.Fatal("ExistsBySlug(zeta) = false")
	}
	if ok, _ := repo.ExistsBySlug(ctx, "nope"); ok {
		t.Fatal("ExistsBySlug(nope) = true")
	}
	if missing, _ := repo.FindBySlug(ctx, "nope"); missing != nil {
		t.Fatalf("FindBySlug(nope) = %v", missing)
	}
	if missing, _ := repo.FindByID(ctx, amvo.GenerateNewAgentTemplateId()); missing != nil {
		t.Fatalf("FindByID(unknown) = %v", missing)
	}

	if _, err := repo.Save(ctx, agentTestTemplate(t, "alpha", "Alpha", "a")); err != nil {
		t.Fatal(err)
	}
	if _, err := repo.Save(ctx, agentTestTemplate(t, "beta", "Beta", "b")); err != nil {
		t.Fatal(err)
	}
	all, err := repo.FindAll(ctx)
	if err != nil || len(all) != 3 {
		t.Fatalf("FindAll = %d, %v", len(all), err)
	}
	if all[0].Slug != "alpha" || all[1].Slug != "beta" || all[2].Slug != "zeta" {
		t.Fatalf("FindAll order = %s, %s, %s", all[0].Slug, all[1].Slug, all[2].Slug)
	}
	byCategory, err := repo.FindByCategory(ctx, "b")
	if err != nil || len(byCategory) != 2 || byCategory[0].Slug != "beta" || byCategory[1].Slug != "zeta" {
		t.Fatalf("FindByCategory = %v, %v", byCategory, err)
	}

	updated := *got
	updated.Name = "Zeta Renamed"
	if _, err := repo.Save(ctx, &updated); err != nil {
		t.Fatalf("Save(update): %v", err)
	}
	reloaded, rerr := repo.FindByID(ctx, *saved.ID)
	if reloaded == nil {
		t.Fatalf("FindByID after update: %v", rerr)
	}
	if reloaded.Name != "Zeta Renamed" {
		t.Fatalf("name after update = %q", reloaded.Name)
	}

	if err := repo.Delete(ctx, *saved.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if gone, _ := repo.FindByID(ctx, *saved.ID); gone != nil {
		t.Fatal("template still present after delete")
	}
	if ok, _ := repo.ExistsBySlug(ctx, "zeta"); ok {
		t.Fatal("ExistsBySlug after delete = true")
	}
	if err := repo.Delete(ctx, *saved.ID); err != nil {
		t.Fatalf("Delete(again) = %v", err)
	}
}

func agentTestInstance(t *testing.T, userID amvo.UserId, templateID amvo.AgentTemplateId, name string) *entities.UserAgentInstance {
	t.Helper()
	id := amvo.GenerateNewUserAgentInstanceId()
	cfg, err := amvo.NewAgentConfigurationDefaults("prompt for " + name)
	if err != nil {
		t.Fatal(err)
	}
	inst := entities.DefaultUserAgentInstance()
	inst.ID, inst.UserID, inst.TemplateID, inst.AgentName, inst.Configuration = &id, &userID, &templateID, name, &cfg
	out, err := entities.NewUserAgentInstance(inst)
	if err != nil {
		t.Fatalf("NewUserAgentInstance: %v", err)
	}
	return out
}

func agentTestPublic(t *testing.T, userID amvo.UserId, templateID amvo.AgentTemplateId, name, token string) *entities.UserAgentInstance {
	t.Helper()
	inst := agentTestInstance(t, userID, templateID, name)
	if err := inst.GenerateShareToken(token); err != nil {
		t.Fatal(err)
	}
	return inst
}

func agentTestShareToken(n int) string { return fmt.Sprintf("%064d", n) }

func TestUserAgentInstanceRepositoryCRUD(t *testing.T) {
	env := newAgentRepoEnv(t)
	repo, _ := NewORMUserAgentInstanceRepository(env)
	templates, _ := NewORMAgentTemplateRepository(env)
	ctx := context.Background()

	tmpl, err := templates.Save(ctx, agentTestTemplate(t, "tpl-a", "Template A", "a"))
	if err != nil {
		t.Fatal(err)
	}
	userID := amvo.GenerateNewUserId()
	instance, err := repo.Save(ctx, agentTestInstance(t, userID, *tmpl.ID, "Alpha Agent"))
	if err != nil {
		t.Fatalf("Save: %v", err)
	}
	got, err := repo.FindByID(ctx, *instance.ID)
	if err != nil || got == nil || got.AgentName != "Alpha Agent" {
		t.Fatalf("FindByID = %v, %v", got, err)
	}
	byPair, err := repo.FindByUserAndTemplate(ctx, userID, *tmpl.ID)
	if err != nil || byPair == nil {
		t.Fatalf("FindByUserAndTemplate = %v, %v", byPair, err)
	}
	bySlug, err := repo.FindByUserAndTemplateSlug(ctx, userID, "tpl-a")
	if err != nil || bySlug == nil {
		t.Fatalf("FindByUserAndTemplateSlug = %v, %v", bySlug, err)
	}
	if ok, _ := repo.ExistsByUserAndTemplate(ctx, userID, *tmpl.ID); !ok {
		t.Fatal("ExistsByUserAndTemplate = false")
	}
	if n, _ := repo.CountByAgentNameForUser(ctx, userID, "Alpha Agent"); n != 1 {
		t.Fatalf("CountByAgentNameForUser = %d", n)
	}
	if missing, _ := repo.FindByID(ctx, amvo.GenerateNewUserAgentInstanceId()); missing != nil {
		t.Fatalf("FindByID(unknown) = %v", missing)
	}
	if missing, _ := repo.FindByUserAndTemplate(ctx, amvo.GenerateNewUserId(), *tmpl.ID); missing != nil {
		t.Fatalf("FindByUserAndTemplate(unknown) = %v", missing)
	}
	if missing, _ := repo.FindByUserAndTemplateSlug(ctx, userID, "nope"); missing != nil {
		t.Fatalf("FindByUserAndTemplateSlug(nope) = %v", missing)
	}

	if err := repo.Delete(ctx, *instance.ID); err != nil {
		t.Fatalf("Delete: %v", err)
	}
	if gone, _ := repo.FindByID(ctx, *instance.ID); gone != nil {
		t.Fatal("instance still present after delete")
	}
	if err := repo.Delete(ctx, *instance.ID); err != nil {
		t.Fatalf("Delete(again) = %v", err)
	}
}

func TestUserAgentInstanceRepositoryIsolationAndOrdering(t *testing.T) {
	env := newAgentRepoEnv(t)
	repo, _ := NewORMUserAgentInstanceRepository(env)
	templates, _ := NewORMAgentTemplateRepository(env)
	ctx := context.Background()

	tmplA, _ := templates.Save(ctx, agentTestTemplate(t, "tpl-a", "Template A", "a"))
	tmplB, _ := templates.Save(ctx, agentTestTemplate(t, "tpl-b", "Template B", "b"))
	tmplC, _ := templates.Save(ctx, agentTestTemplate(t, "tpl-c", "Template C", "c"))
	tmplZ, _ := templates.Save(ctx, agentTestTemplate(t, "tpl-z", "Template Z", "z"))
	userA, userB := amvo.GenerateNewUserId(), amvo.GenerateNewUserId()

	for name, tmpl := range map[string]amvo.AgentTemplateId{"beta": *tmplB.ID, "alpha": *tmplA.ID, "gamma": *tmplC.ID} {
		if _, err := repo.Save(ctx, agentTestInstance(t, userA, tmpl, name)); err != nil {
			t.Fatal(err)
		}
	}
	// Disable alpha.
	alpha, _ := repo.FindByUserAndTemplateSlug(ctx, userA, "tpl-a")
	alpha.IsEnabled = false
	if _, err := repo.Save(ctx, alpha); err != nil {
		t.Fatal(err)
	}
	disabled, _ := repo.FindByID(ctx, *alpha.ID)
	if disabled.IsEnabled {
		t.Fatal("is_enabled was not persisted")
	}
	if _, err := repo.Save(ctx, agentTestInstance(t, userB, *tmplZ.ID, "zeta")); err != nil {
		t.Fatal(err)
	}

	aInstances, err := repo.FindByUser(ctx, userA)
	if err != nil || len(aInstances) != 3 {
		t.Fatalf("FindByUser(A) = %d, %v", len(aInstances), err)
	}
	if aInstances[0].AgentName != "alpha" || aInstances[1].AgentName != "beta" || aInstances[2].AgentName != "gamma" {
		t.Fatalf("FindByUser order = %s, %s, %s", aInstances[0].AgentName, aInstances[1].AgentName, aInstances[2].AgentName)
	}
	bInstances, _ := repo.FindByUser(ctx, userB)
	if len(bInstances) != 1 || bInstances[0].AgentName != "zeta" {
		t.Fatalf("FindByUser(B) = %v", bInstances)
	}
	enabled, err := repo.FindEnabledByUser(ctx, userA)
	if err != nil || len(enabled) != 2 || enabled[0].AgentName != "beta" || enabled[1].AgentName != "gamma" {
		t.Fatalf("FindEnabledByUser = %v, %v", enabled, err)
	}
	if n, _ := repo.CountByAgentNameForUser(ctx, userA, "alpha"); n != 1 {
		t.Fatalf("count alpha = %d", n)
	}
}

func TestUserAgentInstanceRepositorySharing(t *testing.T) {
	env := newAgentRepoEnv(t)
	repo, _ := NewORMUserAgentInstanceRepository(env)
	templates, _ := NewORMAgentTemplateRepository(env)
	ctx := context.Background()

	tmpl, _ := templates.Save(ctx, agentTestTemplate(t, "tpl-share", "Share", "s"))
	userID := amvo.GenerateNewUserId()
	instance := agentTestPublic(t, userID, *tmpl.ID, "Shared", agentTestShareToken(1))
	if _, err := repo.Save(ctx, instance); err != nil {
		t.Fatal(err)
	}
	found, err := repo.FindByShareToken(ctx, agentTestShareToken(1))
	if err != nil || found == nil || *found.ID != *instance.ID {
		t.Fatalf("FindByShareToken = %v, %v", found, err)
	}
	if missing, _ := repo.FindByShareToken(ctx, "nope"); missing != nil {
		t.Fatalf("FindByShareToken(nope) = %v", missing)
	}

	tmpl2, _ := templates.Save(ctx, agentTestTemplate(t, "tpl-private", "Private", "p"))
	private := agentTestInstance(t, userID, *tmpl2.ID, "Private")
	if _, err := repo.Save(ctx, private); err != nil {
		t.Fatal(err)
	}
}

func TestUserAgentInstanceRepositoryPublicInstances(t *testing.T) {
	env := newAgentRepoEnv(t)
	repo, _ := NewORMUserAgentInstanceRepository(env)
	templates, _ := NewORMAgentTemplateRepository(env)
	ctx := context.Background()

	userA := amvo.GenerateNewUserId()
	for i, name := range []string{"beta", "alpha", "gamma"} {
		tmpl, _ := templates.Save(ctx, agentTestTemplate(t, fmt.Sprintf("pub-%d", i), "Pub "+name, "p"))
		inst := agentTestPublic(t, userA, *tmpl.ID, name, agentTestShareToken(10+i))
		if _, err := repo.Save(ctx, inst); err != nil {
			t.Fatal(err)
		}
		time.Sleep(2 * time.Millisecond)
	}
	public, err := repo.FindPublicInstances(ctx, 50, 0, enums.InstanceOrderingCreatedAsc)
	if err != nil || len(public) != 3 {
		t.Fatalf("FindPublicInstances = %d, %v", len(public), err)
	}
	if public[0].AgentName != "beta" || public[2].AgentName != "gamma" {
		t.Fatalf("created_asc order = %s ... %s", public[0].AgentName, public[2].AgentName)
	}
	byName, _ := repo.FindPublicInstances(ctx, 50, 0, enums.InstanceOrderingNameAsc)
	if byName[0].AgentName != "alpha" || byName[2].AgentName != "gamma" {
		t.Fatalf("name_asc order = %s ... %s", byName[0].AgentName, byName[2].AgentName)
	}
	byNameDesc, _ := repo.FindPublicInstances(ctx, 50, 0, enums.InstanceOrderingNameDesc)
	if byNameDesc[0].AgentName != "gamma" {
		t.Fatalf("name_desc order = %s", byNameDesc[0].AgentName)
	}
	firstPage, _ := repo.FindPublicInstances(ctx, 2, 0, enums.InstanceOrderingNameAsc)
	if len(firstPage) != 2 {
		t.Fatalf("limit = %d", len(firstPage))
	}
	secondPage, _ := repo.FindPublicInstances(ctx, 2, 2, enums.InstanceOrderingNameAsc)
	if len(secondPage) != 1 || secondPage[0].AgentName != "gamma" {
		t.Fatalf("offset page = %v", secondPage)
	}
	zero, _ := repo.FindPublicInstances(ctx, 0, 0, enums.InstanceOrderingNameAsc)
	if len(zero) != 0 {
		t.Fatalf("limit 0 returned %d", len(zero))
	}
	// Private instances never show up.
	tmplPrivate, _ := templates.Save(ctx, agentTestTemplate(t, "pub-private", "Private", "p"))
	if _, err := repo.Save(ctx, agentTestInstance(t, userA, *tmplPrivate.ID, "private")); err != nil {
		t.Fatal(err)
	}
	stillPublic, _ := repo.FindPublicInstances(ctx, 50, 0, enums.InstanceOrderingNameAsc)
	if len(stillPublic) != 3 {
		t.Fatalf("private instance leaked into public list (%d)", len(stillPublic))
	}
}

func TestUserAgentInstanceRepositoryOrphaned(t *testing.T) {
	env := newAgentRepoEnv(t)
	repo, _ := NewORMUserAgentInstanceRepository(env)
	templates, _ := NewORMAgentTemplateRepository(env)
	ctx := context.Background()

	creator := amvo.GenerateNewUserId()
	importer := amvo.GenerateNewUserId()
	tmplOrigin, _ := templates.Save(ctx, agentTestTemplate(t, "orphan-origin", "Origin", "o"))
	origin := agentTestPublic(t, creator, *tmplOrigin.ID, "origin", agentTestShareToken(20))
	if _, err := repo.Save(ctx, origin); err != nil {
		t.Fatal(err)
	}
	tmplImport, _ := templates.Save(ctx, agentTestTemplate(t, "orphan-import", "Import", "o"))
	imported := agentTestPublic(t, importer, *tmplImport.ID, "imported", agentTestShareToken(21))
	imported.OriginalCreatorID = &creator
	saved, err := repo.Save(ctx, imported)
	if err != nil {
		t.Fatal(err)
	}
	if ok, _ := repo.IsOrphaned(ctx, *saved.ID); ok {
		t.Fatal("active import reported as orphaned")
	}
	public, _ := repo.FindPublicInstances(ctx, 50, 0, enums.InstanceOrderingNameAsc)
	if len(public) != 2 {
		t.Fatalf("public before delete = %d", len(public))
	}

	if err := repo.Delete(ctx, *origin.ID); err != nil {
		t.Fatal(err)
	}
	if ok, _ := repo.IsOrphaned(ctx, *saved.ID); !ok {
		t.Fatal("import not reported as orphaned after creator deletion")
	}
	public, _ = repo.FindPublicInstances(ctx, 50, 0, enums.InstanceOrderingNameAsc)
	// the orphaned import is excluded (the creator owns no instance any more)
	if len(public) != 0 {
		t.Fatalf("orphaned import still public: %v", public)
	}
	if ok, _ := repo.IsOrphaned(ctx, *saved.ID); !ok {
		t.Fatal("IsOrphaned changed")
	}
	if ok, _ := repo.IsOrphaned(ctx, amvo.GenerateNewUserAgentInstanceId()); ok {
		t.Fatal("IsOrphaned(unknown) = true")
	}
}
