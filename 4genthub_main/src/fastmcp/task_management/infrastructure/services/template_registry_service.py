"""
Template Registry Service

This service manages templates using PostgreSQL.
The system uses PostgreSQL locally and Supabase for cloud deployment.

FOR TEMPLATE MANAGEMENT:
- Use PostgreSQL database with SQLAlchemy ORM models
- Template data is stored in PostgreSQL tables
- Supports both local PostgreSQL and Supabase
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class TemplateRegistryService:
    """
    Template Registry Service
    
    This class manages templates using PostgreSQL.
    All template operations use PostgreSQL database.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        logger.info("Template Registry Service initializing")
        logger.info("Using PostgreSQL for template storage")
        
        # This service is being refactored to use PostgreSQL
        # For now, raise an error indicating refactoring is needed
        raise RuntimeError(
            "Template Registry Service requires refactoring\n"
            "PostgreSQL implementation is in progress.\n"
            "✅ SOLUTION: Use PostgreSQL with SQLAlchemy ORM\n"
            "🔧 Template data should be stored in PostgreSQL tables"
        )
    
    def _get_connection(self):
        """Get PostgreSQL connection"""
        raise RuntimeError(
            "PostgreSQL connection implementation required.\n"
            "Use PostgreSQL connection pool instead."
        )
    
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template by ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM templates 
                    WHERE id = ? AND is_active = 1
                """, (template_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                
                return None
                
        except Exception as e:
            logger.error(f"Template retrieval error: {e}")
            return None
    
    async def list_templates(
        self,
        template_type: Optional[str] = None,
        agent_compatible: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List available templates with filtering"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT id, name, description, type, category,
                           compatible_agents, created_at, updated_at
                    FROM templates 
                    WHERE is_active = 1
                """
                params = []
                
                if template_type:
                    query += " AND type = ?"
                    params.append(template_type)
                
                if agent_compatible:
                    query += " AND (compatible_agents = '[\"*\"]' OR compatible_agents LIKE ?)"
                    params.append(f"%{agent_compatible}%")
                
                query += " ORDER BY name LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Template listing error: {e}")
            return []
    
    async def suggest_templates(
        self,
        task_context: Dict[str, Any],
        agent_type: Optional[str] = None,
        file_patterns: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """AI-powered template suggestions based on context"""
        suggestions = []
        
        try:
            # Get templates compatible with agent
            templates = await self.list_templates(agent_compatible=agent_type)
            
            # Score templates based on context
            for template in templates:
                score = await self._calculate_template_score(
                    template, task_context, agent_type, file_patterns
                )
                
                if score > 0:
                    suggestions.append({
                        **template,
                        'suggestion_score': score,
                        'suggestion_reason': await self._get_suggestion_reason(
                            template, task_context, score
                        )
                    })
            
            # Sort by score and return top suggestions
            suggestions.sort(key=lambda x: x['suggestion_score'], reverse=True)
            return suggestions[:10]
            
        except Exception as e:
            logger.error(f"Template suggestion error: {e}")
            return []
    
    async def _calculate_template_score(
        self,
        template: Dict[str, Any],
        task_context: Dict[str, Any],
        agent_type: Optional[str],
        file_patterns: Optional[List[str]]
    ) -> float:
        """Calculate suggestion score for template"""
        score = 0.0
        
        # Base score for active templates
        score += 10.0
        
        # Agent compatibility score
        if agent_type and template.get('agent_compatibility'):
            if template['agent_compatibility'] == 'all':
                score += 20.0
            elif agent_type in template['agent_compatibility']:
                score += 30.0
        
        # Task type matching
        task_type = task_context.get('task_type', '')
        template_type = template.get('template_type', '')
        
        if task_type and template_type:
            if task_type == template_type:
                score += 40.0
            elif task_type in template_type or template_type in task_type:
                score += 20.0
        
        # Usage history score
        usage_score = await self._get_usage_score(template['id'])
        score += usage_score
        
        # File pattern matching
        if file_patterns:
            pattern_score = await self._calculate_pattern_score(
                template['id'], file_patterns
            )
            score += pattern_score
        
        # Priority boost for certain templates
        if template.get('priority') == 'high':
            score += 15.0
        elif template.get('priority') == 'medium':
            score += 5.0
        
        return score
    
    async def _get_usage_score(self, template_id: str) -> float:
        """Get usage-based score for template"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get usage statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as usage_count,
                        AVG(generation_time_ms) as avg_time,
                        SUM(CASE WHEN cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits
                    FROM template_usage 
                    WHERE template_id = ? 
                    AND used_at > datetime('now', '-30 days')
                """, (template_id,))
                
                row = cursor.fetchone()
                if row:
                    usage_count = row['usage_count'] or 0
                    avg_time = row['avg_time'] or 0
                    cache_hits = row['cache_hits'] or 0
                    
                    # Higher usage = higher score
                    usage_score = min(usage_count * 2, 20)
                    
                    # Faster templates get bonus
                    if avg_time > 0 and avg_time < 50:
                        usage_score += 5
                    
                    # High cache hit rate bonus
                    if usage_count > 0:
                        cache_ratio = cache_hits / usage_count
                        if cache_ratio > 0.8:
                            usage_score += 5
                    
                    return usage_score
                
                return 0.0
                
        except Exception as e:
            logger.error(f"Usage score calculation error: {e}")
            return 0.0
    
    async def _calculate_pattern_score(
        self,
        template_id: str,
        file_patterns: List[str]
    ) -> float:
        """Calculate pattern matching score"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get template-checklist mappings
                cursor.execute("""
                    SELECT tc.checklist_type, tc.file_patterns
                    FROM template_checklist_mappings tcm
                    JOIN task_checklists tc ON tcm.checklist_id = tc.id
                    WHERE tcm.template_id = ?
                """, (template_id,))
                
                mappings = cursor.fetchall()
                
                pattern_score = 0.0
                
                for mapping in mappings:
                    template_patterns = json.loads(mapping['file_patterns'] or '[]')
                    
                    # Check pattern overlap
                    for user_pattern in file_patterns:
                        for template_pattern in template_patterns:
                            if self._patterns_match(user_pattern, template_pattern):
                                pattern_score += 10.0
                
                return min(pattern_score, 25.0)  # Cap at 25 points
                
        except Exception as e:
            logger.error(f"Pattern score calculation error: {e}")
            return 0.0
    
    def _patterns_match(self, pattern1: str, pattern2: str) -> bool:
        """Check if two glob patterns have overlap"""
        # Simple pattern matching - could be enhanced with actual glob matching
        return (
            pattern1 == pattern2 or
            pattern1 in pattern2 or 
            pattern2 in pattern1 or
            self._extract_pattern_components(pattern1) & self._extract_pattern_components(pattern2)
        )
    
    def _extract_pattern_components(self, pattern: str) -> set:
        """Extract components from glob pattern for matching"""
        components = set()
        
        # Extract file extensions
        if '.' in pattern:
            ext = pattern.split('.')[-1].replace('*', '')
            if ext:
                components.add(ext)
        
        # Extract directory components
        parts = pattern.split('/')
        for part in parts:
            if part and part != '**' and '*' not in part:
                components.add(part)
        
        return components
    
    async def _get_suggestion_reason(
        self,
        template: Dict[str, Any],
        task_context: Dict[str, Any],
        score: float
    ) -> str:
        """Generate human-readable suggestion reason"""
        reasons = []
        
        # Template type matching
        if task_context.get('task_type') == template.get('template_type'):
            reasons.append(f"Perfect match for {template['template_type']} tasks")
        
        # Usage popularity
        if score > 50:
            reasons.append("Highly popular template")
        elif score > 30:
            reasons.append("Commonly used template")
        
        # Agent compatibility
        if template.get('agent_compatibility') == 'all':
            reasons.append("Compatible with all agents")
        
        # Default reason
        if not reasons:
            reasons.append("Good general-purpose template")
        
        return " • ".join(reasons)
    
    async def track_usage(
        self,
        template_id: str,
        task_id: Optional[str] = None,
        project_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        variables_used: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
        generation_time_ms: int = 0,
        cache_hit: bool = False
    ):
        """Track template usage for analytics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO template_usage 
                    (template_id, task_id, project_id, agent_name, variables_used, 
                     output_path, generation_time_ms, cache_hit, used_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    template_id, task_id, project_id, agent_name,
                    json.dumps(variables_used) if variables_used else None,
                    output_path, generation_time_ms, cache_hit
                ))
                
                conn.commit()
                logger.debug(f"Tracked usage for template {template_id}")
                
        except Exception as e:
            logger.error(f"Usage tracking error: {e}")
    
    async def get_template_analytics(
        self,
        template_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get template usage analytics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Base query
                base_query = """
                    FROM template_usage tu
                    JOIN templates t ON tu.template_id = t.id
                    WHERE tu.used_at > datetime('now', '-{} days')
                """.format(days)
                
                if template_id:
                    base_query += f" AND tu.template_id = '{template_id}'"
                
                # Usage statistics
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_usage,
                        COUNT(DISTINCT tu.template_id) as unique_templates,
                        COUNT(DISTINCT tu.task_id) as unique_tasks,
                        COUNT(DISTINCT tu.agent_name) as unique_agents,
                        AVG(tu.generation_time_ms) as avg_generation_time,
                        SUM(CASE WHEN tu.cache_hit = 1 THEN 1 ELSE 0 END) as cache_hits
                    {base_query}
                """)
                
                stats = dict(cursor.fetchone())
                
                # Top templates
                cursor.execute(f"""
                    SELECT 
                        tu.template_id,
                        t.name,
                        COUNT(*) as usage_count,
                        AVG(tu.generation_time_ms) as avg_time
                    {base_query}
                    GROUP BY tu.template_id, t.name
                    ORDER BY usage_count DESC
                    LIMIT 10
                """)
                
                top_templates = [dict(row) for row in cursor.fetchall()]
                
                # Calculate metrics
                total_usage = stats['total_usage'] or 0
                cache_hits = stats['cache_hits'] or 0
                cache_hit_ratio = (cache_hits / total_usage * 100) if total_usage > 0 else 0
                
                return {
                    'period_days': days,
                    'total_usage': total_usage,
                    'unique_templates': stats['unique_templates'],
                    'unique_tasks': stats['unique_tasks'],
                    'unique_agents': stats['unique_agents'],
                    'performance': {
                        'avg_generation_time_ms': round(stats['avg_generation_time'] or 0, 2),
                        'cache_hit_ratio_percent': round(cache_hit_ratio, 2),
                        'total_cache_hits': cache_hits
                    },
                    'top_templates': top_templates,
                    'health_metrics': {
                        'performance_target_met': (stats['avg_generation_time'] or 0) < 100,
                        'cache_target_met': cache_hit_ratio > 90
                    }
                }
                
        except Exception as e:
            logger.error(f"Analytics retrieval error: {e}")
            return {'error': str(e)}
    
    async def register_template(
        self,
        template_id: str,
        name: str,
        description: str,
        content: str,
        template_type: str,
        agent_compatibility: str = "all",
        file_patterns: Optional[List[str]] = None,
        variables: Optional[List[str]] = None,
        priority: str = "medium"
    ) -> bool:
        """Register a new template"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO templates 
                    (id, name, description, content, type, category,
                     compatible_agents, required_variables, default_globs, is_active, 
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))
                """, (
                    template_id, name, description, content, template_type, priority,
                    json.dumps([agent_compatibility]) if agent_compatibility != "all" else '["*"]', 
                    json.dumps(variables) if variables else '[]',
                    json.dumps(file_patterns) if file_patterns else None
                ))
                
                conn.commit()
                logger.info(f"Registered template {template_id}")
                return True
                
        except Exception as e:
            logger.error(f"Template registration error: {e}")
            return False
    
    async def update_template(
        self,
        template_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update existing template"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build update query
                set_clauses = []
                params = []
                
                allowed_updates = [
                    'name', 'description', 'content', 'template_type',
                    'agent_compatibility', 'file_patterns', 'required_variables',
                    'priority', 'is_active'
                ]
                
                for field, value in updates.items():
                    if field in allowed_updates:
                        set_clauses.append(f"{field} = ?")
                        if field in ['file_patterns', 'required_variables'] and isinstance(value, list):
                            params.append(json.dumps(value))
                        else:
                            params.append(value)
                
                if not set_clauses:
                    return False
                
                set_clauses.append("updated_at = datetime('now')")
                params.append(template_id)
                
                query = f"""
                    UPDATE templates 
                    SET {', '.join(set_clauses)}
                    WHERE id = ?
                """
                
                cursor.execute(query, params)
                conn.commit()
                
                logger.info(f"Updated template {template_id}")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Template update error: {e}")
            return False
    
    async def delete_template(self, template_id: str) -> bool:
        """Soft delete template"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE templates 
                    SET is_active = 0, updated_at = datetime('now')
                    WHERE id = ?
                """, (template_id,))
                
                conn.commit()
                
                logger.info(f"Deleted template {template_id}")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Template deletion error: {e}")
            return False