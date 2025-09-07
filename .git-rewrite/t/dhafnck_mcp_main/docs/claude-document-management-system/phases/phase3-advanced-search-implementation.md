# Phase 3: Advanced Search & Analytics Implementation Guide

## Overview

This guide provides detailed implementation steps for Phase 3 of the Claude Document Management System, focusing on advanced search features, analytics, and content recommendations.

## Prerequisites

- [x] Phase 1 PostgreSQL baseline completed
- [x] Phase 2 pgvector integration completed
- [ ] Analytics database setup (separate instance or schema)
- [ ] Dashboard framework chosen (Grafana, custom, etc.)

## Implementation Checklist

## 📁 Phase 3 File Creation Locations & Specifications

### Advanced Search Services Directory
**Location**: `dhafnck_mcp_main/services/`

1. **`advanced_query_parser.py`** (~200 lines)
   - **Purpose**: Parse advanced search queries with boolean logic
   - **Key Classes**: `AdvancedQueryParser`, `SearchTerm`, `QueryOperator`
   - **Features**: AND/OR/NOT operations, field-specific queries, wildcards

2. **`faceted_search.py`** (~300 lines)
   - **Purpose**: Implement faceted search functionality
   - **Key Classes**: `FacetedSearchService`, `FacetManager`
   - **Features**: Multi-facet filtering, category aggregation, dynamic facets

3. **`search_analytics.py`** (~250 lines)
   - **Purpose**: Track and analyze search behavior
   - **Key Classes**: `SearchAnalyticsService`, `AnalyticsReporter`
   - **Features**: Query tracking, performance metrics, usage patterns

4. **`recommendation_service.py`** (~400 lines)
   - **Purpose**: Generate content recommendations
   - **Key Classes**: `RecommendationService`, `SimilarityCalculator`
   - **Features**: Document similarity, collaborative filtering, personalized recommendations

### Database Scripts Directory
**Location**: `dhafnck_mcp_main/database/`

5. **`phase3_analytics.sql`** (~100 lines)
   - **Purpose**: Analytics tables and views
   - **Contents**: search_analytics, facet_aggregates, recommendation_cache, user_preferences

6. **`migrations/migration_002_add_analytics.sql`** (~100 lines)
   - **Purpose**: Add analytics capabilities to existing database
   - **Features**: Analytics tables, performance indexes, aggregation views

### Configuration Directory
**Location**: `dhafnck_mcp_main/config/`

7. **`analytics_config.yml`**
   - **Purpose**: Analytics and search configuration
   - **Contents**: Tracking settings, retention policies, facet definitions

### Enhanced CLI Updates
**Location**: `.claude/commands/manage_document_md_postgresql`

8. **Updated CLI Script** (+300 lines)
   - **New Actions**: `advanced-search`, `analytics`, `recommendations`
   - **New Features**: Complex query syntax, search analytics dashboard, recommendation engine

### Test Files Structure
**Location**: `dhafnck_mcp_main/tests/`

#### Unit Tests
9. **`unit/test_advanced_query_parser.py`**
   - **Purpose**: Test query parsing logic
   - **Coverage**: Syntax parsing, field queries, boolean operations

10. **`unit/test_faceted_search.py`**
    - **Purpose**: Test faceted search functionality
    - **Coverage**: Facet generation, filtering, aggregation

11. **`unit/test_search_analytics.py`**
    - **Purpose**: Test analytics data collection
    - **Coverage**: Event logging, metrics calculation, reporting

12. **`unit/test_recommendations.py`**
    - **Purpose**: Test recommendation engine
    - **Coverage**: Similarity calculation, recommendation generation, ranking

#### Integration Tests
13. **`integration/test_advanced_search_integration.py`**
    - **Purpose**: End-to-end advanced search testing
    - **Coverage**: Complete search workflows, performance benchmarks

14. **`phase3/test_phase3.sh`**
    - **Purpose**: Comprehensive Phase 3 integration testing
    - **Coverage**: Advanced search, analytics, recommendations

## Test Strategy for Phase 3

### Unit Tests (Fast, Isolated)
- Query parser validation and syntax testing
- Faceted search algorithm testing
- Analytics calculation and aggregation testing
- Recommendation algorithm accuracy testing

### Integration Tests (Component Interaction)
- Advanced search workflow testing
- Analytics data pipeline testing
- Recommendation system integration testing
- Search dashboard functionality testing

### Performance Tests (Benchmarks)
- Complex query performance testing
- Analytics query optimization testing
- Recommendation generation speed testing
- Large dataset search performance testing

