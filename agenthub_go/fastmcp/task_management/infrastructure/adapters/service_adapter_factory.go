// service_adapter_factory.go ports task_management/infrastructure/adapters/service_adapter_factory.py.
package adapters

import (
	"sync"

	"agenthub/fastmcp/task_management/domain/interfaces"
)

// ServiceAdapterFactory is service_adapter_factory.ServiceAdapterFactory.
type ServiceAdapterFactory struct{}

var (
	safInstance                   *ServiceAdapterFactory
	safOnce                       sync.Once
	safDatabaseSessionFactory     interfaces.IDatabaseSessionFactory
	safEventStore                 interfaces.IEventStore
	safCacheService               interfaces.ICacheService
	safRepositoryFactory          interfaces.IRepositoryFactory
	safTaskRepositoryFactory      interfaces.ITaskRepositoryFactory
	safProjectRepositoryFactory   interfaces.IProjectRepositoryFactory
	safGitBranchRepositoryFactory interfaces.IGitBranchRepositoryFactory
	safMu                         sync.Mutex
)

func GetServiceAdapterFactory() *ServiceAdapterFactory {
	safOnce.Do(func() {
		safInstance = &ServiceAdapterFactory{}
	})
	return safInstance
}

func (f *ServiceAdapterFactory) GetDatabaseSessionFactory() interfaces.IDatabaseSessionFactory {
	safMu.Lock()
	defer safMu.Unlock()
	if safDatabaseSessionFactory == nil {
		safDatabaseSessionFactory = NewSQLAlchemySessionFactory()
	}
	return safDatabaseSessionFactory
}

func (f *ServiceAdapterFactory) GetEventStore() interfaces.IEventStore {
	safMu.Lock()
	defer safMu.Unlock()
	if safEventStore == nil {
		safEventStore = NewEventStoreAdapter()
	}
	return safEventStore
}

func (f *ServiceAdapterFactory) GetCacheService() interfaces.ICacheService {
	safMu.Lock()
	defer safMu.Unlock()
	if safCacheService == nil {
		safCacheService = NewCacheServiceAdapter()
	}
	return safCacheService
}

func (f *ServiceAdapterFactory) GetRepositoryFactory() interfaces.IRepositoryFactory {
	safMu.Lock()
	defer safMu.Unlock()
	if safRepositoryFactory == nil {
		safRepositoryFactory = NewRepositoryFactoryAdapter()
	}
	return safRepositoryFactory
}

func (f *ServiceAdapterFactory) GetTaskRepositoryFactory() interfaces.ITaskRepositoryFactory {
	safMu.Lock()
	defer safMu.Unlock()
	if safTaskRepositoryFactory == nil {
		safTaskRepositoryFactory = NewTaskRepositoryFactoryAdapter()
	}
	return safTaskRepositoryFactory
}

func (f *ServiceAdapterFactory) GetProjectRepositoryFactory() interfaces.IProjectRepositoryFactory {
	safMu.Lock()
	defer safMu.Unlock()
	if safProjectRepositoryFactory == nil {
		safProjectRepositoryFactory = NewProjectRepositoryFactoryAdapter()
	}
	return safProjectRepositoryFactory
}

func (f *ServiceAdapterFactory) GetGitBranchRepositoryFactory() interfaces.IGitBranchRepositoryFactory {
	safMu.Lock()
	defer safMu.Unlock()
	if safGitBranchRepositoryFactory == nil {
		safGitBranchRepositoryFactory = NewGitBranchRepositoryFactoryAdapter()
	}
	return safGitBranchRepositoryFactory
}

func (f *ServiceAdapterFactory) GetNotificationService() interfaces.INotificationService {
	return &PlaceholderNotificationService{}
}

func (f *ServiceAdapterFactory) GetEventBus() interfaces.IEventBus {
	return &PlaceholderEventBus{}
}

func (f *ServiceAdapterFactory) GetLoggingService() interfaces.ILoggingService {
	return &PlaceholderLoggingService{}
}

func (f *ServiceAdapterFactory) GetMonitoringService() interfaces.IMonitoringService {
	return &PlaceholderMonitoringService{}
}

func (f *ServiceAdapterFactory) GetProcessMonitor() interfaces.IProcessMonitor {
	return &PlaceholderProcessMonitor{}
}

func (f *ServiceAdapterFactory) GetValidationService() interfaces.IValidationService {
	return &PlaceholderValidationService{}
}

func (f *ServiceAdapterFactory) GetDocumentValidator() interfaces.IDocumentValidator {
	return &PlaceholderDocumentValidator{}
}

func (f *ServiceAdapterFactory) GetPathResolver() interfaces.IPathResolver {
	return &PlaceholderPathResolver{}
}
