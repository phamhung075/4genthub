# MCP HTTP Client Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting information for the MCP HTTP Client Module, including common issues, diagnostic tools, performance optimization, and recovery procedures.

## Table of Contents

- [Common Issues](#common-issues)
- [Diagnostic Tools](#diagnostic-tools)
- [Error Analysis](#error-analysis)
- [Performance Troubleshooting](#performance-troubleshooting)
- [Network Issues](#network-issues)
- [Authentication Problems](#authentication-problems)
- [Cache Issues](#cache-issues)
- [Recovery Procedures](#recovery-procedures)
- [Monitoring and Logging](#monitoring-and-logging)

---

## Common Issues

### Authentication Failures

#### Issue: "Authentication failed, cannot query tasks"

**Symptoms:**
- Client cannot authenticate with Keycloak
- Error messages about invalid credentials
- No "Authorization" header in requests

**Common Causes:**
1. **Invalid client credentials**
2. **Keycloak server unavailable**
3. **Incorrect realm or client configuration**
4. **Network connectivity issues**

**Diagnosis:**
```bash
# Check environment variables
echo "KEYCLOAK_URL: $KEYCLOAK_URL"
echo "KEYCLOAK_REALM: $KEYCLOAK_REALM" 
echo "KEYCLOAK_CLIENT_ID: $KEYCLOAK_CLIENT_ID"
echo "KEYCLOAK_CLIENT_SECRET: [Set: $([ -n "$KEYCLOAK_CLIENT_SECRET" ] && echo 'Yes' || echo 'No')]"

# Test Keycloak connectivity
curl -f "$KEYCLOAK_URL/auth/realms/$KEYCLOAK_REALM/.well-known/openid-configuration"

# Test client credentials
curl -X POST "$KEYCLOAK_URL/auth/realms/$KEYCLOAK_REALM/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=$KEYCLOAK_CLIENT_ID&client_secret=$KEYCLOAK_CLIENT_SECRET"
```

**Solutions:**
1. **Verify credentials in Keycloak Admin Console**
2. **Check client configuration** (service accounts enabled)
3. **Verify network connectivity** to Keycloak
4. **Check firewall rules** and DNS resolution

```python
# Test authentication programmatically
from utils.mcp_client import TokenManager

def debug_authentication():
    token_manager = TokenManager()
    
    print("🔑 Testing token acquisition...")
    token = token_manager.get_valid_token()
    
    if token:
        print(f"✅ Token acquired: {token[:20]}...")
    else:
        print("❌ Token acquisition failed")
        
        # Check configuration
        config = token_manager.keycloak_config
        print(f"Keycloak URL: {config['url']}")
        print(f"Realm: {config['realm']}")
        print(f"Client ID: {config['client_id']}")
        print(f"Client Secret: {'Set' if config['client_secret'] else 'Not set'}")

debug_authentication()
```

### Connection Timeouts

#### Issue: "Request timeout" or "Connection timed out"

**Symptoms:**
- Slow or hanging requests
- Timeout exceptions in logs
- Intermittent connection failures

**Common Causes:**
1. **Network latency or congestion**
2. **Server overload**
3. **Inappropriate timeout settings**
4. **DNS resolution delays**

**Diagnosis:**
```bash
# Test network connectivity
ping $(echo $MCP_SERVER_URL | sed 's|http[s]*://||' | cut -d: -f1)

# Test HTTP connectivity with timing
curl -w "@curl-format.txt" -o /dev/null -s "$MCP_SERVER_URL/mcp/manage_connection"

# Create curl-format.txt:
cat > curl-format.txt << 'EOF'
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF
```

**Solutions:**
1. **Increase timeout values** in environment variables
2. **Check network infrastructure**
3. **Implement retry logic** with exponential backoff
4. **Use connection pooling** for better efficiency

```python
# Timeout configuration example
import os

# Increase timeouts for slow networks
os.environ.update({
    'MCP_SERVER_TIMEOUT': '30',  # Increased from 10
    'HTTP_MAX_RETRIES': '5',     # More retries
})

from utils.mcp_client import get_default_client
client = get_default_client()
```

### Server Unavailability

#### Issue: "MCP server unavailable" or "Connection refused"

**Symptoms:**
- Cannot connect to MCP server
- Connection refused errors
- No response from server

**Common Causes:**
1. **MCP server not running**
2. **Incorrect server URL**
3. **Port conflicts or firewall blocking**
4. **Server overload or crash**

**Diagnosis:**
```bash
# Check if server is running
curl -f "$MCP_SERVER_URL/mcp/manage_connection" || echo "Server not responding"

# Check port availability
nc -zv $(echo $MCP_SERVER_URL | sed 's|http[s]*://||' | cut -d: -f1) $(echo $MCP_SERVER_URL | sed 's|.*:||')

# Check server logs
docker logs mcp-server-container 2>&1 | tail -50
```

**Solutions:**
1. **Start MCP server** if not running
2. **Verify server URL** and port configuration
3. **Check firewall rules** and network policies
4. **Enable fallback strategy** for resilience

```python
# Enable fallback for server unavailability
import os
os.environ['FALLBACK_STRATEGY'] = 'cache_then_skip'

from utils.mcp_client import ResilientMCPClient
client = ResilientMCPClient()

# This will use cache if server unavailable
tasks = client.query_pending_tasks()
```

---

## Diagnostic Tools

### Connection Test Utility

```python
#!/usr/bin/env python3
"""
Comprehensive MCP client diagnostics tool
"""

import os
import json
import requests
from datetime import datetime
from utils.mcp_client import get_default_client, test_mcp_connection
from utils.cache_manager import get_session_cache

def run_diagnostics():
    """Run comprehensive diagnostics"""
    print("🔍 MCP Client Diagnostics")
    print("=" * 50)
    
    # Environment check
    print("\n1. Environment Configuration:")
    env_vars = [
        'MCP_SERVER_URL', 'MCP_SERVER_TIMEOUT',
        'KEYCLOAK_URL', 'KEYCLOAK_REALM',
        'KEYCLOAK_CLIENT_ID', 'KEYCLOAK_CLIENT_SECRET',
        'FALLBACK_STRATEGY', 'FALLBACK_CACHE_TTL'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if var == 'KEYCLOAK_CLIENT_SECRET':
            display_value = 'Set' if value else 'Not set'
        else:
            display_value = value or 'Not set'
        print(f"   {var}: {display_value}")
    
    # Network connectivity
    print("\n2. Network Connectivity:")
    
    # Test Keycloak connectivity
    keycloak_url = os.getenv('KEYCLOAK_URL')
    if keycloak_url:
        try:
            response = requests.get(f"{keycloak_url}/auth/realms/master", timeout=5)
            print(f"   ✅ Keycloak reachable: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Keycloak unreachable: {e}")
    
    # Test MCP server connectivity
    mcp_url = os.getenv('MCP_SERVER_URL')
    if mcp_url:
        try:
            response = requests.get(f"{mcp_url}/mcp/manage_connection", timeout=5)
            print(f"   ✅ MCP server reachable: {response.status_code}")
        except Exception as e:
            print(f"   ❌ MCP server unreachable: {e}")
    
    # Authentication test
    print("\n3. Authentication Test:")
    try:
        client = get_default_client()
        if client.authenticate():
            print("   ✅ Authentication successful")
        else:
            print("   ❌ Authentication failed")
    except Exception as e:
        print(f"   ❌ Authentication error: {e}")
    
    # MCP functionality test
    print("\n4. MCP Functionality:")
    success = test_mcp_connection()
    if success:
        print("   ✅ Full MCP test successful")
    else:
        print("   ❌ MCP test failed")
    
    # Cache diagnostics
    print("\n5. Cache Status:")
    try:
        cache = get_session_cache()
        stats = cache.get_cache_stats()
        print(f"   Cache directory: {stats['cache_dir']}")
        print(f"   Total files: {stats['total_files']}")
        print(f"   Valid files: {stats['valid_files']}")
        print(f"   Expired files: {stats['expired_files']}")
        print(f"   Total size: {stats['total_size_bytes']} bytes")
    except Exception as e:
        print(f"   ❌ Cache error: {e}")
    
    # Performance test
    print("\n6. Performance Test:")
    try:
        import time
        start_time = time.time()
        
        client = get_default_client()
        tasks = client.query_pending_tasks(limit=5)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        if tasks is not None:
            print(f"   ✅ Query successful: {len(tasks)} tasks in {response_time:.2f}s")
        else:
            print(f"   ⚠️ Query returned no data in {response_time:.2f}s")
    except Exception as e:
        print(f"   ❌ Performance test error: {e}")

if __name__ == "__main__":
    run_diagnostics()
```

### Token Diagnostics

```python
def diagnose_token_issues():
    """Diagnose token-related issues"""
    from utils.mcp_client import TokenManager
    import jwt
    import json
    
    print("🔑 Token Diagnostics")
    print("=" * 30)
    
    token_manager = TokenManager()
    
    # Check cached token
    cache_file = token_manager.token_cache_file
    print(f"Cache file: {cache_file}")
    print(f"Cache exists: {cache_file.exists()}")
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            token = cache_data.get('token')
            expiry = cache_data.get('expiry')
            
            print(f"Cached token expiry: {expiry}")
            
            # Decode token (without verification)
            if token:
                try:
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    print(f"Token subject: {decoded.get('sub')}")
                    print(f"Token client: {decoded.get('azp')}")
                    print(f"Token expiry (JWT): {decoded.get('exp')}")
                    print(f"Token issued at: {decoded.get('iat')}")
                except Exception as e:
                    print(f"Token decode error: {e}")
                    
        except Exception as e:
            print(f"Cache read error: {e}")
    
    # Test token refresh
    print("\nTesting token refresh:")
    token = token_manager.get_valid_token()
    if token:
        print("✅ Token refresh successful")
    else:
        print("❌ Token refresh failed")

# Run token diagnostics
diagnose_token_issues()
```

---

## Error Analysis

### HTTP Error Codes

#### 401 Unauthorized
```python
def handle_401_error(response):
    """Handle 401 authentication errors"""
    print("🔒 Authentication Error (401)")
    
    try:
        error_data = response.json()
        error_type = error_data.get('error', 'unknown')
        
        if error_type == 'invalid_token':
            print("   Issue: Token expired or invalid")
            print("   Solution: Force token refresh")
            
            from utils.mcp_client import get_default_client
            client = get_default_client()
            client.token_manager._request_new_token()
            
        elif error_type == 'invalid_client':
            print("   Issue: Client credentials invalid")
            print("   Solution: Check KEYCLOAK_CLIENT_SECRET")
            
    except Exception as e:
        print(f"   Error parsing 401 response: {e}")
```

#### 429 Too Many Requests
```python
def handle_429_error(response):
    """Handle rate limiting errors"""
    print("🚦 Rate Limit Error (429)")
    
    retry_after = response.headers.get('Retry-After')
    if retry_after:
        print(f"   Retry after: {retry_after} seconds")
        
        import time
        wait_time = int(retry_after)
        print(f"   Waiting {wait_time}s...")
        time.sleep(wait_time)
    else:
        # Default backoff
        print("   Using default backoff: 60s")
        time.sleep(60)
```

#### 500 Internal Server Error
```python
def handle_500_error(response):
    """Handle server errors"""
    print("🔥 Server Error (500)")
    
    # Try fallback strategy
    print("   Attempting fallback to cached data...")
    
    from utils.cache_manager import get_session_cache
    cache = get_session_cache()
    
    cached_tasks = cache.get_pending_tasks()
    if cached_tasks:
        print(f"   ✅ Using {len(cached_tasks)} cached tasks")
        return cached_tasks
    else:
        print("   ❌ No cached data available")
        return None
```

### Exception Handling Patterns

```python
import requests
from requests.exceptions import (
    ConnectionError, Timeout, HTTPError, 
    RequestException, TooManyRedirects
)

def robust_request_handler(client, endpoint, payload):
    """Robust request handler with comprehensive error handling"""
    
    try:
        response = client.make_request(endpoint, payload)
        return response
        
    except ConnectionError as e:
        print(f"🔌 Connection Error: {e}")
        print("   Possible causes:")
        print("   - MCP server not running")
        print("   - Network connectivity issues")
        print("   - DNS resolution problems")
        return None
        
    except Timeout as e:
        print(f"⏱️ Timeout Error: {e}")
        print("   Possible solutions:")
        print("   - Increase MCP_SERVER_TIMEOUT")
        print("   - Check network latency")
        print("   - Verify server performance")
        return None
        
    except HTTPError as e:
        status_code = e.response.status_code
        print(f"🌐 HTTP Error {status_code}: {e}")
        
        if status_code == 401:
            handle_401_error(e.response)
        elif status_code == 429:
            handle_429_error(e.response)
        elif status_code == 500:
            return handle_500_error(e.response)
            
        return None
        
    except TooManyRedirects as e:
        print(f"🔄 Redirect Error: {e}")
        print("   Check MCP_SERVER_URL configuration")
        return None
        
    except RequestException as e:
        print(f"📡 Request Error: {e}")
        print("   Generic request failure")
        return None
        
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        print("   Please check logs for details")
        return None
```

---

## Performance Troubleshooting

### Slow Response Times

#### Issue: Requests taking too long to complete

**Diagnosis:**
```python
import time
from utils.mcp_client import get_default_client

def performance_benchmark():
    """Benchmark MCP client performance"""
    client = get_default_client()
    
    # Warm up connection
    client.authenticate()
    
    test_cases = [
        ("Single task query", lambda: client.query_pending_tasks(limit=1)),
        ("Multiple tasks", lambda: client.query_pending_tasks(limit=10)),
        ("Authentication only", lambda: client.authenticate()),
    ]
    
    for test_name, test_func in test_cases:
        times = []
        
        for i in range(5):  # Run 5 times
            start_time = time.time()
            try:
                result = test_func()
                end_time = time.time()
                times.append(end_time - start_time)
            except Exception as e:
                print(f"   Error in {test_name}: {e}")
                times.append(float('inf'))
        
        avg_time = sum(t for t in times if t != float('inf')) / len([t for t in times if t != float('inf')])
        print(f"{test_name}: {avg_time:.2f}s average")

performance_benchmark()
```

**Solutions:**
1. **Optimize connection pooling**
2. **Implement caching strategy**  
3. **Use async operations** where possible
4. **Reduce payload sizes**

```python
# Optimize connection pool settings
import os
os.environ.update({
    'HTTP_POOL_CONNECTIONS': '20',
    'HTTP_POOL_MAXSIZE': '40',
    'MCP_SERVER_TIMEOUT': '15'
})
```

### Memory Usage Issues

#### Issue: High memory consumption or memory leaks

**Diagnosis:**
```python
import psutil
import gc
from utils.mcp_client import get_default_client
from utils.cache_manager import get_session_cache

def memory_usage_test():
    """Monitor memory usage during operations"""
    process = psutil.Process()
    
    def get_memory():
        return process.memory_info().rss / 1024 / 1024  # MB
    
    print(f"Initial memory: {get_memory():.1f} MB")
    
    # Test client operations
    client = get_default_client()
    print(f"After client creation: {get_memory():.1f} MB")
    
    # Authentication
    client.authenticate()
    print(f"After authentication: {get_memory():.1f} MB")
    
    # Multiple queries
    for i in range(10):
        client.query_pending_tasks(limit=10)
    print(f"After 10 queries: {get_memory():.1f} MB")
    
    # Cache operations
    cache = get_session_cache()
    for i in range(100):
        cache.set(f"test_key_{i}", {"data": "test" * 100})
    print(f"After cache operations: {get_memory():.1f} MB")
    
    # Force garbage collection
    gc.collect()
    print(f"After garbage collection: {get_memory():.1f} MB")
    
    # Cache cleanup
    cache.clear_all()
    print(f"After cache cleanup: {get_memory():.1f} MB")

memory_usage_test()
```

**Solutions:**
1. **Implement cache size limits**
2. **Regular cache cleanup**
3. **Connection pool limits**
4. **Proper resource cleanup**

```python
# Configure memory-conscious settings
import os
os.environ.update({
    'SESSION_CACHE_MAX_SIZE': '10',  # 10 MB limit
    'FALLBACK_CACHE_TTL': '1800',    # 30 minutes
    'HTTP_POOL_MAXSIZE': '10'        # Limit connections
})
```

---

## Network Issues

### Proxy Configuration

#### Issue: Client not working behind corporate proxy

**Diagnosis:**
```bash
# Check proxy environment variables
echo "HTTP_PROXY: $HTTP_PROXY"
echo "HTTPS_PROXY: $HTTPS_PROXY"
echo "NO_PROXY: $NO_PROXY"

# Test proxy connectivity
curl --proxy "$HTTP_PROXY" -I "$MCP_SERVER_URL"
```

**Solutions:**
```python
# Configure proxy in client
import os
import requests

# Set proxy environment variables
os.environ.update({
    'HTTP_PROXY': 'http://proxy.company.com:8080',
    'HTTPS_PROXY': 'http://proxy.company.com:8080',
    'NO_PROXY': 'localhost,127.0.0.1,.local'
})

# Custom session with proxy
session = requests.Session()
session.proxies = {
    'http': os.getenv('HTTP_PROXY'),
    'https': os.getenv('HTTPS_PROXY')
}

# Apply to MCP client
from utils.mcp_client import MCPHTTPClient
client = MCPHTTPClient()
client.session = session
```

### DNS Resolution Issues

#### Issue: Cannot resolve hostnames

**Diagnosis:**
```bash
# Test DNS resolution
nslookup $(echo $MCP_SERVER_URL | sed 's|http[s]*://||' | cut -d: -f1)
nslookup $(echo $KEYCLOAK_URL | sed 's|http[s]*://||' | cut -d: -f1)

# Test with different DNS servers
nslookup $(echo $MCP_SERVER_URL | sed 's|http[s]*://||' | cut -d: -f1) 8.8.8.8
```

**Solutions:**
1. **Use IP addresses instead of hostnames**
2. **Configure custom DNS servers**
3. **Update /etc/hosts for local resolution**
4. **Check corporate DNS policies**

```bash
# Add to /etc/hosts for local development
echo "127.0.0.1 mcp-server.local" >> /etc/hosts
echo "127.0.0.1 keycloak.local" >> /etc/hosts

# Update environment variables
export MCP_SERVER_URL=http://mcp-server.local:8000
export KEYCLOAK_URL=http://keycloak.local:8080
```

---

## Authentication Problems

### Keycloak Configuration Issues

#### Issue: Client not configured properly in Keycloak

**Checklist:**
1. **Client exists in correct realm**
2. **Client ID matches environment variable**
3. **Client secret is current**
4. **Service accounts enabled**
5. **Required roles assigned**

**Verification Script:**
```python
import requests
import os
import json

def verify_keycloak_config():
    """Verify Keycloak client configuration"""
    
    keycloak_url = os.getenv('KEYCLOAK_URL')
    realm = os.getenv('KEYCLOAK_REALM')
    client_id = os.getenv('KEYCLOAK_CLIENT_ID')
    client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET')
    
    print("🔍 Verifying Keycloak Configuration")
    
    # Test realm accessibility
    try:
        response = requests.get(f"{keycloak_url}/auth/realms/{realm}")
        if response.status_code == 200:
            print("✅ Realm accessible")
        else:
            print(f"❌ Realm not accessible: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Realm connection error: {e}")
        return
    
    # Test client credentials
    try:
        response = requests.post(
            f"{keycloak_url}/auth/realms/{realm}/protocol/openid-connect/token",
            data={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            }
        )
        
        if response.status_code == 200:
            token_data = response.json()
            print("✅ Client credentials valid")
            print(f"   Access token received: {token_data['access_token'][:20]}...")
            
            # Test token info
            token_response = requests.post(
                f"{keycloak_url}/auth/realms/{realm}/protocol/openid-connect/token/introspect",
                data={
                    'token': token_data['access_token'],
                    'client_id': client_id,
                    'client_secret': client_secret
                }
            )
            
            if token_response.status_code == 200:
                token_info = token_response.json()
                print(f"   Token active: {token_info.get('active')}")
                print(f"   Token client: {token_info.get('client_id')}")
                print(f"   Token scope: {token_info.get('scope')}")
            
        else:
            error_data = response.json() if response.content else {}
            print(f"❌ Client credentials invalid: {error_data}")
            
    except Exception as e:
        print(f"❌ Client credentials test error: {e}")

verify_keycloak_config()
```

### Token Expiry Issues

#### Issue: Tokens expiring too quickly or not refreshing

**Diagnosis:**
```python
def debug_token_lifecycle():
    """Debug token lifecycle and refresh"""
    from utils.mcp_client import TokenManager
    import time
    
    token_manager = TokenManager()
    
    # Get initial token
    print("🔄 Getting initial token...")
    token = token_manager.get_valid_token()
    
    if token:
        print(f"✅ Token acquired: {token[:20]}...")
        
        # Check expiry timing
        if token_manager.token_expiry:
            import datetime
            now = datetime.datetime.now()
            expiry = token_manager.token_expiry
            time_left = (expiry - now).total_seconds()
            
            print(f"   Token expires in: {time_left:.0f} seconds")
            print(f"   Refresh threshold: {token_manager.refresh_before}s")
            
            # Test refresh logic
            if token_manager._should_refresh():
                print("🔄 Token should be refreshed")
            else:
                print("✅ Token is still valid")
        
        # Force refresh test
        print("\n🔄 Testing forced refresh...")
        old_token = token_manager.token
        token_manager._request_new_token()
        new_token = token_manager.token
        
        if new_token and new_token != old_token:
            print("✅ Token refresh successful")
        else:
            print("❌ Token refresh failed")
    else:
        print("❌ Initial token acquisition failed")

debug_token_lifecycle()
```

---

## Cache Issues

### Cache Corruption

#### Issue: Cache files corrupted or unreadable

**Diagnosis:**
```bash
# Check cache directory
ls -la ~/.claude/.session_cache/
ls -la ~/.claude/.mcp_*

# Check file permissions
ls -la ~/.claude/.mcp_token_cache

# Check file contents
head ~/.claude/.mcp_token_cache
head ~/.claude/.mcp_fallback_cache.json
```

**Solutions:**
```python
def fix_cache_issues():
    """Fix common cache issues"""
    from utils.cache_manager import get_session_cache
    import os
    from pathlib import Path
    
    cache = get_session_cache()
    
    print("🧹 Fixing cache issues...")
    
    # Clear corrupted cache
    try:
        stats = cache.get_cache_stats()
        print(f"Cache files before cleanup: {stats['total_files']}")
        
        # Remove expired and corrupted files
        deleted = cache.cleanup_expired()
        print(f"✅ Cleaned up {deleted} expired files")
        
        # Check token cache
        token_cache = Path.home() / ".claude" / ".mcp_token_cache"
        if token_cache.exists():
            try:
                import json
                with open(token_cache, 'r') as f:
                    json.load(f)  # Test if valid JSON
                print("✅ Token cache is valid")
            except:
                print("🔧 Fixing corrupted token cache...")
                token_cache.unlink()
                print("✅ Token cache cleared")
        
        # Fix permissions
        cache_dir = Path.home() / ".claude"
        if cache_dir.exists():
            os.chmod(cache_dir, 0o700)
            for cache_file in cache_dir.glob(".*"):
                if cache_file.is_file():
                    os.chmod(cache_file, 0o600)
            print("✅ Cache permissions fixed")
        
    except Exception as e:
        print(f"❌ Cache fix error: {e}")

fix_cache_issues()
```

### Cache Performance Issues

#### Issue: Slow cache operations or excessive disk usage

**Diagnosis:**
```python
def diagnose_cache_performance():
    """Diagnose cache performance issues"""
    from utils.cache_manager import get_session_cache
    import time
    import os
    
    cache = get_session_cache()
    
    # Test cache performance
    print("📊 Cache Performance Test")
    
    # Write performance
    start_time = time.time()
    for i in range(100):
        cache.set(f"perf_test_{i}", {"data": "x" * 100})
    write_time = time.time() - start_time
    print(f"Write 100 items: {write_time:.2f}s ({write_time/100*1000:.1f}ms per item)")
    
    # Read performance
    start_time = time.time()
    for i in range(100):
        cache.get(f"perf_test_{i}")
    read_time = time.time() - start_time
    print(f"Read 100 items: {read_time:.2f}s ({read_time/100*1000:.1f}ms per item)")
    
    # Cache size analysis
    stats = cache.get_cache_stats()
    size_mb = stats['total_size_bytes'] / 1024 / 1024
    print(f"Total cache size: {size_mb:.1f} MB")
    
    if size_mb > 50:  # More than 50 MB
        print("⚠️ Cache size is large - consider cleanup")
        
        # Find largest files
        cache_dir = stats['cache_dir']
        import glob
        cache_files = glob.glob(os.path.join(cache_dir, "*.json"))
        file_sizes = [(f, os.path.getsize(f)) for f in cache_files]
        file_sizes.sort(key=lambda x: x[1], reverse=True)
        
        print("📁 Largest cache files:")
        for file_path, size in file_sizes[:5]:
            print(f"   {os.path.basename(file_path)}: {size/1024:.1f} KB")
    
    # Cleanup test data
    for i in range(100):
        cache.delete(f"perf_test_{i}")

diagnose_cache_performance()
```

---

## Recovery Procedures

### Complete System Recovery

#### Full Reset Procedure

```bash
#!/bin/bash
# complete_reset.sh - Full MCP client reset

echo "🔄 Starting MCP Client Complete Reset..."

# 1. Stop any running processes
echo "1. Stopping processes..."
pkill -f "mcp_client"
pkill -f "session_start"

# 2. Clear all caches
echo "2. Clearing caches..."
rm -rf ~/.claude/.session_cache/
rm -f ~/.claude/.mcp_token_cache
rm -f ~/.claude/.mcp_fallback_cache.json

# 3. Reset cache permissions
echo "3. Resetting permissions..."
mkdir -p ~/.claude/.session_cache
chmod 700 ~/.claude
chmod 700 ~/.claude/.session_cache

# 4. Clear environment (optional)
echo "4. Environment variables (check manually):"
echo "   KEYCLOAK_CLIENT_SECRET=[REDACTED]"
echo "   MCP_SERVER_URL=$MCP_SERVER_URL"
echo "   KEYCLOAK_URL=$KEYCLOAK_URL"

# 5. Test connectivity
echo "5. Testing connectivity..."
if curl -f -s "$KEYCLOAK_URL/auth/realms/master" > /dev/null; then
    echo "   ✅ Keycloak reachable"
else
    echo "   ❌ Keycloak not reachable"
fi

if curl -f -s "$MCP_SERVER_URL/mcp/manage_connection" > /dev/null; then
    echo "   ✅ MCP server reachable"
else
    echo "   ❌ MCP server not reachable"
fi

echo "🎉 Reset complete! Test with:"
echo "   python .claude/hooks/utils/mcp_client.py"
```

#### Gradual Recovery

```python
def gradual_recovery():
    """Perform gradual system recovery"""
    from utils.mcp_client import get_default_client, test_mcp_connection
    from utils.cache_manager import get_session_cache
    
    recovery_steps = [
        ("Clear corrupted cache", clear_cache),
        ("Test basic connectivity", test_connectivity),
        ("Verify authentication", verify_auth),
        ("Test MCP functionality", test_mcp),
        ("Restore cache", restore_cache)
    ]
    
    for step_name, step_func in recovery_steps:
        print(f"🔧 {step_name}...")
        
        try:
            success = step_func()
            if success:
                print(f"   ✅ {step_name} successful")
            else:
                print(f"   ❌ {step_name} failed")
                return False
        except Exception as e:
            print(f"   ❌ {step_name} error: {e}")
            return False
    
    print("🎉 Gradual recovery complete!")
    return True

def clear_cache():
    """Clear potentially corrupted cache"""
    cache = get_session_cache()
    cache.clear_all()
    return True

def test_connectivity():
    """Test network connectivity"""
    import requests
    import os
    
    try:
        keycloak_url = os.getenv('KEYCLOAK_URL')
        mcp_url = os.getenv('MCP_SERVER_URL')
        
        requests.get(f"{keycloak_url}/auth/realms/master", timeout=5)
        requests.get(f"{mcp_url}/mcp/manage_connection", timeout=5)
        
        return True
    except:
        return False

def verify_auth():
    """Verify authentication works"""
    try:
        client = get_default_client()
        return client.authenticate()
    except:
        return False

def test_mcp():
    """Test MCP functionality"""
    return test_mcp_connection()

def restore_cache():
    """Restore cache with fresh data"""
    try:
        client = get_default_client()
        cache = get_session_cache()
        
        # Populate cache with fresh data
        tasks = client.query_pending_tasks(limit=10)
        if tasks:
            cache.cache_pending_tasks(tasks)
        
        return True
    except:
        return False

# Run gradual recovery
gradual_recovery()
```

---

## Monitoring and Logging

### Comprehensive Logging Setup

```python
import logging
import sys
from datetime import datetime

def setup_comprehensive_logging():
    """Setup comprehensive logging for diagnostics"""
    
    # Create logger
    logger = logging.getLogger('mcp_client')
    logger.setLevel(logging.DEBUG)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # Console handler for important messages
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler for detailed logging
    from pathlib import Path
    log_dir = Path.home() / ".claude" / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"mcp_client_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Also configure requests logging
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    print(f"📝 Detailed logs: {log_file}")
    return logger

# Setup logging
logger = setup_comprehensive_logging()

# Test logging
logger.info("MCP Client logging initialized")
logger.debug("Debug logging enabled")
```

### Health Check Monitoring

```python
import time
import json
from datetime import datetime, timedelta

class MCPHealthMonitor:
    """Continuous health monitoring for MCP client"""
    
    def __init__(self, check_interval=300):  # 5 minutes
        self.check_interval = check_interval
        self.health_history = []
        self.running = False
    
    def start_monitoring(self):
        """Start health monitoring"""
        import threading
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop)
        self.thread.daemon = True
        self.thread.start()
        
        print("🏥 Health monitoring started")
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()
        print("🏥 Health monitoring stopped")
    
    def _monitoring_loop(self):
        """Health monitoring loop"""
        while self.running:
            try:
                health_data = self.check_health()
                self.health_history.append(health_data)
                
                # Keep only last 24 hours of data
                cutoff_time = datetime.now() - timedelta(hours=24)
                self.health_history = [
                    h for h in self.health_history 
                    if h['timestamp'] > cutoff_time
                ]
                
                # Alert on issues
                if not health_data['healthy']:
                    self.alert_health_issue(health_data)
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                print(f"❌ Health monitor error: {e}")
                time.sleep(60)  # Wait 1 minute on error
    
    def check_health(self):
        """Perform health check"""
        from utils.mcp_client import get_default_client
        from utils.cache_manager import get_session_cache
        
        health_data = {
            'timestamp': datetime.now(),
            'healthy': True,
            'issues': [],
            'metrics': {}
        }
        
        # Test authentication
        try:
            client = get_default_client()
            auth_start = time.time()
            auth_success = client.authenticate()
            auth_time = time.time() - auth_start
            
            health_data['metrics']['auth_time'] = auth_time
            health_data['metrics']['auth_success'] = auth_success
            
            if not auth_success:
                health_data['healthy'] = False
                health_data['issues'].append('Authentication failed')
            
        except Exception as e:
            health_data['healthy'] = False
            health_data['issues'].append(f'Auth error: {str(e)}')
        
        # Test task query
        try:
            query_start = time.time()
            tasks = client.query_pending_tasks(limit=1)
            query_time = time.time() - query_start
            
            health_data['metrics']['query_time'] = query_time
            health_data['metrics']['query_success'] = tasks is not None
            
            if tasks is None:
                health_data['issues'].append('Task query returned no data')
            
        except Exception as e:
            health_data['healthy'] = False
            health_data['issues'].append(f'Query error: {str(e)}')
        
        # Check cache health
        try:
            cache = get_session_cache()
            cache_stats = cache.get_cache_stats()
            
            health_data['metrics']['cache_files'] = cache_stats['total_files']
            health_data['metrics']['cache_size'] = cache_stats['total_size_bytes']
            health_data['metrics']['cache_expired'] = cache_stats['expired_files']
            
            # Alert on cache issues
            if cache_stats['total_size_bytes'] > 100 * 1024 * 1024:  # 100 MB
                health_data['issues'].append('Cache size is large')
            
            if cache_stats['expired_files'] > 50:
                health_data['issues'].append('Many expired cache files')
                
        except Exception as e:
            health_data['issues'].append(f'Cache error: {str(e)}')
        
        return health_data
    
    def alert_health_issue(self, health_data):
        """Alert on health issues"""
        print(f"🚨 Health Alert at {health_data['timestamp']}")
        for issue in health_data['issues']:
            print(f"   ❌ {issue}")
    
    def get_health_report(self):
        """Get health report"""
        if not self.health_history:
            return "No health data available"
        
        recent_checks = self.health_history[-10:]  # Last 10 checks
        healthy_count = sum(1 for h in recent_checks if h['healthy'])
        
        report = f"🏥 Health Report (last {len(recent_checks)} checks)\n"
        report += f"   Healthy: {healthy_count}/{len(recent_checks)}\n"
        
        # Average metrics
        if recent_checks:
            avg_auth_time = sum(h['metrics'].get('auth_time', 0) for h in recent_checks) / len(recent_checks)
            avg_query_time = sum(h['metrics'].get('query_time', 0) for h in recent_checks) / len(recent_checks)
            
            report += f"   Avg auth time: {avg_auth_time:.2f}s\n"
            report += f"   Avg query time: {avg_query_time:.2f}s\n"
        
        # Recent issues
        recent_issues = set()
        for h in recent_checks:
            recent_issues.update(h['issues'])
        
        if recent_issues:
            report += "   Recent issues:\n"
            for issue in recent_issues:
                report += f"     - {issue}\n"
        
        return report

# Usage
monitor = MCPHealthMonitor(check_interval=180)  # Check every 3 minutes
monitor.start_monitoring()

# Get health report after some time
# time.sleep(600)  # Wait 10 minutes
# print(monitor.get_health_report())
# monitor.stop_monitoring()
```

This comprehensive troubleshooting guide provides detailed solutions for common issues, diagnostic tools, and recovery procedures to help maintain a healthy MCP HTTP Client Module deployment.