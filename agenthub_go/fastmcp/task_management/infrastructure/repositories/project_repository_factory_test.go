package repositories

// Tests for the ported ProjectRepositoryFactory against a real PostgreSQL instance.

import (
	"testing"

	domainrepos "agenthub/fastmcp/task_management/domain/repositories"
)

func projectFactoryTestEnv(values map[string]string) func(string) string {
	return func(k string) string { return values[k] }
}

func projectFactoryTestPtr(s string) *string { return &s }

func projectFactoryTestORMFactory(t *testing.T) *ProjectRepositoryFactory {
	t.Helper()
	sessions := newTestRepoEnv(t)
	return NewProjectRepositoryFactory(sessions, projectFactoryTestEnv(map[string]string{
		"DATABASE_TYPE": "postgresql", "ENVIRONMENT": "production",
	}))
}

func TestProjectRepositoryFactoryCreateAndCache(t *testing.T) {
	factory := projectFactoryTestORMFactory(t)
	user := projectRepoTestUserA
	ormType := RepositoryTypeORM

	repo1, err := factory.Create(&ormType, &user, nil, nil)
	if err != nil {
		t.Fatalf("Create: %v", err)
	}
	if _, ok := repo1.(*ORMProjectRepository); !ok {
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
	if len(available) != 2 || available[0] != "orm" || available[1] != "mock" {
		t.Fatalf("available_types = %+v", available)
	}
}

func TestProjectRepositoryFactoryDefaultType(t *testing.T) {
	sessions := newTestRepoEnv(t)

	testEnv := NewProjectRepositoryFactory(sessions, projectFactoryTestEnv(map[string]string{
		"DATABASE_TYPE": "postgresql", "ENVIRONMENT": "test",
	}))
	if rt, err := testEnv.GetDefaultType(); err != nil || rt != RepositoryTypeMock {
		t.Fatalf("test env = %v, %v", rt, err)
	}

	missing := NewProjectRepositoryFactory(sessions, projectFactoryTestEnv(map[string]string{
		"ENVIRONMENT": "production",
	}))
	if _, err := missing.GetDefaultType(); err == nil {
		t.Fatal("missing DATABASE_TYPE must fail")
	}

	prod := NewProjectRepositoryFactory(sessions, projectFactoryTestEnv(map[string]string{
		"DATABASE_TYPE": "postgresql", "ENVIRONMENT": "production",
	}))
	if rt, err := prod.GetDefaultType(); err != nil || rt != RepositoryTypeORM {
		t.Fatalf("prod env = %v, %v", rt, err)
	}

	noDB := NewProjectRepositoryFactory(nil, projectFactoryTestEnv(map[string]string{
		"DATABASE_TYPE": "postgresql", "ENVIRONMENT": "production",
	}))
	if rt, err := noDB.GetDefaultType(); err != nil || rt != RepositoryTypeMock {
		t.Fatalf("no db = %v, %v", rt, err)
	}
}

func TestProjectRepositoryFactoryFallbackAndRegister(t *testing.T) {
	factory := projectFactoryTestORMFactory(t)
	user := projectRepoTestUserA

	// no mock factory: ORM creation failure propagates
	factory.Sessions = nil
	ormType := RepositoryTypeORM
	if _, err := factory.Create(&ormType, &user, nil, nil); err == nil {
		t.Fatal("expected ORM creation failure")
	}

	// register a custom builder and use it
	called := false
	factory.RegisterType("custom", func(userID string, dbPath *string, kwargs Kwargs) (domainrepos.ProjectRepository, error) {
		called = true
		return nil, nil
	})
	custom := RepositoryType("custom")
	repo, err := factory.Create(&custom, &user, nil, nil)
	if err != nil || !called || repo != nil {
		t.Fatalf("custom = %+v, called=%v, err=%v", repo, called, err)
	}
	factory.ClearCache()
	if n := factory.Instances.Len(); n != 0 {
		t.Fatalf("cache not cleared: %d", n)
	}

	// mock type without a MockFactory
	mockType := RepositoryTypeMock
	if _, err := factory.Create(&mockType, &user, nil, nil); err == nil {
		t.Fatal("mock without MockFactory must fail")
	}
}

func TestProjectRepositoryConfigAndManager(t *testing.T) {
	factory := projectFactoryTestORMFactory(t)
	user := projectRepoTestUserA

	cfg := NewRepositoryConfig(projectFactoryTestPtr("invalid"), &user, nil, nil)
	if cfg.RepositoryType != RepositoryTypeORM {
		t.Fatalf("invalid type should fall back to ORM: %s", cfg.RepositoryType)
	}
	repo, err := cfg.CreateRepository(factory)
	if err != nil || repo == nil {
		t.Fatalf("CreateRepository = %v, %v", repo, err)
	}

	envCfg := RepositoryConfigFromEnvironment(projectFactoryTestEnv(map[string]string{
		"MCP_USER_ID":                 projectRepoTestUserA,
		"MCP_PROJECT_REPOSITORY_TYPE": "in_memory",
		"MCP_DB_PATH":                 "/tmp/x.db",
	}))
	if envCfg.RepositoryType != RepositoryTypeInMemory {
		t.Fatalf("env type = %s", envCfg.RepositoryType)
	}
	if envCfg.UserID == nil || *envCfg.UserID != user {
		t.Fatalf("env user = %+v", envCfg.UserID)
	}
	if envCfg.DBPath == nil || *envCfg.DBPath != "/tmp/x.db" {
		t.Fatalf("env db_path = %+v", envCfg.DBPath)
	}

	mgr := NewGlobalRepositoryManager(factory)
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
	if status.GetAny("user_count") != 1 {
		t.Fatalf("status = %+v", status)
	}
	mgr.ClearAll()
	if status, _ := mgr.GetStatus(); status.GetAny("user_count") != 0 {
		t.Fatalf("ClearAll left users: %+v", status)
	}
}

func TestProjectRepositoryConvenienceFunctions(t *testing.T) {
	factory := projectFactoryTestORMFactory(t)
	user := projectRepoTestUserA

	oldFactory, oldManager := DefaultProjectRepositoryFactory, DefaultGlobalRepositoryManager
	DefaultProjectRepositoryFactory = factory
	DefaultGlobalRepositoryManager = NewGlobalRepositoryManager(factory)
	defer func() {
		DefaultProjectRepositoryFactory = oldFactory
		DefaultGlobalRepositoryManager = oldManager
	}()

	repo, err := CreateProjectRepository(&user, nil, nil)
	if err != nil {
		t.Fatalf("CreateProjectRepository: %v", err)
	}
	if _, ok := repo.(*ORMProjectRepository); !ok {
		t.Fatalf("type = %T", repo)
	}
	if _, err := CreateProjectRepository(&user, projectFactoryTestPtr("bogus"), nil); err == nil {
		t.Fatal("invalid repository type must fail")
	}
	if _, err := GetSQLiteRepository(&user, nil); err != nil {
		t.Fatalf("GetSQLiteRepository: %v", err)
	}
	if _, err := GetUserRepository(user); err != nil {
		t.Fatalf("GetUserRepository: %v", err)
	}
	if _, err := GetDefaultRepository(); err == nil {
		t.Fatal("GetDefaultRepository must reject nil user")
	}
}
