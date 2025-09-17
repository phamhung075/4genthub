# 🔧 .mcp.json Configuration Guide

## 📋 Overview

The `.mcp.json` file is the central configuration for Model Context Protocol (MCP) server connections in DhafnckMCP. This guide provides comprehensive documentation for understanding, configuring, and troubleshooting MCP server integrations.

---

## 🏗️ File Structure & Location

### 📁 File Location
```
/home/daihungpham/__projects__/agentic-project/.mcp.json
```

### 🔍 Basic Structure
```json
{
    "mcpServers": {
        "server-name": {
            // Server configuration
        }
    }
}
```

---

## 🖥️ Current Configuration Analysis

### 📄 Complete Current Configuration

```json
{
    "mcpServers": {
        "sequential-thinking": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-sequential-thinking"
            ],
            "env": {}
        },
        "dhafnck_mcp_http": {
            "type": "http",
            "url": "http://localhost:8000/mcp",
            "headers": {
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        },
        "shadcn-ui-server": {
            "command": "npx",
            "args": [
                "@heilgar/shadcn-ui-mcp-server"
            ]
        },
        "browsermcp": {
            "command": "npx",
            "args": [
                "@browsermcp/mcp@latest"
            ]
        },
        "ElevenLabs": {
            "command": "uvx",
            "args": [
                "elevenlabs-mcp"
            ],
            "env": {
                "ELEVENLABS_API_KEY": "sk_152e66d26b1eb6f1a1105474c07e962ee90b42ddf5532809"
            }
        }
    }
}
```

---

## 🔧 Server Types & Configuration

### 🌐 HTTP Servers

HTTP servers connect to remote MCP endpoints via HTTP protocol.

#### **dhafnck_mcp_http** (Primary Server)

```json
{
    "dhafnck_mcp_http": {
        "type": "http",
        "url": "http://localhost:8000/mcp",
        "headers": {
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer <JWT_TOKEN>"
        }
    }
}
```

**Configuration Details:**
- **type**: `"http"` - Specifies HTTP transport
- **url**: MCP endpoint URL (local development server)
- **headers**: Required HTTP headers
  - **Accept**: Content types for requests
  - **Authorization**: Bearer token for authentication

**Environment Variables:**
```bash
# .env configuration
MCP_SERVER_URL=http://localhost:8000/mcp
MCP_JWT_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 📦 NPX Servers

NPX servers are Node.js packages executed via npx command.

#### **sequential-thinking** (AI Reasoning)

```json
{
    "sequential-thinking": {
        "command": "npx",
        "args": [
            "-y",
            "@modelcontextprotocol/server-sequential-thinking"
        ],
        "env": {}
    }
}
```

**Purpose**: Provides advanced AI reasoning capabilities
**Package**: Official MCP sequential thinking server
**Dependencies**: Node.js, npm

#### **shadcn-ui-server** (UI Components)

```json
{
    "shadcn-ui-server": {
        "command": "npx",
        "args": [
            "@heilgar/shadcn-ui-mcp-server"
        ]
    }
}
```

**Purpose**: UI component library integration
**Package**: shadcn/ui MCP server
**Features**: Component installation, documentation

#### **browsermcp** (Browser Automation)

```json
{
    "browsermcp": {
        "command": "npx",
        "args": [
            "@browsermcp/mcp@latest"
        ]
    }
}
```

**Purpose**: Web browser automation and control
**Package**: Browser MCP package
**Capabilities**: Navigation, interaction, scraping

### 🐍 UVX Servers

UVX servers are Python packages executed via uvx command.

#### **ElevenLabs** (Text-to-Speech)

```json
{
    "ElevenLabs": {
        "command": "uvx",
        "args": [
            "elevenlabs-mcp"
        ],
        "env": {
            "ELEVENLABS_API_KEY": "sk_152e66d26b1eb6f1a1105474c07e962ee90b42ddf5532809"
        }
    }
}
```

**Purpose**: Text-to-speech and voice synthesis
**Package**: ElevenLabs MCP package
**Authentication**: API key required

---

## 🔐 Security Configuration

### 🛡️ Authentication Methods

#### **Bearer Token Authentication**
```json
{
    "headers": {
        "Authorization": "Bearer <JWT_TOKEN>"
    }
}
```

#### **API Key Authentication**
```json
{
    "env": {
        "API_KEY": "your-api-key-here"
    }
}
```

### 🔑 Environment Variable Management

```bash
# .env.claude (recommended for sensitive data)
DHAFNCK_MCP_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
ELEVENLABS_API_KEY=sk_152e66d26b1eb6f1a1105474c07e962ee90b42ddf5532809

