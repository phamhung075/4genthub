"""
REST API Routes for User-Specific Agent Management

Comprehensive REST endpoints for managing user agent instances,
templates, analytics, and configurations.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ....auth.interface.fastapi_auth import get_current_user, get_db
from ....auth.domain.entities.user import User
from ...application.facades.agent_management_facade import AgentManagementFacade
from ...infrastructure.repositories.orm.agent_template_repository import ORMAgentTemplateRepository
from ...infrastructure.repositories.orm.user_agent_instance_repository import ORMUserAgentInstanceRepository
from ...domain.value_objects.user_id import UserId

from .models import (
    AgentTemplateListResponse,
    AgentTemplateResponse,
    UserAgentInstanceListResponse,
    UserAgentInstanceResponse,
    CreateInstanceRequest,
    UpdateInstanceRequest,
    UsageAnalyticsResponse,
    UserUsageStats,
    PopularAgentStats,
    AgentConfigurationResponse,
    UpdateConfigurationRequest,
    SuccessResponse,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v2/agent-management",
    tags=["Agent Management - User Instances"]
)


def get_facade(db: Session = Depends(get_db)) -> AgentManagementFacade:
    """Dependency to get AgentManagementFacade with database session."""
    template_repo = ORMAgentTemplateRepository()
    instance_repo = ORMUserAgentInstanceRepository()

    # Inject session for repositories
    template_repo._session = db
    instance_repo._session = db

    return AgentManagementFacade(
        template_repository=template_repo,
        instance_repository=instance_repo
    )


# ============================================================================
# AGENT TEMPLATES ENDPOINTS (Read-Only)
# ============================================================================

@router.get(
    "/templates",
    response_model=AgentTemplateListResponse,
    summary="List all agent templates",
    description="Get list of all available agent templates from agent-library"
)
async def list_templates(
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
):
    """List all available agent templates."""
    try:
        logger.info(f"User {current_user.email} listing agent templates")

        templates = facade.list_available_templates()

        template_responses = [
            AgentTemplateResponse(
                id=str(t.id.value),
                slug=t.slug,
                name=t.name,
                description=t.description,
                category=t.category,
                version=t.version,
                system_prompt=t.configuration.system_prompt,
                tools=list(t.configuration.tools),
                capabilities=t.configuration.capabilities or {},
                rules=list(t.configuration.rules) if t.configuration.rules else None,
                output_format=t.configuration.output_format,
                metadata=t.metadata,
                created_at=t.created_at
            )
            for t in templates
        ]

        return AgentTemplateListResponse(
            success=True,
            templates=template_responses,
            count=len(template_responses)
        )

    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}"
        )


@router.get(
    "/templates/{slug}",
    response_model=AgentTemplateResponse,
    summary="Get specific agent template",
    description="Get detailed information about a specific agent template"
)
async def get_template(
    slug: str,
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
):
    """Get specific agent template by slug."""
    try:
        logger.info(f"User {current_user.email} getting template: {slug}")

        template = facade.get_template_by_slug(slug)

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{slug}' not found"
            )

        return AgentTemplateResponse(
            id=str(template.id.value),
            slug=template.slug,
            name=template.name,
            description=template.description,
            category=template.category,
            version=template.version,
            system_prompt=template.configuration.system_prompt,
            tools=list(template.configuration.tools),
            capabilities=template.configuration.capabilities or {},
            rules=list(template.configuration.rules) if template.configuration.rules else None,
            output_format=template.configuration.output_format,
            metadata=template.metadata,
            created_at=template.created_at
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template: {str(e)}"
        )


# ============================================================================
# USER AGENT INSTANCES ENDPOINTS (CRUD)
# ============================================================================

@router.get(
    "/instances",
    response_model=UserAgentInstanceListResponse,
    summary="List user's agent instances",
    description="Get list of all agent instances owned by current user"
)
async def list_user_instances(
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
):
    """List all user's agent instances."""
    try:
        user_id = UserId(current_user.id)
        logger.info(f"User {current_user.email} listing their agent instances")

        instances = facade.get_user_instances(user_id)

        instance_responses = [
            UserAgentInstanceResponse(
                id=str(inst.id.value),
                user_id=str(inst.user_id.value),
                template_id=str(inst.template_id.value),
                agent_name=inst.agent_name,
                is_customized=inst.is_customized,
                visibility=inst.visibility,
                usage_count=inst.usage_count,
                last_used_at=inst.last_used_at,
                created_at=inst.created_at,
                updated_at=inst.updated_at,
                system_prompt=inst.configuration.system_prompt,
                tools=list(inst.configuration.tools),
                capabilities=inst.configuration.capabilities or {},
                rules=list(inst.configuration.rules) if inst.configuration.rules else None,
                output_format=inst.configuration.output_format
            )
            for inst in instances
        ]

        return UserAgentInstanceListResponse(
            success=True,
            instances=instance_responses,
            count=len(instance_responses)
        )

    except Exception as e:
        logger.error(f"Error listing user instances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list instances: {str(e)}"
        )


