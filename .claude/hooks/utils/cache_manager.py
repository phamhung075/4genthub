#!/usr/bin/env python3
"""
Cache Manager Module for MCP Session Context

This module provides caching capabilities for MCP session data with intelligent
cache invalidation, fallback strategies, and performance optimization.

Task ID: f6a4bd18-c48a-498a-9702-c8118996b8fe (Phase 1.3)
Architecture Reference: Session Hook Enhancement
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from threading import Lock

# Configure logging
logger = logging.getLogger(__name__)

class CacheManager:
    """Manages caching for session context data with smart invalidation."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize cache manager with configurable cache directory."""
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".claude" / ".session_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        
        # Configuration from environment
        self.default_ttl = int(os.getenv("SESSION_CACHE_TTL", "3600"))  # 1 hour
        self.max_cache_size = int(os.getenv("SESSION_CACHE_MAX_SIZE", "50"))  # 50 MB
        self.cleanup_interval = int(os.getenv("CACHE_CLEANUP_INTERVAL", "86400"))  # 24 hours
        
    def get(self, key: str, ttl: Optional[int] = None) -> Optional[Any]:
        """Get cached data by key with TTL check."""
        ttl = ttl or self.default_ttl
        cache_file = self.cache_dir / f"{self._hash_key(key)}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with self.lock:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # Check if cache is still valid
                cached_time = cache_data.get("timestamp", 0)
                if (time.time() - cached_time) < ttl:
                    logger.debug(f"Cache hit for key: {key}")
                    return cache_data.get("data")
                else:
                    logger.debug(f"Cache expired for key: {key}")
                    # Clean up expired cache
                    cache_file.unlink(missing_ok=True)
                    return None
                    
        except Exception as e:
            logger.warning(f"Failed to read cache for key {key}: {e}")
            return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Cache data with key and optional TTL."""
        ttl = ttl or self.default_ttl
        cache_file = self.cache_dir / f"{self._hash_key(key)}.json"
        
        try:
            with self.lock:
                cache_data = {
                    "key": key,
                    "timestamp": time.time(),
                    "ttl": ttl,
                    "data": data
                }
                
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2, default=str)
                
                logger.debug(f"Cached data for key: {key}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cache data for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete cached data by key."""
        cache_file = self.cache_dir / f"{self._hash_key(key)}.json"
        
        try:
            with self.lock:
                cache_file.unlink(missing_ok=True)
                logger.debug(f"Deleted cache for key: {key}")
                return True
        except Exception as e:
            logger.warning(f"Failed to delete cache for key {key}: {e}")
            return False
    
    def clear_all(self) -> bool:
        """Clear all cached data."""
        try:
            with self.lock:
                for cache_file in self.cache_dir.glob("*.json"):
                    cache_file.unlink(missing_ok=True)
                logger.info("Cleared all cache data")
                return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """Clean up expired cache entries and return count of deleted files."""
        deleted_count = 0
        current_time = time.time()
        
        try:
            with self.lock:
                for cache_file in self.cache_dir.glob("*.json"):
                    try:
                        with open(cache_file, 'r') as f:
                            cache_data = json.load(f)
                        
                        cached_time = cache_data.get("timestamp", 0)
                        ttl = cache_data.get("ttl", self.default_ttl)
                        
                        if (current_time - cached_time) >= ttl:
                            cache_file.unlink()
                            deleted_count += 1
                            
                    except Exception as e:
                        logger.warning(f"Failed to check cache file {cache_file}: {e}")
                        # Delete corrupted cache files
                        cache_file.unlink(missing_ok=True)
                        deleted_count += 1
                        
            logger.info(f"Cleaned up {deleted_count} expired cache entries")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired cache: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "cache_dir": str(self.cache_dir),
            "total_files": 0,
            "total_size_bytes": 0,
            "expired_files": 0,
            "valid_files": 0
        }
        
        current_time = time.time()
        
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                stats["total_files"] += 1
                stats["total_size_bytes"] += cache_file.stat().st_size
                
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    
                    cached_time = cache_data.get("timestamp", 0)
                    ttl = cache_data.get("ttl", self.default_ttl)
                    
                    if (current_time - cached_time) >= ttl:
                        stats["expired_files"] += 1
                    else:
                        stats["valid_files"] += 1
                        
                except Exception:
                    stats["expired_files"] += 1
                    
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            
        return stats
    
    def _hash_key(self, key: str) -> str:
        """Generate a safe filename from cache key."""
        import hashlib
        return hashlib.md5(key.encode('utf-8')).hexdigest()