### Phase 3 File Creation Checklist
- [ ] Create `services/advanced_query_parser.py` with boolean logic
- [ ] Create `services/faceted_search.py` with multi-facet support
- [ ] Create `services/search_analytics.py` with usage tracking
- [ ] Create `services/recommendation_service.py` with similarity engine
- [ ] Create `database/phase3_analytics.sql` analytics schema
- [ ] Create `database/migrations/migration_002_add_analytics.sql`
- [ ] Update CLI script with advanced search functions
- [ ] Create `config/analytics_config.yml` configuration
- [ ] Create unit test files for all Phase 3 components
- [ ] Create integration test for complete advanced search workflow
- [ ] Create `tests/phase3/test_phase3.sh` comprehensive test script

### Step 1: Advanced Query Language

#### 1.1 Query Parser Implementation
```python
# advanced_query_parser.py
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class QueryOperator(Enum):
    AND = "AND"
    OR = "OR"  
    NOT = "NOT"

@dataclass
class SearchTerm:
    field: Optional[str]
    value: str
    operator: QueryOperator
    is_phrase: bool = False
    boost: float = 1.0

class AdvancedQueryParser:
    def __init__(self):
        self.field_mappings = {
            'title': 'title',
            'content': 'content', 
            'category': 'category',
            'author': 'created_by',
            'tag': 'labels',
            'date': 'created_at'
        }
        
    def parse_query(self, query: str) -> List[SearchTerm]:
        """Parse advanced search query into structured terms"""
        terms = []
        
        # Handle quoted phrases
        phrase_pattern = r'"([^"]*)"'
        phrases = re.findall(phrase_pattern, query)
        for phrase in phrases:
            terms.append(SearchTerm(None, phrase, QueryOperator.AND, is_phrase=True))
            query = query.replace(f'"{phrase}"', '', 1)
        
        # Handle field-specific queries (field:value)
        field_pattern = r'(\w+):([^\s]+)'
        field_matches = re.findall(field_pattern, query)
        for field, value in field_matches:
            if field in self.field_mappings:
                terms.append(SearchTerm(self.field_mappings[field], value, QueryOperator.AND))
                query = re.sub(f'{field}:{re.escape(value)}', '', query)
        
        # Handle remaining terms
        remaining_terms = query.strip().split()
        for term in remaining_terms:
            if term.upper() in ['AND', 'OR', 'NOT']:
                continue
            if term:
                terms.append(SearchTerm(None, term, QueryOperator.AND))
        
        return terms
    
    def build_sql_query(self, terms: List[SearchTerm]) -> Tuple[str, List]:
        """Convert parsed terms to SQL WHERE clause"""
        conditions = []
        params = []
        
        for term in terms:
            if term.field:
                if term.field == 'created_at':
                    conditions.append(f"{term.field}::date = %s")
                    params.append(term.value)
                elif term.field == 'labels':
                    conditions.append(f"%s = ANY(string_to_array({term.field}, ','))")
                    params.append(term.value)
                else:
                    conditions.append(f"{term.field} ILIKE %s")
                    params.append(f"%{term.value}%")
            else:
                if term.is_phrase:
                    conditions.append("search_vector @@ phraseto_tsquery('english', %s)")
                    params.append(term.value)
                else:
                    conditions.append("search_vector @@ plainto_tsquery('english', %s)")
                    params.append(term.value)
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        return where_clause, params
```

**Checklist:**
- [ ] Query parser class implemented
- [ ] Field-specific search support added
- [ ] Phrase search handling implemented
- [ ] Boolean operators supported
- [ ] SQL generation working

#### 1.2 Search Syntax Documentation
```markdown
# Advanced Search Syntax

## Basic Search
- `postgresql database` - Search for documents containing both terms
- `"exact phrase"` - Search for exact phrase match

## Field-Specific Search
- `title:authentication` - Search in title field only
- `category:api` - Search in category field
- `author:admin` - Search by document creator
- `date:2024-01-15` - Search by creation date
- `tag:testing` - Search by tag/label

## Boolean Operations
- `postgresql AND database` - Both terms must be present
- `authentication OR login` - Either term can be present  
- `database NOT postgresql` - Exclude documents with "postgresql"

## Combined Examples
- `title:api category:testing "error handling"`
- `postgresql AND (database OR connection)`
- `author:admin date:2024-01-15`
```

**Checklist:**
- [ ] Search syntax documented
- [ ] Examples provided for each feature
- [ ] User guide created
- [ ] Help system integrated

### Step 2: Faceted Search Implementation

