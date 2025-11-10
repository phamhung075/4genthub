"""
REST API Routes for User-Specific Agent Management

Comprehensive REST endpoints for managing user agent instances,
templates, analytics, and configurations.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ....auth.domain.entities.user import User
from ....auth.interface.fastapi_auth import get_current_user, get_db
from ...application.facades.agent_management_facade import AgentManagementFacade
from ...domain.value_objects.user_id import UserId
from ...infrastructure.repositories.orm.agent_template_repository import (
    ORMAgentTemplateRepository,
)
from ...infrastructure.repositories.orm.user_agent_instance_repository import (
    ORMUserAgentInstanceRepository,
)
from .models import (
    AgentConfigurationResponse,
    AgentTemplateListResponse,
    AgentTemplateResponse,
    CreateInstanceRequest,
    ImportAgentRequest,
    MarketplaceAgentResponse,
    MarketplaceListResponse,
    ShareAgentResponse,
    SharedAgentPreviewResponse,
    SuccessResponse,
    UpdateConfigurationRequest,
    UpdateInstanceRequest,
    UsageAnalyticsResponse,
    UserAgentInstanceListResponse,
    UserAgentInstanceResponse,
    UserUsageStats,
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
                system_prompt=t.default_configuration.system_prompt,
                tools=list(t.default_configuration.tools),
                capabilities=t.default_configuration.capabilities or {},
                rules=list(t.default_configuration.rules) if t.default_configuration.rules else None,
                output_format=t.default_configuration.output_format,
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
            system_prompt=template.default_configuration.system_prompt,
            tools=list(template.default_configuration.tools),
            capabilities=template.default_configuration.capabilities or {},
            rules=list(template.default_configuration.rules) if template.default_configuration.rules else None,
            output_format=template.default_configuration.output_format,
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
                is_enabled=inst.is_enabled,
                visibility=inst.visibility,
                usage_count=inst.usage_count,
                last_used_at=inst.last_used_at,
                created_at=inst.created_at,
                updated_at=inst.updated_at,
                is_imported=inst.original_creator_id is not None,
                original_creator_id=str(inst.original_creator_id.value) if inst.original_creator_id else None,
                is_read_only=(
                    inst.original_creator_id is not None and
                    str(inst.original_creator_id.value) != str(user_id.value)
                ),
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
            is_enabled=instance.is_enabled,
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

        # Broadcast WebSocket event for real-time UI updates
        try:
            from ....task_management.application.services.websocket_notification_service import (
                WebSocketNotificationService,
            )
            agent_data = {
                "id": str(instance.id.value),
                "user_id": str(instance.user_id.value),
                "template_id": str(instance.template_id.value),
                "agent_name": instance.agent_name,
                "name": instance.agent_name,
                "is_customized": instance.is_customized,
                "is_enabled": instance.is_enabled,
                "visibility": instance.visibility,
                "usage_count": instance.usage_count,
            }
            WebSocketNotificationService.sync_broadcast_agent_event(
                event_type="created",
                agent_id=str(instance.id.value),
                project_id="default",
                user_id=str(current_user.id),
                agent_data=agent_data
            )
        except Exception as ws_error:
            logger.warning(f"Failed to broadcast WebSocket event: {ws_error}")

        return UserAgentInstanceResponse(
            id=str(instance.id.value),
            user_id=str(instance.user_id.value),
            template_id=str(instance.template_id.value),
            agent_name=instance.agent_name,
            is_customized=instance.is_customized,
            is_enabled=instance.is_enabled,
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


@router.post(
    "/instances/bulk-create",
    response_model=list[UserAgentInstanceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk create agent instances",
    description="Create instances for multiple templates in a single request. Only creates instances that don't already exist."
)
async def bulk_create_instances(
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
):
    """
    Create instances for all available agent templates that the user doesn't already have.

    This endpoint:
    - Gets all available templates from the agent library
    - Checks which templates the user already has instances for
    - Creates instances only for missing templates
    - Returns the newly created instances
    """
    try:
        user_id = UserId(current_user.id)
        logger.info(f"User {current_user.email} bulk creating all agent instances")

        # Create instances for all templates (facade handles duplicate checking)
        created_instances = facade.bulk_create_instances(user_id=user_id, template_slugs=None)

        # Broadcast WebSocket events for each created instance (real-time UI updates)
        from ....task_management.application.services.websocket_notification_service import (
            WebSocketNotificationService,
        )
        for instance in created_instances:
            try:
                # Prepare agent data for WebSocket payload
                agent_data = {
                    "id": str(instance.id.value),
                    "user_id": str(instance.user_id.value),
                    "template_id": str(instance.template_id.value),
                    "agent_name": instance.agent_name,
                    "name": instance.agent_name,  # Include both for compatibility
                    "is_customized": instance.is_customized,
                    "is_enabled": instance.is_enabled,
                    "visibility": instance.visibility,
                    "usage_count": instance.usage_count,
                    "last_used_at": instance.last_used_at.isoformat() if instance.last_used_at else None,
                    "created_at": instance.created_at.isoformat() if instance.created_at else None,
                    "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
                }

                # Emit WebSocket event for this agent creation
                WebSocketNotificationService.sync_broadcast_agent_event(
                    event_type="created",
                    agent_id=str(instance.id.value),
                    project_id="default",  # User agent instances are not project-scoped
                    user_id=str(current_user.id),
                    agent_data=agent_data
                )
            except Exception as ws_error:
                # Don't fail the entire bulk creation if WebSocket fails
                logger.warning(f"Failed to broadcast WebSocket event for agent {instance.agent_name}: {ws_error}")

        # Convert to response format
        instance_responses = [
            UserAgentInstanceResponse(
                id=str(instance.id.value),
                user_id=str(instance.user_id.value),
                template_id=str(instance.template_id.value),
                agent_name=instance.agent_name,
                is_customized=instance.is_customized,
                is_enabled=instance.is_enabled,
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
            for instance in created_instances
        ]

        logger.info(f"Bulk created {len(instance_responses)} agent instances with WebSocket notifications")
        return instance_responses

    except Exception as e:
        logger.error(f"Error bulk creating instances: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk create instances: {str(e)}"
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
        # Handle both UUID and non-UUID user IDs (for development)
        try:
            user_id = UserId(current_user.id)
        except ValueError:
            # Convert non-UUID ID to deterministic UUID v5
            import uuid
            namespace_uuid = uuid.UUID('00000000-0000-0000-0000-000000000000')
            user_uuid = str(uuid.uuid5(namespace_uuid, current_user.id))
            user_id = UserId(user_uuid)
            logger.info(f"Converted non-UUID user ID '{current_user.id}' to UUID: {user_uuid}")

        logger.info(f"User {current_user.email} updating instance: {instance_id}")

        # Update instance using facade (facade will check read-only permissions)
        updated_instance = facade.update_instance(
            user_id=user_id,
            instance_id=instance_id,
            agent_name=request.agent_name,
            is_enabled=request.is_enabled,
            system_prompt=request.system_prompt,
            tools=request.tools,
            capabilities=request.capabilities,
            rules=request.rules,
            output_format=request.output_format,
            visibility=request.visibility
        )

        # Broadcast WebSocket event for real-time UI updates
        try:
            from ....task_management.application.services.websocket_notification_service import (
                WebSocketNotificationService,
            )
            agent_data = {
                "id": str(updated_instance.id.value),
                "user_id": str(updated_instance.user_id.value),
                "template_id": str(updated_instance.template_id.value),
                "agent_name": updated_instance.agent_name,
                "name": updated_instance.agent_name,
                "is_customized": updated_instance.is_customized,
                "is_enabled": updated_instance.is_enabled,
                "visibility": updated_instance.visibility,
                "usage_count": updated_instance.usage_count,
            }
            WebSocketNotificationService.sync_broadcast_agent_event(
                event_type="updated",
                agent_id=str(updated_instance.id.value),
                project_id="default",
                user_id=str(current_user.id),
                agent_data=agent_data
            )
        except Exception as ws_error:
            logger.warning(f"Failed to broadcast WebSocket event: {ws_error}")

        # Build response
        return UserAgentInstanceResponse(
            id=updated_instance.id.value,
            user_id=updated_instance.user_id.value,
            template_id=updated_instance.template_id.value,
            agent_name=updated_instance.agent_name,
            is_customized=updated_instance.is_customized,
            is_enabled=updated_instance.is_enabled,
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
        error_msg = str(e)
        logger.error(f"Validation error updating instance {instance_id}: {error_msg}")

        # Check if this is a read-only violation (imported agent)
        if "Cannot edit imported agent" in error_msg or "original creator" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg
            )

        # Other validation errors are 400 Bad Request
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
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

        # Get instance first to retrieve name for WebSocket notification
        agent_name = None
        try:
            user_instances = facade.get_user_instances(user_id=user_id)
            matching_instance = next((inst for inst in user_instances if str(inst.id.value) == instance_id), None)
            if matching_instance:
                agent_name = matching_instance.agent_name
                logger.info(f"Found agent name for WebSocket: {agent_name}")
            else:
                logger.warning(f"Instance {instance_id} not found in user's instances")
        except Exception as e:
            logger.warning(f"Could not retrieve instance name before delete: {e}")

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

        # Broadcast WebSocket event for real-time UI updates
        try:
            from ....task_management.application.services.websocket_notification_service import (
                WebSocketNotificationService,
            )
            agent_data = {
                "id": instance_id,
                "user_id": str(current_user.id),
                "name": agent_name,
                "agent_name": agent_name,  # Include both for compatibility
            }
            WebSocketNotificationService.sync_broadcast_agent_event(
                event_type="deleted",
                agent_id=instance_id,
                project_id="default",
                user_id=str(current_user.id),
                agent_data=agent_data
            )
        except Exception as ws_error:
            logger.warning(f"Failed to broadcast WebSocket event: {ws_error}")

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


# ============================================================================
# Agent Sharing Endpoints (Phase 3.6-3.10)
# ============================================================================

@router.post("/instances/{instance_id}/share", response_model=ShareAgentResponse)
async def share_agent(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
) -> ShareAgentResponse:
    """
    Share an agent instance publicly (Phase 3.6).

    Generates a secure 64-character share token and makes the instance public.
    Only the instance owner can share.

    Args:
        instance_id: UUID of the instance to share
        current_user: Authenticated user (from JWT)
        facade: AgentManagementFacade dependency

    Returns:
        ShareAgentResponse with share_token and shareable URL

    Raises:
        404: Instance not found or not owned by user
        500: Server error during sharing
    """
    try:
        user_id = UserId(current_user.id)
        logger.info(f"User {current_user.email} sharing instance: {instance_id}")

        # Call facade to share the agent (returns share_token string)
        share_token = facade.share_agent(
            user_id=user_id,
            instance_id=instance_id
        )

        # Construct shareable URL
        shareable_url = f"/api/v2/agent-management/marketplace/{share_token}"

        return ShareAgentResponse(
            instance_id=instance_id,
            share_token=share_token,
            shareable_url=shareable_url,
            visibility="public",
            message="Agent shared successfully"
        )

    except ValueError as e:
        logger.error(f"Validation error sharing instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sharing instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to share agent: {str(e)}"
        )


@router.post("/instances/{instance_id}/unshare", response_model=SuccessResponse)
async def unshare_agent(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
) -> SuccessResponse:
    """
    Revoke share token and make agent private (Phase 3.7).

    Only the instance owner can unshare. Existing imports remain unaffected
    as they are copies.

    Args:
        instance_id: UUID of the instance to unshare
        current_user: Authenticated user (from JWT)
        facade: AgentManagementFacade dependency

    Returns:
        SuccessResponse confirming unshare

    Raises:
        404: Instance not found or not owned by user
        500: Server error during unsharing
    """
    try:
        user_id = UserId(current_user.id)
        logger.info(f"User {current_user.email} unsharing instance: {instance_id}")

        # Call facade to unshare the agent (returns True on success)
        facade.unshare_agent(
            user_id=user_id,
            instance_id=instance_id
        )

        return SuccessResponse(
            message="Agent unshared successfully. It is now private."
        )

    except ValueError as e:
        logger.error(f"Validation error unsharing instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unsharing instance {instance_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unshare agent: {str(e)}"
        )


@router.post("/import", response_model=UserAgentInstanceResponse)
async def import_agent(
    request: ImportAgentRequest,
    current_user: User = Depends(get_current_user),
    facade: AgentManagementFacade = Depends(get_facade)
) -> UserAgentInstanceResponse:
    """
    Import a shared agent from marketplace (Phase 3.8).

    Creates a copy of the shared agent for the current user.
    Handles name collisions by appending "- created by [creator_email]".
    Records import in agent_import_history.

    Args:
        request: ImportAgentRequest with share_token
        current_user: Authenticated user (from JWT)
        facade: AgentManagementFacade dependency

    Returns:
        UserAgentInstanceResponse for the imported instance

    Raises:
        400: Invalid share token format
        404: Share token not found or agent not public
        409: User already has instance for this template
        500: Server error during import
    """
    try:
        # Handle both UUID and non-UUID user IDs (for development)
        try:
            user_id = UserId(current_user.id)
        except ValueError:
            # If user ID is not a valid UUID (e.g., 'dev-user-001' in development),
            # create a deterministic UUID from it using UUID v5 (name-based)
            import uuid
            namespace_uuid = uuid.UUID('00000000-0000-0000-0000-000000000000')
            user_uuid = str(uuid.uuid5(namespace_uuid, current_user.id))
            user_id = UserId(user_uuid)
            logger.info(f"Converted non-UUID user ID '{current_user.id}' to UUID: {user_uuid}")

        logger.info(f"User {current_user.email} importing agent with share token")

        # Call facade to import the agent
        imported_instance = facade.import_agent(
            share_token=request.share_token,
            importer_user_id=user_id,
            creator_email=current_user.email
        )

        # Convert to response model
        # Imported agents are read-only for the importer
        is_read_only = (
            imported_instance.original_creator_id is not None and
            str(imported_instance.original_creator_id.value) != str(user_id.value)
        )

        return UserAgentInstanceResponse(
            id=str(imported_instance.id.value),
            user_id=str(imported_instance.user_id.value),
            template_id=str(imported_instance.template_id.value),
            agent_name=imported_instance.agent_name,
            is_customized=imported_instance.is_customized,
            is_enabled=imported_instance.is_enabled,
            visibility=imported_instance.visibility,
            usage_count=imported_instance.usage_count,
            last_used_at=imported_instance.last_used_at,
            created_at=imported_instance.created_at,
            updated_at=imported_instance.updated_at,
            is_imported=True,  # This is an imported agent
            original_creator_id=str(imported_instance.original_creator_id.value) if imported_instance.original_creator_id else None,
            is_read_only=is_read_only,  # Read-only for non-owners
            system_prompt=imported_instance.configuration.system_prompt,
            tools=list(imported_instance.configuration.tools),
            capabilities=imported_instance.configuration.capabilities,
            rules=list(imported_instance.configuration.rules) if imported_instance.configuration.rules else None,
            output_format=imported_instance.configuration.output_format
        )

    except ValueError as e:
        logger.error(f"Validation error importing agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing agent with token {request.share_token[:10]}...: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import agent: {str(e)}"
        )


@router.get("/marketplace", response_model=MarketplaceListResponse)
async def browse_marketplace(
    category: str | None = None,
    search: str | None = None,
    sort: str | None = "recent",
    page: int = 1,
    page_size: int = 50,
    facade: AgentManagementFacade = Depends(get_facade)
) -> MarketplaceListResponse:
    """
    Browse publicly shared agents in marketplace (Phase 3.9).

    Lists all public agents with filtering and sorting options.
    No authentication required - marketplace is public.

    Args:
        category: Filter by agent category (e.g., 'development')
        search: Search in agent names
        sort: Sort order ('popular', 'recent')
        page: Page number (1-indexed)
        page_size: Results per page (max 100)
        facade: AgentManagementFacade dependency

    Returns:
        MarketplaceListResponse with list of agents

    Raises:
        400: Invalid pagination parameters
        500: Server error during query
    """
    try:
        logger.info("Browsing marketplace with filters")

        # Validate pagination
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page number must be >= 1"
            )
        if page_size < 1 or page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page size must be between 1 and 100"
            )

        # Calculate offset
        offset = (page - 1) * page_size

        # Get public instances from facade
        instances = facade.get_marketplace_agents(limit=page_size, offset=offset)

        # TODO: Implement filtering and sorting (category, search, sort)
        # For now, return all instances as-is

        # Get template information for each instance
        agent_responses = []
        for instance in instances:
            template = facade.get_template_by_id(
                str(instance.template_id.value) if hasattr(instance.template_id, 'value')
                else str(instance.template_id)
            )

            # Build customizations summary
            customizations = []
            if instance.is_customized:
                customizations.append("Custom configuration")

            agent_responses.append(
                MarketplaceAgentResponse(
                    instance_id=str(instance.id.value),
                    agent_name=instance.agent_name,
                    template_slug=template.slug if template else "unknown",
                    creator_display_name=instance.get_creator_display_name(),
                    share_token=instance.share_token or "",
                    customizations_summary=", ".join(customizations) if customizations else "Default template",
                    usage_count=instance.usage_count,
                    created_at=instance.created_at
                )
            )

        return MarketplaceListResponse(
            agents=agent_responses,
            total=len(agent_responses),
            page=page,
            page_size=page_size,
            message=f"Found {len(agent_responses)} public agents"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error browsing marketplace: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to browse marketplace: {str(e)}"
        )


@router.get("/marketplace/{share_token}", response_model=SharedAgentPreviewResponse)
async def preview_shared_agent(
    share_token: str,
    facade: AgentManagementFacade = Depends(get_facade)
) -> SharedAgentPreviewResponse:
    """
    Preview a shared agent before importing (Phase 3.10).

    Public endpoint - no authentication required.
    Shows read-only configuration preview and creator info.

    Args:
        share_token: 64-character share token
        facade: AgentManagementFacade dependency

    Returns:
        SharedAgentPreviewResponse with agent details

    Raises:
        400: Invalid share token format
        404: Share token not found or agent not public
        500: Server error during preview
    """
    try:
        logger.info("Previewing shared agent with token")

        # Call facade to get preview
        instance = facade.get_shared_agent_preview(share_token)

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shared agent not found or is no longer public"
            )

        # Get template information
        template = facade.get_template_by_id(
            str(instance.template_id.value) if hasattr(instance.template_id, 'value')
            else str(instance.template_id)
        )

        # Build configuration preview
        configuration_preview = {
            "system_prompt": instance.configuration.system_prompt,
            "tools": list(instance.configuration.tools),
            "capabilities": instance.configuration.capabilities or {},
            "rules": list(instance.configuration.rules) if instance.configuration.rules else [],
            "output_format": instance.configuration.output_format
        }

        # Build customizations summary
        customizations = []
        if instance.is_customized:
            customizations.append("Custom configuration")
        customizations_summary = ", ".join(customizations) if customizations else "Default template configuration"

        return SharedAgentPreviewResponse(
            agent_name=instance.agent_name,
            template_slug=template.slug if template else "unknown",
            creator_display_name=instance.get_creator_display_name(),
            configuration_preview=configuration_preview,
            customizations_summary=customizations_summary,
            can_import=True,
            message="Agent preview loaded successfully"
        )

    except ValueError as e:
        logger.error(f"Validation error previewing shared agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing shared agent {share_token[:10]}...: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview shared agent: {str(e)}"
        )