@router.get(
    "/instances/{instance_id}",
    response_model=UserAgentInstanceResponse,
    summary="Get specific agent instance",
    description="Get detailed information about a specific agent instance"
)
async def get_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
):
    """Get specific agent instance by ID."""
    try:
        user_id = UserId(current_user.id)
        logger.info(f"User {current_user.email} getting instance: {instance_id}")

        # Get user's instances and find the requested one
        instances = facade.get_user_instances(user_id)
        instance = next((i for i in instances if str(i.id.value) == instance_id), None)

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instance '{instance_id}' not found or access denied"
            )

        return UserAgentInstanceResponse(
            id=str(instance.id.value),
            user_id=str(instance.user_id.value),
            template_id=str(instance.template_id.value),
            agent_name=instance.agent_name,
            is_customized=instance.is_customized,
            visibility=instance.visibility,
            usage_count=instance.usage_count,
            last_used_at=instance.last_used_at,
            created_at=instance.created_at,
            updated_at=instance.updated_at,
            system_prompt=instance.configuration.system_prompt,
            tools=list(instance.configuration.tools),
            capabilities=instance.configuration.capabilities or {},
            rules=list(instance.configuration.rules) if instance.configuration.rules else None,
            output_format=instance.configuration.output_format
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get instance: {str(e)}"
        )


@router.post(
    "/instances",
    response_model=UserAgentInstanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create/customize agent instance",
    description="Create a new customized agent instance from a template"
)
async def create_instance(
    request: CreateInstanceRequest,
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
):
    """Create new agent instance (auto-creates on first call)."""
    try:
        user_id = UserId(current_user.id)
        logger.info(f"User {current_user.email} creating instance from: {request.template_slug}")

        # Get or create instance (facade handles this)
        instance = facade.get_or_create_instance(user_id, request.template_slug)

        # Apply customizations if provided
        if any([request.agent_name, request.system_prompt, request.tools,
                request.capabilities, request.rules, request.output_format]):
            # TODO: Implement customization method in facade
            logger.info("Customizations requested but not yet implemented")

        return UserAgentInstanceResponse(
            id=str(instance.id.value),
            user_id=str(instance.user_id.value),
            template_id=str(instance.template_id.value),
            agent_name=instance.agent_name,
            is_customized=instance.is_customized,
            visibility=instance.visibility,
            usage_count=instance.usage_count,
            last_used_at=instance.last_used_at,
            created_at=instance.created_at,
            updated_at=instance.updated_at,
            system_prompt=instance.configuration.system_prompt,
            tools=list(instance.configuration.tools),
            capabilities=instance.configuration.capabilities or {},
            rules=list(instance.configuration.rules) if instance.configuration.rules else None,
            output_format=instance.configuration.output_format
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating instance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create instance: {str(e)}"
        )