# Reference in .mcp.json
{
    "headers": {
        "Authorization": "Bearer ${DHAFNCK_MCP_JWT}"
    },
    "env": {
        "ELEVENLABS_API_KEY": "${ELEVENLABS_API_KEY}"
    }
}
```

### ⚠️ Security Best Practices

1. **Never commit API keys** to version control
2. **Use environment variables** for sensitive data
3. **Rotate tokens regularly** (JWT tokens expire)
4. **Validate server certificates** for HTTPS connections
5. **Use least privilege** access patterns

---

## 🚀 Advanced Configuration

### 🔄 Custom Server Addition

#### Adding a New HTTP Server
```json
{
    "my-custom-server": {
        "type": "http",
        "url": "https://api.example.com/mcp",
        "headers": {
            "Accept": "application/json",
            "Authorization": "Bearer ${CUSTOM_API_TOKEN}",
            "X-Custom-Header": "custom-value"
        },
        "timeout": 30000,
        "retries": 3
    }
}
```

#### Adding a New NPX Server
```json
{
    "custom-npm-server": {
        "command": "npx",
        "args": [
            "-y",
            "@my-org/custom-mcp-server",
            "--config",
            "./config.json"
        ],
        "env": {
            "NODE_ENV": "production",
            "CUSTOM_CONFIG": "value"
        },
        "cwd": "./custom-server-workspace"
    }
}
```

#### Adding a New Python Server
```json
{
    "custom-python-server": {
        "command": "uvx",
        "args": [
            "my-custom-mcp-package",
            "--port",
            "8001"
        ],
        "env": {
            "PYTHON_ENV": "production",
            "API_ENDPOINT": "https://api.example.com"
        }
    }
}
```

### ⚙️ Advanced Configuration Options

#### **Timeouts and Retries**
```json
{
    "server-name": {
        "type": "http",
        "url": "https://api.example.com/mcp",
        "timeout": 30000,          // 30 seconds
        "retries": 3,              // 3 retry attempts
        "retryDelay": 1000         // 1 second between retries
    }
}
```

#### **Custom Working Directory**
```json
{
    "server-name": {
        "command": "npx",
        "args": ["package-name"],
        "cwd": "./custom-workspace",
        "env": {
            "NODE_ENV": "development"
        }
    }
}
```

#### **Health Check Configuration**
```json
{
    "server-name": {
        "type": "http",
        "url": "https://api.example.com/mcp",
        "healthCheck": {
            "enabled": true,
            "endpoint": "/health",
            "interval": 30000,       // 30 seconds
            "timeout": 5000          // 5 seconds
        }
    }
}
```

---

## 🧪 Testing & Validation

### ✅ Configuration Validation

#### **JSON Syntax Check**
```bash
# Validate JSON syntax
cat .mcp.json | python -m json.tool

# Or using jq
cat .mcp.json | jq .
```

#### **Schema Validation Script**
```python
#!/usr/bin/env python3
import json
import jsonschema

