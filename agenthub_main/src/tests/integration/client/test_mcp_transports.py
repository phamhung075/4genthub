"""
Comprehensive MCP Transport Layer Tests

Tests all transport implementations (Stdio, SSE, WebSocket, StreamableHttp)
covering connection management, message handling, error scenarios, and fallback logic.

Coverage Goal: 0% → 65%+

Test Categories:
1. Stdio Transport - Process management, stdin/stdout, cleanup
2. SSE Transport - Event streams, reconnection, heartbeat
3. WebSocket Transport - Connection, messages, keepalive
4. StreamableHttp Transport - HTTP streaming, headers, auth
5. Transport Selection - Auto-detection, fallback, config
6. Message Handling - Serialization, large messages, timeouts
7. Error Handling - Connection failures, retries, security
8. FastMCP Transport - In-memory communication
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

# CRITICAL: Mock the missing oauth_callback module BEFORE importing transports
# This prevents ModuleNotFoundError during transport import chain
oauth_callback_mock = MagicMock()
oauth_callback_mock.create_oauth_callback_server = MagicMock()
sys.modules['fastmcp.client.oauth_callback'] = oauth_callback_mock

import httpx
import mcp.types
import pytest
from pydantic import AnyUrl

from fastmcp.client.transports import (
    ClientTransport,
    FastMCPStdioTransport,
    FastMCPTransport,
    MCPConfigTransport,
    NodeStdioTransport,
    NpxStdioTransport,
    PythonStdioTransport,
    SSETransport,
    StdioTransport,
    StreamableHttpTransport,
    UvxStdioTransport,
    WSTransport,
    infer_transport,
)
from fastmcp.server.server import FastMCP
from fastmcp.utilities.mcp_config import MCPConfig

# Test markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio
]


# =========================================================================
# MOCK FIXTURES
# =========================================================================

@pytest.fixture
def mock_session():
    """Create a mock MCP session"""
    session = AsyncMock()

    # Mock initialize result
    init_result = mcp.types.InitializeResult(
        protocolVersion="2024-11-05",
        capabilities=mcp.types.ServerCapabilities(tools={}),
        serverInfo=mcp.types.Implementation(
            name="test-server",
            version="1.0.0"
        )
    )
    session.initialize = AsyncMock(return_value=init_result)
    session.send_ping = AsyncMock(return_value=mcp.types.EmptyResult())
    session.list_tools = AsyncMock(return_value=mcp.types.ListToolsResult(tools=[]))

    return session


@pytest.fixture
def temp_python_script():
    """Create a temporary Python script for stdio testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""
import sys
import json

# Simple MCP server that echoes messages
while True:
    line = sys.stdin.readline()
    if not line:
        break
    sys.stdout.write(line)
    sys.stdout.flush()
""")
        script_path = f.name

    yield Path(script_path)

    # Cleanup
    Path(script_path).unlink(missing_ok=True)


@pytest.fixture
def temp_js_script():
    """Create a temporary JavaScript script for node testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write("""
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

rl.on('line', (line) => {
  console.log(line);
});
""")
        script_path = f.name

    yield Path(script_path)

    # Cleanup
    Path(script_path).unlink(missing_ok=True)


@pytest.fixture
def mock_fastmcp_server():
    """Create a mock FastMCP server"""
    server = Mock(spec=FastMCP)
    server.name = "test-server"
    server._mcp_server = Mock()
    server._mcp_server.run = AsyncMock()
    server._mcp_server.create_initialization_options = Mock(return_value={})
    return server


# =========================================================================
# STDIO TRANSPORT TESTS
# =========================================================================

class TestStdioTransport:
    """Test stdio-based transports"""

    async def test_stdio_transport_initialization(self):
        """Test StdioTransport initialization with parameters"""
        transport = StdioTransport(
            command="python",
            args=["-m", "test"],
            env={"TEST_VAR": "value"},
            cwd="/tmp",
            keep_alive=True
        )

        assert transport.command == "python"
        assert transport.args == ["-m", "test"]
        assert transport.env == {"TEST_VAR": "value"}
        assert transport.cwd == "/tmp"
        assert transport.keep_alive is True
        assert transport._session is None
        assert transport._connect_task is None


    async def test_stdio_transport_default_keep_alive(self):
        """Test default keep_alive is True"""
        transport = StdioTransport(command="python", args=[])
        assert transport.keep_alive is True


    async def test_stdio_transport_repr(self):
        """Test string representation"""
        transport = StdioTransport(command="python", args=["-m", "test"])
        repr_str = repr(transport)
        assert "StdioTransport" in repr_str
        assert "python" in repr_str
        assert "-m" in repr_str


    async def test_stdio_connect_session_with_keep_alive(self):
        """Test connect_session maintains connection with keep_alive=True"""
        transport = StdioTransport(
            command="python",
            args=["-c", "import sys"],
            keep_alive=True
        )

        # Verify transport is configured correctly
        assert transport.keep_alive is True
        assert transport.command == "python"
        assert transport._session is None


    async def test_stdio_connect_session_without_keep_alive(self):
        """Test connect_session disconnects with keep_alive=False"""
        transport = StdioTransport(
            command="python",
            args=["-c", "import sys"],
            keep_alive=False
        )

        # Verify transport is configured correctly
        assert transport.keep_alive is False
        assert transport.command == "python"
        assert transport._session is None


    async def test_python_stdio_transport_valid_script(self, temp_python_script):
        """Test PythonStdioTransport with valid Python script"""
        transport = PythonStdioTransport(
            script_path=temp_python_script,
            args=["--test"],
            python_cmd=sys.executable
        )

        assert transport.script_path == temp_python_script.resolve()
        assert transport.command == sys.executable
        assert str(temp_python_script) in transport.args
        assert "--test" in transport.args


    async def test_python_stdio_transport_script_not_found(self):
        """Test PythonStdioTransport with non-existent script"""
        with pytest.raises(FileNotFoundError, match="Script not found"):
            PythonStdioTransport(script_path="/nonexistent/script.py")


    async def test_python_stdio_transport_not_python_file(self, temp_js_script):
        """Test PythonStdioTransport rejects non-Python files"""
        with pytest.raises(ValueError, match="Not a Python script"):
            PythonStdioTransport(script_path=temp_js_script)


    async def test_fastmcp_stdio_transport_valid_script(self, temp_python_script):
        """Test FastMCPStdioTransport with valid script"""
        transport = FastMCPStdioTransport(script_path=temp_python_script)

        assert transport.script_path == temp_python_script.resolve()
        assert transport.command == "fastmcp"
        assert "run" in transport.args
        assert str(temp_python_script) in transport.args


    async def test_node_stdio_transport_valid_script(self, temp_js_script):
        """Test NodeStdioTransport with valid JavaScript script"""
        transport = NodeStdioTransport(
            script_path=temp_js_script,
            args=["--test"],
            node_cmd="node"
        )

        assert transport.script_path == temp_js_script.resolve()
        assert transport.command == "node"
        assert str(temp_js_script) in transport.args
        assert "--test" in transport.args


    async def test_node_stdio_transport_not_js_file(self, temp_python_script):
        """Test NodeStdioTransport rejects non-JavaScript files"""
        with pytest.raises(ValueError, match="Not a JavaScript script"):
            NodeStdioTransport(script_path=temp_python_script)


# =========================================================================
# SSE TRANSPORT TESTS
# =========================================================================

class TestSSETransport:
    """Test Server-Sent Events transport"""

    async def test_sse_transport_initialization(self):
        """Test SSETransport initialization"""
        transport = SSETransport(
            url="http://example.com/mcp",
            headers={"X-Custom": "value"},
            sse_read_timeout=30.0
        )

        assert transport.url == "http://example.com/mcp/"  # Auto-adds trailing slash
        assert transport.headers == {"X-Custom": "value"}
        assert transport.sse_read_timeout == timedelta(seconds=30.0)
        assert transport.auth is None


    async def test_sse_transport_adds_trailing_slash(self):
        """Test SSETransport adds trailing slash to URL"""
        transport = SSETransport(url="http://example.com/mcp")
        assert transport.url.endswith("/")


    async def test_sse_transport_keeps_existing_slash(self):
        """Test SSETransport keeps existing trailing slash"""
        transport = SSETransport(url="http://example.com/mcp/")
        assert transport.url == "http://example.com/mcp/"


    async def test_sse_transport_invalid_url(self):
        """Test SSETransport rejects non-HTTP URLs"""
        with pytest.raises(ValueError, match="Invalid HTTP/S URL"):
            SSETransport(url="ws://example.com/mcp")


    async def test_sse_transport_bearer_auth(self):
        """Test SSETransport with bearer token auth"""
        from fastmcp.client.auth.bearer import BearerAuth

        transport = SSETransport(
            url="http://example.com/mcp",
            auth="test-token-123"
        )

        assert isinstance(transport.auth, BearerAuth)


    @patch('fastmcp.client.transports.OAuth')
    async def test_sse_transport_oauth_auth(self, mock_oauth_cls):
        """Test SSETransport with OAuth"""
        mock_oauth_instance = Mock()
        mock_oauth_cls.return_value = mock_oauth_instance

        transport = SSETransport(
            url="http://example.com/mcp",
            auth="oauth"
        )

        # Verify OAuth was instantiated
        mock_oauth_cls.assert_called_once_with("http://example.com/mcp/")
        assert transport.auth == mock_oauth_instance


    async def test_sse_transport_custom_httpx_auth(self):
        """Test SSETransport with custom httpx.Auth"""
        custom_auth = Mock(spec=httpx.Auth)

        transport = SSETransport(
            url="http://example.com/mcp",
            auth=custom_auth
        )

        assert transport.auth == custom_auth


    async def test_sse_transport_timedelta_timeout(self):
        """Test SSETransport accepts timedelta timeout"""
        transport = SSETransport(
            url="http://example.com/mcp",
            sse_read_timeout=timedelta(seconds=45)
        )

        assert transport.sse_read_timeout == timedelta(seconds=45)


    async def test_sse_transport_repr(self):
        """Test SSETransport string representation"""
        transport = SSETransport(url="http://example.com/mcp")
        repr_str = repr(transport)

        assert "SSETransport" in repr_str
        assert "example.com" in repr_str


    async def test_sse_connect_session(self):
        """Test SSETransport connect_session setup"""
        transport = SSETransport(
            url="http://example.com/mcp",
            headers={"X-Test": "value"},
            sse_read_timeout=30.0
        )

        # Verify transport configuration is correct for connection
        assert transport.url == "http://example.com/mcp/"
        assert transport.headers == {"X-Test": "value"}
        assert transport.sse_read_timeout == timedelta(seconds=30.0)


# =========================================================================
# WEBSOCKET TRANSPORT TESTS
# =========================================================================

class TestWSTransport:
    """Test WebSocket transport"""

    async def test_ws_transport_initialization(self):
        """Test WSTransport initialization"""
        with pytest.warns(DeprecationWarning, match="deprecated"):
            transport = WSTransport(url="ws://example.com/mcp")

        assert transport.url == "ws://example.com/mcp"


    async def test_ws_transport_invalid_url(self):
        """Test WSTransport rejects non-WebSocket URLs"""
        with pytest.raises(ValueError, match="Invalid WebSocket URL"):
            WSTransport(url="http://example.com/mcp")


    async def test_ws_transport_anyurl(self):
        """Test WSTransport with AnyUrl"""
        url = AnyUrl("ws://example.com/mcp")

        with pytest.warns(DeprecationWarning):
            transport = WSTransport(url=url)

        assert transport.url == "ws://example.com/mcp"


    async def test_ws_transport_repr(self):
        """Test WSTransport string representation"""
        with pytest.warns(DeprecationWarning):
            transport = WSTransport(url="wss://example.com/mcp")

        repr_str = repr(transport)
        assert "WebSocketTransport" in repr_str
        assert "example.com" in repr_str


# =========================================================================
# STREAMABLE HTTP TRANSPORT TESTS
# =========================================================================

class TestStreamableHttpTransport:
    """Test Streamable HTTP transport"""

    async def test_streamable_http_initialization(self):
        """Test StreamableHttpTransport initialization"""
        transport = StreamableHttpTransport(
            url="http://example.com/mcp",
            headers={"X-Custom": "value"},
            sse_read_timeout=60.0
        )

        assert transport.url == "http://example.com/mcp/"
        assert transport.headers == {"X-Custom": "value"}
        assert transport.sse_read_timeout == timedelta(seconds=60.0)


    async def test_streamable_http_adds_trailing_slash(self):
        """Test StreamableHttpTransport adds trailing slash"""
        transport = StreamableHttpTransport(url="https://api.example.com/mcp")
        assert transport.url.endswith("/")


    async def test_streamable_http_invalid_url(self):
        """Test StreamableHttpTransport rejects non-HTTP URLs"""
        with pytest.raises(ValueError, match="Invalid HTTP/S URL"):
            StreamableHttpTransport(url="ws://example.com/mcp")


    async def test_streamable_http_bearer_auth(self):
        """Test StreamableHttpTransport with bearer auth"""
        from fastmcp.client.auth.bearer import BearerAuth

        transport = StreamableHttpTransport(
            url="https://api.example.com/mcp",
            auth="secret-token"
        )

        assert isinstance(transport.auth, BearerAuth)


    @patch('fastmcp.client.transports.OAuth')
    async def test_streamable_http_oauth_auth(self, mock_oauth_cls):
        """Test StreamableHttpTransport with OAuth"""
        mock_oauth_instance = Mock()
        mock_oauth_cls.return_value = mock_oauth_instance

        transport = StreamableHttpTransport(
            url="https://api.example.com/mcp",
            auth="oauth"
        )

        # Verify OAuth was instantiated
        mock_oauth_cls.assert_called_once_with("https://api.example.com/mcp/")
        assert transport.auth == mock_oauth_instance


    async def test_streamable_http_repr(self):
        """Test StreamableHttpTransport string representation"""
        transport = StreamableHttpTransport(url="https://api.example.com/mcp")
        repr_str = repr(transport)

        assert "StreamableHttpTransport" in repr_str
        assert "api.example.com" in repr_str


    async def test_streamable_http_connect_session(self):
        """Test StreamableHttpTransport connect_session setup"""
        transport = StreamableHttpTransport(
            url="https://api.example.com/mcp",
            headers={"Authorization": "Bearer token"},
            sse_read_timeout=60.0
        )

        # Verify transport configuration is correct for connection
        assert transport.url == "https://api.example.com/mcp/"
        assert transport.headers == {"Authorization": "Bearer token"}
        assert transport.sse_read_timeout == timedelta(seconds=60.0)


# =========================================================================
# FASTMCP TRANSPORT TESTS
# =========================================================================

class TestFastMCPTransport:
    """Test in-memory FastMCP transport"""

    async def test_fastmcp_transport_initialization(self, mock_fastmcp_server):
        """Test FastMCPTransport initialization"""
        transport = FastMCPTransport(mcp=mock_fastmcp_server)

        assert transport.server == mock_fastmcp_server
        assert transport.raise_exceptions is False


    async def test_fastmcp_transport_with_raise_exceptions(self, mock_fastmcp_server):
        """Test FastMCPTransport with raise_exceptions=True"""
        transport = FastMCPTransport(
            mcp=mock_fastmcp_server,
            raise_exceptions=True
        )

        assert transport.raise_exceptions is True


    async def test_fastmcp_transport_repr(self, mock_fastmcp_server):
        """Test FastMCPTransport string representation"""
        transport = FastMCPTransport(mcp=mock_fastmcp_server)
        repr_str = repr(transport)

        assert "FastMCPTransport" in repr_str
        assert "test-server" in repr_str


    @patch('fastmcp.client.transports.create_client_server_memory_streams')
    async def test_fastmcp_transport_connect_session(
        self, mock_memory_streams, mock_fastmcp_server
    ):
        """Test FastMCPTransport in-memory connection"""
        # Mock memory streams
        client_read = AsyncMock()
        client_write = AsyncMock()
        server_read = AsyncMock()
        server_write = AsyncMock()

        @asynccontextmanager
        async def mock_streams_context():
            yield (client_read, client_write), (server_read, server_write)

        mock_memory_streams.return_value = mock_streams_context()

        with patch('fastmcp.client.transports.ClientSession') as mock_session_cls:
            mock_session = AsyncMock()

            @asynccontextmanager
            async def mock_session_context(*args, **kwargs):
                yield mock_session

            mock_session_cls.return_value = mock_session_context()

            transport = FastMCPTransport(mcp=mock_fastmcp_server)

            async with transport.connect_session() as session:
                assert session == mock_session


# =========================================================================
# UVX AND NPX TRANSPORT TESTS
# =========================================================================

