"""
Comprehensive tests for server import and mounting functionality (server.py)

This test suite covers:
- import_server() method with and without prefixes (lines 1781-1903)
- mount() method in direct and proxy modes (lines 1656-1779)
- MountedServer dataclass (lines 2059-2062)
- add_resource_prefix() function (lines 2065-2113)
- remove_resource_prefix() function (lines 2116-2170)
- Server composition and prefix handling

Target Coverage: Lines 1656-1903, 2059-2170
"""

import warnings
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Check if client module can be imported, skip mount tests if not
CLIENT_AVAILABLE = False
try:
    # Try to patch the problematic oauth_callback module before importing Client
    with patch('fastmcp.client.auth.oauth'):
        import fastmcp.client  # noqa: F401 - Import used to test availability, CLIENT_AVAILABLE flag set
        CLIENT_AVAILABLE = True
except (ImportError, AttributeError, ModuleNotFoundError):
    CLIENT_AVAILABLE = False

# Import the module under test - comes after availability check
from fastmcp.server.server import (  # noqa: E402 - Import after client availability check
    FastMCP,
    MountedServer,
    add_resource_prefix,
    remove_resource_prefix,
)

# Import related components for testing - intentional order to group test dependencies
# ruff: noqa: I001
try:
    from mcp.server.lowlevel.server import Server as MCPServer  # noqa: F401 - Used in test assertions
    from fastmcp.settings import Settings
except ImportError as e:
    pytest.skip(f"Required imports not available: {e}", allow_module_level=True)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_settings():
    """Mock Settings instance"""
    settings = Mock(spec=Settings)
    settings.resource_prefix_format = "path"
    settings.deprecation_warnings = False
    return settings


@pytest.fixture
def parent_server():
    """Create parent FastMCP server for testing"""
    with patch('fastmcp.server.server.MCPServer'):
        server = FastMCP(name="ParentServer")
        return server


@pytest.fixture
def child_server():
    """Create child FastMCP server for testing"""
    with patch('fastmcp.server.server.MCPServer'):
        server = FastMCP(name="ChildServer")
        server._has_lifespan = False
        return server


# ============================================================================
# MountedServer Dataclass Tests (Lines 2059-2062)
# ============================================================================

class TestMountedServerDataclass:
    """Test MountedServer dataclass initialization and attributes"""

    def test_mounted_server_with_all_fields(self):
        """Test MountedServer initialization with all attributes specified"""
        with patch('fastmcp.server.server.MCPServer'):
            server = FastMCP(name="TestServer")

            mounted = MountedServer(
                prefix="api/v1",
                server=server,
                resource_prefix_format="path"
            )

            assert mounted.prefix == "api/v1"
            assert mounted.server is server
            assert mounted.resource_prefix_format == "path"


    def test_mounted_server_with_minimal_fields(self):
        """Test MountedServer initialization with None defaults"""
        with patch('fastmcp.server.server.MCPServer'):
            server = FastMCP(name="TestServer")

            mounted = MountedServer(
                prefix=None,
                server=server
            )

            assert mounted.prefix is None
            assert mounted.server is server
            assert mounted.resource_prefix_format is None


    def test_mounted_server_with_protocol_format(self):
        """Test MountedServer initialization with protocol format"""
        with patch('fastmcp.server.server.MCPServer'):
            server = FastMCP(name="TestServer")

            mounted = MountedServer(
                prefix="legacy",
                server=server,
                resource_prefix_format="protocol"
            )

            assert mounted.prefix == "legacy"
            assert mounted.server is server
            assert mounted.resource_prefix_format == "protocol"


# ============================================================================
# Resource Prefix Handling Tests (Lines 2065-2170)
# ============================================================================

