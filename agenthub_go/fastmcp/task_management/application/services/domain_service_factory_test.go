package services

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/interfaces"
)

// The fakes embed the interface so they satisfy it without spelling out every
// method; tests only exercise identity, never the promoted methods.
type zpDomFakeDatabaseSessionFactory struct {
	interfaces.IDatabaseSessionFactory
}
type zpDomFakeEventStore struct{ interfaces.IEventStore }
type zpDomFakeCacheService struct{ interfaces.ICacheService }
type zpDomFakeRepositoryFactory struct{ interfaces.IRepositoryFactory }
type zpDomFakeTaskRepositoryFactory struct {
	interfaces.ITaskRepositoryFactory
}
type zpDomFakeProjectRepositoryFactory struct {
	interfaces.IProjectRepositoryFactory
}
type zpDomFakeGitBranchRepositoryFactory struct {
	interfaces.IGitBranchRepositoryFactory
}
type zpDomFakeNotificationService struct {
	interfaces.INotificationService
}
type zpDomFakeEventBus struct{ interfaces.IEventBus }
type zpDomFakeLoggingService struct{ interfaces.ILoggingService }
type zpDomFakeMonitoringService struct {
	interfaces.IMonitoringService
}
type zpDomFakeProcessMonitor struct{ interfaces.IProcessMonitor }
type zpDomFakeValidationService struct {
	interfaces.IValidationService
}
type zpDomFakeDocumentValidator struct{ interfaces.IDocumentValidator }
type zpDomFakePathResolver struct{ interfaces.IPathResolver }
type zpDomFakeHintManager struct{}

// zpDomResetServices restores the process-wide state between tests (the Python class
// state is global too, tests just reassign the class attributes).
func zpDomResetServices() {
	zpDomDatabaseSessionFactory = nil
	zpDomEventStore = nil
	zpDomCacheService = nil
	zpDomRepositoryFactory = nil
	zpDomTaskRepositoryFactory = nil
	zpDomProjectRepositoryFactory = nil
	zpDomGitBranchRepositoryFactory = nil
	zpDomNotificationService = nil
	zpDomEventBus = nil
	zpDomLoggingService = nil
	zpDomMonitoringService = nil
	zpDomProcessMonitor = nil
	zpDomValidationService = nil
	zpDomDocumentValidator = nil
	zpDomPathResolver = nil
	zpDomHintManager = nil
}

// TestDomainServiceFactory_InjectAndGet checks that a provided service replaces the
// shared state and is returned by its getter.
func TestDomainServiceFactory_InjectAndGet(t *testing.T) {
	zpDomResetServices()
	defer zpDomResetServices()

	var f DomainServiceFactory
	cache := &zpDomFakeCacheService{}
	f.InjectServices(map[string]any{"cache_service": cache})

	if got := f.GetCacheService(); got != interfaces.ICacheService(cache) {
		t.Fatalf("GetCacheService = %v, want the injected cache service", got)
	}
}

// TestDomainServiceFactory_InjectIsPartial checks that absent keys are left untouched
// and that present nil clears the value, as in the Python membership checks.
func TestDomainServiceFactory_InjectIsPartial(t *testing.T) {
	zpDomResetServices()
	defer zpDomResetServices()

	var f DomainServiceFactory
	store := &zpDomFakeEventStore{}
	f.InjectServices(map[string]any{"event_store": store})
	f.InjectServices(map[string]any{"unknown_service": 42})

	if got := f.GetEventStore(); got != interfaces.IEventStore(store) {
		t.Fatalf("GetEventStore = %v, want the injected event store", got)
	}

	// A cleared service is re-created by the lazy initializer (the database session
	// factory is still unset), so the getter yields the adapter factory's event store.
	f.InjectServices(map[string]any{"event_store": nil})
	if got := f.GetEventStore(); got == nil || got == interfaces.IEventStore(store) {
		t.Fatalf("GetEventStore after nil injection = %v, want the adapter event store", got)
	}
}

