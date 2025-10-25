"""
Comprehensive test suite for fastmcp.server.openapi module.

Tests cover:
- _slugify function for text normalization
- MCPType and RouteType enums
- RouteMap dataclass with validation
- Route type determination logic
- OpenAPITool execution
- OpenAPIResource reading
- OpenAPIResourceTemplate creation
- FastMCPOpenAPI server initialization and component creation

Target: 50%+ coverage (217+ lines of 434 missing)
"""

import json
import re
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from mcp.types import ToolAnnotations

from fastmcp.exceptions import ToolError
from fastmcp.server.openapi import (
    DEFAULT_ROUTE_MAPPINGS,
    MCPType,
    FastMCPOpenAPI,
    OpenAPIResource,
    OpenAPIResourceTemplate,
    OpenAPITool,
    RouteMap,
    RouteType,
    _determine_route_type,
    _slugify,
)
from fastmcp.utilities.openapi import HTTPRoute, ParameterInfo, RequestBodyInfo


class TestSlugify:
    """Test suite for _slugify function."""

    def test_slugify_basic_text(self):
        """Test basic text conversion to slug format."""
        assert _slugify("Hello World") == "Hello_World"
        assert _slugify("test-api-endpoint") == "test_api_endpoint"
        assert _slugify("user.profile.get") == "user_profile_get"

    def test_slugify_empty_string(self):
        """Test slugify with empty input."""
        assert _slugify("") == ""

    def test_slugify_removes_special_characters(self):
        """Test removal of non-alphanumeric characters."""
        assert _slugify("user@email!com") == "useremailcom"
        assert _slugify("test#$%^&*()endpoint") == "testendpoint"
        assert _slugify("api/v1/users") == "apiv1users"

    def test_slugify_multiple_spaces_and_separators(self):
        """Test handling of multiple consecutive spaces and separators."""
        assert _slugify("hello   world") == "hello_world"
        assert _slugify("test---api") == "test_api"
        assert _slugify("user...profile") == "user_profile"

    def test_slugify_leading_trailing_underscores(self):
        """Test removal of leading and trailing underscores."""
        assert _slugify("_test_") == "test"
        assert _slugify("___api___") == "api"

    def test_slugify_preserves_alphanumeric_and_underscores(self):
        """Test that alphanumeric and underscores are preserved."""
        assert _slugify("Test_API_123") == "Test_API_123"
        assert _slugify("getUserProfile") == "getUserProfile"


class TestMCPType:
    """Test suite for MCPType enum."""

    def test_mcp_type_values(self):
        """Test MCPType enum has all expected values."""
        assert MCPType.TOOL.value == "TOOL"
        assert MCPType.RESOURCE.value == "RESOURCE"
        assert MCPType.RESOURCE_TEMPLATE.value == "RESOURCE_TEMPLATE"
        assert MCPType.EXCLUDE.value == "EXCLUDE"

    def test_mcp_type_comparison(self):
        """Test MCPType enum comparison."""
        assert MCPType.TOOL == MCPType.TOOL
        assert MCPType.TOOL != MCPType.RESOURCE


class TestRouteType:
    """Test suite for deprecated RouteType enum."""

    def test_route_type_values(self):
        """Test RouteType enum has all expected values."""
        assert RouteType.TOOL.value == "TOOL"
        assert RouteType.RESOURCE.value == "RESOURCE"
        assert RouteType.RESOURCE_TEMPLATE.value == "RESOURCE_TEMPLATE"
        assert RouteType.IGNORE.value == "IGNORE"