class TestResourcePrefixHandling:
    """Test add_resource_prefix and remove_resource_prefix functions"""

    def test_add_resource_prefix_path_format(self):
        """Test add_resource_prefix with path-style format (lines 2099-2111)"""
        # Standard path format: protocol://prefix/path
        result = add_resource_prefix(
            uri="resource://path/to/resource",
            prefix="api/v1",
            prefix_format="path"
        )
        assert result == "resource://api/v1/path/to/resource"

        # Absolute path with triple slash
        result_absolute = add_resource_prefix(
            uri="resource:///absolute/path",
            prefix="prefix",
            prefix_format="path"
        )
        assert result_absolute == "resource://prefix//absolute/path"

        # Complex nested path
        result_nested = add_resource_prefix(
            uri="weather://forecast/daily/temperature",
            prefix="api/v2",
            prefix_format="path"
        )
        assert result_nested == "weather://api/v2/forecast/daily/temperature"


    def test_add_resource_prefix_protocol_format(self):
        """Test add_resource_prefix with protocol-style format (lines 2096-2098)"""
        # Legacy protocol format: prefix+protocol://path
        result = add_resource_prefix(
            uri="resource://path/to/resource",
            prefix="api",
            prefix_format="protocol"
        )
        assert result == "api+resource://path/to/resource"

        # Multiple segments in prefix
        result_multi = add_resource_prefix(
            uri="weather://forecast",
            prefix="external_api",
            prefix_format="protocol"
        )
        assert result_multi == "external_api+weather://forecast"


    def test_add_resource_prefix_empty_prefix(self):
        """Test add_resource_prefix with empty prefix returns original URI (line 2088)"""
        original = "resource://path/to/resource"

        # Empty string prefix
        result_empty = add_resource_prefix(uri=original, prefix="", prefix_format="path")
        assert result_empty == original

        # None prefix
        result_none = add_resource_prefix(uri=original, prefix=None, prefix_format="path")
        assert result_none == original


    def test_add_resource_prefix_invalid_uri_format(self):
        """Test add_resource_prefix raises ValueError for invalid URI (lines 2102-2106)"""
        with pytest.raises(ValueError, match="Invalid URI format"):
            add_resource_prefix(
                uri="invalid_uri_without_protocol",
                prefix="api",
                prefix_format="path"
            )

        with pytest.raises(ValueError, match="Invalid URI format"):
            add_resource_prefix(
                uri="also:invalid:format",
                prefix="api",
                prefix_format="path"
            )


    def test_add_resource_prefix_invalid_format_type(self):
        """Test add_resource_prefix raises ValueError for invalid prefix format (line 2113)"""
        with pytest.raises(ValueError, match="Invalid prefix format"):
            add_resource_prefix(
                uri="resource://path",
                prefix="api",
                prefix_format="invalid_format"
            )


    @patch('fastmcp.server.server._settings')
    def test_add_resource_prefix_uses_settings_default(self, mock_settings):
        """Test add_resource_prefix uses settings default when format is None (line 2094)"""
        mock_settings.resource_prefix_format = "protocol"

        result = add_resource_prefix(
            uri="resource://path/to/resource",
            prefix="api",
            prefix_format=None
        )

        # Should use settings default (protocol format)
        assert result == "api+resource://path/to/resource"


    def test_remove_resource_prefix_path_format(self):
        """Test remove_resource_prefix with path-style format"""
        # Standard path format removal
        result = remove_resource_prefix(
            uri="resource://api/v1/path/to/resource",
            prefix="api/v1",
            prefix_format="path"
        )
        assert result == "resource://path/to/resource"

        # Absolute path removal
        result_absolute = remove_resource_prefix(
            uri="resource://prefix//absolute/path",
            prefix="prefix",
            prefix_format="path"
        )
        assert result_absolute == "resource:///absolute/path"

        # Nested path removal
        result_nested = remove_resource_prefix(
            uri="weather://api/v2/forecast/daily",
            prefix="api/v2",
            prefix_format="path"
        )
        assert result_nested == "weather://forecast/daily"


    def test_remove_resource_prefix_protocol_format(self):
        """Test remove_resource_prefix with protocol-style format"""
        # Legacy protocol format removal
        result = remove_resource_prefix(
            uri="api+resource://path/to/resource",
            prefix="api",
            prefix_format="protocol"
        )
        assert result == "resource://path/to/resource"

        # Multiple segment prefix
        result_multi = remove_resource_prefix(
            uri="external_api+weather://forecast",
            prefix="external_api",
            prefix_format="protocol"
        )
        assert result_multi == "weather://forecast"


    def test_remove_resource_prefix_empty_prefix(self):
        """Test remove_resource_prefix with empty prefix returns original URI"""
        original = "resource://path/to/resource"

        # Empty string prefix
        result_empty = remove_resource_prefix(uri=original, prefix="", prefix_format="path")
        assert result_empty == original

        # None prefix
        result_none = remove_resource_prefix(uri=original, prefix=None, prefix_format="path")
        assert result_none == original


    @patch('fastmcp.server.server._settings')
    def test_remove_resource_prefix_uses_settings_default(self, mock_settings):
        """Test remove_resource_prefix uses settings default when format is None"""
        mock_settings.resource_prefix_format = "protocol"

        result = remove_resource_prefix(
            uri="api+resource://path/to/resource",
            prefix="api",
            prefix_format=None
        )

        # Should use settings default (protocol format)
        assert result == "resource://path/to/resource"