class SessionContextCache(CacheManager):
    """Specialized cache manager for session context data."""
    
    def __init__(self):
        super().__init__(cache_dir=str(Path.home() / ".claude" / ".session_context_cache"))
        
        # Session-specific cache keys
        self.PENDING_TASKS_KEY = "mcp_pending_tasks"
        self.NEXT_TASK_KEY = "mcp_next_task_{branch_id}"
        self.PROJECT_CONTEXT_KEY = "project_context_{branch_id}"
        self.GIT_STATUS_KEY = "git_status"
        
        # Short TTL for dynamic data
        self.task_cache_ttl = int(os.getenv("TASK_CACHE_TTL", "900"))  # 15 minutes
        self.git_cache_ttl = int(os.getenv("GIT_CACHE_TTL", "300"))   # 5 minutes
    
    def cache_pending_tasks(self, tasks: List[Dict]) -> bool:
        """Cache pending tasks with short TTL."""
        return self.set(self.PENDING_TASKS_KEY, tasks, self.task_cache_ttl)
    
    def get_pending_tasks(self) -> Optional[List[Dict]]:
        """Get cached pending tasks."""
        return self.get(self.PENDING_TASKS_KEY, self.task_cache_ttl)
    
    def cache_next_task(self, branch_id: str, task: Dict) -> bool:
        """Cache next recommended task for branch."""
        key = self.NEXT_TASK_KEY.format(branch_id=branch_id)
        return self.set(key, task, self.task_cache_ttl)
    
    def get_next_task(self, branch_id: str) -> Optional[Dict]:
        """Get cached next task for branch."""
        key = self.NEXT_TASK_KEY.format(branch_id=branch_id)
        return self.get(key, self.task_cache_ttl)
    
    def cache_git_status(self, git_data: Dict) -> bool:
        """Cache git status information."""
        return self.set(self.GIT_STATUS_KEY, git_data, self.git_cache_ttl)
    
    def get_git_status(self) -> Optional[Dict]:
        """Get cached git status."""
        return self.get(self.GIT_STATUS_KEY, self.git_cache_ttl)
    
    def cache_project_context(self, branch_id: str, context: Dict) -> bool:
        """Cache project context for branch."""
        key = self.PROJECT_CONTEXT_KEY.format(branch_id=branch_id)
        return self.set(key, context, self.default_ttl)
    
    def get_project_context(self, branch_id: str) -> Optional[Dict]:
        """Get cached project context."""
        key = self.PROJECT_CONTEXT_KEY.format(branch_id=branch_id)
        return self.get(key, self.default_ttl)


# Factory function for easy usage
def get_session_cache() -> SessionContextCache:
    """Get session context cache instance."""
    return SessionContextCache()


# CLI for cache management
def main():
    """CLI interface for cache management."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Session Cache Manager")
    parser.add_argument('--stats', action='store_true', help='Show cache statistics')
    parser.add_argument('--cleanup', action='store_true', help='Clean expired cache entries')
    parser.add_argument('--clear', action='store_true', help='Clear all cache data')
    parser.add_argument('--test', action='store_true', help='Test cache functionality')
    
    args = parser.parse_args()
    
    cache = get_session_cache()
    
    if args.stats:
        stats = cache.get_cache_stats()
        print(json.dumps(stats, indent=2))
    
    if args.cleanup:
        count = cache.cleanup_expired()
        print(f"Cleaned up {count} expired entries")
    
    if args.clear:
        cache.clear_all()
        print("Cache cleared")
    
    if args.test:
        # Test cache functionality
        print("Testing cache functionality...")
        
        # Test set/get
        test_data = {"test": "data", "timestamp": datetime.now().isoformat()}
        cache.set("test_key", test_data, 60)
        retrieved = cache.get("test_key")
        
        if retrieved and retrieved["test"] == "data":
            print("✅ Cache set/get works")
        else:
            print("❌ Cache set/get failed")
        
        # Test specialized methods
        cache.cache_pending_tasks([{"task": "test"}])
        tasks = cache.get_pending_tasks()
        
        if tasks and tasks[0]["task"] == "test":
            print("✅ Task caching works")
        else:
            print("❌ Task caching failed")
        
        print("Cache test completed")


if __name__ == "__main__":
    main()