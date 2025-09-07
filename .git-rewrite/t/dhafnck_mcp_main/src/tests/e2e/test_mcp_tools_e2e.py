import pytest
import pytest_asyncio
import httpx
import asyncio

BASE_URL = "http://localhost:8000"

REQUIRED_HEADERS = {
    "content-type": "application/json",
    "accept": "application/json, text/event-stream",
    "mcp-protocol-version": "2025-06-18",
}

INIT_HEADERS = {
    "content-type": "application/json",
    "accept": "application/json, text/event-stream"
}

# Helper to merge/override headers

def get_headers(init=False, **overrides):
    base = INIT_HEADERS.copy() if init else REQUIRED_HEADERS.copy()
    base.update(overrides)
    return base

async def is_server_running():
    """Check if the MCP server is running and accessible with proper MCP endpoints"""
    try:
        async with httpx.AsyncClient() as client:
            # First check if server is running
            health_response = await client.get(f"{BASE_URL}/health", timeout=5.0)
            if health_response.status_code != 200:
                return False
            
            # Then check if MCP endpoints are available
            test_response = await client.post(
                f"{BASE_URL}/mcp/tool/manage_task",
                json={
                    "jsonrpc": "2.0",
                    "method": "manage_task", 
                    "params": {"action": "list", "project_id": "default_project"},
                    "id": "test-connection"
                },
                headers={
                    "content-type": "application/json",
                    "accept": "application/json, text/event-stream",
                    "mcp-protocol-version": "2025-06-18",
                    "mcp-session-id": "test-session"
                },
                timeout=5.0
            )
            # Return true if we get any response (even errors) - this means endpoints exist
            return test_response.status_code != 404
    except (httpx.ConnectError, httpx.TimeoutException, Exception):
        return False

@pytest_asyncio.fixture(scope="function")
async def require_server():
    """Fixture that skips all tests if server is not running"""
    if not await is_server_running():
        pytest.skip(
            f"MCP server not running on {BASE_URL}. "
            "To run E2E tests, start the server with: python working_server.py "
            "or ensure the Docker container has proper MCP endpoints configured."
        )

