"""
Database Adapter for SQLite/PostgreSQL compatibility

Handles JSON operations across different database engines.
"""

import json
import logging
from typing import Any, Dict, Optional
from contextlib import contextmanager
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from .session_manager import get_session

logger = logging.getLogger(__name__)


class DatabaseAdapter:
    """Database adapter that handles SQLite/PostgreSQL differences."""
    
    def __init__(self, engine: Engine):
        self.engine = engine
        self.is_postgresql = engine.dialect.name == 'postgresql'
        self.is_sqlite = engine.dialect.name == 'sqlite'
    
    def json_extract(self, column: str, path: str) -> str:
        """Generate JSON extract expression for different databases."""
        if self.is_postgresql:
            # PostgreSQL: column->>'path' or column->'path'
            return f"{column}->>{path!r}"
        elif self.is_sqlite:
            # SQLite: JSON_EXTRACT(column, '$.path')
            return f"JSON_EXTRACT({column}, '$.{path}')"
        else:
            raise NotImplementedError(f"JSON extract not implemented for {self.engine.dialect.name}")
    
    def json_set(self, column: str, path: str, value: Any) -> str:
        """Generate JSON set expression for different databases."""
        json_value = json.dumps(value)
        
        if self.is_postgresql:
            # PostgreSQL: jsonb_set(column, '{path}', '"value"')
            return f"jsonb_set({column}, '{{{path}}}', {json_value!r})"
        elif self.is_sqlite:
            # SQLite: JSON_SET(column, '$.path', 'value')
            return f"JSON_SET({column}, '$.{path}', {json_value!r})"
        else:
            raise NotImplementedError(f"JSON set not implemented for {self.engine.dialect.name}")
    
    def json_merge(self, column: str, new_data: Dict[str, Any]) -> str:
        """Generate JSON merge expression for different databases."""
        json_data = json.dumps(new_data)
        
        if self.is_postgresql:
            # PostgreSQL: column || '{"new": "data"}'::jsonb
            return f"{column} || {json_data!r}::jsonb"
        elif self.is_sqlite:
            # SQLite: JSON_PATCH(column, '{"new": "data"}')
            return f"JSON_PATCH({column}, {json_data!r})"
        else:
            raise NotImplementedError(f"JSON merge not implemented for {self.engine.dialect.name}")
    
    def prepare_json_value(self, value: Any) -> str:
        """Prepare a value for JSON storage."""
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)
    
    def parse_json_value(self, value: Optional[str]) -> Any:
        """Parse a JSON value from database."""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    
    def create_json_contains_condition(self, column: str, search_dict: Dict[str, Any]) -> str:
        """Create a condition to check if JSON contains specific key-value pairs."""
        if self.is_postgresql:
            # PostgreSQL: column @> '{"key": "value"}'::jsonb
            search_json = json.dumps(search_dict)
            return f"{column} @> {search_json!r}::jsonb"
        elif self.is_sqlite:
            # SQLite: Multiple JSON_EXTRACT checks
            conditions = []
            for key, value in search_dict.items():
                json_value = json.dumps(value)
                conditions.append(f"JSON_EXTRACT({column}, '$.{key}') = {json_value!r}")
            return " AND ".join(conditions)
        else:
            raise NotImplementedError(f"JSON contains not implemented for {self.engine.dialect.name}")
    
    def get_json_keys(self, column: str) -> str:
        """Get all keys from a JSON object."""
        if self.is_postgresql:
            # PostgreSQL: jsonb_object_keys(column)
            return f"jsonb_object_keys({column})"
        elif self.is_sqlite:
            # SQLite: This is more complex, would need custom function
            # For now, return a placeholder
            return f"'not_implemented_for_sqlite'"
        else:
            raise NotImplementedError(f"JSON keys not implemented for {self.engine.dialect.name}")
    
    def execute_with_json_result(self, query: str, params: Optional[Dict] = None) -> Any:
        """Execute query and parse JSON results."""
        with self.engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            rows = result.fetchall()
            
            # Convert rows to dictionaries and parse JSON fields
            parsed_rows = []
            for row in rows:
                row_dict = dict(row._mapping)
                # Parse JSON fields
                for key, value in row_dict.items():
                    if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                        try:
                            row_dict[key] = json.loads(value)
                        except json.JSONDecodeError:
                            pass  # Keep as string if not valid JSON
                parsed_rows.append(row_dict)
            
            return parsed_rows
    
    def get_schema_type(self) -> str:
        """Get the appropriate schema type for JSON fields."""
        if self.is_postgresql:
            return "JSONB"
        elif self.is_sqlite:
            return "TEXT"
        else:
            return "TEXT"
    
    def migrate_to_postgresql(self, sqlite_db_path: str, postgresql_url: str):
        """Migrate data from SQLite to PostgreSQL (for Supabase migration)."""
        # This would be implemented when you're ready to migrate
        pass
    
    @contextmanager
    def get_session(self):
        """Get a database session context manager.
        
        This method provides compatibility for ORM repositories that expect
        the DatabaseAdapter to provide session management.
        """
        with get_session() as session:
            yield session