// TestDomainServiceFactory_InjectIgnoresWrongType documents that a value which does
// not implement the target interface cannot be stored in Go.
func TestDomainServiceFactory_InjectIgnoresWrongType(t *testing.T) {
	zpDomResetServices()
	defer zpDomResetServices()

	var f DomainServiceFactory
	f.InjectServices(map[string]any{"cache_service": "not a cache service"})

	// The unusable value is dropped; the lazy initializer supplies the adapter cache.
	if got := f.GetCacheService(); got == nil {
		t.Fatal("GetCacheService = nil, want the adapter cache service")
	}
}

// TestDomainServiceFactory_LazyInitUsesServiceAdapterFactory checks that the lazy
// initializer fills every service from the infrastructure ServiceAdapterFactory
// (the Python import succeeds), including the repository factories.
func TestDomainServiceFactory_LazyInitUsesServiceAdapterFactory(t *testing.T) {
	zpDomResetServices()
	defer zpDomResetServices()

	var f DomainServiceFactory
	if f.GetDatabaseSessionFactory() == nil {
		t.Fatal("GetDatabaseSessionFactory = nil")
	}
	if f.GetTaskRepositoryFactory() == nil || f.GetGitBranchRepositoryFactory() == nil {
		t.Fatal("repository factories must come from the adapter factory")
	}
	logging := f.GetLoggingService()
	if logging == nil || logging.GetLogger("test") == nil {
		t.Fatal("logging service missing")
	}
}

// TestDomainServiceFactory_LazyInitGuardQuirk checks the Python quirk: once the
// database session factory is set, the lazy initializer returns early, so an unset
// logging service stays nil even when its getter runs.
func TestDomainServiceFactory_LazyInitGuardQuirk(t *testing.T) {
	zpDomResetServices()
	defer zpDomResetServices()

	var f DomainServiceFactory
	f.InjectServices(map[string]any{"database_session_factory": &zpDomFakeDatabaseSessionFactory{}})

	if got := f.GetLoggingService(); got != nil {
		t.Fatalf("GetLoggingService = %v, want nil because the lazy guard returns early", got)
	}
}

// TestDomainServiceFactory_LazyInitHintManager checks the always-failing
// create_hint_manager import fallback (the Python .hint_manager module does not exist).
func TestDomainServiceFactory_LazyInitHintManager(t *testing.T) {
	zpDomResetServices()
	defer zpDomResetServices()

	var f DomainServiceFactory
	got := f.GetHintManager()
	if got == nil {
		t.Fatalf("GetHintManager = nil, want the fallback mock")
	}
	if _, ok := got.(zpDomHintManagerMock); !ok {
		t.Fatalf("GetHintManager type = %T, want zpDomHintManagerMock", got)
	}
}

