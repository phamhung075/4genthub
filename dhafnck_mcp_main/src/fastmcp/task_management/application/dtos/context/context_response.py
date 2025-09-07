"""Context Response DTOs"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime

from ....domain.entities.context import TaskContext


@dataclass
class ContextResponse:
    """Response DTO for context operations"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    context: Optional[TaskContext] = None
    
    @classmethod
    def success_response(cls, context: TaskContext = None, data: Dict[str, Any] = None, 
                        message: str = "Operation successful") -> 'ContextResponse':
        """Create a success response"""
        return cls(
            success=True,
            message=message,
            data=data,
            context=context
        )
    
    @classmethod
    def error_response(cls, error: str, message: str = "Operation failed") -> 'ContextResponse':
        """Create an error response"""
        return cls(
            success=False,
            message=message,
            error=error
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            'success': self.success,
            'message': self.message
        }
        
        if self.data:
            result['data'] = self.data
        
        if self.error:
            result['error'] = self.error
            
        if self.context:
            result['context'] = self.context.to_dict()
            
        return result


@dataclass
class CreateContextResponse(ContextResponse):
    """Response DTO for creating a context"""
    pass


@dataclass
class UpdateContextResponse(ContextResponse):
    """Response DTO for updating a context"""
    pass


@dataclass
class DeleteContextResponse(ContextResponse):
    """Response DTO for deleting a context"""
    pass


@dataclass
class ListContextsResponse(ContextResponse):
    """Response DTO for listing contexts"""
    contexts: List[TaskContext] = field(default_factory=list)
    
    @classmethod
    def success_response(cls, contexts: List[TaskContext], 
                        message: str = "Contexts retrieved successfully") -> 'ListContextsResponse':
        """Create a success response with contexts"""
        return cls(
            success=True,
            message=message,
            contexts=contexts
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = super().to_dict()
        result['contexts'] = [context.to_dict() for context in self.contexts]
        return result


@dataclass
class GetPropertyResponse(ContextResponse):
    """Response DTO for getting a property"""
    value: Any = None
    
    @classmethod
    def success_response(cls, value: Any, 
                        message: str = "Property retrieved successfully") -> 'GetPropertyResponse':
        """Create a success response with property value"""
        return cls(
            success=True,
            message=message,
            value=value
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = super().to_dict()
        result['value'] = self.value
        return result


@dataclass
class UpdatePropertyResponse(ContextResponse):
    """Response DTO for updating a property"""
    pass


@dataclass
class MergeContextResponse(ContextResponse):
    """Response DTO for merging context data"""
    pass


@dataclass
class MergeDataResponse(ContextResponse):
    """Response DTO for merging data (alias for MergeContextResponse)"""
    pass


@dataclass
class AddInsightResponse(ContextResponse):
    """Response DTO for adding an insight"""
    pass


@dataclass
class AddProgressResponse(ContextResponse):
    """Response DTO for adding progress"""
    pass


@dataclass
class UpdateNextStepsResponse(ContextResponse):
    """Response DTO for updating next steps"""
    pass