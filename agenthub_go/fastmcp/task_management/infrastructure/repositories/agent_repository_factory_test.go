package repositories

// Tests for the ported AgentRepositoryFactory against a real PostgreSQL instance.

import (
	"testing"

	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
)

func agentFactoryTestORMFactory(t *testing.T) *AgentRepositoryFactory {
	t.Helper()
	sessions := newTestRepoEnv(t)
	return NewAgentRepositoryFactory(sessions, projectFactoryTestEnv(map[string]string{
		"DATABASE_TYPE": "postgresql", "ENVIRONMENT": "production",
	}))
}

func TestAgentRepositoryFactoryCreateAndCache(t *testing.T) {
	factory := agentFactoryTestORMFactory(t)
	user := projectRepoTestUserA
	ormType := AgentRepositoryTypeORM

	repo1, err := factory.Create(&ormType, &user, nil, nil)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if _, ok := repo1.(*ORMAgentRepository); !ok {
		t.Fatalf("repository type = %T", repo1)
	}
	repo2, err := factory.Create(&ormType, &user, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if repo1 != repo2 {
		t.Fatal("expected the cached instance")
	}
	other := projectRepoTestUserB
	repo3, err := factory.Create(&ormType, &other, nil, nil)
	if err != nil {
		t.Fatal(err)
	}
	if repo3 == repo1 {
		t.Fatal("different users must not share an instance")
	}
	if _, err := factory.Create(&ormType, nil, nil, nil); err == nil {
		t.Fatal("nil user must be rejected")
	}

	info, err := factory.GetInfo()
	if err != nil {
		t.Fatal(err)
	}
	if info.GetAny("default_type") != "orm" {
		t.Fatalf("default_type = %+v", info.GetAny("default_type"))
	}
	if info.GetAny("cached_instances") != 2 {
		t.Fatalf("cached_instances = %+v", info.GetAny("cached_instances"))
	}
	available, _ := info.GetAny("available_types").([]any)
	if len(available) != 1 || available[0] != "orm" {
		t.Fatalf("available_types = %+v", available)
	}
}

func TestAgentRepositoryFactoryDefaultType(t *testing.T) {
	sessions := newTestRepoEnv(t)

	testEnv := NewAgentRepositoryFactory(sessions, projectFactoryTestEnv(map[string]string{
		"DATABASE_TYPE": "postgresql", "ENVIRONMENT": "test",
	}))
	if rt, err := testEnv.GetDefaultType(); err != nil || rt != AgentRepositoryTypeMock {
		t.Fatalf("test env = %v, %v", rt, err)
	}

	missing := NewAgentRepositoryFactory(sessions, projectFactoryTestEnv(map[string]string{
		"ENVIRONMENT": "production",
	}))
	if _, err := missing.GetDefaultType(); err == nil {
		t.Fatal("missing DATABASE_TYPE must fail")
	}

	prod := NewAgentRepositoryFactory(sessions, projectFactoryTestEnv(map[string]string{
		"DATABASE_TYPE": "sqlite", "ENVIRONMENT": "production",
	}))
	if rt, err := prod.GetDefaultType(); err != nil || rt != AgentRepositoryTypeORM {
		t.Fatalf("prod env = %v, %v", rt, err)
	}
}

func TestAgentRepositoryFactoryUnportedAndRegister(t *testing.T) {
	factory := agentFactoryTestORMFactory(t)
	user := projectRepoTestUserA

	// The non-ORM branch needs the not-yet-ported repository_factory hook.
	mockType := AgentRepositoryTypeMock
	if _, err := factory.Create(&mockType, &user, nil, nil); err == nil {
		t.Fatal("missing UnportedFactory must fail")
	}
	factory.UnportedFactory = func() (domainrepos.AgentRepository, error) { return nil, nil }
	if repo, err := factory.Create(&mockType, &user, nil, nil); err != nil || repo != nil {
		t.Fatalf("hook = %+v, %v", repo, err)
	}

	// The registered-type map is only used by GetInfo/RegisterType (like Python).
	called := false
	factory.RegisterType("custom", func(userID string, dbPath *string, kwargs Kwargs) (domainrepos.AgentRepository, error) {
		called = true
		return nil, nil
	})
	custom := AgentRepositoryType("custom")
	if _, err := factory.Create(&custom, &user, nil, nil); err != nil {
		t.Fatal(err)
	}
	if called {
		t.Fatal("CreateInstance must not use the registered-type map")
	}
	info, err := factory.GetInfo()
	if err != nil {
		t.Fatal(err)
	}
	available, _ := info.GetAny("available_types").([]any)
	if len(available) != 2 || available[0] != "orm" || available[1] != "custom" {
		t.Fatalf("available_types = %+v", available)
	}

	factory.ClearCache()
	if n := factory.Instances.Len(); n != 0 {
		t.Fatalf("cache not cleared: %d", n)
	}
}

func TestAgentRepositoryConfigAndManager(t *testing.T) {
	factory := agentFactoryTestORMFactory(t)
	user := projectRepoTestUserA

	cfg := NewAgentRepositoryConfig(projectFactoryTestPtr("invalid"), &user, nil, nil)
	if cfg.RepositoryType != AgentRepositoryTypeORM {
		t.Fatalf("invalid type should fall back to ORM: %s", cfg.RepositoryType)
	}
	repo, err := cfg.CreateRepository(factory)
	if err != nil || repo == nil {
		t.Fatalf("CreateRepository = %v, %v", repo, err)
	}

	envCfg := AgentRepositoryConfigFromEnvironment(projectFactoryTestEnv(map[string]string{
		"MCP_USER_ID":               projectRepoTestUserA,
		"MCP_AGENT_REPOSITORY_TYPE": "in_memory",
		"MCP_DB_PATH":               "/tmp/x.db",
	}))
	if envCfg.RepositoryType != AgentRepositoryTypeInMemory {
		t.Fatalf("env type = %s", envCfg.RepositoryType)
	}
	if envCfg.UserID == nil || *envCfg.UserID != user {
		t.Fatalf("env user = %+v", envCfg.UserID)
	}
	if envCfg.DBPath == nil || *envCfg.DBPath != "/tmp/x.db" {
		t.Fatalf("env db_path = %+v", envCfg.DBPath)
	}

	mgr := NewGlobalAgentRepositoryManager(factory)
	got, err := mgr.GetForUser(user)
	if err != nil {
		t.Fatal(err)
	}
	again, err := mgr.GetForUser(user)
	if err != nil || again != got {
		t.Fatalf("GetForUser cache = %v, %v", again, err)
	}
	if _, err := mgr.GetDefault(); err == nil {
		t.Fatal("GetDefault must reject nil user")
	}
	status, err := mgr.GetStatus()
	if err != nil {
		t.Fatal(err)
	}
	if status.GetAny("user_repositories") != 1 {
		t.Fatalf("status = %+v", status.GetAny("user_repositories"))
	}
	cachedUsers, _ := status.GetAny("cached_users").([]string)
	if len(cachedUsers) != 1 || cachedUsers[0] != user {
		t.Fatalf("cached_users = %+v", cachedUsers)
	}
	mgr.ClearAll()
	if status, _ := mgr.GetStatus(); status.GetAny("user_repositories") != 0 {
		t.Fatalf("ClearAll left users: %+v", status)
	}
}

func TestAgentRepositoryConvenienceFunctions(t *testing.T) {
	factory := agentFactoryTestORMFactory(t)
	user := projectRepoTestUserA

	oldFactory, oldManager := DefaultAgentRepositoryFactory, DefaultGlobalAgentRepositoryManager
	DefaultAgentRepositoryFactory = factory
	DefaultGlobalAgentRepositoryManager = NewGlobalAgentRepositoryManager(factory)
	defer func() {
		DefaultAgentRepositoryFactory = oldFactory
		DefaultGlobalAgentRepositoryManager = oldManager
	}()

	repo, err := CreateAgentRepository(&user, nil, nil)
	if err != nil {
		t.Fatalf("CreateAgentRepository: %v", err)
	}
	if _, ok := repo.(*ORMAgentRepository); !ok {
		t.Fatalf("type = %T", repo)
	}
	if _, err := CreateAgentRepository(&user, projectFactoryTestPtr("bogus"), nil); err == nil {
		t.Fatal("invalid repository type must fail")
	}
	if _, err := GetSQLiteAgentRepository(&user, nil); err != nil {
		t.Fatalf("GetSQLiteAgentRepository: %v", err)
	}
	// The instance cache key ignores kwargs, so the repository created above (without a
	// project) is returned; Python's class-level cache behaves the same way.
	project := "p1"
	cachedRepo, err := GetORMAgentRepository(&user, &project)
	if err != nil {
		t.Fatalf("GetORMAgentRepository: %v", err)
	}
	if cachedRepo.(*ORMAgentRepository).ProjectID != nil {
		t.Fatalf("expected the cached (project-less) instance, got %+v", cachedRepo.(*ORMAgentRepository).ProjectID)
	}
	factory.ClearCache()
	ormRepo, err := GetORMAgentRepository(&user, &project)
	if err != nil {
		t.Fatalf("GetORMAgentRepository: %v", err)
	}
	if ormRepo.(*ORMAgentRepository).ProjectID == nil || *ormRepo.(*ORMAgentRepository).ProjectID != project {
		t.Fatalf("project id = %+v", ormRepo.(*ORMAgentRepository).ProjectID)
	}
	if _, err := GetUserAgentRepository(user); err != nil {
		t.Fatalf("GetUserAgentRepository: %v", err)
	}
	if _, err := GetDefaultAgentRepository(); err == nil {
		t.Fatal("GetDefaultAgentRepository must reject nil user")
	}
	if CreateAgentRepositoryFactory() == nil {
		t.Fatal("CreateAgentRepositoryFactory returned nil")
	}
}