#### 2.1 Facet Data Structure
```sql
-- Create facets table for dynamic faceting
CREATE TABLE search_facets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    facet_type VARCHAR(20) NOT NULL, -- 'term', 'date_range', 'numeric'
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert default facets
INSERT INTO search_facets (name, display_name, field_name, facet_type, sort_order) VALUES
('category', 'Category', 'category', 'term', 1),
('author', 'Author', 'created_by', 'term', 2),
('date_created', 'Date Created', 'created_at', 'date_range', 3),
('tags', 'Tags', 'labels', 'term', 4),
('status', 'Status', 'status', 'term', 5);

-- Create facet values aggregation view
CREATE MATERIALIZED VIEW facet_aggregates AS
SELECT 
    'category' as facet_name,
    category as facet_value,
    COUNT(*) as doc_count
FROM documents 
WHERE status = 'active' AND category IS NOT NULL
GROUP BY category

UNION ALL

SELECT 
    'author' as facet_name,
    created_by as facet_value,
    COUNT(*) as doc_count
FROM documents 
WHERE status = 'active' AND created_by IS NOT NULL
GROUP BY created_by

UNION ALL

SELECT 
    'status' as facet_name,
    status as facet_value,
    COUNT(*) as doc_count
FROM documents 
WHERE status IS NOT NULL
GROUP BY status;

-- Create index for facet queries
CREATE INDEX idx_facet_aggregates ON facet_aggregates(facet_name, facet_value);

-- Refresh materialized view function
CREATE OR REPLACE FUNCTION refresh_facet_aggregates()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY facet_aggregates;
END;
$$ LANGUAGE plpgsql;
```

**Checklist:**
- [ ] Facets table created
- [ ] Default facets configured
- [ ] Materialized view for aggregation created
- [ ] Refresh function implemented
- [ ] Indexes created for performance

#### 2.2 Faceted Search API
```python
# faceted_search.py
from typing import Dict, List, Any, Optional
import psycopg2
from datetime import datetime, timedelta

class FacetedSearchService:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_available_facets(self) -> List[Dict]:
        """Get all available facets with their current values"""
        cursor = self.db.cursor()
        
        # Get facet definitions
        cursor.execute("""
            SELECT name, display_name, field_name, facet_type
            FROM search_facets 
            WHERE is_active = true
            ORDER BY sort_order
        """)
        facets = cursor.fetchall()
        
        result = []
        for name, display_name, field_name, facet_type in facets:
            # Get facet values
            if facet_type == 'date_range':
                values = self._get_date_range_facets(field_name)
            else:
                cursor.execute("""
                    SELECT facet_value, doc_count
                    FROM facet_aggregates
                    WHERE facet_name = %s
                    ORDER BY doc_count DESC
                    LIMIT 20
                """, (name,))
                values = [{'value': v, 'count': c} for v, c in cursor.fetchall()]
            
            result.append({
                'name': name,
                'display_name': display_name,
                'type': facet_type,
                'values': values
            })
        
        cursor.close()
        return result
    
    def _get_date_range_facets(self, field_name: str) -> List[Dict]:
        """Generate date range facets"""
        cursor = self.db.cursor()
        
        # Get date ranges
        now = datetime.now()
        ranges = [
            ('Last 7 days', now - timedelta(days=7)),
            ('Last 30 days', now - timedelta(days=30)),
            ('Last 90 days', now - timedelta(days=90)),
            ('Last year', now - timedelta(days=365))
        ]
        
        result = []
        for label, since_date in ranges:
            cursor.execute(f"""
                SELECT COUNT(*) FROM documents 
                WHERE {field_name} >= %s AND status = 'active'
            """, (since_date,))
            count = cursor.fetchone()[0]
            
            if count > 0:
                result.append({
                    'value': since_date.isoformat(),
                    'label': label,
                    'count': count
                })
        
        cursor.close()
        return result
    
    def search_with_facets(self, 
                          query: str = "",
                          filters: Dict[str, List[str]] = None,
                          limit: int = 20,
                          offset: int = 0) -> Dict[str, Any]:
        """Perform faceted search"""
        cursor = self.db.cursor()
        
        # Build base query
        base_conditions = ["status = 'active'"]
        params = []
        
        # Add text search
        if query:
            base_conditions.append("search_vector @@ plainto_tsquery('english', %s)")
            params.append(query)
        
        # Add facet filters
        if filters:
            for facet_name, values in filters.items():
                if values:
                    # Get field name for facet
                    cursor.execute("SELECT field_name FROM search_facets WHERE name = %s", (facet_name,))
                    field_row = cursor.fetchone()
                    if field_row:
                        field_name = field_row[0]
                        placeholders = ','.join(['%s'] * len(values))
                        base_conditions.append(f"{field_name} IN ({placeholders})")
                        params.extend(values)
        
        where_clause = " AND ".join(base_conditions)
        
        # Get search results
        search_query = f"""
            SELECT path, title, description, category, created_at, created_by
            FROM documents
            WHERE {where_clause}
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        
        cursor.execute(search_query, params)
        documents = cursor.fetchall()
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM documents WHERE {where_clause}"
        cursor.execute(count_query, params[:-2])  # Remove limit/offset
        total_count = cursor.fetchone()[0]
        
        cursor.close()
        
        return {
            'documents': [
                {
                    'path': doc[0],
                    'title': doc[1], 
                    'description': doc[2],
                    'category': doc[3],
                    'created_at': doc[4].isoformat() if doc[4] else None,
                    'created_by': doc[5]
                }
                for doc in documents
            ],
            'total_count': total_count,
            'facets': self.get_available_facets()
        }
```