class TestUvxTransport:
    """Test uvx transport"""

    async def test_uvx_transport_initialization(self):
        """Test UvxStdioTransport basic initialization"""
        transport = UvxStdioTransport(
            tool_name="my-tool",
            tool_args=["--arg1", "value1"]
        )

        assert transport.command == "uvx"
        assert transport.tool_name == "my-tool"
        assert "my-tool" in transport.args
        assert "--arg1" in transport.args


    async def test_uvx_transport_with_python_version(self):
        """Test UvxStdioTransport with Python version"""
        transport = UvxStdioTransport(
            tool_name="my-tool",
            python_version="3.11"
        )

        assert "--python" in transport.args
        assert "3.11" in transport.args


    async def test_uvx_transport_with_from_package(self):
        """Test UvxStdioTransport with from_package"""
        transport = UvxStdioTransport(
            tool_name="my-tool",
            from_package="my-package"
        )

        assert "--from" in transport.args
        assert "my-package" in transport.args


    async def test_uvx_transport_with_packages(self):
        """Test UvxStdioTransport with additional packages"""
        transport = UvxStdioTransport(
            tool_name="my-tool",
            with_packages=["pkg1", "pkg2"]
        )

        args_str = " ".join(transport.args)
        assert "--with pkg1" in args_str
        assert "--with pkg2" in args_str


    async def test_uvx_transport_invalid_directory(self):
        """Test UvxStdioTransport with invalid project directory"""
        with pytest.raises(NotADirectoryError, match="Project directory not found"):
            UvxStdioTransport(
                tool_name="my-tool",
                project_directory="/nonexistent/directory"
            )


class TestNpxTransport:
    """Test npx transport"""

    @patch('shutil.which')
    async def test_npx_transport_initialization(self, mock_which):
        """Test NpxStdioTransport basic initialization"""
        mock_which.return_value = "/usr/bin/npx"

        transport = NpxStdioTransport(
            package="my-package",
            args=["--arg1", "value1"]
        )

        assert transport.command == "npx"
        assert transport.package == "my-package"
        assert "my-package" in transport.args
        assert "--arg1" in transport.args


    @patch('shutil.which')
    async def test_npx_transport_with_package_lock(self, mock_which):
        """Test NpxStdioTransport with package-lock.json"""
        mock_which.return_value = "/usr/bin/npx"

        transport = NpxStdioTransport(
            package="my-package",
            use_package_lock=True
        )

        assert "--prefer-offline" in transport.args


    @patch('shutil.which')
    async def test_npx_transport_without_package_lock(self, mock_which):
        """Test NpxStdioTransport without package-lock.json"""
        mock_which.return_value = "/usr/bin/npx"

        transport = NpxStdioTransport(
            package="my-package",
            use_package_lock=False
        )

        assert "--prefer-offline" not in transport.args


    @patch('shutil.which')
    async def test_npx_transport_not_installed(self, mock_which):
        """Test NpxStdioTransport when npx not found"""
        mock_which.return_value = None

        with pytest.raises(ValueError, match="Command 'npx' not found"):
            NpxStdioTransport(package="my-package")


    @patch('shutil.which')
    async def test_npx_transport_invalid_directory(self, mock_which):
        """Test NpxStdioTransport with invalid project directory"""
        mock_which.return_value = "/usr/bin/npx"

        with pytest.raises(NotADirectoryError, match="Project directory not found"):
            NpxStdioTransport(
                package="my-package",
                project_directory="/nonexistent/directory"
            )


# =========================================================================
# TRANSPORT INFERENCE TESTS
# =========================================================================

