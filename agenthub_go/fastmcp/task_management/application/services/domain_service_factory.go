// Domain Service Factory - Application Layer
//
// This factory provides access to domain interfaces without violating DDD layer
// boundaries. It delegates to infrastructure adapters through dependency injection
// (Python application/services/domain_service_factory.py).
//
// Python keeps every service in a class-level attribute and makes the class a
// process-wide singleton through __new__. The Go port keeps the same shared state in
// package-level variables, so every zero DomainServiceFactory sees and mutates the
// same services; the singleton instance itself carries no state.

package services

import (
	"agenthub/fastmcp/task_management/domain/interfaces"
	"agenthub/fastmcp/task_management/infrastructure/adapters"
)

// DomainServiceFactory is the factory for accessing domain services through
// dependency injection. Its methods mirror the Python class methods; all of them
// operate on the process-wide package state below.
type DomainServiceFactory struct{}

// Service instances, injected by infrastructure (Python class attributes).
var (
	zpDomDatabaseSessionFactory     interfaces.IDatabaseSessionFactory
	zpDomEventStore                 interfaces.IEventStore
	zpDomCacheService               interfaces.ICacheService
	zpDomRepositoryFactory          interfaces.IRepositoryFactory
	zpDomTaskRepositoryFactory      interfaces.ITaskRepositoryFactory
	zpDomProjectRepositoryFactory   interfaces.IProjectRepositoryFactory
	zpDomGitBranchRepositoryFactory interfaces.IGitBranchRepositoryFactory
	zpDomNotificationService        interfaces.INotificationService
	zpDomEventBus                   interfaces.IEventBus
	zpDomLoggingService             interfaces.ILoggingService
	zpDomMonitoringService          interfaces.IMonitoringService
	zpDomProcessMonitor             interfaces.IProcessMonitor
	zpDomValidationService          interfaces.IValidationService
	zpDomDocumentValidator          interfaces.IDocumentValidator
	zpDomPathResolver               interfaces.IPathResolver
	// Python's HintManager (from .hint_manager) is not ported; the value is held as
	// any and the lazy fallback installs a minimal marker (see lazyInitHintManager).
	zpDomHintManager any
)

// InjectServices mirrors inject_services(**services): every provided key replaces the
// matching class attribute and absent keys are left untouched. Python assigns the raw
// value, so a value that does not implement the matching Go interface is ignored here
// (Go cannot store it in the typed variable).
func (DomainServiceFactory) InjectServices(services map[string]any) {
	zpDomInject(services, "database_session_factory", &zpDomDatabaseSessionFactory)
	zpDomInject(services, "event_store", &zpDomEventStore)
	zpDomInject(services, "cache_service", &zpDomCacheService)
	zpDomInject(services, "repository_factory", &zpDomRepositoryFactory)
	zpDomInject(services, "task_repository_factory", &zpDomTaskRepositoryFactory)
	zpDomInject(services, "project_repository_factory", &zpDomProjectRepositoryFactory)
	zpDomInject(services, "git_branch_repository_factory", &zpDomGitBranchRepositoryFactory)
	zpDomInject(services, "notification_service", &zpDomNotificationService)
	zpDomInject(services, "event_bus", &zpDomEventBus)
	zpDomInject(services, "logging_service", &zpDomLoggingService)
	zpDomInject(services, "monitoring_service", &zpDomMonitoringService)
	zpDomInject(services, "process_monitor", &zpDomProcessMonitor)
	zpDomInject(services, "validation_service", &zpDomValidationService)
	zpDomInject(services, "document_validator", &zpDomDocumentValidator)
	zpDomInject(services, "path_resolver", &zpDomPathResolver)
	zpDomInject(services, "hint_manager", &zpDomHintManager)
}

// zpDomInject assigns services[key] to dst when the key is present. A present nil
// clears the destination; a value of a different dynamic type is left out, because
// the typed destination cannot hold it.
func zpDomInject[T any](services map[string]any, key string, dst *T) {
	v, ok := services[key]
	if !ok {
		return
	}
	if v == nil {
		var zero T
		*dst = zero
		return
	}
	if typed, ok := v.(T); ok {
		*dst = typed
	}
}

// GetDatabaseSessionFactory gets the database session factory.
func (DomainServiceFactory) GetDatabaseSessionFactory() interfaces.IDatabaseSessionFactory {
	if zpDomDatabaseSessionFactory == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomDatabaseSessionFactory
}

// GetEventStore gets the event store.
func (DomainServiceFactory) GetEventStore() interfaces.IEventStore {
	if zpDomEventStore == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomEventStore
}

// GetCacheService gets the cache service.
func (DomainServiceFactory) GetCacheService() interfaces.ICacheService {
	if zpDomCacheService == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomCacheService
}

// GetRepositoryFactory gets the repository factory.
func (DomainServiceFactory) GetRepositoryFactory() interfaces.IRepositoryFactory {
	if zpDomRepositoryFactory == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomRepositoryFactory
}

