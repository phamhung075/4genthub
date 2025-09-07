"""Domain Service Factory - Application Layer

This factory provides access to domain interfaces without violating DDD layer boundaries.
It delegates to infrastructure adapters through dependency injection.
"""

from typing import Optional

from fastmcp.task_management.domain.interfaces.database_session import IDatabaseSessionFactory
from fastmcp.task_management.domain.interfaces.event_store import IEventStore
from fastmcp.task_management.domain.interfaces.notification_service import INotificationService
from fastmcp.task_management.domain.interfaces.cache_service import ICacheService
from fastmcp.task_management.domain.interfaces.event_bus import IEventBus
from fastmcp.task_management.domain.interfaces.repository_factory import (
    IRepositoryFactory, ITaskRepositoryFactory, IProjectRepositoryFactory, 
    IGitBranchRepositoryFactory
)
from fastmcp.task_management.domain.interfaces.logging_service import ILoggingService
from fastmcp.task_management.domain.interfaces.monitoring_service import IMonitoringService, IProcessMonitor
from fastmcp.task_management.domain.interfaces.validation_service import IValidationService, IDocumentValidator
from fastmcp.task_management.domain.interfaces.utility_service import IPathResolver, IAgentDocGenerator


class DomainServiceFactory:
    """Factory for accessing domain services through dependency injection"""
    
    _instance = None
    
    # Service instances (injected by infrastructure)
    _database_session_factory: Optional[IDatabaseSessionFactory] = None
    _event_store: Optional[IEventStore] = None
    _cache_service: Optional[ICacheService] = None
    _repository_factory: Optional[IRepositoryFactory] = None
    _task_repository_factory: Optional[ITaskRepositoryFactory] = None
    _project_repository_factory: Optional[IProjectRepositoryFactory] = None
    _git_branch_repository_factory: Optional[IGitBranchRepositoryFactory] = None
    _notification_service: Optional[INotificationService] = None
    _event_bus: Optional[IEventBus] = None
    _logging_service: Optional[ILoggingService] = None
    _monitoring_service: Optional[IMonitoringService] = None
    _process_monitor: Optional[IProcessMonitor] = None
    _validation_service: Optional[IValidationService] = None
    _document_validator: Optional[IDocumentValidator] = None
    _path_resolver: Optional[IPathResolver] = None
    _agent_doc_generator: Optional[IAgentDocGenerator] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def inject_services(cls, **services):
        """Inject services from infrastructure layer"""
        if 'database_session_factory' in services:
            cls._database_session_factory = services['database_session_factory']
        if 'event_store' in services:
            cls._event_store = services['event_store']
        if 'cache_service' in services:
            cls._cache_service = services['cache_service']
        if 'repository_factory' in services:
            cls._repository_factory = services['repository_factory']
        if 'task_repository_factory' in services:
            cls._task_repository_factory = services['task_repository_factory']
        if 'project_repository_factory' in services:
            cls._project_repository_factory = services['project_repository_factory']
        if 'git_branch_repository_factory' in services:
            cls._git_branch_repository_factory = services['git_branch_repository_factory']
        if 'notification_service' in services:
            cls._notification_service = services['notification_service']
        if 'event_bus' in services:
            cls._event_bus = services['event_bus']
        if 'logging_service' in services:
            cls._logging_service = services['logging_service']
        if 'monitoring_service' in services:
            cls._monitoring_service = services['monitoring_service']
        if 'process_monitor' in services:
            cls._process_monitor = services['process_monitor']
        if 'validation_service' in services:
            cls._validation_service = services['validation_service']
        if 'document_validator' in services:
            cls._document_validator = services['document_validator']
        if 'path_resolver' in services:
            cls._path_resolver = services['path_resolver']
        if 'agent_doc_generator' in services:
            cls._agent_doc_generator = services['agent_doc_generator']
    
    @classmethod
    def get_database_session_factory(cls) -> IDatabaseSessionFactory:
        """Get database session factory"""
        if cls._database_session_factory is None:
            cls._lazy_init_services()
        return cls._database_session_factory
    
    @classmethod
    def get_event_store(cls) -> IEventStore:
        """Get event store"""
        if cls._event_store is None:
            cls._lazy_init_services()
        return cls._event_store
    
    @classmethod
    def get_cache_service(cls) -> ICacheService:
        """Get cache service"""
        if cls._cache_service is None:
            cls._lazy_init_services()
        return cls._cache_service
    
    @classmethod
    def get_repository_factory(cls) -> IRepositoryFactory:
        """Get repository factory"""
        if cls._repository_factory is None:
            cls._lazy_init_services()
        return cls._repository_factory
    
    @classmethod
    def get_task_repository_factory(cls) -> ITaskRepositoryFactory:
        """Get task repository factory"""
        if cls._task_repository_factory is None:
            cls._lazy_init_services()
        return cls._task_repository_factory
    
    @classmethod
    def get_project_repository_factory(cls) -> IProjectRepositoryFactory:
        """Get project repository factory"""
        if cls._project_repository_factory is None:
            cls._lazy_init_services()
        return cls._project_repository_factory
    
    @classmethod
    def get_git_branch_repository_factory(cls) -> IGitBranchRepositoryFactory:
        """Get git branch repository factory"""
        if cls._git_branch_repository_factory is None:
            cls._lazy_init_services()
        return cls._git_branch_repository_factory
    
    @classmethod
    def get_notification_service(cls) -> INotificationService:
        """Get notification service"""
        if cls._notification_service is None:
            cls._lazy_init_services()
        return cls._notification_service
    
    @classmethod
    def get_event_bus(cls) -> IEventBus:
        """Get event bus"""
        if cls._event_bus is None:
            cls._lazy_init_services()
        return cls._event_bus
    
    @classmethod
    def get_logging_service(cls) -> ILoggingService:
        """Get logging service"""
        if cls._logging_service is None:
            cls._lazy_init_services()
        return cls._logging_service
    
    @classmethod
    def get_monitoring_service(cls) -> IMonitoringService:
        """Get monitoring service"""
        if cls._monitoring_service is None:
            cls._lazy_init_services()
        return cls._monitoring_service
    
    @classmethod
    def get_process_monitor(cls) -> IProcessMonitor:
        """Get process monitor"""
        if cls._process_monitor is None:
            cls._lazy_init_services()
        return cls._process_monitor
    
    @classmethod
    def get_validation_service(cls) -> IValidationService:
        """Get validation service"""
        if cls._validation_service is None:
            cls._lazy_init_services()
        return cls._validation_service
    
    @classmethod
    def get_document_validator(cls) -> IDocumentValidator:
        """Get document validator"""
        if cls._document_validator is None:
            cls._lazy_init_services()
        return cls._document_validator
    
    @classmethod
    def get_path_resolver(cls) -> IPathResolver:
        """Get path resolver"""
        if cls._path_resolver is None:
            cls._lazy_init_services()
        return cls._path_resolver
    
    @classmethod
    def get_agent_doc_generator(cls) -> IAgentDocGenerator:
        """Get agent doc generator"""
        if cls._agent_doc_generator is None:
            cls._lazy_init_services()
        return cls._agent_doc_generator
    
    @classmethod
    def _lazy_init_services(cls):
        """Lazy initialization of services using infrastructure adapters"""
        if cls._database_session_factory is None:
            # Import here to avoid circular dependencies and layer violations
            try:
                # This is the only allowed infrastructure import - through the factories
                from ...infrastructure.adapters.service_adapter_factory import ServiceAdapterFactory
                
                # Initialize all services
                cls._database_session_factory = ServiceAdapterFactory.get_database_session_factory()
                cls._event_store = ServiceAdapterFactory.get_event_store()
                cls._cache_service = ServiceAdapterFactory.get_cache_service()
                cls._repository_factory = ServiceAdapterFactory.get_repository_factory()
                cls._task_repository_factory = ServiceAdapterFactory.get_task_repository_factory()
                cls._project_repository_factory = ServiceAdapterFactory.get_project_repository_factory()
                cls._git_branch_repository_factory = ServiceAdapterFactory.get_git_branch_repository_factory()
                cls._notification_service = ServiceAdapterFactory.get_notification_service()
                cls._event_bus = ServiceAdapterFactory.get_event_bus()
                cls._logging_service = ServiceAdapterFactory.get_logging_service()
                cls._monitoring_service = ServiceAdapterFactory.get_monitoring_service()
                cls._process_monitor = ServiceAdapterFactory.get_process_monitor()
                cls._validation_service = ServiceAdapterFactory.get_validation_service()
                cls._document_validator = ServiceAdapterFactory.get_document_validator()
                cls._path_resolver = ServiceAdapterFactory.get_path_resolver()
                cls._agent_doc_generator = ServiceAdapterFactory.get_agent_doc_generator()
            except ImportError:
                # Fallback to placeholder implementations
                from fastmcp.task_management.domain.interfaces.logging_service import LogLevel
                import logging
                
                class FallbackLoggingService:
                    def get_logger(self, name):
                        return logging.getLogger(name)
                
                cls._logging_service = FallbackLoggingService()
                # Other services would need similar fallbacks