// TestDomainServiceFactory_InjectAndGetAll checks every getter returns its injected
// service, mirroring the Python class attributes one-for-one.
func TestDomainServiceFactory_InjectAndGetAll(t *testing.T) {
	zpDomResetServices()
	defer zpDomResetServices()

	var f DomainServiceFactory
	dbSessionFactory := &zpDomFakeDatabaseSessionFactory{}
	eventStore := &zpDomFakeEventStore{}
	cacheService := &zpDomFakeCacheService{}
	repositoryFactory := &zpDomFakeRepositoryFactory{}
	taskRepositoryFactory := &zpDomFakeTaskRepositoryFactory{}
	projectRepositoryFactory := &zpDomFakeProjectRepositoryFactory{}
	gitBranchRepositoryFactory := &zpDomFakeGitBranchRepositoryFactory{}
	notificationService := &zpDomFakeNotificationService{}
	eventBus := &zpDomFakeEventBus{}
	loggingService := &zpDomFakeLoggingService{}
	monitoringService := &zpDomFakeMonitoringService{}
	processMonitor := &zpDomFakeProcessMonitor{}
	validationService := &zpDomFakeValidationService{}
	documentValidator := &zpDomFakeDocumentValidator{}
	pathResolver := &zpDomFakePathResolver{}
	hintManager := &zpDomFakeHintManager{}

	f.InjectServices(map[string]any{
		"database_session_factory":      dbSessionFactory,
		"event_store":                   eventStore,
		"cache_service":                 cacheService,
		"repository_factory":            repositoryFactory,
		"task_repository_factory":       taskRepositoryFactory,
		"project_repository_factory":    projectRepositoryFactory,
		"git_branch_repository_factory": gitBranchRepositoryFactory,
		"notification_service":          notificationService,
		"event_bus":                     eventBus,
		"logging_service":               loggingService,
		"monitoring_service":            monitoringService,
		"process_monitor":               processMonitor,
		"validation_service":            validationService,
		"document_validator":            documentValidator,
		"path_resolver":                 pathResolver,
		"hint_manager":                  hintManager,
	})

	if got := f.GetDatabaseSessionFactory(); got != interfaces.IDatabaseSessionFactory(dbSessionFactory) {
		t.Errorf("GetDatabaseSessionFactory mismatch: %v", got)
	}
	if got := f.GetEventStore(); got != interfaces.IEventStore(eventStore) {
		t.Errorf("GetEventStore mismatch: %v", got)
	}
	if got := f.GetCacheService(); got != interfaces.ICacheService(cacheService) {
		t.Errorf("GetCacheService mismatch: %v", got)
	}
	if got := f.GetRepositoryFactory(); got != interfaces.IRepositoryFactory(repositoryFactory) {
		t.Errorf("GetRepositoryFactory mismatch: %v", got)
	}
	if got := f.GetTaskRepositoryFactory(); got != interfaces.ITaskRepositoryFactory(taskRepositoryFactory) {
		t.Errorf("GetTaskRepositoryFactory mismatch: %v", got)
	}
	if got := f.GetProjectRepositoryFactory(); got != interfaces.IProjectRepositoryFactory(projectRepositoryFactory) {
		t.Errorf("GetProjectRepositoryFactory mismatch: %v", got)
	}
	if got := f.GetGitBranchRepositoryFactory(); got != interfaces.IGitBranchRepositoryFactory(gitBranchRepositoryFactory) {
		t.Errorf("GetGitBranchRepositoryFactory mismatch: %v", got)
	}
	if got := f.GetNotificationService(); got != interfaces.INotificationService(notificationService) {
		t.Errorf("GetNotificationService mismatch: %v", got)
	}
	if got := f.GetEventBus(); got != interfaces.IEventBus(eventBus) {
		t.Errorf("GetEventBus mismatch: %v", got)
	}
	if got := f.GetLoggingService(); got != interfaces.ILoggingService(loggingService) {
		t.Errorf("GetLoggingService mismatch: %v", got)
	}
	if got := f.GetMonitoringService(); got != interfaces.IMonitoringService(monitoringService) {
		t.Errorf("GetMonitoringService mismatch: %v", got)
	}
	if got := f.GetProcessMonitor(); got != interfaces.IProcessMonitor(processMonitor) {
		t.Errorf("GetProcessMonitor mismatch: %v", got)
	}
	if got := f.GetValidationService(); got != interfaces.IValidationService(validationService) {
		t.Errorf("GetValidationService mismatch: %v", got)
	}
	if got := f.GetDocumentValidator(); got != interfaces.IDocumentValidator(documentValidator) {
		t.Errorf("GetDocumentValidator mismatch: %v", got)
	}
	if got := f.GetPathResolver(); got != interfaces.IPathResolver(pathResolver) {
		t.Errorf("GetPathResolver mismatch: %v", got)
	}
	if got := f.GetHintManager(); got != any(hintManager) {
		t.Errorf("GetHintManager mismatch: %v", got)
	}
}

// TestDomainServiceFactory_SharedState checks the singleton behavior: two values see
// the same package state, like the Python __new__ singleton.
func TestDomainServiceFactory_SharedState(t *testing.T) {
	zpDomResetServices()
	defer zpDomResetServices()

	first := DomainServiceFactory{}
	second := DomainServiceFactory{}
	cache := &zpDomFakeCacheService{}
	first.InjectServices(map[string]any{"cache_service": cache})

	if got := second.GetCacheService(); got != interfaces.ICacheService(cache) {
		t.Fatalf("second factory GetCacheService = %v, want the shared cache service", got)
	}
}
