"""
Pydantic Models for Agent Management REST API

Request and response models for user-specific agent system endpoints.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, UUID4


# ============================================================================
# Agent Template Models (Read-Only)
# ============================================================================

class AgentTemplateResponse(BaseModel):
    """Response model for agent template"""
    id: str = Field(..., description="Template UUID")
    slug: str = Field(..., description="Template slug (e.g., 'coding-agent')")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Agent category")
    version: str = Field(..., description="Template version")
    system_prompt: str = Field(..., description="Default system prompt")
    tools: List[str] = Field(default_factory=list, description="Available tools")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Agent capabilities")
    rules: Optional[List[str]] = Field(None, description="Agent rules")
    output_format: Optional[str] = Field(None, description="Output format preference")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class AgentTemplateListResponse(BaseModel):
    """Response model for list of agent templates"""
    success: bool = True
    templates: List[AgentTemplateResponse]
    count: int
    message: Optional[str] = None


# ============================================================================
# User Agent Instance Models (CRUD)
# ============================================================================

class CreateInstanceRequest(BaseModel):
    """Request to create/customize agent instance"""
    template_slug: str = Field(..., description="Template to instantiate from")
    agent_name: Optional[str] = Field(None, description="Custom name for instance")
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")
    tools: Optional[List[str]] = Field(None, description="Custom tool list")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="Custom capabilities")
    rules: Optional[List[str]] = Field(None, description="Custom rules")
    output_format: Optional[str] = Field(None, description="Custom output format")
    visibility: str = Field(default="private", description="'private' or 'public'")


class UpdateInstanceRequest(BaseModel):
    """Request to update agent instance"""
    agent_name: Optional[str] = Field(None, description="Updated name")
    system_prompt: Optional[str] = Field(None, description="Updated system prompt")
    tools: Optional[List[str]] = Field(None, description="Updated tool list")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="Updated capabilities")
    rules: Optional[List[str]] = Field(None, description="Updated rules")
    output_format: Optional[str] = Field(None, description="Updated output format")
    visibility: Optional[str] = Field(None, description="Updated visibility")


class UserAgentInstanceResponse(BaseModel):
    """Response model for user agent instance"""
    id: str = Field(..., description="Instance UUID")
    user_id: str = Field(..., description="Owner user ID")
    template_id: str = Field(..., description="Source template UUID")
    agent_name: str = Field(..., description="Instance name")
    is_customized: bool = Field(..., description="Whether instance is customized")
    visibility: str = Field(..., description="'private' or 'public'")
    usage_count: int = Field(default=0, description="Number of times used")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Configuration details
    system_prompt: str = Field(..., description="Active system prompt")
    tools: List[str] = Field(default_factory=list, description="Active tools")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Active capabilities")
    rules: Optional[List[str]] = Field(None, description="Active rules")
    output_format: Optional[str] = Field(None, description="Active output format")

    class Config:
        from_attributes = True


class UserAgentInstanceListResponse(BaseModel):
    """Response model for list of user instances"""
    success: bool = True
    instances: List[UserAgentInstanceResponse]
    count: int
    message: Optional[str] = None


# ============================================================================
# Usage Analytics Models
# ============================================================================

class UserUsageStats(BaseModel):
    """User's agent usage statistics"""
    total_calls: int = Field(..., description="Total agent calls")
    unique_agents: int = Field(..., description="Number of unique agents used")
    most_used_agent: Optional[str] = Field(None, description="Most frequently used agent")
    last_activity: Optional[datetime] = Field(None, description="Last agent usage")
    usage_by_agent: Dict[str, int] = Field(default_factory=dict, description="Call count per agent")


class PopularAgentStats(BaseModel):
    """Global agent popularity statistics"""
    slug: str
    name: str
    total_users: int = Field(..., description="Number of users using this agent")
    total_calls: int = Field(..., description="Total calls across all users")
    avg_calls_per_user: float = Field(..., description="Average calls per user")


class UsageAnalyticsResponse(BaseModel):
    """Response model for usage analytics"""
    success: bool = True
    user_stats: Optional[UserUsageStats] = None
    popular_agents: Optional[List[PopularAgentStats]] = None
    message: Optional[str] = None


# ============================================================================
# Agent Configuration Models
# ============================================================================

class AgentConfigurationResponse(BaseModel):
    """Response model for agent configuration"""
    success: bool = True
    instance_id: Optional[str] = Field(None, description="Instance ID if exists")
    template_id: str = Field(..., description="Template ID")
    is_customized: bool = Field(..., description="Whether config is customized")
    configuration: Dict[str, Any] = Field(..., description="Complete configuration")
    message: Optional[str] = None


class UpdateConfigurationRequest(BaseModel):
    """Request to update agent configuration"""
    system_prompt: Optional[str] = Field(None, description="Updated system prompt")
    tools: Optional[List[str]] = Field(None, description="Updated tool list")
    capabilities: Optional[Dict[str, Any]] = Field(None, description="Updated capabilities")
    rules: Optional[List[str]] = Field(None, description="Updated rules")
    output_format: Optional[str] = Field(None, description="Updated output format")


# ============================================================================
# Agent Sharing Models
# ============================================================================

class ShareAgentResponse(BaseModel):
    """Response model for sharing an agent"""
    success: bool = True
    instance_id: str = Field(..., description="Instance UUID")
    share_token: str = Field(..., description="64-character share token")
    shareable_url: str = Field(..., description="URL for sharing")
    visibility: str = Field(..., description="Visibility status ('public')")
    message: Optional[str] = None


class ImportAgentRequest(BaseModel):
    """Request to import a shared agent"""
    share_token: str = Field(..., description="64-character share token from shared agent")


class MarketplaceAgentResponse(BaseModel):
    """Response model for marketplace agent listing"""
    instance_id: str = Field(..., description="Instance UUID")
    agent_name: str = Field(..., description="Agent display name")
    template_slug: str = Field(..., description="Template slug")
    creator_display_name: str = Field(..., description="Creator attribution")
    share_token: str = Field(..., description="Share token for importing")
    customizations_summary: str = Field(..., description="Summary of customizations")
    usage_count: int = Field(default=0, description="Usage statistics")
    created_at: datetime = Field(..., description="Creation timestamp")


class MarketplaceListResponse(BaseModel):
    """Response model for marketplace agent list"""
    success: bool = True
    agents: List[MarketplaceAgentResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of agents")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=50, description="Results per page")
    message: Optional[str] = None


class SharedAgentPreviewResponse(BaseModel):
    """Response model for shared agent preview"""
    success: bool = True
    agent_name: str = Field(..., description="Agent display name")
    template_slug: str = Field(..., description="Template slug")
    creator_display_name: str = Field(..., description="Creator attribution")
    configuration_preview: Dict[str, Any] = Field(..., description="Configuration details")
    customizations_summary: str = Field(..., description="Summary of changes from template")
    can_import: bool = Field(default=True, description="Whether user can import this agent")
    message: Optional[str] = None


# ============================================================================
# Generic Response Models
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: str
    detail: Optional[str] = None
