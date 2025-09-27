"""
Resource-based CRUD Permission System

This module provides granular permission checking for MCP resources
with support for resource-specific CRUD operations.
"""

from typing import List, Dict, Optional, Set, Any
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Enumeration of MCP resource types"""
    PROJECTS = "projects"
    TASKS = "tasks"
    SUBTASKS = "subtasks"
    CONTEXTS = "contexts"
    AGENTS = "agents"
    BRANCHES = "branches"
    MCP = "mcp"


class PermissionAction(Enum):
    """CRUD actions for resources"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    DELEGATE = "delegate"


@dataclass
class ResourcePermission:
    """Represents a permission for a specific resource and action"""
    resource: ResourceType
    action: PermissionAction
    
    @property
    def scope_name(self) -> str:
        """Get the scope name in format 'resource:action'"""
        return f"{self.resource.value}:{self.action.value}"
    
    @classmethod
    def from_scope(cls, scope: str) -> Optional["ResourcePermission"]:
        """Create ResourcePermission from scope string"""
        try:
            if ":" not in scope:
                return None
            resource_str, action_str = scope.split(":", 1)
            
            # Try to match resource type
            resource = None
            for res_type in ResourceType:
                if res_type.value == resource_str:
                    resource = res_type
                    break
            
            if not resource:
                return None
            
            # Try to match action
            action = None
            for perm_action in PermissionAction:
                if perm_action.value == action_str:
                    action = perm_action
                    break
            
            if not action:
                return None
            
            return cls(resource=resource, action=action)
        except Exception as e:
            logger.debug(f"Could not parse scope '{scope}': {e}")
            return None


class PermissionChecker:
    """Utility class for checking resource permissions"""
    
    def __init__(self, token_payload: Dict[str, Any]):
        """
        Initialize permission checker with JWT token payload
        
        Args:
            token_payload: Decoded JWT token payload
        """
        self.token_payload = token_payload
        self.scopes = self._extract_scopes()
        self.permissions = self._extract_permissions()
        self.roles = self._extract_roles()
        
    def _extract_scopes(self) -> Set[str]:
        """Extract scopes from token"""
        scopes = set()
        
        # Check 'scope' field (OAuth2 style)
        if "scope" in self.token_payload:
            scope_str = self.token_payload["scope"]
            if isinstance(scope_str, str):
                scopes.update(scope_str.split())
        
        # Check 'scopes' field (array style)
        if "scopes" in self.token_payload:
            scope_list = self.token_payload["scopes"]
            if isinstance(scope_list, list):
                scopes.update(scope_list)
        
        return scopes
    
    def _extract_permissions(self) -> Dict[str, Dict[str, bool]]:
        """Extract permissions from token payload"""
        permissions = {}
        
        # Check direct permissions object
        if "permissions" in self.token_payload:
            perms = self.token_payload["permissions"]
            if isinstance(perms, dict):
                # Handle nested structure like permissions.projects.create
                for resource, actions in perms.items():
                    if isinstance(actions, dict):
                        permissions[resource] = actions
                    elif isinstance(actions, bool):
                        # Handle flat structure like permissions.create
                        permissions[resource] = {"all": actions}
        
        # Parse scopes into permissions
        for scope in self.scopes:
            perm = ResourcePermission.from_scope(scope)
            if perm:
                resource = perm.resource.value
                action = perm.action.value
                if resource not in permissions:
                    permissions[resource] = {}
                permissions[resource][action] = True
        
        return permissions
    
    def _extract_roles(self) -> Set[str]:
        """Extract roles from token"""
        roles = set()
        
        # Check realm_roles
        if "realm_roles" in self.token_payload:
            realm_roles = self.token_payload["realm_roles"]
            if isinstance(realm_roles, list):
                roles.update(realm_roles)
        
        # Check realm_access.roles
        if "realm_access" in self.token_payload:
            realm_access = self.token_payload["realm_access"]
            if isinstance(realm_access, dict) and "roles" in realm_access:
                access_roles = realm_access["roles"]
                if isinstance(access_roles, list):
                    roles.update(access_roles)
        
        return roles
    
    def has_permission(self, resource: ResourceType, action: PermissionAction) -> bool:
        """
        Check if user has specific permission for resource and action
        
        Args:
            resource: The resource type
            action: The action to perform
            
        Returns:
            True if user has permission, False otherwise
        """
        # Admin role has all permissions
        if "admin" in self.roles:
            return True
        
        # Check specific scope
        scope = f"{resource.value}:{action.value}"
        if scope in self.scopes:
            return True
        
        # Check permissions object
        resource_perms = self.permissions.get(resource.value, {})
        if resource_perms.get(action.value, False):
            return True
        
        # Check for "all" permission on resource
        if resource_perms.get("all", False):
            return True
        
        # Check for global permissions (backward compatibility)
        global_perms = self.permissions.get("global", {})
        if global_perms.get(action.value, False):
            return True
        
        return False
    
    def has_scope(self, scope: str) -> bool:
        """Check if user has specific scope"""
        return scope in self.scopes
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role"""
        return role in self.roles
    
    def has_any_permission(self, resource: ResourceType, actions: List[PermissionAction]) -> bool:
        """Check if user has any of the specified permissions"""
        return any(self.has_permission(resource, action) for action in actions)
    
    def has_all_permissions(self, resource: ResourceType, actions: List[PermissionAction]) -> bool:
        """Check if user has all of the specified permissions"""
        return all(self.has_permission(resource, action) for action in actions)
    
    def get_allowed_actions(self, resource: ResourceType) -> List[PermissionAction]:
        """Get all allowed actions for a resource"""
        allowed = []
        for action in PermissionAction:
            if self.has_permission(resource, action):
                allowed.append(action)
        return allowed
    
    def get_allowed_resources(self) -> List[ResourceType]:
        """Get all resources user has any permission for"""
        allowed = []
        for resource in ResourceType:
            if any(self.has_permission(resource, action) for action in PermissionAction):
                allowed.append(resource)
        return allowed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert permissions to dictionary format"""
        return {
            "scopes": list(self.scopes),
            "roles": list(self.roles),
            "permissions": self.permissions,
            "allowed_resources": [r.value for r in self.get_allowed_resources()]
        }