**Checklist:**
- [ ] Faceted search service implemented
- [ ] Date range facets working
- [ ] Multi-facet filtering supported
- [ ] Search results with facets returned
- [ ] Performance optimized

### Step 3: Search Analytics Implementation

#### 3.1 Analytics Database Schema
```sql
-- Create analytics tables
CREATE TABLE search_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100),
    user_id VARCHAR(100),
    query_text TEXT NOT NULL,
    query_type VARCHAR(20) DEFAULT 'text', -- 'text', 'semantic', 'hybrid', 'faceted'
    results_count INTEGER NOT NULL DEFAULT 0,
    response_time_ms INTEGER,
    clicked_results JSONB, -- Array of clicked document IDs
    filters_used JSONB, -- Facet filters applied
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

-- Create indexes for analytics
CREATE INDEX idx_search_analytics_timestamp ON search_analytics(timestamp);
CREATE INDEX idx_search_analytics_query ON search_analytics USING GIN(to_tsvector('english', query_text));
CREATE INDEX idx_search_analytics_user ON search_analytics(user_id, timestamp);

-- Create search performance table
CREATE TABLE search_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    query_type VARCHAR(20) NOT NULL,
    avg_response_time_ms NUMERIC(10,2),
    total_searches INTEGER,
    successful_searches INTEGER,
    zero_result_searches INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(date, query_type)
);

-- Create popular searches view
CREATE MATERIALIZED VIEW popular_searches AS
SELECT 
    query_text,
    COUNT(*) as search_count,
    AVG(results_count) as avg_results,
    AVG(response_time_ms) as avg_response_time,
    MAX(timestamp) as last_searched
FROM search_analytics
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY query_text
ORDER BY search_count DESC;

CREATE INDEX idx_popular_searches ON popular_searches(search_count DESC);
```

**Checklist:**
- [ ] Analytics tables created
- [ ] Search tracking implemented
- [ ] Performance metrics table created
- [ ] Popular searches view created
- [ ] Indexes optimized

#### 3.2 Analytics Service
```python
# search_analytics.py
import json
from typing import Dict, List, Optional
import psycopg2
from datetime import datetime, timedelta

class SearchAnalyticsService:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def log_search(self,
                   query: str,
                   query_type: str,
                   results_count: int,
                   response_time_ms: int,
                   session_id: Optional[str] = None,
                   user_id: Optional[str] = None,
                   filters_used: Optional[Dict] = None,
                   ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None):
        """Log a search event"""
        cursor = self.db.cursor()
        
        cursor.execute("""
            INSERT INTO search_analytics 
            (session_id, user_id, query_text, query_type, results_count, 
             response_time_ms, filters_used, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            session_id, user_id, query, query_type, results_count,
            response_time_ms, json.dumps(filters_used) if filters_used else None,
            ip_address, user_agent
        ))
        
        self.db.commit()
        cursor.close()
    
    def log_click(self, search_id: str, document_id: str, position: int):
        """Log a search result click"""
        cursor = self.db.cursor()
        
        # Update clicked_results array
        cursor.execute("""
            UPDATE search_analytics 
            SET clicked_results = COALESCE(clicked_results, '[]'::jsonb) || %s::jsonb
            WHERE id = %s
        """, (json.dumps({'document_id': document_id, 'position': position}), search_id))
        
        self.db.commit()
        cursor.close()
    
    def get_search_metrics(self, days: int = 30) -> Dict:
        """Get search analytics metrics"""
        cursor = self.db.cursor()
        
        since_date = datetime.now() - timedelta(days=days)
        
        # Total searches
        cursor.execute("""
            SELECT COUNT(*) FROM search_analytics 
            WHERE timestamp >= %s
        """, (since_date,))
        total_searches = cursor.fetchone()[0]
        
        # Unique users
        cursor.execute("""
            SELECT COUNT(DISTINCT user_id) FROM search_analytics 
            WHERE timestamp >= %s AND user_id IS NOT NULL
        """, (since_date,))
        unique_users = cursor.fetchone()[0]
        
        # Average response time
        cursor.execute("""
            SELECT AVG(response_time_ms) FROM search_analytics 
            WHERE timestamp >= %s
        """, (since_date,))
        avg_response_time = cursor.fetchone()[0] or 0
        
        # Zero result searches
        cursor.execute("""
            SELECT COUNT(*) FROM search_analytics 
            WHERE timestamp >= %s AND results_count = 0
        """, (since_date,))
        zero_results = cursor.fetchone()[0]
        
        # Popular queries
        cursor.execute("""
            SELECT query_text, COUNT(*) as count
            FROM search_analytics 
            WHERE timestamp >= %s
            GROUP BY query_text
            ORDER BY count DESC
            LIMIT 10
        """, (since_date,))
        popular_queries = cursor.fetchall()
        
        # Search trends (daily)
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as searches
            FROM search_analytics 
            WHERE timestamp >= %s
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (since_date,))
        daily_trends = cursor.fetchall()
        
        cursor.close()
        
        return {
            'total_searches': total_searches,
            'unique_users': unique_users,
            'avg_response_time_ms': round(float(avg_response_time), 2),
            'zero_result_rate': round((zero_results / max(total_searches, 1)) * 100, 2),
            'popular_queries': [{'query': q, 'count': c} for q, c in popular_queries],
            'daily_trends': [{'date': str(d), 'searches': c} for d, c in daily_trends]
        }
    
    def get_query_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get query suggestions based on popular searches"""
        cursor = self.db.cursor()
        
        cursor.execute("""
            SELECT query_text, search_count
            FROM popular_searches
            WHERE query_text ILIKE %s
            ORDER BY search_count DESC
            LIMIT %s
        """, (f"%{partial_query}%", limit))
        
        suggestions = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        return suggestions
```