@pytest.mark.asyncio
async def test_manage_task_e2e(require_server):
    """E2E: manage_task tool basic call stub"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
        response = await client.post(
            "/mcp/tool/manage_task",
            json={
                "jsonrpc": "2.0",
                "method": "manage_task",
                "params": {"action": "list", "project_id": "default_project"},
                "id": "test-manage-task"
            }
        )
        print("manage_task_e2e:", response.status_code, response.text)
        assert response.status_code == 200
        # assert ...

@pytest.mark.asyncio
async def test_manage_subtask_e2e(require_server):
    """E2E: manage_subtask tool basic call stub"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
        response = await client.post(
            "/mcp/tool/manage_subtask",
            json={
                "jsonrpc": "2.0",
                "method": "manage_subtask",
                "params": {"action": "list", "task_id": "dummy", "project_id": "default_project"},
                "id": "test-manage-subtask"
            }
        )
        print("manage_subtask_e2e:", response.status_code, response.text)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_manage_dependency_e2e(require_server):
    """E2E: manage_dependency tool basic call stub"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
        response = await client.post(
            "/mcp/tool/manage_dependency",
            json={
                "jsonrpc": "2.0",
                "method": "manage_dependency",
                "params": {"action": "list", "task_id": "dummy", "project_id": "default_project"},
                "id": "test-manage-dependency"
            }
        )
        print("manage_dependency_e2e:", response.status_code, response.text)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_manage_rule_e2e(require_server):
    """E2E: manage_rule tool basic call stub"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
        response = await client.post(
            "/mcp/tool/manage_rule",
            json={
                "jsonrpc": "2.0",
                "method": "manage_rule",
                "params": {"action": "list"},
                "id": "test-manage-rule"
            }
        )
        print("manage_rule_e2e:", response.status_code, response.text)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_manage_context_e2e(require_server):
    """E2E: manage_context tool basic call stub"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
        response = await client.post(
            "/mcp/tool/manage_context",
            json={
                "jsonrpc": "2.0",
                "method": "manage_context",
                "params": {"action": "list", "project_id": "default_project"},
                "id": "test-manage-context"
            }
        )
        print("manage_context_e2e:", response.status_code, response.text)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_manage_project_e2e(require_server):
    """E2E: manage_project tool basic call stub"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
        response = await client.post(
            "/mcp/tool/manage_project",
            json={
                "jsonrpc": "2.0",
                "method": "manage_project",
                "params": {"action": "list"},
                "id": "test-manage-project"
            }
        )
        print("manage_project_e2e:", response.status_code, response.text)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_manage_agent_e2e(require_server):
    """E2E: manage_agent tool basic call stub"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
        response = await client.post(
            "/mcp/tool/manage_agent",
            json={
                "jsonrpc": "2.0",
                "method": "manage_agent",
                "params": {"action": "list"},
                "id": "test-manage-agent"
            }
        )
        print("manage_agent_e2e:", response.status_code, response.text)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_call_agent_e2e(require_server):
    """E2E: call_agent tool basic call stub"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
        response = await client.post(
            "/mcp/tool/call_agent",
            json={
                "jsonrpc": "2.0",
                "method": "call_agent",
                "params": {"name_agent": "dummy_agent"},
                "id": "test-call-agent"
            }
        )
        print("call_agent_e2e:", response.status_code, response.text)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_manage_compliance_e2e(require_server):
    """E2E: manage_compliance tool basic call stub"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
        response = await client.post(
            "/mcp/tool/manage_compliance",
            json={
                "jsonrpc": "2.0",
                "method": "manage_compliance",
                "params": {"action": "get_compliance_dashboard"},
                "id": "test-manage-compliance"
            }
        )
        print("manage_compliance_e2e:", response.status_code, response.text)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_manage_template_e2e(require_server):
    """E2E: manage_template tool basic call stub"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
        response = await client.post(
            "/mcp/tool/manage_template",
            json={
                "jsonrpc": "2.0",
                "method": "manage_template",
                "params": {"action": "list"},
                "id": "test-manage-template"
            }
        )
        print("manage_template_e2e:", response.status_code, response.text)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_manage_checklist_e2e(require_server):
    """E2E: manage_checklist tool basic call stub"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
        response = await client.post(
            "/mcp/tool/manage_checklist",
            json={
                "jsonrpc": "2.0",
                "method": "manage_checklist",
                "params": {"action": "list", "project_id": "default_project"},
                "id": "test-manage-checklist"
            }
        )
        print("manage_checklist_e2e:", response.status_code, response.text)
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_manage_connection_e2e(require_server):
    """E2E: manage_connection tool basic call stub"""
    async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
        response = await client.post(
            "/mcp/tool/manage_connection",
            json={
                "jsonrpc": "2.0",
                "method": "manage_connection",
                "params": {"action": "health_check"},
                "id": "test-manage-connection"
            }
        )
        print("manage_connection_e2e:", response.status_code, response.text)
        assert response.status_code == 200
# disabled for now, user no want auth for now
# @pytest.mark.asyncio
# async def test_auth_tools_e2e():
#     """E2E: auth tools (validate_token, get_rate_limit_status, revoke_token, get_auth_status, generate_token) stubs"""
#     async with httpx.AsyncClient(base_url=BASE_URL, headers=get_headers()) as client:
#         # These endpoints may require a valid token; adjust as needed
#         for tool in ["validate_token", "get_rate_limit_status", "revoke_token", "get_auth_status", "generate_token"]:
#             response = await client.post(
#                 f"/mcp/tool/{tool}",
#                 json={
#                     "jsonrpc": "2.0",
#                     "method": tool,
#                     "params": {"token": "dummy"},
#                     "id": f"test-auth-{tool}"
#                 }
#             )
#             print(f"auth_tools_e2e {tool}:", response.status_code, response.text)
#             # Some may return 401/403 if auth is enabled
#             assert response.status_code in (200, 401, 403) 

# Negative tests for header enforcement (disabled for now ,  user no want auth for now  )
# @pytest.mark.asyncio
# async def test_missing_headers_rejected():
#     async with httpx.AsyncClient(base_url=BASE_URL) as client:
#         # Missing all headers
#         response = await client.post(
#             "/mcp/tool/manage_task",
#             json={
#                 "jsonrpc": "2.0",
#                 "method": "manage_task",
#                 "params": {"action": "list", "project_id": "default_project"},
#                 "id": "test-manage-task"
#             }
#         )
#         assert response.status_code in (400, 406, 415)
#         # Missing session id
#         bad_headers = get_headers()
#         bad_headers.pop("mcp-session-id")
#         response = await client.post(
#             "/mcp/tool/manage_task",
#             json={
#                 "jsonrpc": "2.0",
#                 "method": "manage_task",
#                 "params": {"action": "list", "project_id": "default_project"},
#                 "id": "test-manage-task"
#             },
#             headers=bad_headers
#         )
#         assert response.status_code in (400, 406, 415)
#         # Missing protocol version
#         bad_headers = get_headers()
#         bad_headers.pop("mcp-protocol-version")
#         response = await client.post(
#             "/mcp/tool/manage_task",
#             json={
#                 "jsonrpc": "2.0",
#                 "method": "manage_task",
#                 "params": {"action": "list", "project_id": "default_project"},
#                 "id": "test-manage-task"
#             },
#             headers=bad_headers
#         )
#         assert response.status_code in (400, 406, 415)
#         # Wrong content-type
#         bad_headers = get_headers()
#         bad_headers["content-type"] = "text/plain"
#         response = await client.post(
#             "/mcp/tool/manage_task",
#             json={
#                 "jsonrpc": "2.0",
#                 "method": "manage_task",
#                 "params": {"action": "list", "project_id": "default_project"},
#                 "id": "test-manage-task"
#             },
#             headers=bad_headers
#         )
#         assert response.status_code in (400, 406, 415) 