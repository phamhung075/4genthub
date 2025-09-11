#!/usr/bin/env python
"""Analytics API Routes - Business intelligence and usage pattern analysis"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, func, distinct

from ...auth.interface.fastapi_auth import get_authenticated_user
from ...task_management.infrastructure.database.database_config import get_database_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics & Intelligence"])


@router.get("/context-usage")
async def get_context_usage_analytics(
    user: Dict[str, Any] = Depends(get_authenticated_user),
    days: int = Query(30, ge=1, le=365, description="Days of data to analyze"),
    include_patterns: bool = Query(True, description="Include usage patterns")
) -> Dict[str, Any]:
    """
    Analyze context usage patterns across the system.
    
    Provides insights into:
    - Most accessed contexts
    - Context creation patterns
    - Inheritance utilization
    - Usage trends over time
    """
    
    user_id = user["sub"]
    
    try:
        with get_database_session() as session:
            # Context access patterns
            context_query = text("""
                SELECT 
                    'task' as context_type,
                    COUNT(*) as access_count,
                    COUNT(DISTINCT context_id) as unique_contexts,
                    AVG(CASE 
                        WHEN updated_at > created_at 
                        THEN EXTRACT(EPOCH FROM updated_at - created_at) 
                        ELSE 0 
                    END) as avg_session_duration,
                    DATE(created_at) as access_date
                FROM tasks 
                WHERE user_id = :user_id 
                    AND created_at >= :since_date
                GROUP BY DATE(created_at)
                
                UNION ALL
                
                SELECT 
                    'global' as context_type,
                    COUNT(*) as access_count,
                    1 as unique_contexts,
                    0 as avg_session_duration,
                    DATE(updated_at) as access_date
                FROM global_contexts
                WHERE user_id = :user_id 
                    AND updated_at >= :since_date
                GROUP BY DATE(updated_at)
                
                ORDER BY access_date DESC
            """)
            
            since_date = datetime.now() - timedelta(days=days)
            result = session.execute(context_query, {
                "user_id": user_id,
                "since_date": since_date
            })
            
            # Process results
            daily_usage = defaultdict(lambda: {
                "task_contexts": 0,
                "global_contexts": 0,
                "total_accesses": 0
            })
            
            total_task_contexts = 0
            total_global_contexts = 0
            
            for row in result:
                date_str = row.access_date.isoformat()
                context_type = row.context_type
                
                daily_usage[date_str][f"{context_type}_contexts"] = row.access_count
                daily_usage[date_str]["total_accesses"] += row.access_count
                
                if context_type == "task":
                    total_task_contexts += row.unique_contexts
                elif context_type == "global":
                    total_global_contexts += row.unique_contexts
            
            # Context hierarchy utilization
            hierarchy_query = text("""
                SELECT 
                    COUNT(DISTINCT t.project_id) as projects_used,
                    COUNT(DISTINCT t.git_branch_id) as branches_used,
                    COUNT(DISTINCT t.id) as tasks_created,
                    AVG(CASE WHEN t.context_id IS NOT NULL THEN 1.0 ELSE 0.0 END) as context_utilization_rate
                FROM tasks t
                WHERE t.user_id = :user_id 
                    AND t.created_at >= :since_date
            """)
            
            hierarchy_result = session.execute(hierarchy_query, {
                "user_id": user_id,
                "since_date": since_date
            }).fetchone()
            
            analytics_data = {
                "analysis_period": {
                    "days": days,
                    "start_date": since_date.isoformat(),
                    "end_date": datetime.now().isoformat()
                },
                "context_summary": {
                    "total_task_contexts": total_task_contexts,
                    "total_global_contexts": total_global_contexts,
                    "projects_utilized": hierarchy_result.projects_used or 0,
                    "branches_utilized": hierarchy_result.branches_used or 0,
                    "context_utilization_rate": float(hierarchy_result.context_utilization_rate or 0)
                },
                "daily_usage": dict(daily_usage),
                "hierarchy_health": {
                    "project_branch_ratio": (
                        (hierarchy_result.branches_used or 0) / max(hierarchy_result.projects_used or 1, 1)
                    ),
                    "task_branch_ratio": (
                        (hierarchy_result.tasks_created or 0) / max(hierarchy_result.branches_used or 1, 1)
                    )
                }
            }
            
            # Add usage patterns if requested
            if include_patterns:
                # Most active contexts
                active_contexts_query = text("""
                    SELECT 
                        t.title,
                        t.status,
                        t.priority,
                        COUNT(DISTINCT DATE(t.updated_at)) as active_days,
                        MAX(t.updated_at) as last_activity
                    FROM tasks t
                    WHERE t.user_id = :user_id 
                        AND t.updated_at >= :since_date
                    GROUP BY t.id, t.title, t.status, t.priority
                    ORDER BY active_days DESC, last_activity DESC
                    LIMIT 10
                """)
                
                active_contexts = session.execute(active_contexts_query, {
                    "user_id": user_id,
                    "since_date": since_date
                }).fetchall()
                
                analytics_data["usage_patterns"] = {
                    "most_active_contexts": [
                        {
                            "title": ctx.title,
                            "status": ctx.status,
                            "priority": ctx.priority,
                            "active_days": ctx.active_days,
                            "last_activity": ctx.last_activity.isoformat()
                        }
                        for ctx in active_contexts
                    ],
                    "context_lifecycle_insights": _analyze_context_lifecycle(session, user_id, since_date)
                }
            
            return analytics_data
            
    except Exception as e:
        logger.error(f"Error analyzing context usage: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze context usage patterns")


@router.get("/agent-performance")
async def get_agent_performance_analytics(
    user: Dict[str, Any] = Depends(get_authenticated_user),
    days: int = Query(30, ge=1, le=365, description="Days of data to analyze")
) -> Dict[str, Any]:
    """
    Analyze agent performance and coordination patterns.
    
    Provides insights into:
    - Agent task completion rates
    - Most effective agent combinations
    - Task completion times by agent
    - Agent specialization patterns
    """
    
    user_id = user["sub"]
    
    try:
        with get_database_session() as session:
            # Agent task completion analysis
            agent_performance_query = text("""
                SELECT 
                    ta.assignee_id as agent_name,
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN t.status = 'done' THEN 1 END) as completed_tasks,
                    COUNT(CASE WHEN t.status = 'in_progress' THEN 1 END) as active_tasks,
                    COUNT(CASE WHEN t.status = 'blocked' THEN 1 END) as blocked_tasks,
                    AVG(CASE 
                        WHEN t.status = 'done' AND t.updated_at > t.created_at
                        THEN EXTRACT(EPOCH FROM t.updated_at - t.created_at) / 3600 
                    END) as avg_completion_hours,
                    COUNT(DISTINCT t.priority) as priority_variety,
                    MAX(t.updated_at) as last_activity
                FROM tasks t
                JOIN task_assignees ta ON t.id = ta.task_id
                WHERE t.user_id = :user_id 
                    AND t.created_at >= :since_date
                GROUP BY ta.assignee_id
                ORDER BY completed_tasks DESC, total_tasks DESC
            """)
            
            since_date = datetime.now() - timedelta(days=days)
            agent_results = session.execute(agent_performance_query, {
                "user_id": user_id,
                "since_date": since_date
            }).fetchall()
            
            # Agent collaboration patterns
            collaboration_query = text("""
                SELECT 
                    t.id as task_id,
                    t.title,
                    t.status,
                    ARRAY_AGG(ta.assignee_id ORDER BY ta.assignee_id) as agent_team,
                    COUNT(ta.assignee_id) as team_size,
                    EXTRACT(EPOCH FROM MAX(t.updated_at) - MIN(t.created_at)) / 3600 as duration_hours
                FROM tasks t
                JOIN task_assignees ta ON t.id = ta.task_id
                WHERE t.user_id = :user_id 
                    AND t.created_at >= :since_date
                    AND t.status IN ('done', 'in_progress')
                GROUP BY t.id, t.title, t.status
                HAVING COUNT(ta.assignee_id) > 1
                ORDER BY team_size DESC, duration_hours ASC
                LIMIT 20
            """)
            
            collaboration_results = session.execute(collaboration_query, {
                "user_id": user_id,
                "since_date": since_date
            }).fetchall()
            
            # Process agent performance data
            agent_metrics = []
            for agent in agent_results:
                completion_rate = (agent.completed_tasks / max(agent.total_tasks, 1)) * 100
                
                agent_metrics.append({
                    "agent_name": agent.agent_name,
                    "total_tasks": agent.total_tasks,
                    "completed_tasks": agent.completed_tasks,
                    "active_tasks": agent.active_tasks,
                    "blocked_tasks": agent.blocked_tasks,
                    "completion_rate": completion_rate,
                    "avg_completion_hours": float(agent.avg_completion_hours or 0),
                    "priority_variety": agent.priority_variety,
                    "last_activity": agent.last_activity.isoformat() if agent.last_activity else None,
                    "efficiency_score": _calculate_agent_efficiency(
                        completion_rate,
                        agent.avg_completion_hours or 0,
                        agent.blocked_tasks / max(agent.total_tasks, 1)
                    )
                })
            
            # Process collaboration patterns
            collaboration_patterns = []
            team_effectiveness = defaultdict(list)
            
            for collab in collaboration_results:
                # Convert PostgreSQL array to Python list (if using PostgreSQL)
                # For SQLite, you might need to handle this differently
                agent_team = collab.agent_team if isinstance(collab.agent_team, list) else []
                
                collaboration_patterns.append({
                    "task_title": collab.title,
                    "status": collab.status,
                    "team_size": collab.team_size,
                    "agent_team": agent_team,
                    "duration_hours": float(collab.duration_hours or 0)
                })
                
                # Track team effectiveness
                team_key = ",".join(sorted(agent_team))
                team_effectiveness[team_key].append({
                    "status": collab.status,
                    "duration": float(collab.duration_hours or 0)
                })
            
            # Calculate team effectiveness metrics
            effective_teams = []
            for team, tasks in team_effectiveness.items():
                completed_tasks = [t for t in tasks if t["status"] == "done"]
                avg_duration = sum(t["duration"] for t in completed_tasks) / max(len(completed_tasks), 1)
                completion_rate = (len(completed_tasks) / len(tasks)) * 100
                
                effective_teams.append({
                    "team_composition": team.split(","),
                    "total_tasks": len(tasks),
                    "completed_tasks": len(completed_tasks),
                    "completion_rate": completion_rate,
                    "avg_duration_hours": avg_duration,
                    "effectiveness_score": (completion_rate / max(avg_duration, 1)) * 10  # Normalized score
                })
            
            # Sort by effectiveness
            effective_teams.sort(key=lambda x: x["effectiveness_score"], reverse=True)
            
            return {
                "analysis_period": {
                    "days": days,
                    "start_date": since_date.isoformat(),
                    "end_date": datetime.now().isoformat()
                },
                "agent_performance": {
                    "individual_metrics": agent_metrics,
                    "top_performers": sorted(agent_metrics, key=lambda x: x["efficiency_score"], reverse=True)[:5],
                    "collaboration_patterns": collaboration_patterns[:10],
                    "effective_teams": effective_teams[:5]
                },
                "performance_insights": {
                    "total_agents_active": len(agent_metrics),
                    "avg_completion_rate": sum(a["completion_rate"] for a in agent_metrics) / max(len(agent_metrics), 1),
                    "most_collaborative_agent": max(
                        agent_metrics, 
                        key=lambda x: x["total_tasks"]
                    )["agent_name"] if agent_metrics else None,
                    "specialization_recommendations": _generate_specialization_recommendations(agent_metrics)
                }
            }
            
    except Exception as e:
        logger.error(f"Error analyzing agent performance: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze agent performance")


@router.get("/system-insights")
async def get_system_insights(
    user: Dict[str, Any] = Depends(get_authenticated_user),
    days: int = Query(7, ge=1, le=30, description="Days for trend analysis")
) -> Dict[str, Any]:
    """
    Generate high-level system insights and recommendations.
    
    Combines multiple data sources to provide:
    - System health trends
    - Productivity insights
    - Optimization recommendations
    - Usage efficiency metrics
    """
    
    user_id = user["sub"]
    
    try:
        with get_database_session() as session:
            # System activity trends
            activity_query = text("""
                SELECT 
                    DATE(created_at) as activity_date,
                    COUNT(*) as tasks_created,
                    COUNT(CASE WHEN status = 'done' THEN 1 END) as tasks_completed,
                    COUNT(DISTINCT git_branch_id) as branches_active,
                    COUNT(DISTINCT project_id) as projects_active,
                    AVG(CASE WHEN status = 'done' AND updated_at > created_at 
                        THEN EXTRACT(EPOCH FROM updated_at - created_at) / 3600 
                    END) as avg_task_completion_hours
                FROM tasks 
                WHERE user_id = :user_id 
                    AND created_at >= :since_date
                GROUP BY DATE(created_at)
                ORDER BY activity_date DESC
            """)
            
            since_date = datetime.now() - timedelta(days=days)
            activity_results = session.execute(activity_query, {
                "user_id": user_id,
                "since_date": since_date
            }).fetchall()
            
            # Calculate trends and insights
            daily_metrics = []
            total_tasks_created = 0
            total_tasks_completed = 0
            productivity_scores = []
            
            for day in activity_results:
                productivity_score = (
                    (day.tasks_completed / max(day.tasks_created, 1)) * 0.4 +
                    (day.branches_active * 0.3) +
                    (day.projects_active * 0.3)
                ) * 10
                
                daily_metrics.append({
                    "date": day.activity_date.isoformat(),
                    "tasks_created": day.tasks_created,
                    "tasks_completed": day.tasks_completed,
                    "branches_active": day.branches_active,
                    "projects_active": day.projects_active,
                    "avg_completion_hours": float(day.avg_task_completion_hours or 0),
                    "productivity_score": productivity_score
                })
                
                total_tasks_created += day.tasks_created
                total_tasks_completed += day.tasks_completed
                productivity_scores.append(productivity_score)
            
            # Generate insights and recommendations
            avg_productivity = sum(productivity_scores) / max(len(productivity_scores), 1)
            completion_rate = (total_tasks_completed / max(total_tasks_created, 1)) * 100
            
            recommendations = []
            
            # Productivity recommendations
            if avg_productivity < 5:
                recommendations.append({
                    "type": "productivity",
                    "priority": "high",
                    "message": "Consider breaking down large tasks into smaller, manageable subtasks",
                    "metric": "low_productivity_score"
                })
            
            if completion_rate < 60:
                recommendations.append({
                    "type": "completion",
                    "priority": "medium", 
                    "message": "Focus on completing existing tasks before creating new ones",
                    "metric": "low_completion_rate"
                })
            
            # Branch and project organization
            avg_branches_per_day = sum(d["branches_active"] for d in daily_metrics) / max(len(daily_metrics), 1)
            if avg_branches_per_day > 10:
                recommendations.append({
                    "type": "organization",
                    "priority": "medium",
                    "message": "Consider consolidating work into fewer branches to improve focus",
                    "metric": "high_branch_fragmentation"
                })
            
            return {
                "analysis_period": {
                    "days": days,
                    "start_date": since_date.isoformat(),
                    "end_date": datetime.now().isoformat()
                },
                "system_health": {
                    "overall_productivity_score": avg_productivity,
                    "task_completion_rate": completion_rate,
                    "avg_branches_per_day": avg_branches_per_day,
                    "system_utilization": "optimal" if avg_productivity > 7 else "moderate" if avg_productivity > 4 else "needs_improvement"
                },
                "trends": {
                    "daily_metrics": daily_metrics,
                    "productivity_trend": _calculate_trend(productivity_scores),
                    "completion_trend": _calculate_completion_trend(daily_metrics)
                },
                "insights": {
                    "recommendations": recommendations,
                    "key_metrics": {
                        "total_tasks_created": total_tasks_created,
                        "total_tasks_completed": total_tasks_completed,
                        "most_productive_day": max(daily_metrics, key=lambda x: x["productivity_score"])["date"] if daily_metrics else None,
                        "efficiency_rating": "high" if completion_rate > 80 else "medium" if completion_rate > 60 else "needs_improvement"
                    }
                }
            }
            
    except Exception as e:
        logger.error(f"Error generating system insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate system insights")


def _analyze_context_lifecycle(session: Session, user_id: str, since_date: datetime) -> Dict[str, Any]:
    """Analyze context creation, usage, and completion patterns."""
    
    lifecycle_query = text("""
        SELECT 
            AVG(EXTRACT(EPOCH FROM updated_at - created_at) / 3600) as avg_task_lifetime_hours,
            COUNT(CASE WHEN status = 'done' THEN 1 END) as completed_contexts,
            COUNT(CASE WHEN status = 'todo' THEN 1 END) as pending_contexts,
            COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as active_contexts,
            COUNT(CASE WHEN status = 'blocked' THEN 1 END) as blocked_contexts
        FROM tasks
        WHERE user_id = :user_id AND created_at >= :since_date
    """)
    
    result = session.execute(lifecycle_query, {
        "user_id": user_id,
        "since_date": since_date
    }).fetchone()
    
    return {
        "avg_lifetime_hours": float(result.avg_task_lifetime_hours or 0),
        "context_distribution": {
            "completed": result.completed_contexts,
            "pending": result.pending_contexts,
            "active": result.active_contexts,
            "blocked": result.blocked_contexts
        },
        "health_score": (
            (result.completed_contexts / max(
                result.completed_contexts + result.pending_contexts + result.active_contexts + result.blocked_contexts, 1
            )) * 100
        )
    }


def _calculate_agent_efficiency(completion_rate: float, avg_hours: float, blocked_ratio: float) -> float:
    """Calculate a normalized efficiency score for an agent."""
    
    # Completion rate component (0-40 points)
    completion_score = (completion_rate / 100) * 40
    
    # Speed component (0-30 points) - inverse of average hours, capped at reasonable limits
    speed_score = max(0, 30 - (avg_hours / 24) * 10)  # Penalty for tasks taking more than 24 hours
    
    # Reliability component (0-30 points) - penalty for blocked tasks
    reliability_score = max(0, 30 - (blocked_ratio * 100))
    
    return completion_score + speed_score + reliability_score


def _generate_specialization_recommendations(agent_metrics: List[Dict]) -> List[str]:
    """Generate agent specialization recommendations based on performance patterns."""
    
    recommendations = []
    
    if not agent_metrics:
        return ["No agent data available for recommendations"]
    
    # Find top performers
    top_performer = max(agent_metrics, key=lambda x: x["efficiency_score"])
    if top_performer["efficiency_score"] > 70:
        recommendations.append(f"Consider having {top_performer['agent_name']} mentor other agents")
    
    # Find agents that might need support
    struggling_agents = [a for a in agent_metrics if a["completion_rate"] < 50]
    if struggling_agents:
        recommendations.append("Some agents have low completion rates - consider task reassignment or additional support")
    
    # Identify specialization opportunities
    high_volume_agents = [a for a in agent_metrics if a["total_tasks"] > 10]
    if len(high_volume_agents) < len(agent_metrics) * 0.5:
        recommendations.append("Consider specializing agents for specific task types to improve efficiency")
    
    return recommendations


def _calculate_trend(values: List[float]) -> str:
    """Calculate trend direction from a list of values."""
    
    if len(values) < 2:
        return "insufficient_data"
    
    # Simple linear trend calculation
    recent_avg = sum(values[:len(values)//2]) / max(len(values)//2, 1)
    older_avg = sum(values[len(values)//2:]) / max(len(values) - len(values)//2, 1)
    
    if recent_avg > older_avg * 1.1:
        return "improving"
    elif recent_avg < older_avg * 0.9:
        return "declining"
    else:
        return "stable"


def _calculate_completion_trend(daily_metrics: List[Dict]) -> str:
    """Calculate completion rate trend from daily metrics."""
    
    completion_rates = [
        (d["tasks_completed"] / max(d["tasks_created"], 1)) * 100
        for d in daily_metrics
    ]
    
    return _calculate_trend(completion_rates)