**Checklist:**
- [ ] Analytics service implemented
- [ ] Search event logging working
- [ ] Click tracking implemented
- [ ] Metrics calculation working
- [ ] Query suggestions implemented

### Step 4: Content Recommendation Engine

#### 4.1 Recommendation Database Schema
```sql
-- Document similarity table
CREATE TABLE document_similarity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    target_document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    similarity_score NUMERIC(5,4) NOT NULL,
    similarity_type VARCHAR(20) NOT NULL, -- 'content', 'categorical', 'collaborative'
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(source_document_id, target_document_id, similarity_type)
);

CREATE INDEX idx_document_similarity_source ON document_similarity(source_document_id, similarity_score DESC);
CREATE INDEX idx_document_similarity_target ON document_similarity(target_document_id, similarity_score DESC);

-- User interaction tracking
CREATE TABLE user_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(100) NOT NULL,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    interaction_type VARCHAR(20) NOT NULL, -- 'view', 'search_click', 'direct_access'
    duration_seconds INTEGER,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_interactions_user ON user_interactions(user_id, timestamp DESC);
CREATE INDEX idx_user_interactions_document ON user_interactions(document_id, timestamp DESC);

-- Recommendation cache
CREATE TABLE recommendation_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cache_key VARCHAR(200) NOT NULL,
    recommendations JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    
    UNIQUE(cache_key)
);

CREATE INDEX idx_recommendation_cache_key ON recommendation_cache(cache_key);
CREATE INDEX idx_recommendation_cache_expires ON recommendation_cache(expires_at);
```

**Checklist:**
- [ ] Similarity tables created
- [ ] User interaction tracking implemented
- [ ] Recommendation cache implemented
- [ ] Indexes optimized for queries
- [ ] Data retention policies set