class TestRouteMap:
    """Test suite for RouteMap dataclass."""

    def test_route_map_basic_initialization(self):
        """Test basic RouteMap initialization with mcp_type."""
        route_map = RouteMap(mcp_type=MCPType.TOOL)
        assert route_map.mcp_type == MCPType.TOOL
        assert route_map.methods == "*"
        assert route_map.pattern == r".*"

    def test_route_map_with_custom_methods(self):
        """Test RouteMap with specific HTTP methods."""
        route_map = RouteMap(methods=["GET", "POST"], mcp_type=MCPType.RESOURCE)
        assert route_map.methods == ["GET", "POST"]
        assert route_map.mcp_type == MCPType.RESOURCE

    def test_route_map_with_pattern(self):
        """Test RouteMap with custom pattern."""
        pattern = r"/api/users/.*"
        route_map = RouteMap(pattern=pattern, mcp_type=MCPType.RESOURCE_TEMPLATE)
        assert route_map.pattern == pattern

    def test_route_map_with_tags(self):
        """Test RouteMap with tags filtering."""
        route_map = RouteMap(tags={"admin", "internal"}, mcp_type=MCPType.EXCLUDE)
        assert route_map.tags == {"admin", "internal"}

    def test_route_map_with_mcp_tags(self):
        """Test RouteMap with MCP tags to apply."""
        route_map = RouteMap(mcp_tags={"api", "v1"}, mcp_type=MCPType.TOOL)
        assert route_map.mcp_tags == {"api", "v1"}

    def test_route_map_backward_compatibility_route_type(self):
        """Test backward compatibility with deprecated route_type parameter."""
        import fastmcp

        # Save original setting
        original = fastmcp.settings.deprecation_warnings
        try:
            fastmcp.settings.deprecation_warnings = True
            with pytest.warns(DeprecationWarning, match="route_type.*deprecated"):
                route_map = RouteMap(route_type=MCPType.TOOL)
                assert route_map.mcp_type == MCPType.TOOL
        finally:
            fastmcp.settings.deprecation_warnings = original

    def test_route_map_backward_compatibility_ignore(self):
        """Test backward compatibility with deprecated IGNORE value."""
        import fastmcp

        # Save original setting
        original = fastmcp.settings.deprecation_warnings
        try:
            fastmcp.settings.deprecation_warnings = True
            with pytest.warns(DeprecationWarning, match="IGNORE.*deprecated"):
                route_map = RouteMap(route_type=RouteType.IGNORE)
                assert route_map.mcp_type == MCPType.EXCLUDE
        finally:
            fastmcp.settings.deprecation_warnings = original

    def test_route_map_missing_mcp_type_raises_error(self):
        """Test that missing mcp_type raises ValueError."""
        with pytest.raises(ValueError, match="mcp_type.*must be provided"):
            RouteMap()


class TestDetermineRouteType:
    """Test suite for _determine_route_type function."""

    def test_determine_route_type_method_match(self):
        """Test route type determination with method matching."""
        route = HTTPRoute(
            path="/api/users",
            method="GET",
            operation_id="getUsers",
        )
        mappings = [RouteMap(methods=["GET"], mcp_type=MCPType.RESOURCE)]
        result = _determine_route_type(route, mappings)
        assert result.mcp_type == MCPType.RESOURCE

    def test_determine_route_type_pattern_match(self):
        """Test route type determination with pattern matching."""
        route = HTTPRoute(
            path="/api/users/123",
            method="GET",
            operation_id="getUserById",
        )
        mappings = [
            RouteMap(pattern=r".*/users/.*", mcp_type=MCPType.RESOURCE_TEMPLATE)
        ]
        result = _determine_route_type(route, mappings)
        assert result.mcp_type == MCPType.RESOURCE_TEMPLATE

    def test_determine_route_type_wildcard_method(self):
        """Test route type determination with wildcard method."""
        route = HTTPRoute(
            path="/api/data",
            method="POST",
            operation_id="createData",
        )
        mappings = [RouteMap(methods="*", mcp_type=MCPType.TOOL)]
        result = _determine_route_type(route, mappings)
        assert result.mcp_type == MCPType.TOOL

    def test_determine_route_type_tag_matching(self):
        """Test route type determination with tag filtering."""
        route = HTTPRoute(
            path="/api/admin",
            method="GET",
            operation_id="getAdmin",
            tags=["admin", "internal"],
        )
        # Should match - all tags present
        mappings = [RouteMap(tags={"admin"}, mcp_type=MCPType.EXCLUDE)]
        result = _determine_route_type(route, mappings)
        assert result.mcp_type == MCPType.EXCLUDE

    def test_determine_route_type_tag_no_match(self):
        """Test route type determination when tags don't match."""
        route = HTTPRoute(
            path="/api/public",
            method="GET",
            operation_id="getPublic",
            tags=["public"],
        )
        # Should not match - missing required tag
        mappings = [
            RouteMap(tags={"admin"}, mcp_type=MCPType.EXCLUDE),
            RouteMap(mcp_type=MCPType.TOOL),  # Fallback
        ]
        result = _determine_route_type(route, mappings)
        assert result.mcp_type == MCPType.TOOL

    def test_determine_route_type_priority_order(self):
        """Test that first matching route map wins."""
        route = HTTPRoute(
            path="/api/users",
            method="GET",
            operation_id="getUsers",
        )
        mappings = [
            RouteMap(methods=["GET"], mcp_type=MCPType.RESOURCE),
            RouteMap(methods=["GET"], mcp_type=MCPType.TOOL),  # Should not match
        ]
        result = _determine_route_type(route, mappings)
        assert result.mcp_type == MCPType.RESOURCE

    def test_determine_route_type_default_fallback(self):
        """Test default fallback when no mappings match."""
        route = HTTPRoute(
            path="/api/unknown",
            method="DELETE",
            operation_id="deleteUnknown",
        )
        mappings = [RouteMap(methods=["GET"], mcp_type=MCPType.RESOURCE)]
        result = _determine_route_type(route, mappings)
        # Should fall back to default TOOL
        assert result.mcp_type == MCPType.TOOL

    def test_determine_route_type_compiled_pattern(self):
        """Test route type determination with compiled regex pattern."""
        route = HTTPRoute(
            path="/api/v2/users",
            method="GET",
            operation_id="getUsersV2",
        )
        pattern = re.compile(r".*/v2/.*")
        mappings = [RouteMap(pattern=pattern, mcp_type=MCPType.RESOURCE)]
        result = _determine_route_type(route, mappings)
        assert result.mcp_type == MCPType.RESOURCE