def require_permission(resource: ResourceType, action: PermissionAction):
    """
    Decorator for FastAPI endpoints to require specific permission
    
    Usage:
        @router.post("/projects")
        @require_permission(ResourceType.PROJECTS, PermissionAction.CREATE)
        async def create_project(request: Request):
            ...
    """
    from functools import wraps
    from fastapi import HTTPException, Request
    
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get user from request (assumes authentication middleware has run)
            if not hasattr(request.state, "user") or not request.state.user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            user = request.state.user
            
            # Get token payload
            token_payload = getattr(user, "token", {})
            if not token_payload:
                raise HTTPException(status_code=401, detail="No token payload found")
            
            # Check permission
            checker = PermissionChecker(token_payload)
            if not checker.has_permission(resource, action):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {resource.value}:{action.value}"
                )
            
            # Add permission checker to request state for use in endpoint
            request.state.permissions = checker
            
            return await func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator


def require_any_permission(*permissions: List[tuple[ResourceType, PermissionAction]]):
    """
    Decorator to require any of the specified permissions
    
    Usage:
        @require_any_permission(
            (ResourceType.TASKS, PermissionAction.CREATE),
            (ResourceType.TASKS, PermissionAction.UPDATE)
        )
    """
    from functools import wraps
    from fastapi import HTTPException, Request
    
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not hasattr(request.state, "user") or not request.state.user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            user = request.state.user
            token_payload = getattr(user, "token", {})
            if not token_payload:
                raise HTTPException(status_code=401, detail="No token payload found")
            
            checker = PermissionChecker(token_payload)
            
            # Check if user has any of the required permissions
            has_any = False
            for resource, action in permissions:
                if checker.has_permission(resource, action):
                    has_any = True
                    break
            
            if not has_any:
                perm_strs = [f"{r.value}:{a.value}" for r, a in permissions]
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: requires any of {', '.join(perm_strs)}"
                )
            
            request.state.permissions = checker
            return await func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator


def require_scope(scope: str):
    """
    Decorator to require specific scope
    
    Usage:
        @require_scope("mcp-api")
    """
    from functools import wraps
    from fastapi import HTTPException, Request
    
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not hasattr(request.state, "user") or not request.state.user:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            user = request.state.user
            token_payload = getattr(user, "token", {})
            if not token_payload:
                raise HTTPException(status_code=401, detail="No token payload found")
            
            checker = PermissionChecker(token_payload)
            
            if not checker.has_scope(scope):
                raise HTTPException(
                    status_code=403,
                    detail=f"Scope required: {scope}"
                )
            
            request.state.permissions = checker
            return await func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator