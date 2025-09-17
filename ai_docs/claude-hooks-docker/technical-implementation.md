# Claude Hooks Docker Client - Technical Implementation Guide

## Overview

This document provides detailed technical implementation guidance for containerizing the Claude hooks system, including code examples, configuration details, and step-by-step implementation instructions.

## Table of Contents

1. [Project Structure](#project-structure)
2. [Core Components Implementation](#core-components-implementation)
3. [API Implementation](#api-implementation)
4. [Hook Engine Implementation](#hook-engine-implementation)
5. [Validation System](#validation-system)
6. [Session Management](#session-management)
7. [Integration with MCP Server](#integration-with-mcp-server)
8. [Testing Strategy](#testing-strategy)
9. [Migration Path](#migration-path)

## Project Structure

```
claude-hooks-docker/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py                 # FastAPI application
│   │   ├── routes/
│   │   │   ├── hooks.py           # Hook endpoints
│   │   │   ├── validation.py      # Validation endpoints
│   │   │   ├── context.py         # Context endpoints
│   │   │   └── health.py          # Health check endpoints
│   │   ├── middleware/
│   │   │   ├── auth.py           # Authentication middleware
│   │   │   ├── logging.py        # Request logging
│   │   │   └── error_handler.py  # Error handling
│   │   └── models/
│   │       ├── requests.py       # Request models
│   │       └── responses.py      # Response models
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py             # Hook engine
│   │   ├── config.py             # Configuration management
│   │   └── exceptions.py         # Custom exceptions
│   │
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── base.py              # Base validator class
│   │   ├── file_system.py       # File system validator
│   │   ├── documentation.py     # Documentation validator
│   │   ├── command.py           # Command validator
│   │   └── mcp_task.py          # MCP task validator
│   │
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── base.py              # Base processor class
│   │   ├── logging.py           # Logging processor
│   │   ├── hints.py             # Hints processor
│   │   └── context_injection.py # Context injection
│   │
│   ├── session/
│   │   ├── __init__.py
│   │   ├── manager.py           # Session manager
│   │   ├── storage.py           # Storage backends
│   │   └── models.py            # Session models
│   │
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── mcp.py              # MCP server client
│   │   ├── keycloak.py         # Keycloak client
│   │   └── redis.py            # Redis client
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py            # Logging utilities
│       ├── metrics.py           # Metrics collection
│       └── cache.py             # Caching utilities
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── config/
│   ├── default.yaml             # Default configuration
│   ├── development.yaml         # Development config
│   ├── production.yaml          # Production config
│   └── testing.yaml             # Testing config
│
├── docker/
│   ├── Dockerfile              # Main Dockerfile
│   ├── Dockerfile.dev          # Development Dockerfile
│   └── entrypoint.sh           # Container entrypoint
│
├── scripts/
│   ├── migrate.py              # Migration script
│   ├── setup.py                # Setup script
│   └── health_check.py         # Health check script
│
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Development dependencies
├── docker-compose.yml          # Docker Compose config
├── docker-compose.dev.yml      # Development Compose
├── .env.example               # Environment variables example
└── README.md                  # Project documentation
```

## Core Components Implementation

### 1. FastAPI Application Setup

```python
# src/api/app.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from .routes import hooks, validation, context, health
from .middleware import AuthMiddleware, LoggingMiddleware, ErrorHandlerMiddleware
from ..core.config import settings
from ..clients import MCPClient, RedisClient
from ..session import SessionManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    app.state.redis = await RedisClient.create(settings.REDIS_URL)
    app.state.mcp_client = MCPClient(settings.MCP_SERVER_URL)
    app.state.session_manager = SessionManager(app.state.redis)

    yield

    # Shutdown
    await app.state.redis.close()
    await app.state.mcp_client.close()

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="Claude Hooks Service",
        version="1.0.0",
        description="Containerized hook service for Claude Code",
        lifespan=lifespan
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    # Add custom middleware
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(AuthMiddleware)

    # Include routers
    app.include_router(hooks.router, prefix="/api/v1/hooks", tags=["hooks"])
    app.include_router(validation.router, prefix="/api/v1/validation", tags=["validation"])
    app.include_router(context.router, prefix="/api/v1/context", tags=["context"])
    app.include_router(health.router, prefix="/health", tags=["health"])

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
```

### 2. Configuration Management

```python
# src/core/config.py
from pydantic import BaseSettings, Field, validator
from typing import List, Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # API Configuration
    API_PORT: int = Field(default=9000, env="API_PORT")
    API_PREFIX: str = Field(default="/api/v1", env="API_PREFIX")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")

    # Security
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_EXPIRATION: int = Field(default=3600, env="JWT_EXPIRATION")
    API_KEY: Optional[str] = Field(None, env="API_KEY")
    ALLOWED_ORIGINS: List[str] = Field(default=["http://localhost:*"], env="ALLOWED_ORIGINS")

    # Database Configuration
    POSTGRES_URL: str = Field(..., env="POSTGRES_URL")
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    # MCP Server
    MCP_SERVER_URL: str = Field(..., env="MCP_SERVER_URL")
    MCP_API_KEY: Optional[str] = Field(None, env="MCP_API_KEY")
    MCP_TIMEOUT: int = Field(default=30, env="MCP_TIMEOUT")

    # Keycloak Configuration
    KEYCLOAK_URL: Optional[str] = Field(None, env="KEYCLOAK_URL")
    KEYCLOAK_REALM: str = Field(default="4genthub", env="KEYCLOAK_REALM")
    KEYCLOAK_CLIENT_ID: str = Field(default="claude-hooks", env="KEYCLOAK_CLIENT_ID")
    KEYCLOAK_CLIENT_SECRET: Optional[str] = Field(None, env="KEYCLOAK_CLIENT_SECRET")

    # Project Configuration
    PROJECT_PATH: Path = Field(default="/project", env="PROJECT_PATH")
    AI_DOCS_PATH: Path = Field(default="/project/ai_docs", env="AI_DOCS_PATH")
    AI_DATA_PATH: Path = Field(default="/app/data", env="AI_DATA_PATH")

    # Cache Configuration
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")
    CACHE_MAX_SIZE: int = Field(default=1000, env="CACHE_MAX_SIZE")

    # Performance
    MAX_WORKERS: int = Field(default=10, env="MAX_WORKERS")
    REQUEST_TIMEOUT: int = Field(default=60, env="REQUEST_TIMEOUT")

    @validator("PROJECT_PATH", "AI_DOCS_PATH", "AI_DATA_PATH")
    def validate_paths(cls, v):
        """Ensure paths are Path objects"""
        return Path(v) if not isinstance(v, Path) else v

    @validator("ALLOWED_ORIGINS", pre=True)
    def parse_origins(cls, v):
        """Parse comma-separated origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
```

## API Implementation

### 1. Hook Routes Implementation

```python
# src/api/routes/hooks.py
from fastapi import APIRouter, Request, HTTPException, Depends
from typing import Dict, Any
import asyncio

from ..models.requests import PreToolUseRequest, PostToolUseRequest, SessionStartRequest
from ..models.responses import HookResponse, SessionResponse
from ...core.engine import HookEngine
from ...core.exceptions import ValidationError, ProcessingError

router = APIRouter()

def get_hook_engine(request: Request) -> HookEngine:
    """Dependency to get hook engine"""
    return HookEngine(
        session_manager=request.app.state.session_manager,
        mcp_client=request.app.state.mcp_client,
        redis=request.app.state.redis
    )

@router.post("/pre-tool-use", response_model=HookResponse)
async def pre_tool_use(
    request: PreToolUseRequest,
    engine: HookEngine = Depends(get_hook_engine)
) -> HookResponse:
    """Process pre-tool-use hook"""
    try:
        result = await engine.process_pre_tool_use(request)
        return result
    except ValidationError as e:
        return HookResponse(
            blocked=True,
            errors=[str(e)],
            hints=e.hints if hasattr(e, 'hints') else []
        )
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/post-tool-use", response_model=HookResponse)
async def post_tool_use(
    request: PostToolUseRequest,
    engine: HookEngine = Depends(get_hook_engine)
) -> HookResponse:
    """Process post-tool-use hook"""
    try:
        result = await engine.process_post_tool_use(request)
        return result
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/session-start", response_model=SessionResponse)
async def session_start(
    request: SessionStartRequest,
    engine: HookEngine = Depends(get_hook_engine)
) -> SessionResponse:
    """Initialize a new session"""
    try:
        session = await engine.start_session(request)
        return SessionResponse(
            session_id=session.id,
            context=session.context,
            expires_at=session.expires_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time hook processing"""
    engine = HookEngine(
        session_manager=websocket.app.state.session_manager,
        mcp_client=websocket.app.state.mcp_client,
        redis=websocket.app.state.redis
    )

    await websocket.accept()

    try:
        while True:
            # Receive hook request
            data = await websocket.receive_json()

            # Process based on hook type
            if data.get("type") == "pre-tool-use":
                request = PreToolUseRequest(**data["payload"])
                result = await engine.process_pre_tool_use(request)
            elif data.get("type") == "post-tool-use":
                request = PostToolUseRequest(**data["payload"])
                result = await engine.process_post_tool_use(request)
            else:
                result = {"error": "Unknown hook type"}

            # Send response
            await websocket.send_json(result.dict() if hasattr(result, 'dict') else result)

    except WebSocketDisconnect:
        await engine.cleanup_session(client_id)
```

### 2. Request/Response Models

```python
# src/api/models/requests.py
from pydantic import BaseModel, Field, validator
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class ToolType(str, Enum):
    """Supported tool types"""
    BASH = "Bash"
    EDIT = "Edit"
    WRITE = "Write"
    READ = "Read"
    GREP = "Grep"
    GLOB = "Glob"
    TASK = "Task"

class BaseHookRequest(BaseModel):
    """Base request model for hooks"""
    session_id: str = Field(..., description="Session identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[str] = Field(None, description="User identifier")
    project_id: Optional[str] = Field(None, description="Project identifier")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PreToolUseRequest(BaseHookRequest):
    """Request model for pre-tool-use hook"""
    tool: ToolType = Field(..., description="Tool being invoked")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator("parameters")
    def validate_parameters(cls, v, values):
        """Validate parameters based on tool type"""
        tool = values.get("tool")

        if tool == ToolType.BASH and "command" not in v:
            raise ValueError("Bash tool requires 'command' parameter")
        elif tool == ToolType.EDIT and not all(k in v for k in ["file_path", "old_string", "new_string"]):
            raise ValueError("Edit tool requires 'file_path', 'old_string', and 'new_string' parameters")

        return v

class PostToolUseRequest(BaseHookRequest):
    """Request model for post-tool-use hook"""
    tool: ToolType = Field(..., description="Tool that was invoked")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters used")
    result: Dict[str, Any] = Field(..., description="Tool execution result")
    success: bool = Field(..., description="Whether tool execution succeeded")
    error: Optional[str] = Field(None, description="Error message if failed")

class SessionStartRequest(BaseModel):
    """Request model for session initialization"""
    user_id: str = Field(..., description="User identifier")
    project_id: str = Field(..., description="Project identifier")
    git_branch: Optional[str] = Field(None, description="Git branch name")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
```

```python
# src/api/models/responses.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class HookResponse(BaseModel):
    """Response model for hook processing"""
    blocked: bool = Field(False, description="Whether operation was blocked")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    hints: List[str] = Field(default_factory=list, description="Helpful hints")
    context_updates: Optional[Dict[str, Any]] = Field(None, description="Context updates")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        schema_extra = {
            "example": {
                "blocked": False,
                "errors": [],
                "warnings": ["File will be created in project root"],
                "hints": ["Consider using ai_docs/ for documentation"],
                "context_updates": {"files_modified": 1}
            }
        }

class SessionResponse(BaseModel):
    """Response model for session operations"""
    session_id: str = Field(..., description="Session identifier")
    context: Dict[str, Any] = Field(..., description="Session context")
    expires_at: datetime = Field(..., description="Session expiration time")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")

class ValidationResponse(BaseModel):
    """Response model for validation operations"""
    valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions")
    details: Optional[Dict[str, Any]] = Field(None, description="Validation details")
```

## Hook Engine Implementation

```python
# src/core/engine.py
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from ..validators import ValidatorRegistry
from ..processors import ProcessorRegistry
from ..session import SessionManager, Session
from ..clients import MCPClient
from .exceptions import ValidationError, ProcessingError

logger = logging.getLogger(__name__)

class HookEngine:
    """Core engine for processing hook requests"""

    def __init__(self, session_manager: SessionManager, mcp_client: MCPClient, redis):
        self.session_manager = session_manager
        self.mcp_client = mcp_client
        self.redis = redis
        self.validators = ValidatorRegistry()
        self.processors = ProcessorRegistry()

    async def process_pre_tool_use(self, request) -> Dict[str, Any]:
        """Process pre-tool-use hook with validation and context injection"""

        # 1. Load or create session
        session = await self._get_or_create_session(request.session_id, request)

        # 2. Run validators in parallel
        validation_tasks = []
        for validator_name in self.validators.get_validators_for_tool(request.tool):
            validator = self.validators.get(validator_name)
            validation_tasks.append(validator.validate(request, session))

        validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)

        # 3. Process validation results
        errors = []
        warnings = []
        hints = []
        blocked = False

        for result in validation_results:
            if isinstance(result, Exception):
                logger.error(f"Validator error: {result}")
                errors.append(str(result))
                blocked = True
            elif result and not result.is_valid:
                errors.extend(result.errors)
                warnings.extend(result.warnings)
                hints.extend(result.hints)
                blocked = blocked or result.should_block

        # 4. If not blocked, run processors
        context_updates = {}
        if not blocked:
            processor_tasks = []
            for processor_name in self.processors.get_processors_for_tool(request.tool):
                processor = self.processors.get(processor_name)
                processor_tasks.append(processor.process(request, session))

            processor_results = await asyncio.gather(*processor_tasks, return_exceptions=True)

            for result in processor_results:
                if isinstance(result, Exception):
                    logger.error(f"Processor error: {result}")
                elif result and hasattr(result, 'context_updates'):
                    context_updates.update(result.context_updates)

        # 5. Update session
        session.last_activity = datetime.utcnow()
        session.context.update(context_updates)
        await self.session_manager.update(session)

        # 6. Send updates to MCP if needed
        if context_updates and not blocked:
            await self._update_mcp_context(session, context_updates)

        return {
            "blocked": blocked,
            "errors": errors,
            "warnings": warnings,
            "hints": hints,
            "context_updates": context_updates
        }

    async def process_post_tool_use(self, request) -> Dict[str, Any]:
        """Process post-tool-use hook for logging and context updates"""

        # 1. Load session
        session = await self.session_manager.get(request.session_id)
        if not session:
            raise ProcessingError(f"Session not found: {request.session_id}")

        # 2. Run post-processors
        processor_tasks = []
        for processor_name in self.processors.get_post_processors():
            processor = self.processors.get(processor_name)
            processor_tasks.append(processor.post_process(request, session))

        results = await asyncio.gather(*processor_tasks, return_exceptions=True)

        # 3. Collect updates
        context_updates = {}
        hints = []

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Post-processor error: {result}")
            elif result:
                if hasattr(result, 'context_updates'):
                    context_updates.update(result.context_updates)
                if hasattr(result, 'hints'):
                    hints.extend(result.hints)

        # 4. Update session
        session.context.update(context_updates)
        await self.session_manager.update(session)

        # 5. Update MCP context
        if context_updates:
            await self._update_mcp_context(session, context_updates)

        return {
            "blocked": False,
            "errors": [],
            "warnings": [],
            "hints": hints,
            "context_updates": context_updates
        }

    async def start_session(self, request) -> Session:
        """Initialize a new session"""

        # Create session
        session = await self.session_manager.create(
            user_id=request.user_id,
            project_id=request.project_id,
            context=request.context or {}
        )

        # Initialize MCP context
        await self._initialize_mcp_context(session, request)

        # Run session start processors
        for processor_name in self.processors.get_session_processors():
            processor = self.processors.get(processor_name)
            await processor.on_session_start(session)

        return session

    async def cleanup_session(self, session_id: str):
        """Clean up session on disconnect"""

        session = await self.session_manager.get(session_id)
        if session:
            # Run cleanup processors
            for processor_name in self.processors.get_session_processors():
                processor = self.processors.get(processor_name)
                await processor.on_session_end(session)

            # Archive session
            await self.session_manager.archive(session_id)

    async def _get_or_create_session(self, session_id: str, request) -> Session:
        """Get existing session or create new one"""

        session = await self.session_manager.get(session_id)

        if not session:
            session = await self.session_manager.create(
                session_id=session_id,
                user_id=request.user_id,
                project_id=request.project_id,
                context=request.context or {}
            )

        return session

    async def _update_mcp_context(self, session: Session, updates: Dict[str, Any]):
        """Update MCP server with context changes"""

        try:
            await self.mcp_client.update_context(
                user_id=session.user_id,
                project_id=session.project_id,
                context_updates=updates
            )
        except Exception as e:
            logger.error(f"Failed to update MCP context: {e}")

    async def _initialize_mcp_context(self, session: Session, request):
        """Initialize MCP context for new session"""

        try:
            # Fetch existing context from MCP
            mcp_context = await self.mcp_client.get_context(
                user_id=session.user_id,
                project_id=session.project_id
            )

            # Merge with session context
            if mcp_context:
                session.context.update(mcp_context)
                await self.session_manager.update(session)

        except Exception as e:
            logger.error(f"Failed to initialize MCP context: {e}")
```

## Validation System

```python
# src/validators/file_system.py
import re
from pathlib import Path
from typing import List, Optional
import logging

from .base import BaseValidator, ValidationResult

logger = logging.getLogger(__name__)

class FileSystemValidator(BaseValidator):
    """Validates file system operations"""

    def __init__(self):
        super().__init__()
        self.load_rules()

    def load_rules(self):
        """Load file system validation rules"""

        # Load allowed root files
        self.allowed_root_files = self._load_allowed_files()

        # Load valid test paths
        self.valid_test_paths = self._load_test_paths()

        # Protected patterns
        self.protected_patterns = [
            r'\.env.*',           # Environment files
            r'\.git/.*',          # Git directory
            r'node_modules/.*',   # Node modules
            r'__pycache__/.*',    # Python cache
            r'\.venv/.*'          # Virtual environments
        ]

    async def validate(self, request, session) -> ValidationResult:
        """Validate file operation"""

        tool = request.tool
        params = request.parameters

        if tool in ["Write", "Edit", "MultiEdit"]:
            return await self._validate_write_operation(params, session)
        elif tool == "Bash":
            return await self._validate_bash_command(params, session)

        return ValidationResult(is_valid=True)

    async def _validate_write_operation(self, params, session) -> ValidationResult:
        """Validate file write operations"""

        file_path = Path(params.get("file_path", ""))
        errors = []
        warnings = []
        hints = []

        # Check if path is absolute
        if not file_path.is_absolute():
            file_path = Path("/project") / file_path

        # Check protected patterns
        for pattern in self.protected_patterns:
            if re.match(pattern, str(file_path)):
                errors.append(f"Cannot modify protected file: {file_path}")
                return ValidationResult(
                    is_valid=False,
                    should_block=True,
                    errors=errors
                )

        # Check root directory restrictions
        if file_path.parent == Path("/project"):
            if file_path.name not in self.allowed_root_files:
                errors.append(f"Cannot create {file_path.name} in project root")
                hints.append(f"Allowed root files: {', '.join(self.allowed_root_files)}")

                # Suggest appropriate location
                if file_path.suffix == ".md":
                    hints.append("Documentation files should go in ai_docs/")
                elif "test" in file_path.name.lower():
                    hints.append("Test files should go in appropriate test directories")

                return ValidationResult(
                    is_valid=False,
                    should_block=True,
                    errors=errors,
                    hints=hints
                )

        # Check documentation requirements
        doc_check = await self._check_documentation_requirement(file_path, session)
        if doc_check and not doc_check.is_valid:
            return doc_check

        # Check naming uniqueness
        if await self._check_duplicate_name(file_path):
            warnings.append(f"Similar filename exists elsewhere in project")

        return ValidationResult(
            is_valid=True,
            warnings=warnings,
            hints=hints
        )

    async def _validate_bash_command(self, params, session) -> ValidationResult:
        """Validate bash commands"""

        command = params.get("command", "")
        errors = []
        warnings = []

        # Dangerous command patterns
        dangerous_patterns = [
            r'rm\s+-rf\s+/',          # rm -rf /
            r'rm\s+-rf\s+\*',         # rm -rf *
            r'chmod\s+777',           # chmod 777
            r'curl.*\|.*bash',        # curl | bash
            r'wget.*\|.*sh'           # wget | sh
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command):
                errors.append(f"Dangerous command detected: {command}")
                return ValidationResult(
                    is_valid=False,
                    should_block=True,
                    errors=errors
                )

        # Check for file creation in bash
        if re.search(r'(touch|echo.*>|cat.*>)', command):
            # Extract potential file path
            match = re.search(r'(?:touch|>)\s+([^\s]+)', command)
            if match:
                file_path = Path(match.group(1))
                result = await self._validate_write_operation(
                    {"file_path": str(file_path)},
                    session
                )
                if not result.is_valid:
                    return result

        return ValidationResult(is_valid=True, warnings=warnings)

    def _load_allowed_files(self) -> List[str]:
        """Load allowed root files from configuration"""

        try:
            config_path = Path("/project/.allowed_root_files")
            if config_path.exists():
                return config_path.read_text().strip().split("\n")
        except Exception as e:
            logger.error(f"Failed to load allowed files: {e}")

        # Default allowed files
        return [
            "README.md",
            "CHANGELOG.md",
            "TEST-CHANGELOG.md",
            "CLAUDE.md",
            "CLAUDE.local.md",
            ".gitignore",
            "package.json",
            "requirements.txt",
            "docker-compose.yml"
        ]

    def _load_test_paths(self) -> List[str]:
        """Load valid test paths from configuration"""

        try:
            config_path = Path("/project/.valid_test_paths")
            if config_path.exists():
                return config_path.read_text().strip().split("\n")
        except Exception as e:
            logger.error(f"Failed to load test paths: {e}")

        # Default test paths
        return [
            "tests/",
            "test/",
            "src/tests/",
            "__tests__/",
            "spec/"
        ]

    async def _check_documentation_requirement(self, file_path: Path, session) -> Optional[ValidationResult]:
        """Check if file requires documentation update"""

        doc_path = Path("/project/ai_docs/_absolute_docs") / file_path.relative_to("/project").with_suffix(".md")

        if doc_path.exists():
            # Check if file is in session
            session_key = f"modified_files:{session.id}"
            is_in_session = await self.redis.sismember(session_key, str(file_path))

            if not is_in_session:
                # First modification in session - require doc update
                await self.redis.sadd(session_key, str(file_path))
                await self.redis.expire(session_key, 7200)  # 2 hour session

                return ValidationResult(
                    is_valid=False,
                    should_block=True,
                    errors=[f"File {file_path} has documentation that must be updated"],
                    hints=[f"Update documentation at: {doc_path}"]
                )

        return None

    async def _check_duplicate_name(self, file_path: Path) -> bool:
        """Check for duplicate filenames in project"""

        # Implementation would check for similar names
        # This is simplified for brevity
        return False
```

## Session Management

```python
# src/session/manager.py
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import logging

from .models import Session
from .storage import RedisStorage, PostgreSQLStorage

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages hook sessions with multi-tier storage"""

    def __init__(self, redis_client, postgres_client=None):
        self.redis_storage = RedisStorage(redis_client)
        self.postgres_storage = PostgreSQLStorage(postgres_client) if postgres_client else None
        self.session_ttl = 7200  # 2 hours

    async def create(self, user_id: str, project_id: str,
                    context: Optional[Dict[str, Any]] = None,
                    session_id: Optional[str] = None) -> Session:
        """Create a new session"""

        session = Session(
            id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            project_id=project_id,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(seconds=self.session_ttl),
            context=context or {},
            metadata={}
        )

        # Store in Redis for fast access
        await self.redis_storage.save(session)

        # Persist to PostgreSQL if available
        if self.postgres_storage:
            await self.postgres_storage.save(session)

        logger.info(f"Created session: {session.id}")
        return session

    async def get(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""

        # Try Redis first (L1 cache)
        session = await self.redis_storage.get(session_id)

        if not session and self.postgres_storage:
            # Fallback to PostgreSQL (L2 storage)
            session = await self.postgres_storage.get(session_id)

            if session:
                # Restore to Redis
                await self.redis_storage.save(session)

        return session

    async def update(self, session: Session) -> bool:
        """Update existing session"""

        session.last_activity = datetime.utcnow()

        # Update in Redis
        success = await self.redis_storage.update(session)

        # Update in PostgreSQL
        if self.postgres_storage:
            await self.postgres_storage.update(session)

        return success

    async def delete(self, session_id: str) -> bool:
        """Delete session"""

        # Remove from Redis
        success = await self.redis_storage.delete(session_id)

        # Mark as deleted in PostgreSQL (soft delete)
        if self.postgres_storage:
            await self.postgres_storage.soft_delete(session_id)

        logger.info(f"Deleted session: {session_id}")
        return success

    async def archive(self, session_id: str) -> bool:
        """Archive session for long-term storage"""

        session = await self.get(session_id)

        if session and self.postgres_storage:
            # Ensure persisted to PostgreSQL
            await self.postgres_storage.save(session)

            # Remove from Redis to free memory
            await self.redis_storage.delete(session_id)

            logger.info(f"Archived session: {session_id}")
            return True

        return False

    async def extend(self, session_id: str, seconds: int = 3600) -> bool:
        """Extend session expiration"""

        session = await self.get(session_id)

        if session:
            session.expires_at = datetime.utcnow() + timedelta(seconds=seconds)
            return await self.update(session)

        return False

    async def cleanup_expired(self):
        """Clean up expired sessions"""

        # Get all session keys from Redis
        session_keys = await self.redis_storage.get_all_keys()

        for key in session_keys:
            session_id = key.split(":")[-1]
            session = await self.get(session_id)

            if session and session.is_expired():
                await self.archive(session_id)
                logger.info(f"Cleaned up expired session: {session_id}")
```

## Testing Strategy

```python
# tests/unit/test_validators.py
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.validators.file_system import FileSystemValidator
from src.validators.base import ValidationResult

@pytest.fixture
def file_validator():
    """Create file system validator instance"""
    validator = FileSystemValidator()
    validator.redis = AsyncMock()
    return validator

@pytest.mark.asyncio
async def test_validate_protected_file(file_validator):
    """Test validation blocks protected files"""

    request = Mock(
        tool="Write",
        parameters={"file_path": ".env"}
    )
    session = Mock(id="test-session")

    result = await file_validator.validate(request, session)

    assert not result.is_valid
    assert result.should_block
    assert any("protected" in err.lower() for err in result.errors)

@pytest.mark.asyncio
async def test_validate_root_file_restriction(file_validator):
    """Test validation of root directory files"""

    request = Mock(
        tool="Write",
        parameters={"file_path": "/project/test.py"}
    )
    session = Mock(id="test-session")

    result = await file_validator.validate(request, session)

    assert not result.is_valid
    assert any("root" in err.lower() for err in result.errors)
    assert len(result.hints) > 0

@pytest.mark.asyncio
async def test_validate_allowed_root_file(file_validator):
    """Test validation allows permitted root files"""

    request = Mock(
        tool="Write",
        parameters={"file_path": "/project/README.md"}
    )
    session = Mock(id="test-session")

    result = await file_validator.validate(request, session)

    assert result.is_valid
    assert not result.should_block

@pytest.mark.asyncio
async def test_validate_dangerous_command(file_validator):
    """Test validation blocks dangerous commands"""

    request = Mock(
        tool="Bash",
        parameters={"command": "rm -rf /"}
    )
    session = Mock(id="test-session")

    result = await file_validator.validate(request, session)

    assert not result.is_valid
    assert result.should_block
    assert any("dangerous" in err.lower() for err in result.errors)
```

## Migration Path

### Phase 1: Preparation (Week 1)
1. Set up project structure
2. Implement core components
3. Create Docker configuration
4. Write unit tests

### Phase 2: Integration (Week 2)
1. Integrate with existing hooks
2. Set up API endpoints
3. Configure Redis and PostgreSQL
4. Test with Claude Code

### Phase 3: Migration (Week 3)
1. Run parallel with existing system
2. Migrate session data
3. Update Claude Code configuration
4. Monitor performance

### Phase 4: Optimization (Week 4)
1. Performance tuning
2. Add monitoring and metrics
3. Implement auto-scaling
4. Production deployment

## Conclusion

This technical implementation guide provides a complete blueprint for containerizing the Claude hooks system. The solution offers:

- **Scalability** through containerization and microservices
- **Reliability** with health checks and error handling
- **Performance** via caching and async processing
- **Security** through authentication and encryption
- **Maintainability** with clean architecture and testing

The implementation can be deployed incrementally, allowing for gradual migration from the existing file-based system to the containerized solution.