// GetTaskRepositoryFactory gets the task repository factory.
func (DomainServiceFactory) GetTaskRepositoryFactory() interfaces.ITaskRepositoryFactory {
	if zpDomTaskRepositoryFactory == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomTaskRepositoryFactory
}

// GetProjectRepositoryFactory gets the project repository factory.
func (DomainServiceFactory) GetProjectRepositoryFactory() interfaces.IProjectRepositoryFactory {
	if zpDomProjectRepositoryFactory == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomProjectRepositoryFactory
}

// GetGitBranchRepositoryFactory gets the git branch repository factory.
func (DomainServiceFactory) GetGitBranchRepositoryFactory() interfaces.IGitBranchRepositoryFactory {
	if zpDomGitBranchRepositoryFactory == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomGitBranchRepositoryFactory
}

// GetNotificationService gets the notification service.
func (DomainServiceFactory) GetNotificationService() interfaces.INotificationService {
	if zpDomNotificationService == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomNotificationService
}

// GetEventBus gets the event bus.
func (DomainServiceFactory) GetEventBus() interfaces.IEventBus {
	if zpDomEventBus == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomEventBus
}

// GetLoggingService gets the logging service.
func (DomainServiceFactory) GetLoggingService() interfaces.ILoggingService {
	if zpDomLoggingService == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomLoggingService
}

// GetMonitoringService gets the monitoring service.
func (DomainServiceFactory) GetMonitoringService() interfaces.IMonitoringService {
	if zpDomMonitoringService == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomMonitoringService
}

// GetProcessMonitor gets the process monitor.
func (DomainServiceFactory) GetProcessMonitor() interfaces.IProcessMonitor {
	if zpDomProcessMonitor == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomProcessMonitor
}

// GetValidationService gets the validation service.
func (DomainServiceFactory) GetValidationService() interfaces.IValidationService {
	if zpDomValidationService == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomValidationService
}

// GetDocumentValidator gets the document validator.
func (DomainServiceFactory) GetDocumentValidator() interfaces.IDocumentValidator {
	if zpDomDocumentValidator == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomDocumentValidator
}

// GetPathResolver gets the path resolver.
func (DomainServiceFactory) GetPathResolver() interfaces.IPathResolver {
	if zpDomPathResolver == nil {
		DomainServiceFactory{}.lazyInitServices()
	}
	return zpDomPathResolver
}

// GetHintManager gets the hint manager. HintManager is not part of the Go port yet,
// so the result is the minimal fallback marker (claiming otherwise would be a lie).
func (DomainServiceFactory) GetHintManager() any {
	if zpDomHintManager == nil {
		DomainServiceFactory{}.lazyInitHintManager()
	}
	return zpDomHintManager
}

// lazyInitServices ports _lazy_init_services: when no database session factory was
// injected, every service comes from the infrastructure ServiceAdapterFactory (the
// Python import succeeds because the module exists, so the ImportError fallback
// branch with only a logging service is unreachable and not ported).
func (DomainServiceFactory) lazyInitServices() {
	if zpDomDatabaseSessionFactory != nil {
		return
	}
	f := adapters.GetServiceAdapterFactory()
	zpDomDatabaseSessionFactory = f.GetDatabaseSessionFactory()
	zpDomEventStore = f.GetEventStore()
	zpDomCacheService = f.GetCacheService()
	zpDomRepositoryFactory = f.GetRepositoryFactory()
	zpDomTaskRepositoryFactory = f.GetTaskRepositoryFactory()
	zpDomProjectRepositoryFactory = f.GetProjectRepositoryFactory()
	zpDomGitBranchRepositoryFactory = f.GetGitBranchRepositoryFactory()
	zpDomNotificationService = f.GetNotificationService()
	zpDomEventBus = f.GetEventBus()
	zpDomLoggingService = f.GetLoggingService()
	zpDomMonitoringService = f.GetMonitoringService()
	zpDomProcessMonitor = f.GetProcessMonitor()
	zpDomValidationService = f.GetValidationService()
	zpDomDocumentValidator = f.GetDocumentValidator()
	zpDomPathResolver = f.GetPathResolver()
}

// lazyInitHintManager ports _lazy_init_hint_manager. Python imports
// create_hint_manager from .hint_manager; that module does not exist, so the import
// always raises and the `except Exception` branch installs a unittest.mock.Mock().
// Go has no Mock, so a minimal marker type stands in and keeps the getter non-nil.
func (DomainServiceFactory) lazyInitHintManager() {
	if zpDomHintManager != nil {
		return
	}
	zpDomHintManager = zpDomHintManagerMock{}
}

// zpDomHintManagerMock stands in for Python's unittest.mock.Mock() installed when the
// hint manager import fails. Python's Mock answers every attribute access; no Go
// caller can observe more than a non-nil value because HintManager is not ported.
type zpDomHintManagerMock struct{}