#### 4.2 Recommendation Service
```python
# recommendation_service.py
import numpy as np
from typing import List, Dict, Tuple, Optional
import psycopg2
from datetime import datetime, timedelta
import json

class RecommendationService:
    def __init__(self, db_connection):
        self.db = db_connection
        self.cache_duration_hours = 6
    
    def calculate_content_similarity(self):
        """Calculate content-based similarity using embeddings"""
        cursor = self.db.cursor()
        
        # Get all documents with embeddings
        cursor.execute("""
            SELECT id, embedding FROM documents 
            WHERE embedding IS NOT NULL AND status = 'active'
        """)
        documents = cursor.fetchall()
        
        # Calculate pairwise similarities
        similarities = []
        for i, (doc1_id, embedding1) in enumerate(documents):
            for j, (doc2_id, embedding2) in enumerate(documents[i+1:], i+1):
                # Calculate cosine similarity
                similarity = 1 - self._cosine_distance(embedding1, embedding2)
                
                if similarity > 0.5:  # Only store meaningful similarities
                    similarities.append((doc1_id, doc2_id, similarity, 'content'))
        
        # Batch insert similarities
        if similarities:
            cursor.executemany("""
                INSERT INTO document_similarity 
                (source_document_id, target_document_id, similarity_score, similarity_type)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (source_document_id, target_document_id, similarity_type)
                DO UPDATE SET similarity_score = EXCLUDED.similarity_score,
                             calculated_at = NOW()
            """, similarities)
        
        self.db.commit()
        cursor.close()
        
        return len(similarities)
    
    def _cosine_distance(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine distance between two vectors"""
        if not vec1 or not vec2:
            return 1.0
        
        # Convert to numpy arrays
        a = np.array(vec1)
        b = np.array(vec2)
        
        # Calculate cosine distance
        return 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    def get_similar_documents(self, 
                            document_id: str, 
                            limit: int = 5,
                            min_similarity: float = 0.6) -> List[Dict]:
        """Get documents similar to the given document"""
        cursor = self.db.cursor()
        
        cursor.execute("""
            SELECT 
                d.id, d.path, d.title, d.description, d.category,
                ds.similarity_score, ds.similarity_type
            FROM document_similarity ds
            JOIN documents d ON ds.target_document_id = d.id
            WHERE ds.source_document_id = %s 
                AND ds.similarity_score >= %s
                AND d.status = 'active'
            ORDER BY ds.similarity_score DESC
            LIMIT %s
        """, (document_id, min_similarity, limit))
        
        results = cursor.fetchall()
        cursor.close()
        
        return [
            {
                'id': row[0],
                'path': row[1],
                'title': row[2],
                'description': row[3],
                'category': row[4],
                'similarity_score': float(row[5]),
                'similarity_type': row[6]
            }
            for row in results
        ]
    
    def get_personalized_recommendations(self, 
                                       user_id: str, 
                                       limit: int = 10) -> List[Dict]:
        """Get personalized recommendations based on user behavior"""
        cache_key = f"recommendations:{user_id}:{limit}"
        
        # Check cache first
        cached = self._get_cached_recommendations(cache_key)
        if cached:
            return cached
        
        cursor = self.db.cursor()
        
        # Get user's recent interactions
        cursor.execute("""
            SELECT document_id, COUNT(*) as interaction_count
            FROM user_interactions
            WHERE user_id = %s 
                AND timestamp >= NOW() - INTERVAL '30 days'
            GROUP BY document_id
            ORDER BY interaction_count DESC
            LIMIT 10
        """, (user_id,))
        
        user_documents = cursor.fetchall()
        
        if not user_documents:
            # New user - return popular documents
            cursor.execute("""
                SELECT d.id, d.path, d.title, d.description, d.category,
                       COUNT(ui.id) as popularity_score
                FROM documents d
                LEFT JOIN user_interactions ui ON d.id = ui.document_id
                WHERE d.status = 'active'
                GROUP BY d.id, d.path, d.title, d.description, d.category
                ORDER BY popularity_score DESC
                LIMIT %s
            """, (limit,))
        else:
            # Get recommendations based on similar documents
            doc_ids = [doc_id for doc_id, _ in user_documents]
            placeholders = ','.join(['%s'] * len(doc_ids))
            
            cursor.execute(f"""
                SELECT 
                    d.id, d.path, d.title, d.description, d.category,
                    AVG(ds.similarity_score) as avg_similarity
                FROM document_similarity ds
                JOIN documents d ON ds.target_document_id = d.id
                WHERE ds.source_document_id IN ({placeholders})
                    AND ds.target_document_id NOT IN ({placeholders})
                    AND d.status = 'active'
                GROUP BY d.id, d.path, d.title, d.description, d.category
                ORDER BY avg_similarity DESC
                LIMIT %s
            """, doc_ids + doc_ids + [limit])
        
        results = cursor.fetchall()
        cursor.close()
        
        recommendations = [
            {
                'id': row[0],
                'path': row[1],
                'title': row[2],
                'description': row[3],
                'category': row[4],
                'score': float(row[5]) if len(row) > 5 else 0.0
            }
            for row in results
        ]
        
        # Cache recommendations
        self._cache_recommendations(cache_key, recommendations)
        
        return recommendations
    
    def track_interaction(self, 
                         user_id: str, 
                         document_id: str, 
                         interaction_type: str,
                         duration_seconds: Optional[int] = None):
        """Track user interaction with document"""
        cursor = self.db.cursor()
        
        cursor.execute("""
            INSERT INTO user_interactions 
            (user_id, document_id, interaction_type, duration_seconds)
            VALUES (%s, %s, %s, %s)
        """, (user_id, document_id, interaction_type, duration_seconds))
        
        self.db.commit()
        cursor.close()
    
    def _get_cached_recommendations(self, cache_key: str) -> Optional[List[Dict]]:
        """Get cached recommendations if they exist and are not expired"""
        cursor = self.db.cursor()
        
        cursor.execute("""
            SELECT recommendations FROM recommendation_cache
            WHERE cache_key = %s AND expires_at > NOW()
        """, (cache_key,))
        
        result = cursor.fetchone()
        cursor.close()
        
        return json.loads(result[0]) if result else None
    
    def _cache_recommendations(self, cache_key: str, recommendations: List[Dict]):
        """Cache recommendations"""
        cursor = self.db.cursor()
        
        expires_at = datetime.now() + timedelta(hours=self.cache_duration_hours)
        
        cursor.execute("""
            INSERT INTO recommendation_cache (cache_key, recommendations, expires_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (cache_key)
            DO UPDATE SET 
                recommendations = EXCLUDED.recommendations,
                created_at = NOW(),
                expires_at = EXCLUDED.expires_at
        """, (cache_key, json.dumps(recommendations), expires_at))
        
        self.db.commit()
        cursor.close()
```

