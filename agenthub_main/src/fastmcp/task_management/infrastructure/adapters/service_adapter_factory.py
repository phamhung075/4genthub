"""Service Adapter Factory - Infrastructure Layer

This factory provides domain interfaces to the application layer,
ensuring DDD compliance by abstracting infrastructure dependencies.
"""

from typing import Optional

from ...domain.interfaces.database_session import IDatabaseSessionFactory
from ...domain.interfaces.event_store import IEventStore
from ...domain.interfaces.notification_service import INotificationService
from ...domain.interfaces.cache_service import ICacheService
from ...domain.interfaces.event_bus import IEventBus
from ...domain.interfaces.repository_factory import (
    IRepositoryFactory, ITaskRepositoryFactory, IProjectRepositoryFactory, 
    IGitBranchRepositoryFactory
)
from ...domain.interfaces.logging_service import ILoggingService
from ...domain.interfaces.monitoring_service import IMonitoringService, IProcessMonitor
from ...domain.interfaces.validation_service import IValidationService, IDocumentValidator
from ...domain.interfaces.utility_service import IPathResolver, IAgentDocGenerator

from .sqlalchemy_session_adapter import SQLAlchemySessionFactory
from .event_store_adapter import EventStoreAdapter
from .cache_service_adapter import CacheServiceAdapter
from .repository_factory_adapter import (
    RepositoryFactoryAdapter, TaskRepositoryFactoryAdapter,
    ProjectRepositoryFactoryAdapter, GitBranchRepositoryFactoryAdapter
)


class ServiceAdapterFactory:
    """Factory for creating domain service interfaces"""
    
    _instance = None
    _database_session_factory: Optional[IDatabaseSessionFactory] = None
    _event_store: Optional[IEventStore] = None
    _cache_service: Optional[ICacheService] = None
    _repository_factory: Optional[IRepositoryFactory] = None
    _task_repository_factory: Optional[ITaskRepositoryFactory] = None
    _project_repository_factory: Optional[IProjectRepositoryFactory] = None
    _git_branch_repository_factory: Optional[IGitBranchRepositoryFactory] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_database_session_factory(cls) -> IDatabaseSessionFactory:
        """Get database session factory"""
        if cls._database_session_factory is None:
            cls._database_session_factory = SQLAlchemySessionFactory()
        return cls._database_session_factory
    
    @classmethod
    def get_event_store(cls) -> IEventStore:
        """Get event store"""
        if cls._event_store is None:
            cls._event_store = EventStoreAdapter()
        return cls._event_store
    
    @classmethod
    def get_cache_service(cls) -> ICacheService:
        """Get cache service"""
        if cls._cache_service is None:
            cls._cache_service = CacheServiceAdapter()
        return cls._cache_service
    
    @classmethod
    def get_repository_factory(cls) -> IRepositoryFactory:
        """Get repository factory"""
        if cls._repository_factory is None:
            cls._repository_factory = RepositoryFactoryAdapter()
        return cls._repository_factory
    
    @classmethod
    def get_task_repository_factory(cls) -> ITaskRepositoryFactory:
        """Get task repository factory"""
        if cls._task_repository_factory is None:
            cls._task_repository_factory = TaskRepositoryFactoryAdapter()
        return cls._task_repository_factory
    
    @classmethod
    def get_project_repository_factory(cls) -> IProjectRepositoryFactory:
        """Get project repository factory"""
        if cls._project_repository_factory is None:
            cls._project_repository_factory = ProjectRepositoryFactoryAdapter()
        return cls._project_repository_factory
    
    @classmethod
    def get_git_branch_repository_factory(cls) -> IGitBranchRepositoryFactory:
        """Get git branch repository factory"""
        if cls._git_branch_repository_factory is None:
            cls._git_branch_repository_factory = GitBranchRepositoryFactoryAdapter()
        return cls._git_branch_repository_factory
    
    @classmethod
    def get_notification_service(cls) -> INotificationService:
        """Get notification service - placeholder implementation"""
        from .placeholder_adapters import PlaceholderNotificationService
        return PlaceholderNotificationService()
    
    @classmethod
    def get_event_bus(cls) -> IEventBus:
        """Get event bus - placeholder implementation"""
        from .placeholder_adapters import PlaceholderEventBus
        return PlaceholderEventBus()
    
    @classmethod
    def get_logging_service(cls) -> ILoggingService:
        """Get logging service - placeholder implementation"""
        from .placeholder_adapters import PlaceholderLoggingService
        return PlaceholderLoggingService()
    
    @classmethod
    def get_monitoring_service(cls) -> IMonitoringService:
        """Get monitoring service - placeholder implementation"""
        from .placeholder_adapters import PlaceholderMonitoringService
        return PlaceholderMonitoringService()
    
    @classmethod
    def get_process_monitor(cls) -> IProcessMonitor:
        """Get process monitor - placeholder implementation"""
        from .placeholder_adapters import PlaceholderProcessMonitor
        return PlaceholderProcessMonitor()
    
    @classmethod
    def get_validation_service(cls) -> IValidationService:
        """Get validation service - placeholder implementation"""
        from .placeholder_adapters import PlaceholderValidationService
        return PlaceholderValidationService()
    
    @classmethod
    def get_document_validator(cls) -> IDocumentValidator:
        """Get document validator - placeholder implementation"""
        from .placeholder_adapters import PlaceholderDocumentValidator
        return PlaceholderDocumentValidator()
    
    @classmethod
    def get_path_resolver(cls) -> IPathResolver:
        """Get path resolver - placeholder implementation"""
        from .placeholder_adapters import PlaceholderPathResolver
        return PlaceholderPathResolver()
    
    @classmethod
    def get_agent_doc_generator(cls) -> IAgentDocGenerator:
        """Get agent doc generator - placeholder implementation"""
        from .placeholder_adapters import PlaceholderAgentDocGenerator
        return PlaceholderAgentDocGenerator()