# MCP JSON schema
schema = {
    "type": "object",
    "properties": {
        "mcpServers": {
            "type": "object",
            "patternProperties": {
                "^[a-zA-Z0-9_-]+$": {
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {
                                "type": {"const": "http"},
                                "url": {"type": "string", "format": "uri"},
                                "headers": {"type": "object"}
                            },
                            "required": ["type", "url"]
                        },
                        {
                            "type": "object",
                            "properties": {
                                "command": {"type": "string"},
                                "args": {"type": "array"},
                                "env": {"type": "object"}
                            },
                            "required": ["command", "args"]
                        }
                    ]
                }
            }
        }
    },
    "required": ["mcpServers"]
}

# Validate configuration
with open('.mcp.json', 'r') as f:
    config = json.load(f)

try:
    jsonschema.validate(config, schema)
    print("✅ Configuration is valid")
except jsonschema.ValidationError as e:
    print(f"❌ Configuration error: {e.message}")
```

### 🔍 Server Connectivity Testing

#### **Test HTTP Servers**
```bash
# Test dhafnck_mcp_http server
curl -H "Accept: application/json" \
     -H "Authorization: Bearer ${JWT_TOKEN}" \
     http://localhost:8000/mcp

# Expected response: MCP server information
```

#### **Test NPX Servers**
```bash
# Test sequential-thinking server (locally)
npx -y @modelcontextprotocol/server-sequential-thinking --help

# Test shadcn-ui-server
npx @heilgar/shadcn-ui-mcp-server --version
```

#### **Test UVX Servers**
```bash
# Test ElevenLabs server
ELEVENLABS_API_KEY=your-key uvx elevenlabs-mcp --help
```

### 🐛 Debugging Configuration Issues

#### **Common Error Messages**

1. **Connection Refused**
   ```
   Error: connect ECONNREFUSED 127.0.0.1:8000
   ```
   **Solution**: Ensure server is running, check URL and port

2. **Authentication Failed**
   ```
   Error: 401 Unauthorized
   ```
   **Solution**: Verify JWT token, check expiration

3. **Package Not Found**
   ```
   Error: Package '@example/package' not found
   ```
   **Solution**: Verify package name, check npm registry

4. **Environment Variable Missing**
   ```
   Error: ELEVENLABS_API_KEY is required
   ```
   **Solution**: Set required environment variables

---

## 🔄 Environment-Specific Configurations

### 🏠 Development Configuration

```json
{
    "mcpServers": {
        "dhafnck_mcp_http": {
            "type": "http",
            "url": "http://localhost:8000/mcp",
            "headers": {
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer ${DEV_JWT_TOKEN}"
            }
        }
    }
}
```

### 🏭 Production Configuration

```json
{
    "mcpServers": {
        "dhafnck_mcp_http": {
            "type": "http",
            "url": "https://api.dhafnck.com/mcp",
            "headers": {
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer ${PROD_JWT_TOKEN}"
            },
            "timeout": 10000,
            "retries": 3
        }
    }
}
```

### 🧪 Testing Configuration

```json
{
    "mcpServers": {
        "dhafnck_mcp_http": {
            "type": "http",
            "url": "http://test-server:8000/mcp",
            "headers": {
                "Accept": "application/json",
                "Authorization": "Bearer ${TEST_JWT_TOKEN}"
            }
        }
    }
}
```

---

## 📊 Performance Optimization

### ⚡ Connection Pooling

```json
{
    "dhafnck_mcp_http": {
        "type": "http",
        "url": "http://localhost:8000/mcp",
        "connectionPool": {
            "maxConnections": 10,
            "keepAlive": true,
            "timeout": 30000
        }
    }
}
```

### 🔄 Caching Configuration

```json
{
    "server-name": {
        "type": "http",
        "url": "https://api.example.com/mcp",
        "cache": {
            "enabled": true,
            "ttl": 300,              // 5 minutes
            "maxSize": 100           // 100 cached responses
        }
    }
}
```

### 📈 Monitoring Configuration

```json
{
    "server-name": {
        "type": "http",
        "url": "https://api.example.com/mcp",
        "monitoring": {
            "enabled": true,
            "metrics": ["response_time", "error_rate", "throughput"],
            "alerting": {
                "responseTimeThreshold": 5000,
                "errorRateThreshold": 0.05
            }
        }
    }
}
```

---

## 🛠️ Troubleshooting Guide

### 🔍 Diagnostic Commands

#### **Check Server Status**
```bash
# List running processes
ps aux | grep -E "(npx|uvx|node)"