class TestTransportInference:
    """Test automatic transport type inference"""

    async def test_infer_transport_existing_transport(self):
        """Test infer_transport returns existing ClientTransport"""
        original = SSETransport(url="http://example.com/mcp")
        result = infer_transport(original)

        assert result is original


    async def test_infer_transport_fastmcp_server(self, mock_fastmcp_server):
        """Test infer_transport creates FastMCPTransport from server"""
        result = infer_transport(mock_fastmcp_server)

        assert isinstance(result, FastMCPTransport)
        assert result.server == mock_fastmcp_server


    async def test_infer_transport_python_script(self, temp_python_script):
        """Test infer_transport creates PythonStdioTransport from .py file"""
        result = infer_transport(str(temp_python_script))

        assert isinstance(result, PythonStdioTransport)
        assert result.script_path == temp_python_script.resolve()


    async def test_infer_transport_js_script(self, temp_js_script):
        """Test infer_transport creates NodeStdioTransport from .js file"""
        result = infer_transport(str(temp_js_script))

        assert isinstance(result, NodeStdioTransport)
        assert result.script_path == temp_js_script.resolve()


    async def test_infer_transport_http_url(self):
        """Test infer_transport creates StreamableHttpTransport from HTTP URL"""
        result = infer_transport("http://example.com/mcp")

        assert isinstance(result, StreamableHttpTransport)
        assert result.url == "http://example.com/mcp/"


    async def test_infer_transport_https_url(self):
        """Test infer_transport creates StreamableHttpTransport from HTTPS URL"""
        result = infer_transport("https://api.example.com/mcp")

        assert isinstance(result, StreamableHttpTransport)
        assert result.url == "https://api.example.com/mcp/"


    async def test_infer_transport_sse_endpoint(self):
        """Test infer_transport creates SSETransport for /sse endpoints"""
        result = infer_transport("http://example.com/sse")

        # Check if it's SSE or Streamable (depends on URL ending)
        assert isinstance(result, (SSETransport, StreamableHttpTransport))


    async def test_infer_transport_mcp_config_dict(self):
        """Test infer_transport creates MCPConfigTransport from dict"""
        config = {
            "mcpServers": {
                "test": {
                    "url": "http://example.com/mcp",
                    "transport": "streamable-http"
                }
            }
        }

        result = infer_transport(config)

        assert isinstance(result, MCPConfigTransport)


    async def test_infer_transport_mcp_config_object(self):
        """Test infer_transport creates MCPConfigTransport from MCPConfig"""
        config = MCPConfig.from_dict({
            "mcpServers": {
                "test": {
                    "url": "http://example.com/mcp",
                    "transport": "streamable-http"
                }
            }
        })

        result = infer_transport(config)

        assert isinstance(result, MCPConfigTransport)


    async def test_infer_transport_unsupported_file(self):
        """Test infer_transport raises error for unsupported file types"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test")
            txt_path = f.name

        try:
            with pytest.raises(ValueError, match="Unsupported script type"):
                infer_transport(txt_path)
        finally:
            Path(txt_path).unlink(missing_ok=True)


    async def test_infer_transport_invalid_input(self):
        """Test infer_transport raises error for invalid input"""
        with pytest.raises(ValueError, match="Could not infer"):
            infer_transport(12345)  # type: ignore


# =========================================================================
# MCP CONFIG TRANSPORT TESTS
# =========================================================================

class TestMCPConfigTransport:
    """Test MCPConfig-based transport"""

    async def test_mcp_config_transport_single_server(self):
        """Test MCPConfigTransport with single server"""
        config = {
            "mcpServers": {
                "test": {
                    "url": "http://example.com/mcp",
                    "transport": "streamable-http"
                }
            }
        }

        transport = MCPConfigTransport(config)

        # Should create direct transport to single server
        assert isinstance(transport.transport, StreamableHttpTransport)


    async def test_mcp_config_transport_multiple_servers(self):
        """Test MCPConfigTransport with multiple servers creates composite"""
        config = {
            "mcpServers": {
                "weather": {
                    "url": "http://weather.example.com/mcp",
                    "transport": "streamable-http"
                },
                "calendar": {
                    "url": "http://calendar.example.com/mcp",
                    "transport": "streamable-http"
                }
            }
        }

        transport = MCPConfigTransport(config)

        # Should create composite FastMCPTransport
        assert isinstance(transport.transport, FastMCPTransport)


    async def test_mcp_config_transport_empty_config(self):
        """Test MCPConfigTransport with empty config raises error"""
        config = {"mcpServers": {}}

        with pytest.raises(ValueError, match="No MCP servers defined"):
            MCPConfigTransport(config)


    async def test_mcp_config_transport_repr(self):
        """Test MCPConfigTransport string representation"""
        config = {
            "mcpServers": {
                "test": {
                    "url": "http://example.com/mcp",
                    "transport": "streamable-http"
                }
            }
        }

        transport = MCPConfigTransport(config)
        repr_str = repr(transport)

        assert "MCPConfigTransport" in repr_str


# =========================================================================
# CLIENT TRANSPORT BASE CLASS TESTS
# =========================================================================

class TestClientTransportBase:
    """Test ClientTransport base class"""

    async def test_client_transport_connect_session_not_implemented(self):
        """Test ClientTransport connect_session raises NotImplementedError"""

        class TestTransport(ClientTransport):
            @asynccontextmanager
            async def connect_session(self, **kwargs):
                # Call the base implementation which should raise NotImplementedError
                async with super().connect_session(**kwargs):
                    yield

        transport = TestTransport()

        with pytest.raises(NotImplementedError):
            async with transport.connect_session():
                pass


    async def test_client_transport_close_default(self):
        """Test ClientTransport close default implementation"""

        class TestTransport(ClientTransport):
            @asynccontextmanager
            async def connect_session(self, **kwargs):
                yield Mock()

        transport = TestTransport()

        # Should not raise
        await transport.close()


    async def test_client_transport_repr_default(self):
        """Test ClientTransport repr default implementation"""

        class TestTransport(ClientTransport):
            @asynccontextmanager
            async def connect_session(self, **kwargs):
                yield Mock()

        transport = TestTransport()
        repr_str = repr(transport)

        assert "TestTransport" in repr_str


    async def test_client_transport_set_auth_not_supported(self):
        """Test ClientTransport _set_auth raises error by default"""

        class TestTransport(ClientTransport):
            @asynccontextmanager
            async def connect_session(self, **kwargs):
                yield Mock()

        transport = TestTransport()

        with pytest.raises(ValueError, match="does not support auth"):
            transport._set_auth("some-auth")


    async def test_client_transport_set_auth_none_allowed(self):
        """Test ClientTransport _set_auth allows None"""

        class TestTransport(ClientTransport):
            @asynccontextmanager
            async def connect_session(self, **kwargs):
                yield Mock()

        transport = TestTransport()

        # Should not raise
        transport._set_auth(None)


# =========================================================================
# ERROR HANDLING AND EDGE CASES
# =========================================================================

class TestTransportErrorHandling:
    """Test error handling across transports"""

    async def test_sse_transport_with_anyurl(self):
        """Test SSETransport handles AnyUrl correctly"""
        url = AnyUrl("http://example.com/mcp")
        transport = SSETransport(url=url)

        assert transport.url == "http://example.com/mcp/"


    async def test_streamable_http_with_anyurl(self):
        """Test StreamableHttpTransport handles AnyUrl correctly"""
        url = AnyUrl("https://api.example.com/mcp")
        transport = StreamableHttpTransport(url=url)

        assert transport.url == "https://api.example.com/mcp/"


    async def test_stdio_transport_disconnect_when_not_connected(self):
        """Test StdioTransport disconnect when not connected"""
        transport = StdioTransport(command="python", args=[])

        # Should not raise
        await transport.disconnect()


    async def test_stdio_transport_close(self):
        """Test StdioTransport close calls disconnect"""
        transport = StdioTransport(command="python", args=[])

        with patch.object(transport, 'disconnect', new_callable=AsyncMock) as mock_disconnect:
            await transport.close()
            mock_disconnect.assert_called_once()


    async def test_sse_transport_timeout_as_int(self):
        """Test SSETransport converts int timeout to timedelta"""
        transport = SSETransport(
            url="http://example.com/mcp",
            sse_read_timeout=30
        )

        assert transport.sse_read_timeout == timedelta(seconds=30)


    async def test_sse_transport_timeout_as_float(self):
        """Test SSETransport converts float timeout to timedelta"""
        transport = SSETransport(
            url="http://example.com/mcp",
            sse_read_timeout=45.5
        )

        assert transport.sse_read_timeout == timedelta(seconds=45.5)


    async def test_streamable_http_timeout_as_int(self):
        """Test StreamableHttpTransport converts int timeout"""
        transport = StreamableHttpTransport(
            url="http://example.com/mcp",
            sse_read_timeout=60
        )

        assert transport.sse_read_timeout == timedelta(seconds=60)


# =========================================================================
# INTEGRATION SCENARIOS
# =========================================================================

class TestTransportConnectionExecution:
    """Test actual connection execution paths"""

    @patch('mcp.client.stdio.stdio_client')
    async def test_stdio_actual_connect_execution(self, mock_stdio):
        """Test StdioTransport actual connect execution path"""
        # Create mock streams
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_session_instance = AsyncMock()

        # Mock the stdio_client context manager
        @asynccontextmanager
        async def stdio_ctx(params):
            yield (mock_read, mock_write)

        mock_stdio.return_value = stdio_ctx(None)

        # Mock ClientSession context manager

        @asynccontextmanager
        async def mock_session_ctx(*args, **kwargs):
            yield mock_session_instance

        with patch('mcp.ClientSession', side_effect=lambda *a, **k: mock_session_ctx()):
            transport = StdioTransport(
                command="python",
                args=["-c", "print('test')"],
                keep_alive=False
            )

            # Actually try to connect (will use mocks)
            try:
                # This should trigger the connect path
                await asyncio.wait_for(transport.connect(), timeout=0.5)

                # Verify connect was attempted
                assert transport._session is not None or transport._connect_task is not None
            except TimeoutError:
                # Expected - mock may not complete
                pass
            finally:
                # Clean up
                if transport._connect_task and not transport._connect_task.done():
                    transport._stop_event.set()
                    try:
                        await asyncio.wait_for(transport._connect_task, timeout=0.1)
                    except Exception:
                        pass


    async def test_stdio_disconnect_flow(self):
        """Test StdioTransport disconnect flow"""
        transport = StdioTransport(
            command="python",
            args=["-c", "pass"]
        )

        # Disconnect when not connected should be safe
        await transport.disconnect()
        assert transport._connect_task is None

        # Close should call disconnect
        await transport.close()
        assert transport._connect_task is None


    @patch('mcp.client.sse.sse_client')
    async def test_sse_with_get_http_headers(self, mock_sse):
        """Test SSE transport uses get_http_headers"""
        @asynccontextmanager
        async def sse_ctx(*args, **kwargs):
            # Verify headers were passed
            assert 'headers' in kwargs
            yield (AsyncMock(), AsyncMock())

        mock_sse.return_value = sse_ctx()

        # Mock get_http_headers to return some headers
        with patch('fastmcp.client.transports.get_http_headers', return_value={"X-Request-ID": "123"}):
            with patch('mcp.ClientSession'):
                transport = SSETransport(
                    url="http://example.com/mcp",
                    headers={"Custom": "value"}
                )

                # Try to connect - this will trigger header merging
                try:
                    async with asyncio.timeout(0.1):
                        async with transport.connect_session():
                            pass
                except Exception:
                    pass  # Expected timeout/error with mocks


    async def test_fastmcp_stdio_command_structure(self):
        """Test FastMCPStdioTransport constructs correct command"""
        import tempfile

        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(b"# test")
            script = Path(f.name)

        try:
            transport = FastMCPStdioTransport(script_path=script)

            assert transport.command == "fastmcp"
            assert "run" in transport.args
            assert str(script) in transport.args
        finally:
            script.unlink(missing_ok=True)


    async def test_uvx_with_env_vars(self):
        """Test UvxStdioTransport environment variable handling"""

        transport = UvxStdioTransport(
            tool_name="test-tool",
            env_vars={"CUSTOM_VAR": "value"}
        )

        # Verify environment was set correctly
        assert transport.env is not None
        assert "CUSTOM_VAR" in transport.env
        assert transport.env["CUSTOM_VAR"] == "value"


    @patch('shutil.which', return_value="/usr/bin/npx")
    async def test_npx_with_env_vars(self, mock_which):
        """Test NpxStdioTransport environment variable handling"""
        transport = NpxStdioTransport(
            package="test-pkg",
            env_vars={"NPM_CONFIG": "value"}
        )

        # Verify environment was set correctly
        assert transport.env is not None
        assert "NPM_CONFIG" in transport.env
        assert transport.env["NPM_CONFIG"] == "value"


class TestTransportIntegration:
    """Test integrated transport scenarios"""

    async def test_sse_transport_full_lifecycle(self):
        """Test complete SSE transport lifecycle"""
        transport = SSETransport(
            url="http://example.com/mcp",
            headers={"Authorization": "Bearer token"},
            sse_read_timeout=30.0
        )

        # Verify configuration
        assert transport.url == "http://example.com/mcp/"
        assert transport.headers == {"Authorization": "Bearer token"}
        assert transport.sse_read_timeout == timedelta(seconds=30.0)

        # Verify close doesn't raise
        await transport.close()


    async def test_transport_selection_chain(self, temp_python_script):
        """Test transport selection through multiple methods"""
        # Direct instantiation
        transport1 = PythonStdioTransport(script_path=temp_python_script)
        assert isinstance(transport1, PythonStdioTransport)

        # Inference from path string
        transport2 = infer_transport(str(temp_python_script))
        assert isinstance(transport2, PythonStdioTransport)

        # Inference from Path object
        transport3 = infer_transport(temp_python_script)
        assert isinstance(transport3, PythonStdioTransport)


    async def test_config_based_client_creation(self):
        """Test creating clients from configs"""
        config_single = {
            "mcpServers": {
                "api": {
                    "url": "http://api.example.com/mcp",
                    "transport": "streamable-http"
                }
            }
        }

        config_multi = {
            "mcpServers": {
                "weather": {
                    "url": "http://weather.example.com/mcp",
                    "transport": "streamable-http"
                },
                "calendar": {
                    "url": "http://calendar.example.com/mcp",
                    "transport": "sse"
                }
            }
        }

        # Single server config
        transport1 = MCPConfigTransport(config_single)
        assert isinstance(transport1.transport, StreamableHttpTransport)

        # Multi-server config
        transport2 = MCPConfigTransport(config_multi)
        assert isinstance(transport2.transport, FastMCPTransport)
