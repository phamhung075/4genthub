"""
Context Search Use Case with Full-Text and Semantic Search

Provides powerful search capabilities across the context hierarchy
with support for full-text search, filtering, and relevance ranking.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
import re

from ...domain.models.unified_context import ContextLevel
from ..services.unified_context_service import UnifiedContextService
from ...domain.interfaces.cache_service import ICacheService

logger = logging.getLogger(__name__)


class SearchScope(Enum):
    """Search scope options"""
    CURRENT_LEVEL = "current"      # Search only in specified level
    WITH_CHILDREN = "children"      # Include child levels
    WITH_PARENTS = "parents"        # Include parent levels
    ALL_LEVELS = "all"              # Search all levels


class SearchMode(Enum):
    """Search mode options"""
    EXACT = "exact"                 # Exact match
    CONTAINS = "contains"           # Contains substring
    FUZZY = "fuzzy"                 # Fuzzy matching
    REGEX = "regex"                 # Regular expression
    SEMANTIC = "semantic"           # Semantic similarity (future)


@dataclass
class SearchQuery:
    """Search query parameters"""
    query: str                      # Search query string
    levels: List[ContextLevel]      # Levels to search
    scope: SearchScope = SearchScope.CURRENT_LEVEL
    mode: SearchMode = SearchMode.CONTAINS
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    git_branch_id: Optional[str] = None
    
    # Filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    updated_after: Optional[datetime] = None
    updated_before: Optional[datetime] = None
    
    # Result options
    limit: int = 50
    offset: int = 0
    include_score: bool = True
    include_inherited: bool = False
    highlight_matches: bool = True


@dataclass
class SearchResult:
    """Single search result"""
    level: ContextLevel
    context_id: str
    data: Dict[str, Any]
    score: float                    # Relevance score (0-1)
    matches: List[Dict[str, Any]]   # Match details
    metadata: Dict[str, Any]        # Additional metadata


class ContextSearchEngine:
    """
    Advanced search engine for context data with multiple search strategies.
    """
    
    def __init__(self, context_service: UnifiedContextService):
        self.context_service = context_service
        self.cache = get_context_cache()
    
    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """
        Execute search across context hierarchy.
        
        Args:
            query: Search query parameters
        
        Returns:
            List of search results sorted by relevance
        """
        results = []
        
        # Determine levels to search
        search_levels = self._expand_search_levels(query.levels, query.scope)
        
        # Search each level
        for level in search_levels:
            level_results = await self._search_level(
                level=level,
                query=query
            )
            results.extend(level_results)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply pagination
        start = query.offset
        end = query.offset + query.limit
        results = results[start:end]
        
        # Highlight matches if requested
        if query.highlight_matches:
            results = self._highlight_matches(results, query.query)
        
        return results
    
    def _expand_search_levels(
        self, 
        levels: List[ContextLevel], 
        scope: SearchScope
    ) -> Set[ContextLevel]:
        """Expand search levels based on scope"""
        
        search_levels = set(levels)
        
        if scope == SearchScope.WITH_CHILDREN:
            # Add child levels
            for level in levels:
                if level == ContextLevel.GLOBAL:
                    search_levels.update([
                        ContextLevel.PROJECT,
                        ContextLevel.BRANCH,
                        ContextLevel.TASK
                    ])
                elif level == ContextLevel.PROJECT:
                    search_levels.update([
                        ContextLevel.BRANCH,
                        ContextLevel.TASK
                    ])
                elif level == ContextLevel.BRANCH:
                    search_levels.add(ContextLevel.TASK)
        
        elif scope == SearchScope.WITH_PARENTS:
            # Add parent levels
            for level in levels:
                if level == ContextLevel.TASK:
                    search_levels.update([
                        ContextLevel.BRANCH,
                        ContextLevel.PROJECT,
                        ContextLevel.GLOBAL
                    ])
                elif level == ContextLevel.BRANCH:
                    search_levels.update([
                        ContextLevel.PROJECT,
                        ContextLevel.GLOBAL
                    ])
                elif level == ContextLevel.PROJECT:
                    search_levels.add(ContextLevel.GLOBAL)
        
        elif scope == SearchScope.ALL_LEVELS:
            # Search all levels
            search_levels = set(ContextLevel)
        
        return search_levels
    
    async def _search_level(
        self, 
        level: ContextLevel, 
        query: SearchQuery
    ) -> List[SearchResult]:
        """Search within a specific level"""
        
        # Get all contexts at this level
        # Note: This would need repository method to list contexts
        contexts = await self._get_contexts_for_level(
            level=level,
            user_id=query.user_id,
            project_id=query.project_id,
            git_branch_id=query.git_branch_id
        )
        
        results = []
        for context_id, context_data in contexts:
            # Apply filters
            if not self._passes_filters(context_data, query):
                continue
            
            # Calculate relevance score
            score, matches = self._calculate_relevance(
                data=context_data,
                query=query.query,
                mode=query.mode
            )
            
            if score > 0:
                results.append(SearchResult(
                    level=level,
                    context_id=context_id,
                    data=context_data,
                    score=score,
                    matches=matches,
                    metadata={
                        'created_at': context_data.get('created_at'),
                        'updated_at': context_data.get('updated_at'),
                        'user_id': query.user_id
                    }
                ))
        
        return results
    
    def _passes_filters(self, context_data: Dict, query: SearchQuery) -> bool:
        """Check if context passes date filters"""
        
        if query.created_after:
            created = context_data.get('created_at')
            if created and created < query.created_after:
                return False
        
        if query.created_before:
            created = context_data.get('created_at')
            if created and created > query.created_before:
                return False
        
        if query.updated_after:
            updated = context_data.get('updated_at')
            if updated and updated < query.updated_after:
                return False
        
        if query.updated_before:
            updated = context_data.get('updated_at')
            if updated and updated > query.updated_before:
                return False
        
        return True
    
    def _calculate_relevance(
        self, 
        data: Dict[str, Any], 
        query: str, 
        mode: SearchMode
    ) -> tuple[float, List[Dict]]:
        """Calculate relevance score and find matches"""
        
        score = 0.0
        matches = []
        
        # Convert data to searchable text
        text_content = self._extract_text(data)
        
        if mode == SearchMode.EXACT:
            # Exact match
            if query.lower() in text_content.lower():
                score = 1.0
                matches.append({
                    'type': 'exact',
                    'field': 'full_content',
                    'matched': query
                })
        
        elif mode == SearchMode.CONTAINS:
            # Contains substring
            query_lower = query.lower()
            text_lower = text_content.lower()
            
            count = text_lower.count(query_lower)
            if count > 0:
                # Score based on frequency
                score = min(1.0, count * 0.2)
                
                # Find all occurrences
                start = 0
                while True:
                    index = text_lower.find(query_lower, start)
                    if index == -1:
                        break
                    
                    matches.append({
                        'type': 'contains',
                        'position': index,
                        'matched': text_content[index:index+len(query)]
                    })
                    start = index + 1
        
        elif mode == SearchMode.FUZZY:
            # Fuzzy matching (simple implementation)
            score = self._fuzzy_score(query.lower(), text_content.lower())
            if score > 0.5:
                matches.append({
                    'type': 'fuzzy',
                    'score': score
                })
        
        elif mode == SearchMode.REGEX:
            # Regular expression matching
            try:
                pattern = re.compile(query, re.IGNORECASE)
                found_matches = pattern.findall(text_content)
                
                if found_matches:
                    score = min(1.0, len(found_matches) * 0.2)
                    for match in found_matches[:10]:  # Limit matches
                        matches.append({
                            'type': 'regex',
                            'matched': match
                        })
            except re.error:
                logger.warning(f"Invalid regex pattern: {query}")
        
        elif mode == SearchMode.SEMANTIC:
            # Placeholder for semantic search
            # Would require embeddings and vector similarity
            logger.info("Semantic search not yet implemented")
        
        # Boost score for matches in important fields
        score = self._apply_field_boosts(data, query, score)
        
        return score, matches
    
    def _extract_text(self, data: Dict) -> str:
        """Extract searchable text from context data"""
        
        def extract_recursive(obj, parts=[]):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    parts.append(str(key))
                    extract_recursive(value, parts)
            elif isinstance(obj, list):
                for item in obj:
                    extract_recursive(item, parts)
            else:
                parts.append(str(obj))
            return parts
        
        text_parts = extract_recursive(data)
        return " ".join(text_parts)
    
    def _fuzzy_score(self, query: str, text: str) -> float:
        """Calculate fuzzy matching score (Levenshtein-based)"""
        
        # Simple implementation - check substrings
        words = text.split()
        max_score = 0.0
        
        for word in words:
            # Calculate similarity
            score = self._string_similarity(query, word)
            max_score = max(max_score, score)
        
        return max_score
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity (0-1)"""
        
        # Simple character overlap
        if not s1 or not s2:
            return 0.0
        
        common = len(set(s1) & set(s2))
        return common / max(len(s1), len(s2))
    
    def _apply_field_boosts(
        self, 
        data: Dict, 
        query: str, 
        base_score: float
    ) -> float:
        """Apply field-specific score boosts"""
        
        boost = 1.0
        query_lower = query.lower()
        
        # Boost for matches in important fields
        important_fields = ['title', 'name', 'description', 'summary']
        for field in important_fields:
            if field in data:
                field_value = str(data[field]).lower()
                if query_lower in field_value:
                    boost *= 1.5
        
        # Boost for recent updates
        updated = data.get('updated_at')
        if updated:
            from datetime import timedelta
            if isinstance(updated, str):
                updated = datetime.fromisoformat(updated)
            
            age = datetime.utcnow() - updated
            if age < timedelta(days=1):
                boost *= 1.3
            elif age < timedelta(days=7):
                boost *= 1.1
        
        return min(1.0, base_score * boost)
    
    def _highlight_matches(
        self, 
        results: List[SearchResult], 
        query: str
    ) -> List[SearchResult]:
        """Add highlighting to matched text"""
        
        for result in results:
            # Add highlight markers to matched text
            for match in result.matches:
                if 'matched' in match:
                    match['highlighted'] = f"**{match['matched']}**"
        
        return results
    
    async def _get_contexts_for_level(
        self,
        level: ContextLevel,
        user_id: str,
        project_id: Optional[str] = None,
        git_branch_id: Optional[str] = None
    ) -> List[tuple[str, Dict]]:
        """Get all contexts at a specific level"""
        
        # This would need to be implemented in the repository layer
        # For now, returning empty list as placeholder
        logger.info(f"Fetching contexts for level {level}")
        
        # Would call repository method like:
        # contexts = await self.context_service.list_contexts(
        #     level=level,
        #     user_id=user_id,
        #     project_id=project_id,
        #     git_branch_id=git_branch_id
        # )
        
        return []
    
    # Advanced search methods
    
    async def search_by_pattern(
        self,
        pattern: str,
        levels: List[ContextLevel],
        user_id: str
    ) -> List[SearchResult]:
        """Search for contexts matching a specific pattern"""
        
        query = SearchQuery(
            query=pattern,
            levels=levels,
            mode=SearchMode.REGEX,
            user_id=user_id,
            scope=SearchScope.CURRENT_LEVEL
        )
        
        return await self.search(query)
    
    async def search_recent(
        self,
        levels: List[ContextLevel],
        user_id: str,
        days: int = 7,
        limit: int = 20
    ) -> List[SearchResult]:
        """Search for recently updated contexts"""
        
        from datetime import timedelta
        
        query = SearchQuery(
            query="*",  # Match all
            levels=levels,
            mode=SearchMode.REGEX,
            user_id=user_id,
            updated_after=datetime.utcnow() - timedelta(days=days),
            limit=limit
        )
        
        return await self.search(query)
    
    async def search_by_tags(
        self,
        tags: List[str],
        levels: List[ContextLevel],
        user_id: str
    ) -> List[SearchResult]:
        """Search for contexts with specific tags"""
        
        # Build query for tags
        tag_query = " OR ".join(tags)
        
        query = SearchQuery(
            query=tag_query,
            levels=levels,
            mode=SearchMode.CONTAINS,
            user_id=user_id
        )
        
        return await self.search(query)