@router.put(
    "/instances/{instance_id}",
    response_model=UserAgentInstanceResponse,
    summary="Update agent instance",
    description="Update configuration of an existing agent instance"
)
async def update_instance(
    instance_id: str,
    request: UpdateInstanceRequest,
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
):
    """Update agent instance configuration."""
    try:
        user_id = UserId(current_user.id)
        logger.info(f"User {current_user.email} updating instance: {instance_id}")

        # Update instance using facade
        updated_instance = facade.update_instance(
            user_id=user_id,
            instance_id=instance_id,
            agent_name=request.agent_name,
            system_prompt=request.system_prompt,
            tools=request.tools,
            capabilities=request.capabilities,
            rules=request.rules,
            output_format=request.output_format,
            visibility=request.visibility
        )

        # Build response
        template = facade.get_template_by_slug(updated_instance.template_id.value)
        return UserAgentInstanceResponse(
            id=updated_instance.id.value,
            user_id=updated_instance.user_id.value,
            template_id=updated_instance.template_id.value,
            agent_name=updated_instance.agent_name,
            is_customized=updated_instance.is_customized,
            visibility=updated_instance.visibility,
            usage_count=updated_instance.usage_count,
            last_used_at=updated_instance.last_used_at,
            created_at=updated_instance.created_at,
            updated_at=updated_instance.updated_at,
            system_prompt=updated_instance.configuration.system_prompt,
            tools=list(updated_instance.configuration.tools),
            capabilities=updated_instance.configuration.capabilities or {},
            rules=list(updated_instance.configuration.rules) if updated_instance.configuration.rules else [],
            output_format=updated_instance.configuration.output_format
        )

    except ValueError as e:
        logger.error(f"Validation error updating instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update instance: {str(e)}"
        )


@router.delete(
    "/instances/{instance_id}",
    response_model=SuccessResponse,
    summary="Delete agent instance",
    description="Delete a user's agent instance"
)
async def delete_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
):
    """Delete agent instance."""
    try:
        user_id = UserId(current_user.id)
        logger.info(f"User {current_user.email} deleting instance: {instance_id}")

        # Delete instance using facade
        success = facade.delete_instance(
            user_id=user_id,
            instance_id=instance_id
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete instance"
            )

        return SuccessResponse(
            success=True,
            message=f"Instance {instance_id} deleted successfully"
        )

    except ValueError as e:
        logger.error(f"Validation error deleting instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete instance: {str(e)}"
        )


# ============================================================================
# USAGE ANALYTICS ENDPOINTS
# ============================================================================

@router.get(
    "/analytics/usage",
    response_model=UsageAnalyticsResponse,
    summary="Get user's usage statistics",
    description="Get detailed usage statistics for current user's agents"
)
async def get_user_usage_stats(
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
):
    """Get user's agent usage statistics."""
    try:
        user_id = UserId(current_user.id)
        logger.info(f"User {current_user.email} getting usage statistics")

        instances = facade.get_user_instances(user_id)

        # Calculate stats
        total_calls = sum(inst.usage_count for inst in instances)
        unique_agents = len(instances)
        usage_by_agent = {inst.agent_name: inst.usage_count for inst in instances}

        # Find most used agent
        most_used = max(instances, key=lambda i: i.usage_count) if instances else None
        most_used_name = most_used.agent_name if most_used and most_used.usage_count > 0 else None

        # Find last activity
        instances_with_usage = [i for i in instances if i.last_used_at]
        last_activity = max((i.last_used_at for i in instances_with_usage), default=None)

        user_stats = UserUsageStats(
            total_calls=total_calls,
            unique_agents=unique_agents,
            most_used_agent=most_used_name,
            last_activity=last_activity,
            usage_by_agent=usage_by_agent
        )

        return UsageAnalyticsResponse(
            success=True,
            user_stats=user_stats
        )

    except Exception as e:
        logger.error(f"Error getting usage stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get usage statistics: {str(e)}"
        )


@router.get(
    "/analytics/popular",
    response_model=UsageAnalyticsResponse,
    summary="Get popular agents globally",
    description="Get statistics about most popular agents across all users"
)
async def get_popular_agents(
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade),
    limit: int = 10
):
    """Get globally popular agents."""
    try:
        logger.info(f"User {current_user.email} getting popular agents")

        # TODO: Implement global analytics query
        # For now, return empty list
        return UsageAnalyticsResponse(
            success=True,
            popular_agents=[],
            message="Global analytics not yet implemented"
        )

    except Exception as e:
        logger.error(f"Error getting popular agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get popular agents: {str(e)}"
        )


