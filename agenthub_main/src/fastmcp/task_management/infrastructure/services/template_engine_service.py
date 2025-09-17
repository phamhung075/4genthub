"""Template Engine Service - Infrastructure Layer"""

import asyncio
import hashlib
import time
from datetime import datetime, timezone
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
import logging

try:
    import pybars
    from redis import Redis
except ImportError:
    pybars = None
    Redis = None

from ...domain.entities.template import Template, TemplateResult, TemplateRenderRequest
from ...domain.value_objects.template_id import TemplateId
from ...domain.exceptions.template_exceptions import TemplateRenderError, TemplateCompilationError
from .template_registry_service import TemplateRegistryService

logger = logging.getLogger(__name__)


class TemplateEngineService:
    """Template engine service for rendering templates with caching and performance optimization"""
    
    def __init__(
        self,
        registry_service: TemplateRegistryService,
        redis_client: Optional[Redis] = None
    ):
        if pybars is None:
            raise ImportError("pybars package required for template engine")
            
        self.handlebars = pybars.Compiler()
        self.registry_service = registry_service
        self.redis_client = redis_client
        
        # Performance metrics
        self.render_count = 0
        self.cache_hits = 0
        self.total_render_time = 0.0
        
        # Template compilation cache
        self._compiled_templates = {}
        
        logger.info("TemplateEngineService initialized")
    
    async def render_template(self, request: TemplateRenderRequest) -> TemplateResult:
        """Render template with full caching and performance optimization"""
        start_time = time.time()
        self.render_count += 1
        
        try:
            # Check cache first (unless force regenerate)
            if not request.force_regenerate:
                cache_result = await self._check_cache(request)
                if cache_result:
                    self.cache_hits += 1
                    logger.debug(f"Cache hit for template {request.template_id.value}")
                    return cache_result
            
            # Load template from registry
            template_data = await self.registry_service.get_template(request.template_id.value)
            if not template_data:
                raise TemplateRenderError(
                    f"Template not found: {request.template_id.value}",
                    request.template_id.value
                )
            
            # Compile template (with caching)
            compiled_template = await self._get_compiled_template(
                request.template_id.value, 
                template_data['content']
            )
            
            # Resolve variables
            resolved_context = await self._resolve_variables(
                request.template_id.value,
                request.variables,
                request.task_context
            )
            
            # Render template
            try:
                rendered_content = compiled_template(resolved_context)
            except Exception as e:
                raise TemplateRenderError(
                    f"Template rendering failed: {str(e)}",
                    request.template_id.value,
                    {"variables": resolved_context, "error": str(e)}
                )
            
            # Calculate timing
            generation_time_ms = int((time.time() - start_time) * 1000)
            self.total_render_time += generation_time_ms
            
            # Create result
            result = TemplateResult(
                content=rendered_content,
                template_id=request.template_id,
                variables_used=resolved_context,
                generated_at=datetime.now(timezone.utc),
                generation_time_ms=generation_time_ms,
                cache_hit=False,
                output_path=request.output_path
            )
            
            # Cache result (async)
            asyncio.create_task(self._cache_result(request, result))
            
            logger.info(f"Rendered template {request.template_id.value} in {generation_time_ms}ms")
            return result
            
        except Exception as e:
            logger.error(f"Template rendering failed for {request.template_id.value}: {e}")
            raise
    
    async def _check_cache(self, request: TemplateRenderRequest) -> Optional[TemplateResult]:
        """Check if template result exists in cache"""
        cache_key = self._generate_cache_key(request.template_id.value, request.variables)
        
        # Check Redis cache first
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    data = json.loads(cached_data)
                    return TemplateResult(
                        content=data['content'],
                        template_id=TemplateId(data['template_id']),
                        variables_used=data['variables_used'],
                        generated_at=datetime.fromisoformat(data['generated_at']),
                        generation_time_ms=data['generation_time_ms'],
                        cache_hit=True,
                        output_path=data.get('output_path')
                    )
            except Exception as e:
                logger.warning(f"Redis cache check failed: {e}")
        
        return None
    
    async def _cache_result(self, request: TemplateRenderRequest, result: TemplateResult):
        """Cache template result for performance"""
        cache_key = self._generate_cache_key(request.template_id.value, request.variables)
        
        # Redis cache (1 hour expiry)
        if self.redis_client:
            try:
                cache_data = {
                    'content': result.content,
                    'template_id': result.template_id.value,
                    'variables_used': result.variables_used,
                    'generated_at': result.generated_at.isoformat(),
                    'generation_time_ms': result.generation_time_ms,
                    'cache_hit': result.cache_hit,
                    'output_path': result.output_path
                }
                self.redis_client.setex(
                    cache_key,
                    3600,  # 1 hour TTL
                    json.dumps(cache_data)
                )
            except Exception as e:
                logger.warning(f"Redis cache set failed: {e}")
    
    async def _get_compiled_template(self, template_id: str, content: str):
        """Get compiled template with caching"""
        if template_id in self._compiled_templates:
            return self._compiled_templates[template_id]
        
        try:
            compiled_template = self.handlebars.compile(content)
            self._compiled_templates[template_id] = compiled_template
            return compiled_template
        except Exception as e:
            raise TemplateCompilationError(
                f"Template compilation failed: {str(e)}",
                template_id,
                [str(e)]
            )
    
    async def _resolve_variables(
        self,
        template_id: str,
        variables: Dict[str, Any],
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Resolve variables with hierarchy"""
        resolved_context = {}
        
        # Add task context variables (lower precedence)
        if task_context:
            resolved_context.update(task_context)
        
        # Add request variables (higher precedence)
        resolved_context.update(variables)
        
        # Add system variables
        resolved_context.update({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'template_id': template_id,
            'render_time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        })
        
        return resolved_context
    
    def _generate_cache_key(self, template_id: str, variables: Dict[str, Any]) -> str:
        """Generate cache key for template result"""
        variables_hash = self._hash_variables(variables)
        return f"template:{template_id}:{variables_hash}"
    
    def _hash_variables(self, variables: Dict[str, Any]) -> str:
        """Generate hash for variables"""
        variables_str = json.dumps(variables, sort_keys=True)
        return hashlib.md5(variables_str.encode()).hexdigest()
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'render_count': self.render_count,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': self.cache_hits / max(self.render_count, 1),
            'total_render_time': self.total_render_time,
            'avg_render_time': self.total_render_time / max(self.render_count, 1),
            'compiled_templates_count': len(self._compiled_templates)
        }
    
    async def clear_cache(self, template_id: Optional[str] = None):
        """Clear template cache"""
        if template_id:
            # Clear specific template cache
            if template_id in self._compiled_templates:
                del self._compiled_templates[template_id]
            
            # Clear Redis cache for specific template
            if self.redis_client:
                try:
                    pattern = f"template:{template_id}:*"
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        self.redis_client.delete(*keys)
                except Exception as e:
                    logger.warning(f"Redis cache clear failed: {e}")
        else:
            # Clear all cache
            self._compiled_templates.clear()
            
            if self.redis_client:
                try:
                    pattern = "template:*"
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        self.redis_client.delete(*keys)
                except Exception as e:
                    logger.warning(f"Redis cache clear failed: {e}")
    
    async def suggest_templates(
        self,
        task_context: Dict[str, Any],
        agent_type: Optional[str] = None,
        file_patterns: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Suggest templates based on context"""
        try:
            return await self.registry_service.suggest_templates(
                task_context=task_context,
                agent_type=agent_type,
                file_patterns=file_patterns
            )
        except Exception as e:
            logger.error(f"Template suggestion failed: {e}")
            return [] 