# ============================================================================
# Server Import Tests (Lines 1781-1903)
# ============================================================================

class TestServerImport:
    """Test import_server() method for static server composition"""

    @pytest.mark.asyncio
    async def test_import_server_with_prefix(self):
        """Test importing server with prefix for all component types (lines 1869-1896)"""
        with patch('fastmcp.server.server.MCPServer'):
            parent = FastMCP(name="Parent")
            child = FastMCP(name="Child")

            # Mock components with proper with_key method
            mock_tool = Mock()
            mock_tool.with_key = Mock(return_value=mock_tool)

            mock_resource = Mock()
            mock_resource.with_key = Mock(return_value=mock_resource)

            mock_template = Mock()
            mock_template.with_key = Mock(return_value=mock_template)

            mock_prompt = Mock()
            mock_prompt.with_key = Mock(return_value=mock_prompt)

            # Mock async get methods
            child.get_tools = AsyncMock(return_value={"weather_tool": mock_tool})
            child.get_resources = AsyncMock(return_value={"resource://weather": mock_resource})
            child.get_resource_templates = AsyncMock(return_value={"resource://location/{id}": mock_template})
            child.get_prompts = AsyncMock(return_value={"weather_prompt": mock_prompt})

            # Import with prefix
            await parent.import_server(child, prefix="api")

            # Verify all get methods were called
            child.get_tools.assert_called_once()
            child.get_resources.assert_called_once()
            child.get_resource_templates.assert_called_once()
            child.get_prompts.assert_called_once()

            # Verify prefix was applied to tools (line 1872)
            mock_tool.with_key.assert_called_once_with("api_weather_tool")

            # Verify prefix was applied to prompts (line 1895)
            mock_prompt.with_key.assert_called_once_with("api_weather_prompt")

            # Verify resources and templates got prefixed URIs
            assert mock_resource.with_key.called
            assert mock_template.with_key.called


    @pytest.mark.asyncio
    async def test_import_server_without_prefix(self):
        """Test importing server without prefix preserves original names (lines 1869-1896)"""
        with patch('fastmcp.server.server.MCPServer'):
            parent = FastMCP(name="Parent")
            child = FastMCP(name="Child")

            # Mock components
            mock_tool = Mock()
            mock_resource = Mock()
            mock_template = Mock()
            mock_prompt = Mock()

            # Mock async get methods
            child.get_tools = AsyncMock(return_value={"test_tool": mock_tool})
            child.get_resources = AsyncMock(return_value={"resource://test": mock_resource})
            child.get_resource_templates = AsyncMock(return_value={"resource://tmpl/{id}": mock_template})
            child.get_prompts = AsyncMock(return_value={"test_prompt": mock_prompt})

            # Mock managers' add methods
            parent._tool_manager.add_tool = Mock()
            parent._resource_manager.add_resource = Mock()
            parent._resource_manager.add_template = Mock()
            parent._prompt_manager.add_prompt = Mock()

            # Import without prefix
            await parent.import_server(child, prefix=None)

            # Verify components were added without modification
            parent._tool_manager.add_tool.assert_called_once_with(mock_tool)
            parent._resource_manager.add_resource.assert_called_once_with(mock_resource)
            parent._resource_manager.add_template.assert_called_once_with(mock_template)
            parent._prompt_manager.add_prompt.assert_called_once_with(mock_prompt)


    @pytest.mark.asyncio
    async def test_import_server_empty_components(self):
        """Test importing server with no components"""
        with patch('fastmcp.server.server.MCPServer'):
            parent = FastMCP(name="Parent")
            child = FastMCP(name="Child")

            # Mock empty returns
            child.get_tools = AsyncMock(return_value={})
            child.get_resources = AsyncMock(return_value={})
            child.get_resource_templates = AsyncMock(return_value={})
            child.get_prompts = AsyncMock(return_value={})

            # Should not raise error
            await parent.import_server(child, prefix="empty")

            # Verify all get methods were still called
            child.get_tools.assert_called_once()
            child.get_resources.assert_called_once()
            child.get_resource_templates.assert_called_once()
            child.get_prompts.assert_called_once()


    @pytest.mark.asyncio
    async def test_import_server_deprecated_argument_order(self):
        """Test import_server handles deprecated argument order (lines 1829-1837)"""
        with patch('fastmcp.server.server.MCPServer'):
            with patch('fastmcp.server.server._settings') as mock_settings:
                mock_settings.deprecation_warnings = True

                parent = FastMCP(name="Parent")
                child = FastMCP(name="Child")

                # Mock child methods
                child.get_tools = AsyncMock(return_value={})
                child.get_resources = AsyncMock(return_value={})
                child.get_resource_templates = AsyncMock(return_value={})
                child.get_prompts = AsyncMock(return_value={})

                # Call with old argument order (prefix first, server second)
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    await parent.import_server("api", child)  # Old order

                    # Verify deprecation warning was issued
                    assert len(w) == 1
                    assert issubclass(w[0].category, DeprecationWarning)
                    assert "optional and the first positional argument" in str(w[0].message)