# ============================================================================
# AGENT CONFIGURATION ENDPOINTS
# ============================================================================

@router.get(
    "/configuration/{slug}",
    response_model=AgentConfigurationResponse,
    summary="Get agent configuration",
    description="Get current configuration for an agent (template or user instance)"
)
async def get_configuration(
    slug: str,
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
):
    """Get agent configuration for editing."""
    try:
        user_id = UserId(current_user.id)
        logger.info(f"User {current_user.email} getting configuration for: {slug}")

        # Get or create instance to get current config
        instance = facade.get_or_create_instance(user_id, slug)

        configuration = {
            "system_prompt": instance.configuration.system_prompt,
            "tools": list(instance.configuration.tools),
            "capabilities": instance.configuration.capabilities or {},
            "rules": list(instance.configuration.rules) if instance.configuration.rules else None,
            "output_format": instance.configuration.output_format
        }

        return AgentConfigurationResponse(
            success=True,
            instance_id=str(instance.id.value),
            template_id=str(instance.template_id.value),
            is_customized=instance.is_customized,
            configuration=configuration
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting configuration for {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration: {str(e)}"
        )


@router.put(
    "/configuration/{slug}",
    response_model=AgentConfigurationResponse,
    summary="Update agent configuration",
    description="Save customized configuration for an agent"
)
async def update_configuration(
    slug: str,
    request: UpdateConfigurationRequest,
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
):
    """Update agent configuration."""
    try:
        user_id = UserId(current_user.id)
        logger.info(f"User {current_user.email} updating configuration for: {slug}")

        # Update configuration using facade
        updated_instance = facade.update_configuration(
            user_id=user_id,
            agent_slug=slug,
            system_prompt=request.system_prompt,
            tools=request.tools,
            capabilities=request.capabilities,
            rules=request.rules,
            output_format=request.output_format
        )

        # Get template for response
        template = facade.get_template_by_slug(slug)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent template not found: {slug}"
            )

        return AgentConfigurationResponse(
            success=True,
            instance_id=updated_instance.id.value if updated_instance.id else None,
            template_id=template.id.value,
            is_customized=updated_instance.is_customized,
            configuration={
                "system_prompt": updated_instance.configuration.system_prompt,
                "tools": list(updated_instance.configuration.tools),
                "capabilities": updated_instance.configuration.capabilities or {},
                "rules": list(updated_instance.configuration.rules) if updated_instance.configuration.rules else [],
                "output_format": updated_instance.configuration.output_format
            },
            message=f"Configuration updated for {slug}"
        )

    except ValueError as e:
        logger.error(f"Validation error updating configuration for {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating configuration for {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.post(
    "/configuration/{slug}/reset",
    response_model=AgentConfigurationResponse,
    summary="Reset agent to default",
    description="Reset agent configuration back to template defaults"
)
async def reset_configuration(
    slug: str,
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
):
    """Reset agent configuration to template defaults."""
    try:
        user_id = UserId(current_user.id)
        logger.info(f"User {current_user.email} resetting configuration for: {slug}")

        # Reset configuration using facade
        reset_instance = facade.reset_configuration(
            user_id=user_id,
            agent_slug=slug
        )

        # Get template for response
        template = facade.get_template_by_slug(slug)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent template not found: {slug}"
            )

        return AgentConfigurationResponse(
            success=True,
            instance_id=reset_instance.id.value if reset_instance.id else None,
            template_id=template.id.value,
            is_customized=reset_instance.is_customized,
            configuration={
                "system_prompt": reset_instance.configuration.system_prompt,
                "tools": list(reset_instance.configuration.tools),
                "capabilities": reset_instance.configuration.capabilities or {},
                "rules": list(reset_instance.configuration.rules) if reset_instance.configuration.rules else [],
                "output_format": reset_instance.configuration.output_format
            },
            message=f"Configuration reset to default for {slug}"
        )

    except ValueError as e:
        logger.error(f"Validation error resetting configuration for {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting configuration for {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset configuration: {str(e)}"
        )