**Checklist:**
- [ ] Content similarity calculation implemented
- [ ] Personalized recommendations working
- [ ] User interaction tracking implemented
- [ ] Recommendation caching working
- [ ] Performance optimized

### Step 5: CLI Enhancement for Advanced Features

#### 5.1 Update CLI with Advanced Features
```bash
# Add to manage_document_md_postgresql

# Action: Advanced search with facets
action_advanced_search() {
    local query="$1"
    shift
    
    local facets=""
    local limit=20
    local format="table"
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --category) facets="$facets&category=$2"; shift 2 ;;
            --author) facets="$facets&author=$2"; shift 2 ;;
            --tag) facets="$facets&tag=$2"; shift 2 ;;
            --date-range) facets="$facets&date_range=$2"; shift 2 ;;
            --limit) limit="$2"; shift 2 ;;
            --format) format="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    
    print_header "Advanced Search: $query"
    
    if ! check_db_connection; then
        return 1
    fi
    
    # Build advanced search query
    local where_conditions=("status = 'active'")
    local params=()
    
    if [ -n "$query" ]; then
        where_conditions+=("search_vector @@ plainto_tsquery('english', %s)")
        params+=("$query")
    fi
    
    # Add facet filters
    if [[ "$facets" == *"category="* ]]; then
        local category=$(echo "$facets" | grep -o 'category=[^&]*' | cut -d= -f2)
        where_conditions+=("category = %s")
        params+=("$category")
    fi
    
    local where_clause=$(IFS=' AND '; echo "${where_conditions[*]}")
    
    # Execute search with facets
    if [ "$format" = "json" ]; then
        # JSON output for API integration
        psql -t -A "$DB_CONN" -c "
            SELECT json_agg(json_build_object(
                'path', path,
                'title', title,
                'description', description,
                'category', category,
                'updated_at', updated_at
            ))
            FROM (
                SELECT path, title, description, category, updated_at
                FROM documents
                WHERE $where_clause
                ORDER BY updated_at DESC
                LIMIT $limit
            ) results
        "
    else
        # Table output
        psql "$DB_CONN" -c "
            SELECT path, title, category, updated_at
            FROM documents
            WHERE $where_clause
            ORDER BY updated_at DESC
            LIMIT $limit
        "
    fi
    
    # Show available facets
    print_info "Available facets:"
    psql "$DB_CONN" -c "
        SELECT 
            'Category' as facet,
            category as value,
            COUNT(*) as count
        FROM documents 
        WHERE status = 'active'
        GROUP BY category
        ORDER BY count DESC
        LIMIT 10
    "
}

# Action: Get search analytics
action_analytics() {
    local days=30
    local format="table"
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --days) days="$2"; shift 2 ;;
            --format) format="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    
    print_header "Search Analytics (Last $days days)"
    
    if ! check_db_connection; then
        return 1
    fi
    
    local since_date=$(date -d "$days days ago" '+%Y-%m-%d')
    
    # Total searches
    local total_searches=$(psql -t -A "$DB_CONN" -c "
        SELECT COUNT(*) FROM search_analytics 
        WHERE timestamp >= '$since_date'
    ")
    
    # Popular queries
    print_info "Popular search queries:"
    psql "$DB_CONN" -c "
        SELECT 
            query_text,
            COUNT(*) as search_count,
            AVG(results_count)::integer as avg_results
        FROM search_analytics 
        WHERE timestamp >= '$since_date'
        GROUP BY query_text
        ORDER BY search_count DESC
        LIMIT 10
    "
    
    # Search trends
    print_info "Daily search trends:"
    psql "$DB_CONN" -c "
        SELECT 
            DATE(timestamp) as date,
            COUNT(*) as searches,
            AVG(response_time_ms)::integer as avg_response_time_ms
        FROM search_analytics 
        WHERE timestamp >= '$since_date'
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        LIMIT 7
    "
    
    print_success "Total searches: $total_searches"
}

# Action: Get recommendations
action_recommendations() {
    local document_id="$1"
    local user_id="$2"
    local limit=5
    
    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --limit) limit="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    
    if [ -n "$document_id" ]; then
        print_header "Similar Documents to: $document_id"
        
        psql "$DB_CONN" -c "
            SELECT 
                d.path,
                d.title,
                ds.similarity_score
            FROM document_similarity ds
            JOIN documents d ON ds.target_document_id = d.id
            WHERE ds.source_document_id = '$document_id'
                AND d.status = 'active'
            ORDER BY ds.similarity_score DESC
            LIMIT $limit
        "
    elif [ -n "$user_id" ]; then
        print_header "Personalized Recommendations for: $user_id"
        
        # This would call the recommendation service
        print_info "Recommendation service integration needed"
    else
        print_error "Either document_id or user_id required"
        return 1
    fi
}

# Update show_usage function
show_usage() {
    cat << EOF
${BOLD}Claude Document Management System (Advanced Search)${NC}

${CYAN}Basic Actions:${NC}
  ${GREEN}init${NC}                     Initialize database schema
  ${GREEN}sync${NC}                     Synchronize files with database
  ${GREEN}search${NC} <query>           Full-text search documents
  ${GREEN}semantic-search${NC} <query>  Semantic similarity search
  ${GREEN}list${NC}                     List documents
  ${GREEN}show${NC} <path|id>           Show document details
  ${GREEN}index${NC}                    Generate doc_index.json

${CYAN}Advanced Search:${NC}
  ${GREEN}advanced-search${NC} <query>  Advanced search with facets
                             Options: --category CAT, --author USER, --tag TAG
                                     --date-range RANGE, --limit N, --format json
  ${GREEN}analytics${NC}                Show search analytics
                             Options: --days N, --format json
  ${GREEN}recommendations${NC} <doc_id> Show similar documents
                             Options: --limit N

${CYAN}Advanced Search Examples:${NC}
  # Search with category filter
  manage_document_md advanced-search "database" --category api --limit 10

  # Search with multiple facets
  manage_document_md advanced-search "authentication" --category security --author admin

  # Get analytics
  manage_document_md analytics --days 7

  # Get similar documents
  manage_document_md recommendations doc-uuid-here --limit 5
EOF
}

# Update main function
main() {
    local action="${1:-help}"
    shift || true
    
    case "$action" in
        # ... existing actions ...
        advanced-search)
            action_advanced_search "$@"
            ;;
        analytics)
            action_analytics "$@"
            ;;
        recommendations)
            action_recommendations "$@"
            ;;
        # ... rest of actions ...
    esac
}
```