# Check port usage
netstat -tlnp | grep -E "(8000|3800)"

# Check Docker containers (if applicable)
docker ps | grep dhafnck
```

#### **Test Individual Servers**
```bash
# Test HTTP connectivity
curl -v http://localhost:8000/health

# Test MCP endpoint
curl -H "Accept: application/json" http://localhost:8000/mcp

# Check server logs
tail -f logs/mcp-server.log
```

### 🚨 Common Issues & Solutions

#### **Issue 1: JWT Token Expired**
```bash
# Symptoms
Error: 401 Unauthorized
Response: {"error": "Token expired"}

# Solution
# 1. Generate new token from dashboard
# 2. Update .env.claude file
# 3. Restart Claude Code
```

#### **Issue 2: Server Not Found**
```bash
# Symptoms
Error: ENOTFOUND api.example.com

# Solution
# 1. Check network connectivity
# 2. Verify URL spelling
# 3. Check DNS resolution
nslookup api.example.com
```

#### **Issue 3: Package Installation Fails**
```bash
# Symptoms
Error: Package '@example/package' not found

# Solution
# 1. Check package name and version
# 2. Verify npm registry access
npm search @example/package
# 3. Try manual installation
npm install -g @example/package
```

#### **Issue 4: Environment Variables Not Loaded**
```bash
# Symptoms
Error: Environment variable 'API_KEY' is not defined

# Solution
# 1. Check .env.claude file exists
# 2. Verify variable names match
# 3. Restart Claude Code to reload variables
cat .env.claude | grep API_KEY
```

---

## 📋 Best Practices

### ✅ Configuration Management

1. **Use Environment Variables**: Store sensitive data in .env.claude
2. **Version Control**: Keep .mcp.json in git, exclude .env.claude
3. **Documentation**: Comment complex configurations
4. **Validation**: Test configurations before deployment
5. **Backup**: Keep backup copies of working configurations

### 🔒 Security Practices

1. **Token Rotation**: Regularly update JWT tokens and API keys
2. **Least Privilege**: Use minimal required permissions
3. **HTTPS**: Use encrypted connections for production
4. **Monitoring**: Log and monitor authentication attempts
5. **Validation**: Validate all external inputs

### 🚀 Performance Practices

1. **Connection Pooling**: Reuse connections when possible
2. **Caching**: Cache responses to reduce latency
3. **Timeouts**: Set appropriate timeout values
4. **Monitoring**: Track performance metrics
5. **Optimization**: Profile and optimize slow operations

---

## 📚 References

### 🔗 External Documentation
- [Model Context Protocol Specification](https://modelcontextprotocol.io)
- [Claude Code MCP Integration](https://docs.anthropic.com/claude/mcp)
- [NPX Documentation](https://docs.npmjs.com/cli/v10/commands/npx)
- [UVX Documentation](https://docs.astral.sh/uv/)

### 📖 Internal Documentation
- [CLAUDE.md Configuration Guide](../claude-code/claude-md-configuration-guide.md)
- [Hook System Documentation](../claude-code/hooks-system-guide.md)
- [Agent Library Reference](../core-architecture/agent-library-reference.md)

### 🛠️ Tools and Utilities
- [JSON Schema Validator](https://jsonschema.net/)
- [JWT Decoder](https://jwt.io/)
- [API Testing Tools](https://www.postman.com/)
- [Docker Health Checks](https://docs.docker.com/engine/reference/builder/#healthcheck)

---

**Next Steps**: [Configure CLAUDE.md and CLAUDE.local.md →](claude-md-configuration-guide.md)