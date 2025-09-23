"""
Branch API Controller

This controller handles frontend branch management operations following proper DDD architecture.
It serves as the interface layer, delegating business logic to application facades.
"""

import logging
import time
from typing import Dict, Any, Optional

from sqlalchemy import text

from ...application.facades.git_branch_application_facade import GitBranchApplicationFacade
from ...application.services.facade_service import FacadeService

logger = logging.getLogger(__name__)


class BranchAPIController:
    """
    API Controller for branch management operations.
    
    This controller provides a clean interface between frontend routes and
    application services, ensuring proper separation of concerns.
    """
    
    def __init__(self):
        """Initialize the controller"""
        self.facade_service = FacadeService.get_instance()

    def _refresh_summary_views(self, session) -> Dict[str, Any]:
        """Refresh materialized views backing project/branch summaries when using PostgreSQL."""
        refresh_metadata: Dict[str, Any] = {
            "refreshed": False,
            "refresh_time_ms": None,
            "error": None,
        }

        try:
            bind = session.get_bind()
            if not bind or bind.dialect.name != "postgresql":
                return refresh_metadata

            start = time.perf_counter()
            connection = session.connection()

            # Use autocommit to satisfy PostgreSQL requirements for REFRESH statements.
            autocommit_conn = connection.execution_options(isolation_level="AUTOCOMMIT")

            try:
                autocommit_conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY branch_summaries_mv;"))
                autocommit_conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY project_summaries_mv;"))
            except Exception as refresh_error:
                logger.warning(
                    "Concurrent refresh failed, falling back to non-concurrent refresh: %s",
                    refresh_error,
                )
                autocommit_conn.execute(text("REFRESH MATERIALIZED VIEW branch_summaries_mv;"))
                autocommit_conn.execute(text("REFRESH MATERIALIZED VIEW project_summaries_mv;"))

            refresh_metadata["refreshed"] = True
            refresh_metadata["refresh_time_ms"] = round((time.perf_counter() - start) * 1000, 2)

        except Exception as exc:  # pragma: no cover - defensive logging path
            logger.error("Failed to refresh summary materialized views: %s", exc)
            refresh_metadata["error"] = str(exc)
        finally:
            # Ensure we are not left in a broken transaction state before running read queries.
            try:
                session.rollback()
            except Exception:
                pass

        return refresh_metadata
    
    def get_branches_with_task_counts(self, project_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Get all branches for a project with their task counts.
        
        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Branches with task count data
        """
        try:
            # Get git branch facade through service
            facade = self.facade_service.get_branch_facade(
                project_id=project_id,
                user_id=user_id
            )
            
            # Get branches with task counts
            result = facade.get_branches_with_task_counts(project_id)
            logger.info(f"Branch API Controller: Raw result from facade: {result}")
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", "Failed to fetch branches"),
                    "branches": [],
                    "project_summary": {}
                }
            
            # Get project summary stats
            summary_result = facade.get_project_branch_summary(project_id)
            
            logger.info(f"Retrieved {len(result.get('branches', []))} branches for project {project_id}")
            
            response_data = {
                "success": True,
                "branches": result.get("branches", []),
                "project_summary": summary_result.get("summary", {}),
                "total_branches": len(result.get("branches", []))
            }
            logger.info(f"Branch API Controller: Returning to frontend: {response_data}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error getting branches with task counts for project {project_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "branches": [],
                "project_summary": {}
            }
    
    async def get_branch(self, branch_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Get a single branch with its task counts (async wrapper).
        
        Args:
            branch_id: Branch identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Single branch data with task counts
        """
        # Simply delegate to the sync method
        return self.get_single_branch_summary(branch_id, user_id, session)
    
    def get_single_branch_summary(self, branch_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Get a single branch with its task counts.
        
        Args:
            branch_id: Branch identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Single branch summary data
        """
        try:
            # First, get the project_id from the branch to comply with DDD requirements
            from ...application.services.repository_provider_service import RepositoryProviderService
            
            repo_provider = RepositoryProviderService.get_instance()
            git_branch_repo = repo_provider.get_git_branch_repository(user_id=user_id)
            
            # Find the branch by ID to get its project_id
            import asyncio
            git_branch = asyncio.run(git_branch_repo.find_by_id(branch_id))
            
            if not git_branch:
                logger.warning(f"Branch {branch_id} not found")
                return {
                    "success": False,
                    "error": f"Branch {branch_id} not found",
                    "branch": None
                }
            
            # Create git branch facade with proper project_id for DDD compliance
            facade = self.facade_service.get_branch_facade(
                project_id=git_branch.project_id,
                user_id=user_id
            )
            
            # Get single branch data
            result = facade.get_branch_summary(branch_id)
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", f"Branch {branch_id} not found"),
                    "branch": None
                }
            
            branch_data = result.get("branch")
            if not branch_data:
                return {
                    "success": False,
                    "error": f"Branch {branch_id} not found",
                    "branch": None
                }
            
            logger.info(f"Retrieved branch summary for branch {branch_id}")
            
            return {
                "success": True,
                "branch": branch_data
            }
            
        except Exception as e:
            logger.error(f"Error getting branch summary for branch {branch_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "branch": None
            }
    
    def get_project_branch_stats(self, project_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Get aggregated statistics for all branches in a project.
        
        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Project branch statistics
        """
        try:
            # Get git branch facade through service
            facade = self.facade_service.get_branch_facade(
                project_id=project_id,
                user_id=user_id
            )
            
            # Get branch statistics
            result = facade.get_project_branch_summary(project_id)
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", "Failed to fetch branch statistics"),
                    "stats": {}
                }
            
            logger.info(f"Retrieved branch statistics for project {project_id}")
            
            return {
                "success": True,
                "stats": result.get("summary", {})
            }
            
        except Exception as e:
            logger.error(f"Error getting project branch stats for project {project_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "stats": {}
            }
    
    def get_branch_performance_metrics(self, user_id: str, session) -> Dict[str, Any]:
        """
        Get performance metrics for branch loading endpoints.
        
        Args:
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Performance metrics data
        """
        try:
            # This could be enhanced to get real metrics from a monitoring facade
            # For now, return standard performance metrics
            
            return {
                "success": True,
                "optimization_status": "enabled",
                "query_strategy": "facade_with_optimized_repositories",
                "expected_performance": {
                    "before": {
                        "queries_per_request": "100+ (N+1 problem)",
                        "average_response_time": "2000-3000ms",
                        "database_round_trips": "20+"
                    },
                    "after": {
                        "queries_per_request": "1-3",
                        "average_response_time": "50-150ms",
                        "database_round_trips": "1-3"
                    },
                    "improvement": "~95% reduction in response time"
                },
                "cache_status": {
                    "enabled": "via_redis_decorator",
                    "ttl": "300 seconds (5 minutes)",
                    "invalidation": "automatic_on_changes"
                },
                "recommendations": [
                    "Use /api/branches/summaries endpoint for sidebar loading",
                    "Cache invalidates automatically on branch/task changes",
                    "Monitor this endpoint for performance tracking",
                    "DDD architecture ensures proper separation of concerns"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting branch performance metrics: {e}")
            return {
                "success": False,
                "error": str(e),
                "metrics": {}
            }
    
    async def create_branch(self, project_id: str, name: str, description: str, user_id: str, session) -> Dict[str, Any]:
        """
        Create a new branch following DDD architecture.
        
        Args:
            project_id: Project identifier
            name: Branch name
            description: Branch description
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Created branch data
        """
        try:
            facade = self.facade_service.get_branch_facade(
                project_id=project_id,
                user_id=user_id
            )
            
            result = facade.create_git_branch(project_id, name, description)
            
            if result.get("success"):
                logger.info(f"Branch created successfully: {name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating branch: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_branches(self, project_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        List all branches for a project following DDD architecture.
        
        Args:
            project_id: Project identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            List of branches
        """
        try:
            facade = self.facade_service.get_branch_facade(
                project_id=project_id,
                user_id=user_id
            )
            
            result = facade.list_git_branchs(project_id)
            
            if result.get("success"):
                logger.info(f"Retrieved {len(result.get('git_branchs', []))} branches")
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing branches: {e}")
            return {
                "success": False,
                "error": str(e),
                "git_branchs": []
            }
    
    async def update_branch(self, branch_id: str, name: Optional[str], description: Optional[str], user_id: str, session) -> Dict[str, Any]:
        """
        Update a branch following DDD architecture.
        
        Args:
            branch_id: Branch identifier
            name: New branch name (optional)
            description: New branch description (optional)
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Updated branch data
        """
        try:
            # First, get the project_id from the branch to comply with DDD requirements
            from ...application.services.repository_provider_service import RepositoryProviderService
            
            repo_provider = RepositoryProviderService.get_instance()
            git_branch_repo = repo_provider.get_git_branch_repository(user_id=user_id)
            
            # Find the branch by ID to get its project_id
            git_branch = await git_branch_repo.find_by_id(branch_id)
            
            if not git_branch:
                logger.warning(f"Branch {branch_id} not found for update")
                return {
                    "success": False,
                    "error": f"Branch {branch_id} not found"
                }
            
            # Create facade with proper project_id for DDD compliance
            facade = self.facade_service.get_branch_facade(
                project_id=git_branch.project_id,
                user_id=user_id
            )
            
            result = facade.update_git_branch(branch_id, name, description)
            
            if result.get("success"):
                logger.info(f"Branch {branch_id} updated successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Error updating branch: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_branch(self, branch_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Delete a branch following DDD architecture.
        
        Args:
            branch_id: Branch identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Deletion result
        """
        try:
            # First, get the project_id from the branch to comply with DDD requirements
            from ...application.services.repository_provider_service import RepositoryProviderService
            
            repo_provider = RepositoryProviderService.get_instance()
            git_branch_repo = repo_provider.get_git_branch_repository(user_id=user_id)
            
            # Find the branch by ID to get its project_id
            git_branch = await git_branch_repo.find_by_id(branch_id)
            
            if not git_branch:
                logger.warning(f"Branch {branch_id} not found for deletion")
                return {
                    "success": False,
                    "error": f"Branch {branch_id} not found"
                }
            
            project_id = git_branch.project_id
            logger.info(f"Found branch {branch_id} in project {project_id}, proceeding with deletion")
            
            # Now create the facade with the proper project_id for DDD compliance
            facade = self.facade_service.get_branch_facade(
                project_id=project_id,
                user_id=user_id
            )
            
            result = facade.delete_git_branch(branch_id)
            
            if result.get("success"):
                logger.info(f"Branch {branch_id} deleted successfully from project {project_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error deleting branch {branch_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def assign_agent(self, branch_id: str, agent_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Assign an agent to a branch following DDD architecture.
        
        Args:
            branch_id: Branch identifier
            agent_id: Agent identifier
            user_id: Authenticated user ID
            session: Database session
            
        Returns:
            Assignment result
        """
        try:
            # First, get the project_id from the branch to comply with DDD requirements
            from ...application.services.repository_provider_service import RepositoryProviderService
            
            repo_provider = RepositoryProviderService.get_instance()
            git_branch_repo = repo_provider.get_git_branch_repository(user_id=user_id)
            
            # Find the branch by ID to get its project_id
            git_branch = await git_branch_repo.find_by_id(branch_id)
            
            if not git_branch:
                logger.warning(f"Branch {branch_id} not found for agent assignment")
                return {
                    "success": False,
                    "error": f"Branch {branch_id} not found"
                }
            
            # Create facade with proper project_id for DDD compliance
            facade = self.facade_service.get_branch_facade(
                project_id=git_branch.project_id,
                user_id=user_id
            )
            
            result = facade.assign_agent(branch_id, agent_id)
            
            if result.get("success"):
                logger.info(f"Agent {agent_id} assigned to branch {branch_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error assigning agent: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_branch_task_counts(self, branch_id: str, user_id: str, session) -> Dict[str, Any]:
        """
        Get task counts for a branch following DDD architecture.

        Args:
            branch_id: Branch identifier
            user_id: Authenticated user ID
            session: Database session

        Returns:
            Task counts with nested task_counts object for frontend compatibility
        """
        try:
            # First, get the project_id from the branch to comply with DDD requirements
            from ...application.services.repository_provider_service import RepositoryProviderService

            repo_provider = RepositoryProviderService.get_instance()
            git_branch_repo = repo_provider.get_git_branch_repository(user_id=user_id)

            # Find the branch by ID to get its project_id
            git_branch = await git_branch_repo.find_by_id(branch_id)

            if not git_branch:
                logger.warning(f"Branch {branch_id} not found for task counts")
                return {
                    "success": False,
                    "error": f"Branch {branch_id} not found"
                }

            # Create facade with proper project_id for DDD compliance
            facade = self.facade_service.get_branch_facade(
                project_id=git_branch.project_id,
                user_id=user_id
            )

            # Get branch summary which includes task counts
            result = facade.get_branch_summary(branch_id)

            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", "Failed to get branch summary")
                }

            branch = result.get("branch", {})

            # Create task_counts object in the format frontend expects
            task_counts = {
                "total": branch.get("total_tasks", 0),
                "todo": branch.get("todo_tasks", 0),
                "in_progress": branch.get("in_progress_tasks", 0),
                "done": branch.get("completed_tasks", 0),
                "blocked": branch.get("blocked_tasks", 0),
                "progress_percentage": branch.get("progress_percentage", 0.0)
            }

            logger.info(f"Retrieved task counts for branch {branch_id}")

            return {
                "success": True,
                "task_counts": task_counts,
                "branch_id": branch_id
            }

        except Exception as e:
            logger.error(f"Error getting branch task counts: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_counts": {}
            }

    def get_bulk_summaries(self, project_ids: Optional[list] = None, user_id: str = None,
                          include_archived: bool = False, session=None) -> Dict[str, Any]:
        """
        Get bulk summaries for multiple projects in a single request.
        Queries the materialized views for optimized performance.

        Args:
            project_ids: Optional list of project IDs to fetch
            user_id: User ID for filtering projects
            include_archived: Whether to include archived branches
            session: Database session

        Returns:
            Bulk summary response with all branches and projects
        """
        start_time = time.time()

        refresh_metadata = self._refresh_summary_views(session)

        try:
            # Query branch_summaries_mv
            query = """
            SELECT
                branch_id,
                project_id,
                branch_name,
                branch_status,
                branch_priority,
                total_tasks,
                completed_tasks,
                in_progress_tasks,
                blocked_tasks,
                todo_tasks,
                progress_percentage,
                last_task_activity
            FROM branch_summaries_mv
            WHERE 1=1
            """

            params = {}

            if project_ids:
                # Use IN clause for multiple project IDs
                placeholders = ', '.join([f':p{i}' for i in range(len(project_ids))])
                query += f" AND project_id IN ({placeholders})"
                for i, pid in enumerate(project_ids):
                    params[f'p{i}'] = pid
            elif user_id:
                # Get user's projects first
                user_projects_query = text("""
                    SELECT DISTINCT project_id
                    FROM project_git_branchs b
                    WHERE b.user_id = :user_id
                """)
                result = session.execute(user_projects_query, {'user_id': user_id})
                user_project_ids = [row[0] for row in result]

                if user_project_ids:
                    placeholders = ', '.join([f':p{i}' for i in range(len(user_project_ids))])
                    query += f" AND project_id IN ({placeholders})"
                    for i, pid in enumerate(user_project_ids):
                        params[f'p{i}'] = pid
                else:
                    # No projects found for user
                    return {
                        'success': True,
                        'summaries': {},
                        'projects': {},
                        'metadata': {
                            'count': 0,
                            'query_time_ms': 0,
                            'from_cache': False,
                            'message': 'No projects found for user'
                        },
                        'timestamp': time.time()
                    }

            if not include_archived:
                query += " AND branch_status != 'archived'"

            # Execute query
            result = session.execute(text(query), params)
            rows = result.fetchall()

            # Build response
            summaries = {}
            project_ids_found = set()

            for row in rows:
                branch_summary = {
                    'id': row[0],
                    'project_id': row[1],
                    'name': row[2],
                    'status': row[3],
                    'priority': row[4],
                    'total_tasks': row[5] or 0,
                    'completed_tasks': row[6] or 0,
                    'in_progress_tasks': row[7] or 0,
                    'blocked_tasks': row[8] or 0,
                    'todo_tasks': row[9] or 0,
                    'progress_percentage': float(row[10] or 0),
                    'last_activity': row[11].isoformat() if row[11] else None
                }
                summaries[row[0]] = branch_summary
                project_ids_found.add(row[1])

            # Get project summaries from project_summaries_mv
            projects = {}
            if project_ids_found:
                project_placeholders = ', '.join([f':proj{i}' for i in range(len(project_ids_found))])
                project_query = text(f"""
                    SELECT
                        project_id,
                        project_name,
                        project_description,
                        total_branches,
                        active_branches,
                        total_tasks,
                        completed_tasks,
                        overall_progress_percentage
                    FROM project_summaries_mv
                    WHERE project_id IN ({project_placeholders})
                """)

                project_params = {}
                for i, pid in enumerate(project_ids_found):
                    project_params[f'proj{i}'] = pid

                project_result = session.execute(project_query, project_params)

                for row in project_result:
                    projects[row[0]] = {
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'total_branches': row[3] or 0,
                        'active_branches': row[4] or 0,
                        'total_tasks': row[5] or 0,
                        'completed_tasks': row[6] or 0,
                        'progress_percentage': float(row[7] or 0)
                    }

            query_time = (time.time() - start_time) * 1000  # ms

            logger.info(f"Bulk summaries retrieved: {len(summaries)} branches, {len(projects)} projects in {query_time:.2f}ms")

            response = {
                'success': True,
                'summaries': summaries,
                'projects': projects,
                'metadata': {
                    'count': len(summaries),
                    'query_time_ms': round(query_time, 2),
                    'from_cache': False
                },
                'timestamp': time.time()
            }

            # Surface refresh diagnostics when available so the frontend can detect freshness.
            metadata = response['metadata']
            if refresh_metadata.get('refreshed'):
                metadata['refreshed'] = True
                if refresh_metadata.get('refresh_time_ms') is not None:
                    metadata['refresh_time_ms'] = refresh_metadata['refresh_time_ms']
            if refresh_metadata.get('error'):
                metadata['refresh_error'] = refresh_metadata['error']

            return response

        except Exception as e:
            logger.error(f"Error getting bulk summaries: {e}")
            return {
                'success': False,
                'error': str(e),
                'summaries': {},
                'projects': {},
                'metadata': {'error': str(e)}
            }