class TestOpenAPITool:
    """Test suite for OpenAPITool class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.fixture
    def basic_route(self):
        """Create a basic HTTP route."""
        return HTTPRoute(
            path="/api/users",
            method="GET",
            operation_id="getUsers",
            summary="Get all users",
            description="Retrieves a list of all users",
        )

    def test_openapi_tool_initialization(self, mock_client, basic_route):
        """Test OpenAPITool initialization."""
        tool = OpenAPITool(
            client=mock_client,
            route=basic_route,
            name="getUsers",
            description="Get all users",
            parameters={"type": "object", "properties": {}},
        )
        assert tool.name == "getUsers"
        assert tool._route == basic_route
        assert tool._client == mock_client

    def test_openapi_tool_repr(self, mock_client, basic_route):
        """Test OpenAPITool string representation."""
        tool = OpenAPITool(
            client=mock_client,
            route=basic_route,
            name="getUsers",
            description="Get all users",
            parameters={},
        )
        repr_str = repr(tool)
        assert "OpenAPITool" in repr_str
        assert "getUsers" in repr_str
        assert "GET" in repr_str

    @pytest.mark.asyncio
    async def test_openapi_tool_run_simple_get(self, mock_client, basic_route):
        """Test OpenAPITool execution with simple GET request."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {"users": []}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        tool = OpenAPITool(
            client=mock_client,
            route=basic_route,
            name="getUsers",
            description="Get all users",
            parameters={},
        )

        result = await tool.run({})
        assert len(result) > 0
        mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_openapi_tool_run_with_path_params(self, mock_client):
        """Test OpenAPITool execution with path parameters."""
        route = HTTPRoute(
            path="/api/users/{id}",
            method="GET",
            operation_id="getUserById",
            parameters=[
                ParameterInfo(
                    name="id",
                    location="path",
                    required=True,
                    schema={"type": "string"},
                )
            ],
        )

        mock_response = Mock()
        mock_response.json.return_value = {"id": "123", "name": "Test User"}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        tool = OpenAPITool(
            client=mock_client,
            route=route,
            name="getUserById",
            description="Get user by ID",
            parameters={},
        )

        result = await tool.run({"id": "123"})
        assert len(result) > 0
        # Verify path was replaced
        call_args = mock_client.request.call_args
        assert "123" in call_args[1]["url"]

    @pytest.mark.asyncio
    async def test_openapi_tool_run_missing_required_path_param(self, mock_client):
        """Test OpenAPITool execution with missing required path parameter."""
        route = HTTPRoute(
            path="/api/users/{id}",
            method="GET",
            operation_id="getUserById",
            parameters=[
                ParameterInfo(
                    name="id",
                    location="path",
                    required=True,
                    schema={"type": "string"},
                )
            ],
        )

        tool = OpenAPITool(
            client=mock_client,
            route=route,
            name="getUserById",
            description="Get user by ID",
            parameters={},
        )

        with pytest.raises(ToolError, match="Missing required path parameters"):
            await tool.run({})

    @pytest.mark.asyncio
    async def test_openapi_tool_run_with_query_params(self, mock_client):
        """Test OpenAPITool execution with query parameters."""
        route = HTTPRoute(
            path="/api/users",
            method="GET",
            operation_id="searchUsers",
            parameters=[
                ParameterInfo(
                    name="name",
                    location="query",
                    required=False,
                    schema={"type": "string"},
                ),
                ParameterInfo(
                    name="limit",
                    location="query",
                    required=False,
                    schema={"type": "integer"},
                ),
            ],
        )

        mock_response = Mock()
        mock_response.json.return_value = {"users": []}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        tool = OpenAPITool(
            client=mock_client,
            route=route,
            name="searchUsers",
            description="Search users",
            parameters={},
        )

        await tool.run({"name": "test", "limit": 10})
        call_args = mock_client.request.call_args
        assert call_args[1]["params"]["name"] == "test"
        assert call_args[1]["params"]["limit"] == 10

    @pytest.mark.asyncio
    async def test_openapi_tool_run_with_request_body(self, mock_client):
        """Test OpenAPITool execution with request body."""
        route = HTTPRoute(
            path="/api/users",
            method="POST",
            operation_id="createUser",
            request_body=RequestBodyInfo(
                required=True,
                content_schema={"application/json": {"type": "object"}},
            ),
        )

        mock_response = Mock()
        mock_response.json.return_value = {"id": "123", "name": "New User"}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        tool = OpenAPITool(
            client=mock_client,
            route=route,
            name="createUser",
            description="Create user",
            parameters={},
        )

        await tool.run({"name": "New User", "email": "test@example.com"})
        call_args = mock_client.request.call_args
        assert call_args[1]["json"]["name"] == "New User"
        assert call_args[1]["json"]["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_openapi_tool_run_http_error(self, mock_client, basic_route):
        """Test OpenAPITool execution with HTTP error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"
        mock_response.text = "Resource not found"
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=Mock(), response=mock_response
        )
        mock_client.request.return_value = mock_response

        tool = OpenAPITool(
            client=mock_client,
            route=basic_route,
            name="getUsers",
            description="Get all users",
            parameters={},
        )

        with pytest.raises(ValueError, match="HTTP error 404"):
            await tool.run({})

    @pytest.mark.asyncio
    async def test_openapi_tool_run_request_error(self, mock_client, basic_route):
        """Test OpenAPITool execution with request error."""
        mock_client.request.side_effect = httpx.RequestError("Connection failed")

        tool = OpenAPITool(
            client=mock_client,
            route=basic_route,
            name="getUsers",
            description="Get all users",
            parameters={},
        )

        with pytest.raises(ValueError, match="Request error"):
            await tool.run({})


class TestOpenAPIResource:
    """Test suite for OpenAPIResource class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.fixture
    def basic_route(self):
        """Create a basic HTTP route."""
        return HTTPRoute(
            path="/api/data",
            method="GET",
            operation_id="getData",
        )

    def test_openapi_resource_initialization(self, mock_client, basic_route):
        """Test OpenAPIResource initialization."""
        resource = OpenAPIResource(
            client=mock_client,
            route=basic_route,
            uri="resource://data",
            name="data",
            description="Data resource",
        )
        assert resource.name == "data"
        assert str(resource.uri) == "resource://data"
        assert resource._route == basic_route

    def test_openapi_resource_repr(self, mock_client, basic_route):
        """Test OpenAPIResource string representation."""
        resource = OpenAPIResource(
            client=mock_client,
            route=basic_route,
            uri="resource://data",
            name="data",
            description="Data resource",
        )
        repr_str = repr(resource)
        assert "OpenAPIResource" in repr_str
        assert "data" in repr_str

    @pytest.mark.asyncio
    async def test_openapi_resource_read_json(self, mock_client, basic_route):
        """Test OpenAPIResource read with JSON response."""
        mock_response = Mock()
        mock_response.json.return_value = {"key": "value"}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        resource = OpenAPIResource(
            client=mock_client,
            route=basic_route,
            uri="resource://data",
            name="data",
            description="Data resource",
        )

        result = await resource.read()
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["key"] == "value"

    @pytest.mark.asyncio
    async def test_openapi_resource_read_text(self, mock_client, basic_route):
        """Test OpenAPIResource read with text response."""
        mock_response = Mock()
        mock_response.text = "Plain text content"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        resource = OpenAPIResource(
            client=mock_client,
            route=basic_route,
            uri="resource://data",
            name="data",
            description="Data resource",
        )

        result = await resource.read()
        assert result == "Plain text content"

    @pytest.mark.asyncio
    async def test_openapi_resource_read_binary(self, mock_client, basic_route):
        """Test OpenAPIResource read with binary response."""
        mock_response = Mock()
        mock_response.content = b"Binary content"
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        resource = OpenAPIResource(
            client=mock_client,
            route=basic_route,
            uri="resource://data",
            name="data",
            description="Data resource",
        )

        result = await resource.read()
        assert result == b"Binary content"


class TestOpenAPIResourceTemplate:
    """Test suite for OpenAPIResourceTemplate class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        client = AsyncMock(spec=httpx.AsyncClient)
        return client

    @pytest.fixture
    def template_route(self):
        """Create a route with path parameters."""
        return HTTPRoute(
            path="/api/users/{id}",
            method="GET",
            operation_id="getUserById",
            parameters=[
                ParameterInfo(
                    name="id",
                    location="path",
                    required=True,
                    schema={"type": "string"},
                )
            ],
        )

    def test_openapi_resource_template_initialization(
        self, mock_client, template_route
    ):
        """Test OpenAPIResourceTemplate initialization."""
        template = OpenAPIResourceTemplate(
            client=mock_client,
            route=template_route,
            uri_template="resource://user/{id}",
            name="user",
            description="User resource template",
            parameters={"type": "object", "properties": {"id": {"type": "string"}}},
        )
        assert template.name == "user"
        assert template.uri_template == "resource://user/{id}"

    def test_openapi_resource_template_repr(self, mock_client, template_route):
        """Test OpenAPIResourceTemplate string representation."""
        template = OpenAPIResourceTemplate(
            client=mock_client,
            route=template_route,
            uri_template="resource://user/{id}",
            name="user",
            description="User resource template",
            parameters={},
        )
        repr_str = repr(template)
        assert "OpenAPIResourceTemplate" in repr_str
        assert "user" in repr_str

    @pytest.mark.asyncio
    async def test_openapi_resource_template_create_resource(
        self, mock_client, template_route
    ):
        """Test OpenAPIResourceTemplate resource creation."""
        template = OpenAPIResourceTemplate(
            client=mock_client,
            route=template_route,
            uri_template="resource://user/{id}",
            name="user",
            description="User resource template",
            parameters={},
        )

        resource = await template.create_resource(
            uri="resource://user/123",
            params={"id": "123"},
            context=None,
        )
        assert isinstance(resource, OpenAPIResource)
        assert "user" in resource.name


class TestFastMCPOpenAPI:
    """Test suite for FastMCPOpenAPI class."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.fixture
    def basic_openapi_spec(self):
        """Create a basic OpenAPI spec."""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {
                "/users": {
                    "get": {
                        "operationId": "getUsers",
                        "summary": "Get all users",
                        "responses": {"200": {"description": "Success"}},
                    }
                }
            },
        }

    @patch("fastmcp.utilities.openapi.parse_openapi_to_http_routes")
    def test_fastmcp_openapi_initialization(
        self, mock_parse, mock_client, basic_openapi_spec
    ):
        """Test FastMCPOpenAPI initialization."""
        mock_parse.return_value = []

        server = FastMCPOpenAPI(
            openapi_spec=basic_openapi_spec,
            client=mock_client,
            name="Test API",
        )
        assert server.name == "Test API"
        assert server._client == mock_client
        mock_parse.assert_called_once_with(basic_openapi_spec)

    @patch("fastmcp.utilities.openapi.parse_openapi_to_http_routes")
    def test_fastmcp_openapi_default_route_mappings(
        self, mock_parse, mock_client, basic_openapi_spec
    ):
        """Test FastMCPOpenAPI uses default route mappings."""
        mock_route = HTTPRoute(
            path="/users",
            method="GET",
            operation_id="getUsers",
            summary="Get users",
        )
        mock_parse.return_value = [mock_route]

        server = FastMCPOpenAPI(
            openapi_spec=basic_openapi_spec,
            client=mock_client,
        )
        # Should create a tool by default
        assert len(server._tool_manager._tools) > 0

    def test_fastmcp_openapi_generate_default_name_with_operation_id(
        self, mock_client
    ):
        """Test name generation from operation ID."""
        with patch("fastmcp.utilities.openapi.parse_openapi_to_http_routes") as mock:
            mock.return_value = []
            server = FastMCPOpenAPI(openapi_spec={}, client=mock_client)

            route = HTTPRoute(
                path="/users",
                method="GET",
                operation_id="getUsers__v1",
                summary="Get users",
            )
            name = server._generate_default_name(route)
            # Should use first part before double underscore
            assert name == "getUsers"

    def test_fastmcp_openapi_generate_default_name_with_custom_mapping(
        self, mock_client
    ):
        """Test name generation with custom mapping."""
        with patch("fastmcp.utilities.openapi.parse_openapi_to_http_routes") as mock:
            mock.return_value = []
            server = FastMCPOpenAPI(openapi_spec={}, client=mock_client)

            route = HTTPRoute(
                path="/users",
                method="GET",
                operation_id="getUsers",
                summary="Get users",
            )
            mcp_names = {"getUsers": "list_all_users"}
            name = server._generate_default_name(route, mcp_names)
            assert name == "list_all_users"

    def test_fastmcp_openapi_generate_default_name_truncation(self, mock_client):
        """Test name generation truncates long names."""
        with patch("fastmcp.utilities.openapi.parse_openapi_to_http_routes") as mock:
            mock.return_value = []
            server = FastMCPOpenAPI(openapi_spec={}, client=mock_client)

            route = HTTPRoute(
                path="/users",
                method="GET",
                operation_id="a" * 100,  # Very long name
                summary="Get users",
            )
            name = server._generate_default_name(route)
            assert len(name) <= 56

    def test_fastmcp_openapi_get_unique_name(self, mock_client):
        """Test unique name generation with collisions."""
        with patch("fastmcp.utilities.openapi.parse_openapi_to_http_routes") as mock:
            mock.return_value = []
            server = FastMCPOpenAPI(openapi_spec={}, client=mock_client)

            # First call - should return original name
            name1 = server._get_unique_name("test_tool", "tool")
            assert name1 == "test_tool"

            # Second call - should append counter
            name2 = server._get_unique_name("test_tool", "tool")
            assert name2 == "test_tool_2"

            # Third call - should increment counter
            name3 = server._get_unique_name("test_tool", "tool")
            assert name3 == "test_tool_3"

    def test_default_route_mappings_constant(self):
        """Test DEFAULT_ROUTE_MAPPINGS is properly defined."""
        assert isinstance(DEFAULT_ROUTE_MAPPINGS, list)
        assert len(DEFAULT_ROUTE_MAPPINGS) > 0
        assert all(isinstance(rm, RouteMap) for rm in DEFAULT_ROUTE_MAPPINGS)
        # Should default to TOOL
        assert DEFAULT_ROUTE_MAPPINGS[0].mcp_type == MCPType.TOOL

    @patch("fastmcp.utilities.openapi.parse_openapi_to_http_routes")
    def test_fastmcp_openapi_with_route_map_fn(
        self, mock_parse, mock_client, basic_openapi_spec
    ):
        """Test FastMCPOpenAPI with custom route_map_fn."""
        mock_route = HTTPRoute(
            path="/users",
            method="GET",
            operation_id="getUsers",
            summary="Get users",
        )
        mock_parse.return_value = [mock_route]

        def custom_route_mapper(route, mcp_type):
            """Custom route mapper that changes type."""
            if "users" in route.path:
                return MCPType.RESOURCE
            return None

        server = FastMCPOpenAPI(
            openapi_spec=basic_openapi_spec,
            client=mock_client,
            route_map_fn=custom_route_mapper,
        )
        # Should have created a resource instead of tool
        assert len(server._resource_manager._resources) > 0

    @patch("fastmcp.utilities.openapi.parse_openapi_to_http_routes")
    def test_fastmcp_openapi_with_mcp_component_fn(
        self, mock_parse, mock_client, basic_openapi_spec
    ):
        """Test FastMCPOpenAPI with custom mcp_component_fn."""
        mock_route = HTTPRoute(
            path="/api/test",
            method="GET",
            operation_id="getTestData",
            summary="Get test data",
        )
        mock_parse.return_value = [mock_route]

        def custom_component_fn(route, component):
            """Custom component modifier."""
            # Modify component in-place
            if hasattr(component, "description"):
                component.description = "Modified: " + component.description

        server = FastMCPOpenAPI(
            openapi_spec=basic_openapi_spec,
            client=mock_client,
            mcp_component_fn=custom_component_fn,
        )
        # Find the OpenAPI tool (not MCP tools)
        openapi_tools = [
            t
            for t in server._tool_manager._tools.values()
            if isinstance(t, OpenAPITool)
        ]
        assert len(openapi_tools) > 0
        assert openapi_tools[0].description.startswith("Modified:")

    @patch("fastmcp.utilities.openapi.parse_openapi_to_http_routes")
    def test_fastmcp_openapi_exclude_route(
        self, mock_parse, mock_client, basic_openapi_spec
    ):
        """Test FastMCPOpenAPI with excluded routes."""
        mock_route = HTTPRoute(
            path="/api/internal",
            method="GET",
            operation_id="getInternal",
            summary="Internal endpoint",
        )
        mock_parse.return_value = [mock_route]

        # Exclude all routes
        route_maps = [RouteMap(mcp_type=MCPType.EXCLUDE)]

        server = FastMCPOpenAPI(
            openapi_spec=basic_openapi_spec,
            client=mock_client,
            route_maps=route_maps,
        )
        # Should have no OpenAPI tools or resources (may have MCP tools)
        openapi_tools = [
            t
            for t in server._tool_manager._tools.values()
            if isinstance(t, OpenAPITool)
        ]
        assert len(openapi_tools) == 0
        assert len(server._resource_manager._resources) == 0

    @patch("fastmcp.utilities.openapi.parse_openapi_to_http_routes")
    def test_fastmcp_openapi_create_resource_template(
        self, mock_parse, mock_client, basic_openapi_spec
    ):
        """Test FastMCPOpenAPI creates resource templates."""
        mock_route = HTTPRoute(
            path="/users/{id}",
            method="GET",
            operation_id="getUserById",
            summary="Get user by ID",
            parameters=[
                ParameterInfo(
                    name="id",
                    location="path",
                    required=True,
                    schema={"type": "string"},
                )
            ],
        )
        mock_parse.return_value = [mock_route]

        route_maps = [RouteMap(mcp_type=MCPType.RESOURCE_TEMPLATE)]

        server = FastMCPOpenAPI(
            openapi_spec=basic_openapi_spec,
            client=mock_client,
            route_maps=route_maps,
        )
        # Should have created a template
        assert len(server._resource_manager._templates) > 0