# ============================================================================
# Server Mount Tests (Lines 1656-1779)
# ============================================================================

class TestServerMount:
    """Test mount() method for dynamic server composition"""

    @patch('fastmcp.server.proxy.FastMCPProxy')
    @patch('fastmcp.client.transports.FastMCPTransport')
    @patch('fastmcp.client.Client')
    def test_mount_server_direct_mode_with_prefix(self, mock_client, mock_transport, mock_proxy):
        """Test mounting server in direct mode with prefix (lines 1761-1779)"""
        with patch('fastmcp.server.server.MCPServer'):
            parent = FastMCP(name="Parent")
            child = FastMCP(name="Child")
            child._has_lifespan = False  # Direct mode

            # Mock manager mount methods
            parent._tool_manager.mount = Mock()
            parent._resource_manager.mount = Mock()
            parent._prompt_manager.mount = Mock()

            # Mount with prefix (direct mode doesn't need Client/Proxy imports but they're still imported)
            parent.mount(child, prefix="api/v1")

            # Verify mount called on all managers
            assert parent._tool_manager.mount.called
            assert parent._resource_manager.mount.called
            assert parent._prompt_manager.mount.called

            # Verify MountedServer structure
            mounted = parent._tool_manager.mount.call_args[0][0]
            assert isinstance(mounted, MountedServer)
            assert mounted.prefix == "api/v1"
            assert mounted.server is child

            # In direct mode, Client/Proxy should NOT be used
            mock_client.assert_not_called()
            mock_transport.assert_not_called()
            mock_proxy.assert_not_called()


    @patch('fastmcp.server.proxy.FastMCPProxy')
    @patch('fastmcp.client.transports.FastMCPTransport')
    @patch('fastmcp.client.Client')
    def test_mount_server_direct_mode_without_prefix(self, mock_client, mock_transport, mock_proxy):
        """Test mounting server in direct mode without prefix (lines 1687-1689)"""
        with patch('fastmcp.server.server.MCPServer'):
            parent = FastMCP(name="Parent")
            child = FastMCP(name="Child")
            child._has_lifespan = False

            # Mock manager mount methods
            parent._tool_manager.mount = Mock()
            parent._resource_manager.mount = Mock()
            parent._prompt_manager.mount = Mock()

            # Mount without prefix
            parent.mount(child, prefix=None)

            # Verify MountedServer has None prefix
            mounted = parent._tool_manager.mount.call_args[0][0]
            assert mounted.prefix is None
            assert mounted.server is child


    def test_mount_server_proxy_mode_automatic(self):
        """Test mounting server automatically uses proxy mode for custom lifespan (lines 1761-1767)"""
        with patch('fastmcp.server.server.MCPServer'):
            with patch('fastmcp.client.Client') as mock_client_cls:
                with patch('fastmcp.client.transports.FastMCPTransport') as mock_transport_cls:
                    with patch('fastmcp.server.proxy.FastMCPProxy') as mock_proxy_cls:
                        parent = FastMCP(name="Parent")
                        child = FastMCP(name="Child")
                        child._has_lifespan = True  # Has custom lifespan

                        # Mock proxy components
                        mock_transport = Mock()
                        mock_transport_cls.return_value = mock_transport
                        mock_client = Mock()
                        mock_client_cls.return_value = mock_client
                        mock_proxy = Mock()
                        mock_proxy_cls.return_value = mock_proxy

                        # Mock manager mount methods
                        parent._tool_manager.mount = Mock()
                        parent._resource_manager.mount = Mock()
                        parent._prompt_manager.mount = Mock()

                        # Mount (should auto-detect proxy mode needed)
                        parent.mount(child, prefix="api")

                        # Verify proxy chain was created
                        mock_transport_cls.assert_called_once_with(child)
                        mock_client_cls.assert_called_once_with(transport=mock_transport)
                        mock_proxy_cls.assert_called_once_with(mock_client)

                        # Verify proxy was mounted, not original server
                        mounted = parent._tool_manager.mount.call_args[0][0]
                        assert mounted.server is mock_proxy


    def test_mount_server_explicit_proxy_mode(self):
        """Test mounting server with explicit proxy mode flag (line 1766)"""
        with patch('fastmcp.server.server.MCPServer'):
            with patch('fastmcp.client.Client') as mock_client_cls:
                with patch('fastmcp.client.transports.FastMCPTransport') as mock_transport_cls:
                    with patch('fastmcp.server.proxy.FastMCPProxy') as mock_proxy_cls:
                        parent = FastMCP(name="Parent")
                        child = FastMCP(name="Child")
                        child._has_lifespan = False  # No custom lifespan

                        # Mock components
                        mock_proxy_cls.return_value = Mock()
                        mock_client_cls.return_value = Mock()
                        mock_transport_cls.return_value = Mock()

                        # Mock manager mount methods
                        parent._tool_manager.mount = Mock()
                        parent._resource_manager.mount = Mock()
                        parent._prompt_manager.mount = Mock()

                        # Force proxy mode even though no custom lifespan
                        parent.mount(child, prefix="api", as_proxy=True)

                        # Verify proxy was created despite no custom lifespan
                        assert mock_proxy_cls.called
                        assert mock_client_cls.called
                        assert mock_transport_cls.called


    @patch('fastmcp.server.proxy.FastMCPProxy')
    @patch('fastmcp.client.transports.FastMCPTransport')
    @patch('fastmcp.client.Client')
    def test_mount_server_explicit_direct_mode(self, mock_client, mock_transport, mock_proxy):
        """Test mounting server with explicit direct mode flag"""
        with patch('fastmcp.server.server.MCPServer'):
            parent = FastMCP(name="Parent")
            child = FastMCP(name="Child")
            child._has_lifespan = True  # Has custom lifespan

            # Mock manager mount methods
            parent._tool_manager.mount = Mock()
            parent._resource_manager.mount = Mock()
            parent._prompt_manager.mount = Mock()

            # Force direct mode even though has custom lifespan
            parent.mount(child, prefix="api", as_proxy=False)

            # Verify original server was mounted, not proxy
            mounted = parent._tool_manager.mount.call_args[0][0]
            assert mounted.server is child  # Original server, not proxy


    @patch('fastmcp.server.proxy.FastMCPProxy')
    @patch('fastmcp.client.transports.FastMCPTransport')
    @patch('fastmcp.client.Client')
    def test_mount_server_deprecated_separator_warnings(self, mock_client, mock_transport, mock_proxy):
        """Test mount() deprecation warnings for separator parameters (lines 1731-1759)"""
        with patch('fastmcp.server.server.MCPServer'):
            with patch('fastmcp.server.server._settings') as mock_settings:
                mock_settings.deprecation_warnings = True

                parent = FastMCP(name="Parent")
                child = FastMCP(name="Child")
                child._has_lifespan = False

                # Mock manager mount methods
                parent._tool_manager.mount = Mock()
                parent._resource_manager.mount = Mock()
                parent._prompt_manager.mount = Mock()

                # Test tool_separator deprecation
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    parent.mount(child, prefix="api", tool_separator="_")

                    assert any("tool_separator" in str(warning.message) for warning in w)

                # Test resource_separator deprecation
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    parent.mount(child, prefix="api", resource_separator="/")

                    assert any("resource_separator" in str(warning.message) for warning in w)

                # Test prompt_separator deprecation
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    parent.mount(child, prefix="api", prompt_separator="_")

                    assert any("prompt_separator" in str(warning.message) for warning in w)


    @patch('fastmcp.server.proxy.FastMCPProxy')
    @patch('fastmcp.client.transports.FastMCPTransport')
    @patch('fastmcp.client.Client')
    def test_mount_server_deprecated_argument_order(self, mock_client, mock_transport, mock_proxy):
        """Test mount() handles deprecated argument order (lines 1721-1729)"""
        with patch('fastmcp.server.server.MCPServer'):
            with patch('fastmcp.server.server._settings') as mock_settings:
                mock_settings.deprecation_warnings = True

                parent = FastMCP(name="Parent")
                child = FastMCP(name="Child")
                child._has_lifespan = False

                # Mock manager mount methods
                parent._tool_manager.mount = Mock()
                parent._resource_manager.mount = Mock()
                parent._prompt_manager.mount = Mock()

                # Call with old argument order (prefix first, server second)
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    parent.mount("api", child)  # Old order

                    # Verify deprecation warning
                    assert len(w) == 1
                    assert issubclass(w[0].category, DeprecationWarning)
                    assert "optional and the first positional argument" in str(w[0].message)

                # Verify mount still worked correctly after argument swap
                mounted = parent._tool_manager.mount.call_args[0][0]
                assert mounted.prefix == "api"
                assert mounted.server is child


    @patch('fastmcp.server.proxy.FastMCPProxy')
    @patch('fastmcp.client.transports.FastMCPTransport')
    @patch('fastmcp.client.Client')
    def test_mount_server_cache_cleared(self, mock_client, mock_transport, mock_proxy):
        """Test mount() clears cache after mounting (line 1779)"""
        with patch('fastmcp.server.server.MCPServer'):
            parent = FastMCP(name="Parent")
            child = FastMCP(name="Child")
            child._has_lifespan = False

            # Mock manager mount methods
            parent._tool_manager.mount = Mock()
            parent._resource_manager.mount = Mock()
            parent._prompt_manager.mount = Mock()

            # Mock cache clear
            parent._cache.clear = Mock()

            # Mount server
            parent.mount(child, prefix="api")

            # Verify cache was cleared
            parent._cache.clear.assert_called_once()