**Checklist:**
- [ ] Advanced search CLI implemented
- [ ] Analytics dashboard CLI added
- [ ] Recommendations CLI integrated
- [ ] Faceted search support added
- [ ] JSON output format supported

### Step 6: Testing & Performance Validation

#### 6.1 Advanced Search Testing
```bash
#!/bin/bash
# test_phase3.sh

set -e

print_test() {
    echo "🧪 Testing: $1"
}

print_success() {
    echo "✅ $1"
}

print_error() {
    echo "❌ $1"
    exit 1
}

# Test advanced search features
print_test "Advanced search query parsing"

# Test faceted search
print_test "Faceted search functionality"
result=$(./manage_document_md_postgresql advanced-search "test" --category api --format json)
if [[ "$result" == *"path"* ]]; then
    print_success "Faceted search working"
else
    print_error "Faceted search failed"
fi

# Test analytics
print_test "Search analytics"
./manage_document_md_postgresql analytics --days 7 > /dev/null
if [ $? -eq 0 ]; then
    print_success "Analytics working"
else
    print_error "Analytics failed"
fi

# Test recommendations
print_test "Document recommendations"
# First get a document ID
doc_id=$(psql -t -A "$DB_CONN" -c "SELECT id FROM documents LIMIT 1")
if [ -n "$doc_id" ]; then
    ./manage_document_md_postgresql recommendations "$doc_id" --limit 3
    print_success "Recommendations working"
else
    print_error "No documents found for recommendations test"
fi

print_success "Phase 3 testing completed successfully"
```

**Checklist:**
- [ ] Testing script created
- [ ] Advanced search tested
- [ ] Faceted search validated
- [ ] Analytics functionality tested
- [ ] Recommendations tested
- [ ] Performance benchmarks met

## Phase 3 Completion Criteria

### Technical Completion
- [ ] Advanced query language implemented
- [ ] Faceted search working with multiple facets
- [ ] Search analytics tracking all events
- [ ] Content recommendations generated
- [ ] Performance meets requirements (<300ms for complex queries)

### Quality Assurance
- [ ] All advanced search features tested
- [ ] Analytics accuracy validated
- [ ] Recommendation quality assessed
- [ ] Performance benchmarks met
- [ ] User interface intuitive

### Success Metrics
- [ ] Advanced search adoption > 60%
- [ ] Search satisfaction score > 4.0/5.0
- [ ] Analytics dashboard usage > 80%
- [ ] Recommendation click-through rate > 15%

This completes the detailed Phase 3 implementation guide with comprehensive advanced search and analytics capabilities.