class TestOpenAPIToolArrayParameters:
    """Test suite for OpenAPITool array parameter handling."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_openapi_tool_array_path_params_simple(self, mock_client):
        """Test array path parameters with simple types."""
        route = HTTPRoute(
            path="/api/items/{ids}",
            method="GET",
            operation_id="getItemsByIds",
            parameters=[
                ParameterInfo(
                    name="ids",
                    location="path",
                    required=True,
                    schema={"type": "array", "items": {"type": "string"}},
                )
            ],
        )

        mock_response = Mock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        tool = OpenAPITool(
            client=mock_client,
            route=route,
            name="getItemsByIds",
            description="Get items by IDs",
            parameters={},
        )

        await tool.run({"ids": ["id1", "id2", "id3"]})
        call_args = mock_client.request.call_args
        # Should format as comma-separated
        assert "id1,id2,id3" in call_args[1]["url"]

    @pytest.mark.asyncio
    async def test_openapi_tool_array_query_params_explode_true(self, mock_client):
        """Test array query parameters with explode=true."""
        route = HTTPRoute(
            path="/api/search",
            method="GET",
            operation_id="search",
            parameters=[
                ParameterInfo(
                    name="tags",
                    location="query",
                    required=False,
                    schema={
                        "type": "array",
                        "items": {"type": "string"},
                        "explode": True,
                    },
                )
            ],
        )

        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        tool = OpenAPITool(
            client=mock_client,
            route=route,
            name="search",
            description="Search with tags",
            parameters={},
        )

        await tool.run({"tags": ["tag1", "tag2"]})
        call_args = mock_client.request.call_args
        # Should pass array directly for HTTPX to serialize
        assert call_args[1]["params"]["tags"] == ["tag1", "tag2"]

    @pytest.mark.asyncio
    async def test_openapi_tool_array_query_params_explode_false(self, mock_client):
        """Test array query parameters with explode=false."""
        route = HTTPRoute(
            path="/api/search",
            method="GET",
            operation_id="search",
            parameters=[
                ParameterInfo(
                    name="tags",
                    location="query",
                    required=False,
                    schema={
                        "type": "array",
                        "items": {"type": "string"},
                        "explode": False,
                    },
                )
            ],
        )

        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        tool = OpenAPITool(
            client=mock_client,
            route=route,
            name="search",
            description="Search with tags",
            parameters={},
        )

        await tool.run({"tags": ["tag1", "tag2"]})
        call_args = mock_client.request.call_args
        # Should format as comma-separated string
        assert call_args[1]["params"]["tags"] == "tag1,tag2"

    @pytest.mark.asyncio
    async def test_openapi_tool_query_params_filter_none(self, mock_client):
        """Test that None and empty string query params are filtered."""
        route = HTTPRoute(
            path="/api/users",
            method="GET",
            operation_id="getUsers",
            parameters=[
                ParameterInfo(
                    name="name",
                    location="query",
                    required=False,
                    schema={"type": "string"},
                ),
                ParameterInfo(
                    name="status",
                    location="query",
                    required=False,
                    schema={"type": "string"},
                ),
            ],
        )

        mock_response = Mock()
        mock_response.json.return_value = {"users": []}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        tool = OpenAPITool(
            client=mock_client,
            route=route,
            name="getUsers",
            description="Get users",
            parameters={},
        )

        # Pass None and empty string
        await tool.run({"name": None, "status": ""})
        call_args = mock_client.request.call_args
        # Both should be filtered out
        assert call_args[1]["params"] == {}

    @pytest.mark.asyncio
    async def test_openapi_tool_with_header_params(self, mock_client):
        """Test tool execution with header parameters."""
        route = HTTPRoute(
            path="/api/data",
            method="GET",
            operation_id="getData",
            parameters=[
                ParameterInfo(
                    name="X-Custom-Header",
                    location="header",
                    required=False,
                    schema={"type": "string"},
                )
            ],
        )

        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        tool = OpenAPITool(
            client=mock_client,
            route=route,
            name="getData",
            description="Get data",
            parameters={},
        )

        await tool.run({"X-Custom-Header": "custom-value"})
        call_args = mock_client.request.call_args
        # Header should be lowercase
        assert call_args[1]["headers"]["x-custom-header"] == "custom-value"

    @pytest.mark.asyncio
    async def test_openapi_tool_non_json_response(self, mock_client):
        """Test tool handling of non-JSON response."""
        route = HTTPRoute(
            path="/api/data",
            method="GET",
            operation_id="getData",
        )

        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.text = "Plain text response"
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        tool = OpenAPITool(
            client=mock_client,
            route=route,
            name="getData",
            description="Get data",
            parameters={},
        )

        result = await tool.run({})
        # Should return text content
        assert len(result) > 0


class TestOpenAPIResourcePathParams:
    """Test suite for OpenAPIResource path parameter handling."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock HTTP client."""
        return AsyncMock(spec=httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_openapi_resource_with_path_params(self, mock_client):
        """Test OpenAPIResource read with path parameters in URI."""
        route = HTTPRoute(
            path="/api/users/{id}",
            method="GET",
            operation_id="getUserById",
            parameters=[
                ParameterInfo(
                    name="id",
                    location="path",
                    required=True,
                    schema={"type": "string"},
                )
            ],
        )

        mock_response = Mock()
        mock_response.json.return_value = {"id": "123", "name": "Test"}
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = Mock()
        mock_client.request.return_value = mock_response

        resource = OpenAPIResource(
            client=mock_client,
            route=route,
            uri="resource://user/123",
            name="user",
            description="User resource",
        )

        result = await resource.read()
        # Should have replaced path parameter
        call_args = mock_client.request.call_args
        assert "123" in call_args[1]["url"]

    @pytest.mark.asyncio
    async def test_openapi_resource_read_http_error(self, mock_client):
        """Test OpenAPIResource read with HTTP error."""
        route = HTTPRoute(
            path="/api/data",
            method="GET",
            operation_id="getData",
        )

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_response.text = "Server error"
        mock_response.json.side_effect = json.JSONDecodeError("", "", 0)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=Mock(), response=mock_response
        )
        mock_client.request.return_value = mock_response

        resource = OpenAPIResource(
            client=mock_client,
            route=route,
            uri="resource://data",
            name="data",
            description="Data resource",
        )

        with pytest.raises(ValueError, match="HTTP error 500"):
            await resource.read()

    @pytest.mark.asyncio
    async def test_openapi_resource_read_request_error(self, mock_client):
        """Test OpenAPIResource read with request error."""
        route = HTTPRoute(
            path="/api/data",
            method="GET",
            operation_id="getData",
        )

        mock_client.request.side_effect = httpx.RequestError("Network error")

        resource = OpenAPIResource(
            client=mock_client,
            route=route,
            uri="resource://data",
            name="data",
            description="Data resource",
        )

        with pytest.raises(ValueError, match="Request error"):
            await resource.read()
