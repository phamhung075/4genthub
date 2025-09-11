"""
MCP HTTP Client Module - Authentication, Connection Pooling, and Resilience

This module implements HTTP clients for communicating with the MCP server with
authentication, connection pooling, rate limiting, and resilience features.

Architecture Reference: Section 15.2 in mcp-auto-injection-architecture.md
Task ID: bd70c110-c43b-4ec9-b5bc-61cdb03a0833
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logger = logging.getLogger(__name__)


class TokenManager:
    """Manages JWT tokens for hook-to-MCP communication with automatic refresh."""
    
    def __init__(self):
        self.token_cache_file = Path.home() / ".claude" / ".mcp_token_cache"
        self.token = None
        self.token_expiry = None
        self.refresh_before = int(os.getenv("TOKEN_REFRESH_BEFORE_EXPIRY", "60"))
        self.keycloak_config = {
            "url": os.getenv("KEYCLOAK_URL", "http://localhost:8080"),
            "realm": os.getenv("KEYCLOAK_REALM", "dhafnck"),
            "client_id": os.getenv("KEYCLOAK_CLIENT_ID", "claude-hooks"),
            "client_secret": os.getenv("KEYCLOAK_CLIENT_SECRET")
        }
    
    def get_valid_token(self) -> Optional[str]:
        """Get a valid JWT token, refreshing if needed."""
        
        # Check if token needs refresh
        if self._should_refresh():
            self._refresh_token()
        
        return self.token
    
    def _should_refresh(self) -> bool:
        """Check if token should be refreshed."""
        if not self.token or not self.token_expiry:
            return True
        
        time_until_expiry = self.token_expiry.timestamp() - time.time()
        return time_until_expiry < self.refresh_before
    
    def _refresh_token(self):
        """Refresh token using client credentials."""
        
        # Try to load from cache file first
        if self._load_cached_token():
            return
        
        # Get new token from Keycloak
        self._request_new_token()
    
    def _load_cached_token(self) -> bool:
        """Load token from cache if valid."""
        if not self.token_cache_file.exists():
            return False
        
        try:
            with open(self.token_cache_file, 'r') as f:
                cache_data = json.load(f)
                expiry = datetime.fromisoformat(cache_data["expiry"])
                
                if datetime.now() < expiry - timedelta(seconds=self.refresh_before):
                    self.token = cache_data["token"]
                    self.token_expiry = expiry
                    return True
        except Exception as e:
            logger.warning(f"Failed to load cached token: {e}")
        
        return False
    
    def _request_new_token(self) -> bool:
        """Request new token from Keycloak."""
        if not self.keycloak_config["client_secret"]:
            logger.warning("No Keycloak client secret configured")
            return False
        
        try:
            response = requests.post(
                f"{self.keycloak_config['url']}/auth/realms/{self.keycloak_config['realm']}/protocol/openid-connect/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.keycloak_config["client_id"],
                    "client_secret": self.keycloak_config["client_secret"]
                },
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                
                # Cache token
                self._cache_token()
                return True
            else:
                logger.error(f"Token request failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to get token: {e}")
        return False
    
    def _cache_token(self):
        """Cache token to file for reuse."""
        try:
            self.token_cache_file.parent.mkdir(exist_ok=True)
            with open(self.token_cache_file, 'w') as f:
                json.dump({
                    "token": self.token,
                    "expiry": self.token_expiry.isoformat()
                }, f)
            # Secure the file
            os.chmod(self.token_cache_file, 0o600)
        except Exception as e:
            logger.warning(f"Failed to cache token: {e}")


class RateLimiter:
    """Simple rate limiter for HTTP requests."""
    
    def __init__(self, max_requests: int = 100, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def allow_request(self) -> bool:
        """Check if request is allowed under rate limit."""
        current_time = time.time()
        
        # Remove old requests outside time window
        self.requests = [req_time for req_time in self.requests 
                        if current_time - req_time < self.time_window]
        
        # Check if under limit
        if len(self.requests) < self.max_requests:
            self.requests.append(current_time)
            return True
        
        return False


class MCPHTTPClient:
    """HTTP client for communicating with MCP server."""
    
    def __init__(self):
        self.base_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        self.token_manager = TokenManager()
        self.session = requests.Session()
        self.timeout = int(os.getenv("MCP_SERVER_TIMEOUT", "10"))
        
        # Configure session
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Claude-Hooks-MCP-Client/1.0"
        })
    
    def authenticate(self) -> bool:
        """Authenticate with Keycloak and get JWT token."""
        token = self.token_manager.get_valid_token()
        if token:
            self.session.headers.update({
                "Authorization": f"Bearer {token}"
            })
            return True
        return False
    
    def query_pending_tasks(self, limit: int = 5, user_id: Optional[str] = None) -> Optional[List[Dict]]:
        """Query MCP server for pending tasks via HTTP."""
        if not self.authenticate():
            logger.warning("Authentication failed, cannot query tasks")
            return None
        
        try:
            payload = {
                "action": "list",
                "status": "todo",
                "limit": limit
            }
            if user_id:
                payload["user_id"] = user_id
            
            response = self.session.post(
                f"{self.base_url}/mcp/manage_task",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return result.get("data", {}).get("tasks", [])
            else:
                logger.warning(f"Task query failed: {response.status_code}")
        except Exception as e:
            logger.warning(f"Failed to query tasks: {e}")
        
        return None
    
    def get_next_recommended_task(self, git_branch_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Get next recommended task via HTTP."""
        if not self.authenticate():
            return None
        
        try:
            payload = {
                "action": "next",
                "git_branch_id": git_branch_id,
                "include_context": True
            }
            if user_id:
                payload["user_id"] = user_id
            
            response = self.session.post(
                f"{self.base_url}/mcp/manage_task",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    return result.get("data", {}).get("task")
        except Exception as e:
            logger.warning(f"Failed to get next task: {e}")
        
        return None
    
    def make_request(self, endpoint: str, payload: dict) -> Optional[dict]:
        """Make authenticated HTTP request to MCP server."""
        if not self.authenticate():
            return None
        
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 401:
                # Token expired, try to refresh and retry once
                logger.info("Token expired, attempting refresh")
                self.token_manager._request_new_token()
                if self.authenticate():
                    response = self.session.post(
                        f"{self.base_url}{endpoint}",
                        json=payload,
                        timeout=self.timeout
                    )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Request failed: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
        
        return None


class ResilientMCPClient(MCPHTTPClient):
    """HTTP client with fallback strategies for MCP server issues."""
    
    def __init__(self):
        super().__init__()
        self.fallback_cache = Path.home() / ".claude" / ".mcp_fallback_cache.json"
        self.cache_ttl = int(os.getenv("FALLBACK_CACHE_TTL", "3600"))  # 1 hour
        self.fallback_strategy = os.getenv("FALLBACK_STRATEGY", "cache_then_skip")
    
    def query_with_fallback(self, query_func, *args, **kwargs) -> Optional[Any]:
        """Query MCP with multiple fallback strategies."""
        
        # Strategy 1: Try primary MCP server
        try:
            result = query_func(*args, **kwargs)
            if result is not None:
                self._cache_fallback_data(result)
                return result
        except (requests.ConnectionError, requests.Timeout, requests.RequestException):
            logger.warning("MCP server unavailable, trying fallbacks")
        
        # Strategy 2: Use cached data if recent
        if self.fallback_strategy in ["cache_then_skip", "cache_then_error"]:
            cached_data = self._get_cached_fallback()
            if cached_data and self._is_cache_valid(cached_data):
                logger.info("Using cached MCP data")
                return cached_data.get("data")
        
        # Strategy 3: Handle based on strategy
        if self.fallback_strategy == "cache_then_skip":
            logger.warning("All MCP queries failed, continuing without injection")
            return None
        elif self.fallback_strategy == "skip":
            return None
        else:  # error strategy
            raise ConnectionError("MCP server unavailable and no valid fallback data")
    
    def query_pending_tasks(self, limit: int = 5, user_id: Optional[str] = None) -> Optional[List[Dict]]:
        """Query pending tasks with fallback strategies."""
        return self.query_with_fallback(
            super().query_pending_tasks,
            limit=limit,
            user_id=user_id
        )
    
    def get_next_recommended_task(self, git_branch_id: str, user_id: Optional[str] = None) -> Optional[Dict]:
        """Get next recommended task with fallback strategies."""
        return self.query_with_fallback(
            super().get_next_recommended_task,
            git_branch_id=git_branch_id,
            user_id=user_id
        )
    
    def _cache_fallback_data(self, data: Any):
        """Cache data for fallback use."""
        try:
            self.fallback_cache.parent.mkdir(exist_ok=True)
            cache_data = {
                "timestamp": time.time(),
                "data": data
            }
            with open(self.fallback_cache, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Failed to cache fallback data: {e}")
    
    def _get_cached_fallback(self) -> Optional[Dict]:
        """Get cached fallback data."""
        if not self.fallback_cache.exists():
            return None
        
        try:
            with open(self.fallback_cache, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cached fallback data: {e}")
            return None
    
    def _is_cache_valid(self, cache_data: Dict) -> bool:
        """Check if cached data is recent enough."""
        cache_time = cache_data.get("timestamp", 0)
        return (time.time() - cache_time) < self.cache_ttl


class OptimizedMCPClient(ResilientMCPClient):
    """HTTP client with connection pooling and rate limiting."""
    
    def __init__(self):
        super().__init__()
        self.rate_limiter = RateLimiter(
            max_requests=int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "100")),
            time_window=60
        )
        
        # Configure connection pooling with retry strategy
        retry_strategy = Retry(
            total=int(os.getenv("HTTP_MAX_RETRIES", "3")),
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"],
            backoff_factor=1
        )
        
        adapter = HTTPAdapter(
            pool_connections=int(os.getenv("HTTP_POOL_CONNECTIONS", "10")),
            pool_maxsize=int(os.getenv("HTTP_POOL_MAXSIZE", "10")),
            max_retries=retry_strategy,
            pool_block=False
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def make_request(self, endpoint: str, payload: dict) -> Optional[dict]:
        """Make rate-limited request with connection pooling."""
        
        # Check rate limit
        if not self.rate_limiter.allow_request():
            logger.warning("Rate limit exceeded, request throttled")
            return None
        
        # Use parent class method with enhanced session
        return super().make_request(endpoint, payload)


# Convenience functions for easy import
def create_mcp_client(client_type: str = "optimized") -> MCPHTTPClient:
    """Factory function to create MCP client instances."""
    
    if client_type == "basic":
        return MCPHTTPClient()
    elif client_type == "resilient":
        return ResilientMCPClient()
    elif client_type == "optimized":
        return OptimizedMCPClient()
    else:
        raise ValueError(f"Unknown client type: {client_type}")


def get_default_client() -> OptimizedMCPClient:
    """Get default optimized MCP client."""
    return OptimizedMCPClient()


# Example usage and testing functions
def test_mcp_connection() -> bool:
    """Test MCP server connection."""
    client = get_default_client()
    
    try:
        # Test authentication
        if not client.authenticate():
            print("❌ Authentication failed")
            return False
        
        print("✅ Authentication successful")
        
        # Test basic connection
        result = client.make_request("/mcp/manage_connection", {"include_details": True})
        if result:
            print("✅ MCP server connection successful")
            return True
        else:
            print("❌ MCP server connection failed")
            return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Run connection test when executed directly
    print("🔌 Testing MCP HTTP Client Connection...")
    success = test_mcp_connection()
    exit(0 if success else 1)