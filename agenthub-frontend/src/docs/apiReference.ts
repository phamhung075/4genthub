// GENERATED - do not edit by hand.
//
// Produced by agenthub/internal/apiref from the running code: every route registration read
// from the Go source text - the mount directory AND every package those files register
// routes from, resolved through go.mod, so the auth family is counted and not only the
// mount files - and every MCP tool read by calling the server's own builder, so an
// entry reaches this file only because it reaches the wire.
//
// THE DRIFT TEST IS THE WITNESS and reads the code independently; if this file and the code
// disagree, the artefact is wrong rather than the test.

import type { ApiReference } from "../types/apiReference";

export const apiReference: ApiReference = {
  "routes": [
    {
      "method": "POST",
      "path": "/api/auth/dev-login",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/auth/login",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/auth/logout",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/auth/password-requirements",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/auth/provider",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/auth/refresh",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/auth/register",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/auth/registration-success",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/auth/validate-password",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/auth/verify",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/performance/metrics",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/subtasks/summaries",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/tasks/summaries",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/tasks/{task_id}/context/summary",
      "pathParams": [
        "task_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v1/alerts/check-rules",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v1/alerts/events",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v1/alerts/events/{event_index}/acknowledge",
      "pathParams": [
        "event_index"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v1/alerts/rules",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v1/alerts/rules",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "DELETE",
      "path": "/api/v1/alerts/rules/{rule_id}",
      "pathParams": [
        "rule_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v1/alerts/rules/{rule_id}",
      "pathParams": [
        "rule_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v1/alerts/test-webhook",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v1/performance/metrics/alerts",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v1/performance/metrics/clear-cache",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v1/performance/metrics/overview",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v1/performance/metrics/timeseries",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/branches/project/{project_id}/summaries",
      "pathParams": [
        "project_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/branches/summaries/bulk",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/branches/{$}",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "DELETE",
      "path": "/api/v2/branches/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/branches/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/broadcast/notify",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/connections/health",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/connections/status",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/contexts/{level}",
      "pathParams": [
        "level"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/contexts/{level}/list",
      "pathParams": [
        "level"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "DELETE",
      "path": "/api/v2/contexts/{level}/{context_id}",
      "pathParams": [
        "level",
        "context_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/contexts/{level}/{context_id}",
      "pathParams": [
        "level",
        "context_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/contexts/{level}/{context_id}",
      "pathParams": [
        "level",
        "context_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/contexts/{level}/{context_id}/delegate",
      "pathParams": [
        "level",
        "context_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/contexts/{level}/{context_id}/insights",
      "pathParams": [
        "level",
        "context_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/contexts/{level}/{context_id}/progress",
      "pathParams": [
        "level",
        "context_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/contexts/{level}/{context_id}/resolve",
      "pathParams": [
        "level",
        "context_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/contexts/{level}/{context_id}/summary",
      "pathParams": [
        "level",
        "context_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/feedback",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/openrig/feedback",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/machines",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/modules",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/modules/{slug}/versions/{version}",
      "pathParams": [
        "slug",
        "version"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/openrig/modules/{slug}/versions/{version}",
      "pathParams": [
        "slug",
        "version"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/overlay",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/openrig/overlay",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/rooms",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/openrig/rooms",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "DELETE",
      "path": "/api/v2/openrig/rooms/{room}",
      "pathParams": [
        "room"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/rooms/{room}/overlay",
      "pathParams": [
        "room"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/openrig/rooms/{room}/overlay",
      "pathParams": [
        "room"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/rooms/{room}/rigspec",
      "pathParams": [
        "room"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/rooms/{room}/seats",
      "pathParams": [
        "room"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/openrig/rooms/{room}/seats",
      "pathParams": [
        "room"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "DELETE",
      "path": "/api/v2/openrig/rooms/{room}/seats/{seat}",
      "pathParams": [
        "room",
        "seat"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/rooms/{room}/seats/{seat}/links",
      "pathParams": [
        "room",
        "seat"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/openrig/rooms/{room}/seats/{seat}/links",
      "pathParams": [
        "room",
        "seat"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "DELETE",
      "path": "/api/v2/openrig/rooms/{room}/seats/{seat}/links/{to}/{kind}",
      "pathParams": [
        "room",
        "seat",
        "to",
        "kind"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/rooms/{room}/seats/{seat}/messages",
      "pathParams": [
        "room",
        "seat"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/openrig/rooms/{room}/seats/{seat}/messages",
      "pathParams": [
        "room",
        "seat"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/openrig/rooms/{room}/seats/{seat}/messages/{id}/ack",
      "pathParams": [
        "room",
        "seat",
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/openrig/rooms/{room}/seats/{seat}/occupant",
      "pathParams": [
        "room",
        "seat"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/rooms/{room}/seats/{seat}/overlay",
      "pathParams": [
        "room",
        "seat"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/openrig/rooms/{room}/seats/{seat}/overlay",
      "pathParams": [
        "room",
        "seat"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/openrig/rooms/{room}/seats/{seat}/permission-policy",
      "pathParams": [
        "room",
        "seat"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/openrig/rooms/{room}/seats/{seat}/pin",
      "pathParams": [
        "room",
        "seat"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/openrig/rooms/{room}/team",
      "pathParams": [
        "room"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/openrig/seat-status",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/seat-types",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/openrig/seat-types",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/openrig/seat-types/seed",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/openrig/seat-types/{slug}/versions",
      "pathParams": [
        "slug"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/seats/{room}/{seat}",
      "pathParams": [
        "room",
        "seat"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/settings",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/openrig/settings",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/teams",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/openrig/teams",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "DELETE",
      "path": "/api/v2/openrig/teams/{team}",
      "pathParams": [
        "team"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/teams/{team}",
      "pathParams": [
        "team"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/openrig/teams/{team}/members",
      "pathParams": [
        "team"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/openrig/teams/{team}/members",
      "pathParams": [
        "team"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "DELETE",
      "path": "/api/v2/openrig/teams/{team}/members/{user}",
      "pathParams": [
        "team",
        "user"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PATCH",
      "path": "/api/v2/openrig/teams/{team}/members/{user}",
      "pathParams": [
        "team",
        "user"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/projects/",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/projects/",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "DELETE",
      "path": "/api/v2/projects/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/projects/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/projects/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/projects/{id}/health-check",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/sessions",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/sessions/{id}/events",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/subtasks",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/subtasks/task/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "DELETE",
      "path": "/api/v2/subtasks/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/subtasks/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/subtasks/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/subtasks/{id}/complete",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/tasks/",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/tasks/",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "DELETE",
      "path": "/api/v2/tasks/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/tasks/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PUT",
      "path": "/api/v2/tasks/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/tasks/{id}/complete",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/tasks/{id}/events",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/tasks/{task_id}/subtasks/summaries",
      "pathParams": [
        "task_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/tokens",
      "pathParams": [],
      "handler": "list",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/tokens",
      "pathParams": [],
      "handler": "create",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/tokens/",
      "pathParams": [],
      "handler": "list",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/tokens/",
      "pathParams": [],
      "handler": "create",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/tokens/cleanup",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/tokens/generate",
      "pathParams": [],
      "handler": "create",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/tokens/health",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/tokens/legacy/tokens",
      "pathParams": [],
      "handler": "list",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/tokens/validate",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "DELETE",
      "path": "/api/v2/tokens/{token_id}",
      "pathParams": [
        "token_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/api/v2/tokens/{token_id}",
      "pathParams": [
        "token_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PATCH",
      "path": "/api/v2/tokens/{token_id}/reactivate",
      "pathParams": [
        "token_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "PATCH",
      "path": "/api/v2/tokens/{token_id}/revoke",
      "pathParams": [
        "token_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/api/v2/tokens/{token_id}/rotate",
      "pathParams": [
        "token_id"
      ],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/auth/supabase/health",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/auth/supabase/me",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/auth/supabase/oauth/",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/auth/supabase/password-reset",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/auth/supabase/resend-verification",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/auth/supabase/signin",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/auth/supabase/signout",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/auth/supabase/signup",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/auth/supabase/update-password",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/auth/supabase/verify-token",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/health",
      "pathParams": [],
      "handler": "handleHealth",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/mcp",
      "pathParams": [],
      "handler": "mcpSSEHandler",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/mcp",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/register",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/registrations",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "POST",
      "path": "/unregister",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/ws/connector",
      "pathParams": [],
      "handler": "",
      "description": ""
    },
    {
      "method": "GET",
      "path": "/ws/metrics",
      "pathParams": [],
      "handler": "handleWebSocketMetrics",
      "description": "handleWebSocketMetrics ports websocket_routes.metrics(). The Go port keeps its\nPrometheus registry in-process (fastmcp/server/metrics) and exposes the\nconnection gauge and retry counter from GetMetricsSummary."
    },
    {
      "method": "GET",
      "path": "/ws/realtime",
      "pathParams": [],
      "handler": "handleRealtime",
      "description": "handleRealtime ports realtime_updates: resolve the caller from ?token=/bearer under the\nsame AUTH_ENABLED decision every REST route applies (wsAuthenticateRealtime), accept, send\nthe welcome frame, replay missed notifications, then answer ping/heartbeat/subscribe."
    },
    {
      "method": "GET",
      "path": "/ws/sessions/{id}",
      "pathParams": [
        "id"
      ],
      "handler": "",
      "description": ""
    }
  ],
  "tools": [
    {
      "name": "manage_task",
      "description": "\nTASK MANAGEMENT - Complete lifecycle: CRUD | search | dependencies | workflow | vision insights | progress tracking\n\nUSE FOR: Task operations creation→completion | AI recommendations | Project organization | Team collaboration\n\nAI RULES: Create before work (\u003e1 file edit) | Use 'next' for recommendations | Update progress regularly | Complete with summaries | Search before creating | Use manage_subtask for complex work\n\n| Action              | Required                          | Optional                           | Description                        |\n|---------------------|-----------------------------------|------------------------------------|------------------------------------|\n| create              | git_branch_id, title, assignees   | description, status, priority, details, estimated_effort, labels, due_date, dependencies | Create task (min 1 agent)         |\n| update              | task_id                           | title, description, status, priority, details, estimated_effort, assignees, labels, due_date, context_id | Update task                        |\n| get                 | task_id                           | include_context                    | Retrieve task                      |\n| delete              | task_id                           |                                    | Remove task                        |\n| complete            | task_id                           | completion_summary, testing_notes  | Complete task                      |\n| list                | (none)                            | status, priority, assignees, labels, limit, git_branch_id | List with filters                  |\n| search              | query                             | limit, git_branch_id               | Full-text search                   |\n| next                | git_branch_id                     | include_context                    | Get recommended task               |\n| add_dependency      | task_id, dependency_id            |                                    | Add dependency                     |\n| remove_dependency   | task_id, dependency_id            |                                    | Remove dependency                  |\n| ai_plan             | requirements, title, git_branch_id| description, context, auto_create_tasks | AI task plan                       |\n| ai_create           | title, git_branch_id              | enable_ai_breakdown, enable_smart_assignment, ai_requirements | AI-enhanced task                   |\n| ai_enhance          | task_id                           | analyze_complexity, suggest_optimizations, identify_risks | AI insights                        |\n| ai_analyze          | requirements                      | context                            | Analyze requirements               |\n| ai_suggest_agents   | requirements                      | available_agents                   | Suggest agents                     |\n\nVALIDATION: Two-stage (schema: 'action' only → business logic: action-specific) | CRUD needs task_id | Create needs git_branch_id+title+assignees (min 1) | Search needs query | Dependencies need task_id+dependency_id\n\nKEY PARAMS: assignees (@agent-name, comma-separated, REQUIRED for create) | priority (low|medium|high|urgent|critical, affects 'next') | status (todo|in_progress|blocked|review|testing|done|cancelled) | dependencies (task IDs, comma-separated) | include_context (true for vision)\n\nVISION (Auto): Task enrichment | Priority estimation | Workflow hints | Progress tracking | Blocker detection | Impact analysis | Context updates\n\nBEST PRACTICES: Create before work | Specific titles | Update status | Detailed summaries | Search first | Define deps upfront | Use labels\n\nPROGRESS UPDATES: When updating 'status' or 'progress_percentage', you MUST include the 'details' parameter with at least 10 characters describing the progress made. This enforces documentation best practices and ensures all changes are tracked.\n\nExamples:\n```python\n# ❌ WRONG - Will fail validation\nmanage_task(action=\"update\", task_id=\"xxx\", status=\"in_progress\")\n\n# ✅ CORRECT - Includes required details\nmanage_task(\n    action=\"update\",\n    task_id=\"xxx\",\n    status=\"in_progress\",\n    details=\"Started implementation of authentication module\"\n)\n\n# ✅ CORRECT - Progress percentage with details\nmanage_task(\n    action=\"update\",\n    task_id=\"xxx\",\n    progress_percentage=50,\n    details=\"Completed database schema design and API endpoint structure\"\n)\n```\n\nDEPENDENCIES: Sequential (A→B→C) | Parallel | Blocking | Cross-feature | Add IF task needs output OR sequence part\n\nERRORS: Missing fields→specific error | Unknown actions→valid list | Internal→logged+generic | Vision→don't block\n",
      "parameters": {
        "properties": {
          "action": {
            "description": "Task management action. Valid: 'create', 'update', 'get', 'delete', 'complete', 'list', 'search', 'next', 'add_dependency', 'remove_dependency', 'ai_plan', 'ai_create', 'ai_enhance', 'ai_analyze', 'ai_suggest_agents'. Use 'create' to start new work, 'next' to find work, 'complete' when done. AI actions provide intelligent task planning and enhancement.",
            "title": "Action",
            "type": "string"
          },
          "ai_requirements": {
            "default": null,
            "description": "[OPTIONAL] Additional AI requirements for enhanced task creation. Optional for 'ai_create'. Provides context for AI planning.",
            "title": "Ai Requirements",
            "type": "string"
          },
          "analyze_complexity": {
            "default": null,
            "description": "[OPTIONAL] Analyze task complexity using AI. Optional for 'ai_enhance'. Default: true.",
            "title": "Analyze Complexity",
            "type": "boolean"
          },
          "assignee": {
            "default": null,
            "description": "[OPTIONAL] Filter tasks by specific assignee. Optional for 'list' action. Example: 'user123'.",
            "title": "Assignee",
            "type": "string"
          },
          "assignees": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            ],
            "default": null,
            "description": "[OPTIONAL] **REQUIRED for create action** - Assignee identifiers (minimum 1 required). Use @seat-key format (e.g., '@lead', '@go-dev'); a known agent role such as 'coding-agent' is accepted and becomes '@coding-agent'. A bare name that is not a known role is rejected. For multiple assignees use comma-separated: '@lead,@go-dev'.",
            "title": "Assignees"
          },
          "auto_create_tasks": {
            "default": null,
            "description": "[OPTIONAL] Whether to automatically create MCP tasks from AI plan. Optional for 'ai_plan'. Default: true.",
            "title": "Auto Create Tasks",
            "type": "boolean"
          },
          "available_agents": {
            "default": null,
            "description": "[OPTIONAL] Comma-separated list of available agents for assignment suggestions. Optional for 'ai_suggest_agents'.",
            "title": "Available Agents",
            "type": "string"
          },
          "completion_summary": {
            "default": null,
            "description": "[OPTIONAL] DETAILED summary of what was accomplished. Highly recommended for 'complete' action. Example: 'Implemented JWT auth with 2FA support, added password reset flow, integrated with existing user service'",
            "title": "Completion Summary",
            "type": "string"
          },
          "context": {
            "default": null,
            "description": "[OPTIONAL] Planning context for AI operations. Optional. Values: 'new_feature', 'bug_fix', 'enhancement', 'refactor'. Default: 'new_feature'.",
            "title": "Context",
            "type": "string"
          },
          "context_id": {
            "default": null,
            "description": "[OPTIONAL] Context identifier for task. Optional for 'update' action. Usually same as task_id. Used for context synchronization and validation. Auto-created during task creation.",
            "title": "Context Id",
            "type": "string"
          },
          "dependencies": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            ],
            "default": null,
            "description": "[OPTIONAL] Task IDs this task depends on (for create action) - accepts string (single dependency) or comma-separated string (multiple dependencies). Optional. Examples: 'task-uuid' or 'task-uuid-1,task-uuid-2'. Tasks must be completed before this task can start.",
            "title": "Dependencies"
          },
          "dependency_id": {
            "default": null,
            "description": "[OPTIONAL] UUID of task that must be completed first. Required for: add_dependency, remove_dependency. Use to establish task order.",
            "title": "Dependency Id",
            "type": "string"
          },
          "description": {
            "default": null,
            "description": "[OPTIONAL] Detailed task description with acceptance criteria. Optional but recommended for: create. Include technical approach, dependencies, and success criteria.",
            "title": "Description",
            "type": "string"
          },
          "details": {
            "default": null,
            "description": "[OPTIONAL] [REQUIRED when updating status or progress_percentage] Progress notes describing what changed (minimum 10 characters). This field is MANDATORY when updating status or progress to ensure all changes are documented. Optional for: create",
            "title": "Details",
            "type": "string"
          },
          "due_date": {
            "default": null,
            "description": "[OPTIONAL] Target completion date in ISO 8601 format (YYYY-MM-DD or full datetime). Optional. Example: '2024-12-31' or '2024-12-31T23:59:59Z'",
            "title": "Due Date",
            "type": "string"
          },
          "enable_ai_breakdown": {
            "default": null,
            "description": "[OPTIONAL] Enable AI-powered task breakdown into subtasks. Optional for 'ai_create'. Default: false.",
            "title": "Enable Ai Breakdown",
            "type": "boolean"
          },
          "enable_auto_subtasks": {
            "default": null,
            "description": "[OPTIONAL] Enable automatic subtask creation from AI analysis. Optional for 'ai_create'. Default: false.",
            "title": "Enable Auto Subtasks",
            "type": "boolean"
          },
          "enable_smart_assignment": {
            "default": null,
            "description": "[OPTIONAL] Enable AI-powered agent assignment suggestions. Optional for 'ai_create'. Default: false.",
            "title": "Enable Smart Assignment",
            "type": "boolean"
          },
          "estimated_effort": {
            "default": null,
            "description": "[OPTIONAL] Time estimate like '2 hours', '3 days', '1 week'. Helps with planning. Optional for: create, update",
            "title": "Estimated Effort",
            "type": "string"
          },
          "force_full_generation": {
            "default": null,
            "description": "[OPTIONAL] Force vision system regeneration. Optional. Default: false. Use if insights seem stale.",
            "title": "Force Full Generation",
            "type": "boolean"
          },
          "git_branch_id": {
            "default": null,
            "description": "[REQUIRED for 'create' and 'next' actions] Git branch UUID identifier - contains all context (project_id, git_branch_name, user_id). Required for 'create' and 'next' actions. Get from git branch creation or list.",
            "title": "Git Branch Id",
            "type": "string"
          },
          "identify_risks": {
            "default": null,
            "description": "[OPTIONAL] Identify potential risks using AI analysis. Optional for 'ai_enhance'. Default: true.",
            "title": "Identify Risks",
            "type": "boolean"
          },
          "include_context": {
            "default": null,
            "description": "[OPTIONAL] Include vision insights and recommendations (true/false). Optional for 'get' and 'next' actions. Default: false. Set true for AI guidance.",
            "title": "Include Context",
            "type": "boolean"
          },
          "labels": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "items": {
                  "type": "string"
                },
                "type": "array"
              }
            ],
            "default": null,
            "description": "[OPTIONAL] Categories/tags - accepts string (single label) or comma-separated string (multiple labels). Optional. Examples: 'frontend' or 'frontend,auth,bug'. Useful for filtering.",
            "title": "Labels"
          },
          "limit": {
            "default": null,
            "description": "[OPTIONAL] Maximum number of results. Optional for 'list' and 'search'. Default: 50. Range: 1-100",
            "title": "Limit",
            "type": "integer"
          },
          "offset": {
            "default": null,
            "description": "[OPTIONAL] Result offset for pagination. Optional. Default: 0. Used with 'limit' for paginated results.",
            "title": "Offset",
            "type": "integer"
          },
          "planning_context": {
            "default": null,
            "description": "[OPTIONAL] Context for AI planning operations. Optional for 'ai_create'. Values: 'new_feature', 'bug_fix', 'enhancement'. Default: 'new_feature'.",
            "title": "Planning Context",
            "type": "string"
          },
          "priority": {
            "default": null,
            "description": "[OPTIONAL] Task priority: 'low', 'medium', 'high', 'urgent', 'critical'. Default: 'medium'. Higher priority tasks returned first by 'next' action.",
            "title": "Priority",
            "type": "string"
          },
          "progress_percentage": {
            "default": null,
            "description": "[OPTIONAL] Task completion percentage (0-100). Optional for 'update'. Automatically maps to status transitions and progress tracking when supplied.",
            "title": "Progress Percentage",
            "type": "integer"
          },
          "query": {
            "default": null,
            "description": "[OPTIONAL] Search terms for finding tasks. Required for 'search' action. Searches in title, description, and labels. Example: 'authentication jwt'. Note: DEPRECATED for dependency operations - use 'dependency_id' instead.",
            "title": "Query",
            "type": "string"
          },
          "requirements": {
            "default": null,
            "description": "[OPTIONAL] Requirements description or JSON for AI planning. Required for: ai_plan, ai_analyze, ai_suggest_agents. Can be comma-separated text or structured JSON format.",
            "title": "Requirements",
            "type": "string"
          },
          "sort_by": {
            "default": null,
            "description": "[OPTIONAL] Field to sort results by. Optional. Examples: 'created_at', 'updated_at', 'priority', 'status', 'title'.",
            "title": "Sort By",
            "type": "string"
          },
          "sort_order": {
            "default": null,
            "description": "[OPTIONAL] Sort order for results. Optional. Valid values: 'asc', 'desc'. Default: 'desc'.",
            "title": "Sort Order",
            "type": "string"
          },
          "status": {
            "default": null,
            "description": "[OPTIONAL] Task status: 'todo', 'in_progress', 'blocked', 'review', 'testing', 'done', 'cancelled'. Optional. Changes automatically: create→todo, update→in_progress, complete→done",
            "title": "Status",
            "type": "string"
          },
          "suggest_optimizations": {
            "default": null,
            "description": "[OPTIONAL] Generate AI-powered optimization suggestions. Optional for 'ai_enhance'. Default: true.",
            "title": "Suggest Optimizations",
            "type": "boolean"
          },
          "tag": {
            "default": null,
            "description": "[OPTIONAL] Filter tasks by specific tag/label. Optional for 'list' action. Example: 'frontend'.",
            "title": "Tag",
            "type": "string"
          },
          "task_id": {
            "default": null,
            "description": "[OPTIONAL] Task identifier (UUID). Required for: update, get, delete, complete, add/remove_dependency. Get from create response or list/search results.",
            "title": "Task Id",
            "type": "string"
          },
          "testing_notes": {
            "default": null,
            "description": "[OPTIONAL] Description of testing performed. Optional for 'complete' action. Example: 'Added unit tests for auth service, manual testing of login/logout flows, verified token expiry'",
            "title": "Testing Notes",
            "type": "string"
          },
          "title": {
            "default": null,
            "description": "[OPTIONAL] Task title - be specific and action-oriented. Required for: create. Example: 'Implement JWT authentication with refresh tokens' not just 'Auth'",
            "title": "Title",
            "type": "string"
          },
          "user_id": {
            "default": null,
            "description": "[OPTIONAL] User ID performing the operation. Optional - automatically populated from authentication context.",
            "title": "User Id",
            "type": "string"
          }
        },
        "required": [
          "action"
        ],
        "type": "object"
      },
      "actions": []
    },
    {
      "name": "manage_subtask",
      "description": "\nSUBTASK MANAGEMENT - Hierarchical breakdown: CRUD | progress tracking | auto parent updates | context sync\n\nUSE FOR: Breaking down complex tasks | Granular progress | Multi-step workflows\n\nAI RULES: Use for tasks with multiple steps | Update with progress_notes (MANDATORY for update/complete) | progress_percentage auto-maps status | Complete with detailed summaries | All actions auto-update parent\n\n| Action   | Required                 | Optional                           | Description                  |\n|----------|--------------------------|------------------------------------|-----------------------------|\n| create   | task_id, title           | description, status, priority, assignees, progress_notes | Create subtask                  |\n| update   | task_id, subtask_id, progress_notes | title, description, status, priority, assignees, progress_percentage, blockers, insights_found | Update with progress history    |\n| delete   | task_id, subtask_id      |                                    | Remove subtask              |\n| get      | task_id, subtask_id      |                                    | Retrieve subtask            |\n| list     | task_id                  |                                    | List all subtasks           |\n| complete | task_id, subtask_id, completion_summary, progress_notes | impact_on_parent, insights_found | Complete with context       |\n\nVALIDATION: task_id always required | subtask_id for update/delete/get/complete | title for create | progress_notes MANDATORY for update/complete | completion_summary MANDATORY for complete\n\nKEY PARAMS: progress_notes (MANDATORY update/complete, builds timestamped history) | completion_summary (MANDATORY complete, be specific) | progress_percentage (0-100, auto-maps: 0=todo, 1-99=in_progress, 100=done) | assignees (inherits from parent if not specified)\n\nAUTO FEATURES: Progress history tracking | Agent inheritance | Parent progress recalc | Status mapping | Blocker escalation | Insight propagation | Workflow hints\n\nBEST PRACTICES: Update with progress_notes every step | Complete with detailed summary | Use progress_percentage over status | Let assignees inherit\n\n**Progress Documentation Requirements**: The 'progress_notes' parameter is MANDATORY for 'update' and 'complete' actions. This builds timestamped progress history and ensures visibility into work progress. Operations will fail without this field.\n\nUSAGE EXAMPLES:\n```python\n# ❌ WRONG - Will fail validation\nmanage_subtask(action=\"update\", task_id=\"xxx\", subtask_id=\"yyy\", progress_percentage=50)\n\n# ✅ CORRECT - Includes required progress_notes\nmanage_subtask(\n    action=\"update\",\n    task_id=\"xxx\",\n    subtask_id=\"yyy\",\n    progress_percentage=50,\n    progress_notes=\"Completed UI mockup, starting on API integration\"\n)\n\n# ❌ WRONG - Complete without progress_notes\nmanage_subtask(action=\"complete\", task_id=\"xxx\", subtask_id=\"yyy\", completion_summary=\"Done\")\n\n# ✅ CORRECT - Complete with both required fields\nmanage_subtask(\n    action=\"complete\",\n    task_id=\"xxx\",\n    subtask_id=\"yyy\",\n    completion_summary=\"Completed JWT token structure with proper expiry times\",\n    progress_notes=\"Final review completed, structure documented\"\n)\n```\n\nERRORS: Missing fields→specific error | Unknown actions→valid list | Internal→logged+generic | Context updates→don't block\n",
      "parameters": {
        "properties": {
          "action": {
            "description": "[OPTIONAL] Subtask management action to perform. Valid values: create, update, delete, get, list, complete",
            "title": "Action",
            "type": "string"
          },
          "assignees": {
            "default": null,
            "description": "[OPTIONAL] Agent identifiers - **Inherits from parent task if not specified**. Use @agent-name format. Comma-separated for multiple: 'coding-agent,@test-orchestrator-agent'. Leave empty to inherit parent's agents automatically.",
            "title": "Assignees",
            "type": "string"
          },
          "blockers": {
            "default": null,
            "description": "[OPTIONAL] Issues preventing progress. Comma-separated string or JSON array. Example: 'Missing API documentation,Waiting for database schema approval'",
            "title": "Blockers",
            "type": "string"
          },
          "challenges_overcome": {
            "default": null,
            "description": "[OPTIONAL] Challenges faced and how they were resolved. Comma-separated string or JSON array",
            "title": "Challenges Overcome",
            "type": "string"
          },
          "completion_quality": {
            "default": null,
            "description": "[OPTIONAL] Quality assessment of work completed. Example: 'Production-ready', 'Requires review', 'Prototype only'",
            "title": "Completion Quality",
            "type": "string"
          },
          "completion_summary": {
            "default": null,
            "description": "[REQUIRED for 'complete' action] [REQUIRED for 'complete' action] Detailed summary of what was accomplished. BE SPECIFIC! MANDATORY for complete operations. Example: 'Implemented JWT authentication with refresh tokens, 2-hour expiry, and secure httpOnly cookies'",
            "title": "Completion Summary",
            "type": "string"
          },
          "deliverables": {
            "default": null,
            "description": "[OPTIONAL] Artifacts or outputs created. Comma-separated string or JSON array",
            "title": "Deliverables",
            "type": "string"
          },
          "description": {
            "default": null,
            "description": "[OPTIONAL] Detailed subtask description explaining what needs to be done. Include acceptance criteria if relevant",
            "title": "Description",
            "type": "string"
          },
          "impact_on_parent": {
            "default": null,
            "description": "[OPTIONAL] How completing this subtask affects the parent task. Required for complete action",
            "title": "Impact On Parent",
            "type": "string"
          },
          "insights_found": {
            "default": null,
            "description": "[OPTIONAL] Important discoveries or learnings. Comma-separated string or JSON array. Example: 'Found existing utility function for validation,Discovered performance bottleneck in query'",
            "title": "Insights Found",
            "type": "string"
          },
          "next_recommendations": {
            "default": null,
            "description": "[OPTIONAL] Suggestions for future work. Comma-separated string or JSON array",
            "title": "Next Recommendations",
            "type": "string"
          },
          "priority": {
            "default": null,
            "description": "[OPTIONAL] Subtask priority: 'low', 'medium', 'high', 'urgent', 'critical'. Default: inherits from parent",
            "title": "Priority",
            "type": "string"
          },
          "progress_notes": {
            "default": null,
            "description": "[REQUIRED for 'update' and 'complete' actions] [REQUIRED for 'update' and 'complete' actions] Brief description of current work status that builds progress history. MANDATORY for update and complete operations. Creates timestamped progress entries automatically. Minimum 10 characters. Example: 'Completed UI mockup, starting on API integration'",
            "title": "Progress Notes",
            "type": "string"
          },
          "progress_percentage": {
            "default": null,
            "description": "[OPTIONAL] Integer 0-100 representing completion. Automatically maps to status (0=todo, 1-99=in_progress, 100=done). Use this instead of status field",
            "title": "Progress Percentage",
            "type": "integer"
          },
          "skills_learned": {
            "default": null,
            "description": "[OPTIONAL] New skills or knowledge gained. Comma-separated string or JSON array",
            "title": "Skills Learned",
            "type": "string"
          },
          "status": {
            "default": null,
            "description": "[OPTIONAL] Subtask status: 'todo', 'in_progress', 'done'. Note: use progress_percentage instead for automatic status mapping",
            "title": "Status",
            "type": "string"
          },
          "subtask_id": {
            "default": null,
            "description": "[REQUIRED for 'update', 'delete', 'get', 'complete' actions] Subtask identifier (UUID). Required for update, delete, get, complete actions",
            "title": "Subtask Id",
            "type": "string"
          },
          "task_id": {
            "default": null,
            "description": "[REQUIRED for 'create', 'update', 'delete', 'get', 'list', 'complete' actions] Parent task identifier (UUID). Required for all actions",
            "title": "Task Id",
            "type": "string"
          },
          "testing_notes": {
            "default": null,
            "description": "[OPTIONAL] Notes about testing performed. Example: 'Tested login flow with valid/invalid credentials, verified token refresh'",
            "title": "Testing Notes",
            "type": "string"
          },
          "title": {
            "default": null,
            "description": "[REQUIRED for 'create' action] Subtask title. Required for create, optional for update",
            "title": "Title",
            "type": "string"
          },
          "user_id": {
            "default": null,
            "description": "[OPTIONAL] User identifier for authentication and audit trails",
            "title": "User Id",
            "type": "string"
          }
        },
        "required": [
          "action"
        ],
        "type": "object"
      },
      "actions": []
    },
    {
      "name": "manage_context",
      "description": "\nCONTEXT MANAGEMENT - 4-tier hierarchy (Global→Project→Branch→Task): CRUD | inheritance | caching | delegation | insights\n\nACTIONS: create | get | update | delete | resolve (full chain) | delegate (move between levels) | add_insight | add_progress | list\n\nLEVELS: global (user-scoped) | project | branch | task | Each inherits from parent\n\nKEY PARAMS: level (tier) | context_id (ID for level) | force_refresh (bypass cache) | include_inherited (full chain) | propagate_changes (cascade) | delegate_to ('delegate' action) | content ('add_insight'/'add_progress' actions)\n\nFEATURES: Unified API | Auto-inheritance | Smart caching | Change propagation | Delegation queue | Backward compatible\n\nERRORS: Missing fields→specific error | Unknown actions→valid list | Internal→logged+generic\n",
      "parameters": {
        "properties": {
          "action": {
            "description": "[OPTIONAL] Context management action to perform. Valid: 'create', 'get', 'update', 'delete', 'resolve', 'delegate', 'add_insight', 'add_progress', 'list'",
            "title": "Action",
            "type": "string"
          },
          "agent": {
            "default": null,
            "description": "[OPTIONAL] Agent identifier that created the insight or progress update. String identifier for tracking agent contributions",
            "title": "Agent",
            "type": "string"
          },
          "category": {
            "default": null,
            "description": "[OPTIONAL] Insight category for add_insight operations. Valid: 'technical', 'business', 'performance', 'risk', 'discovery'",
            "title": "Category",
            "type": "string"
          },
          "content": {
            "default": null,
            "description": "[REQUIRED for 'add_insight' and 'add_progress' actions] Content for insight or progress operations. String content that will be categorized and added to the specified context level",
            "title": "Content",
            "type": "string"
          },
          "context_id": {
            "default": null,
            "description": "[REQUIRED for all actions except 'list'] Context identifier appropriate for the level. Use user_id for global, project_id for project, git_branch_id for branch, task_id for task",
            "title": "Context Id",
            "type": "string"
          },
          "data": {
            "default": null,
            "description": "[OPTIONAL] Context data as JSON string (automatically parsed). Supports nested structures, arrays, and complex data types",
            "title": "Data",
            "type": "string"
          },
          "delegate_data": {
            "default": null,
            "description": "[OPTIONAL] Specific data to delegate to target level as JSON string. Can be subset of source context or completely new data",
            "title": "Delegate Data",
            "type": "string"
          },
          "delegate_to": {
            "default": null,
            "description": "[REQUIRED for 'delegate' action] Target level for context delegation operations. Valid: 'global', 'project', 'branch', 'task'. Used with delegate action",
            "title": "Delegate To",
            "type": "string"
          },
          "delegation_reason": {
            "default": null,
            "description": "[OPTIONAL] Reason for context delegation for audit trails and team communication. Helps track why data was moved between hierarchy levels",
            "title": "Delegation Reason",
            "type": "string"
          },
          "filters": {
            "default": null,
            "description": "[OPTIONAL] Filter criteria for list operations as JSON string. Supports filtering by data fields, creation dates, agents, and other metadata",
            "title": "Filters",
            "type": "string"
          },
          "force_refresh": {
            "default": null,
            "description": "[OPTIONAL] Bypass cache and force fresh data retrieval. Use when cache consistency is critical. Accepts: 'true', 'false', '1', '0'",
            "title": "Force Refresh",
            "type": "string"
          },
          "git_branch_id": {
            "default": null,
            "description": "[OPTIONAL] Git branch identifier for branch-level context operations. Required for branch and task level operations",
            "title": "Git Branch Id",
            "type": "string"
          },
          "importance": {
            "default": null,
            "description": "[OPTIONAL] Importance level for insights and progress updates. Valid: 'low', 'medium', 'high', 'critical'",
            "title": "Importance",
            "type": "string"
          },
          "include_inherited": {
            "default": null,
            "description": "[OPTIONAL] Include inherited data from parent levels in response. Enables complete context resolution with inheritance chain. Accepts: 'true', 'false', '1', '0'",
            "title": "Include Inherited",
            "type": "string"
          },
          "level": {
            "default": null,
            "description": "[REQUIRED for all actions except 'list'] Context hierarchy level. Valid: 'global' (user-scoped), 'project', 'branch', 'task'. Determines inheritance scope and data isolation",
            "title": "Level",
            "type": "string"
          },
          "project_id": {
            "default": null,
            "description": "[OPTIONAL] Project identifier for project-level context operations. Required for project, branch, and task level operations when not inferrable",
            "title": "Project Id",
            "type": "string"
          },
          "propagate_changes": {
            "default": null,
            "description": "[OPTIONAL] Automatically cascade changes to child levels in hierarchy. Maintains consistency across hierarchy. Accepts: 'true', 'false', '1', '0'",
            "title": "Propagate Changes",
            "type": "string"
          },
          "user_id": {
            "default": null,
            "description": "[OPTIONAL] User identifier for authentication and audit trails. Used for user-scoped global contexts and access control",
            "title": "User Id",
            "type": "string"
          }
        },
        "required": [
          "action"
        ],
        "type": "object"
      },
      "actions": []
    },
    {
      "name": "manage_project",
      "description": "\nPROJECT MANAGEMENT - Complete lifecycle: CRUD | health monitoring | resource management | multi-project coordination\n\nACTIONS: create | get | list | update | delete | project_health_check | cleanup_obsolete | validate_integrity | rebalance_agents\n\nKEY PARAMS: name (REQUIRED for create) | project_id (REQUIRED for most except create/list) | force (bypass safety for maintenance/delete)\n\nFEATURES: Health monitoring | Resource allocation | Cross-project learning | Agent optimization\n\nERRORS: Missing fields→specific error | Duplicate names→rejected | Invalid UUIDs→clear error | Maintenance→safety warnings\n",
      "parameters": {
        "properties": {
          "action": {
            "description": "[OPTIONAL] Project management action to perform. Valid values: create, get, list, update, delete, project_health_check, cleanup_obsolete, validate_integrity, rebalance_agents",
            "title": "Action",
            "type": "string"
          },
          "description": {
            "default": null,
            "description": "[OPTIONAL] Project description. Optional for create/update operations",
            "title": "Description",
            "type": "string"
          },
          "force": {
            "default": null,
            "description": "[OPTIONAL] Force parameter to bypass safety checks for maintenance and delete operations",
            "title": "Force",
            "type": "string"
          },
          "name": {
            "default": null,
            "description": "[REQUIRED for 'create' action] Project name. Required for create, can be used instead of project_id for get action",
            "title": "Name",
            "type": "string"
          },
          "project_id": {
            "default": null,
            "description": "[REQUIRED for most actions except 'create' and 'list'] Project identifier (UUID). Required for most actions except create/list",
            "title": "Project Id",
            "type": "string"
          },
          "user_id": {
            "default": null,
            "description": "[OPTIONAL] User identifier for authentication and audit trails",
            "title": "User Id",
            "type": "string"
          }
        },
        "required": [
          "action"
        ],
        "type": "object"
      },
      "actions": []
    },
    {
      "name": "manage_git_branch",
      "description": "\nGIT BRANCH MANAGEMENT - Branch operations: CRUD | agent assignment | lifecycle | statistics\n\nACTIONS: create | get | list | update | delete | assign_agent | unassign_agent | get_statistics | archive | restore\n\nKEY PARAMS: project_id (REQUIRED for all) | git_branch_name (REQUIRED for create) | git_branch_id (REQUIRED for most except create/list) | agent_id (REQUIRED for assign/unassign)\n\nAGENT ASSIGNMENT: Use git_branch_name OR git_branch_id for identification\n\nSTATISTICS: total_tasks | completed_tasks | progress_percentage\n\nERRORS: Missing fields→specific error | Duplicate names→rejected | Invalid UUIDs→clear error\n",
      "parameters": {
        "properties": {
          "action": {
            "description": "[OPTIONAL] Git branch management action to perform. Valid values: create, get, list, update, delete, assign_agent, unassign_agent, get_statistics, archive, restore",
            "title": "Action",
            "type": "string"
          },
          "agent_id": {
            "default": null,
            "description": "[REQUIRED for 'assign_agent' and 'unassign_agent' actions] Agent identifier for assignment operations. Required for assign_agent/unassign_agent actions",
            "title": "Agent Id",
            "type": "string"
          },
          "git_branch_description": {
            "default": null,
            "description": "[OPTIONAL] Description of the git branch. Optional for create/update operations",
            "title": "Git Branch Description",
            "type": "string"
          },
          "git_branch_id": {
            "default": null,
            "description": "[REQUIRED for most actions except 'create' and 'list'] Git branch identifier (UUID). Required for most actions except create/list",
            "title": "Git Branch Id",
            "type": "string"
          },
          "git_branch_name": {
            "default": null,
            "description": "[REQUIRED for 'create' action] Git branch name. Required for create, optional for update. Can be used instead of git_branch_id for agent assignment",
            "title": "Git Branch Name",
            "type": "string"
          },
          "project_id": {
            "default": null,
            "description": "[REQUIRED for all actions] Project identifier for the git branch operation",
            "title": "Project Id",
            "type": "string"
          },
          "user_id": {
            "default": null,
            "description": "[OPTIONAL] User identifier for authentication and audit trails",
            "title": "User Id",
            "type": "string"
          }
        },
        "required": [
          "action"
        ],
        "type": "object"
      },
      "actions": []
    },
    {
      "name": "manage_seat",
      "description": "Manage seats: list, get, set_occupant (switch the LLM of a seat: runtime claude-code|codex|agy|omp and model id)",
      "parameters": {
        "properties": {
          "action": {
            "description": "list | get | set_occupant",
            "title": "Action",
            "type": "string"
          },
          "model": {
            "default": null,
            "description": "[OPTIONAL for set_occupant] Model id. On UPDATE an empty value is IGNORED - the stored model is kept unchanged and no error is returned, so an empty value cannot be used to reset a model. On CREATE: A blank model is accepted and stored blank: this service substitutes no default and the resolved seat renders no model line. The runtime CLI does substitute one when handed none, measured; which default it picks is not established here.",
            "title": "Model",
            "type": "string"
          },
          "room": {
            "default": null,
            "description": "[OPTIONAL for list, REQUIRED for get and set_occupant] Room slug",
            "title": "Room",
            "type": "string"
          },
          "runtime": {
            "default": null,
            "description": "[REQUIRED for set_occupant] claude-code, codex, agy or omp",
            "title": "Runtime",
            "type": "string"
          },
          "seat": {
            "default": null,
            "description": "[REQUIRED for get and set_occupant] Seat key",
            "title": "Seat",
            "type": "string"
          },
          "user_id": {
            "default": null,
            "description": "[OPTIONAL] ",
            "title": "User Id",
            "type": "string"
          }
        },
        "required": [
          "action"
        ],
        "type": "object"
      },
      "actions": []
    },
    {
      "name": "call_seat",
      "description": "Resolve one exact seat by room and seat key. Returns the seat's runtime, permission policy, resolved snapshot hash and its rendered context files. When the hash is new, the call writes a resolved_seats row for it. 4genthub stores the seat and its context, OpenRig runs the seat, and the brain is the occupant.",
      "parameters": {
        "properties": {
          "room": {
            "description": "[REQUIRED] Room slug, for example 4genthub-dev",
            "title": "Room",
            "type": "string"
          },
          "seat": {
            "description": "[REQUIRED] Seat key, for example lead",
            "title": "Seat",
            "type": "string"
          },
          "user_id": {
            "default": null,
            "description": "[OPTIONAL] ",
            "title": "User Id",
            "type": "string"
          }
        },
        "required": [
          "room",
          "seat"
        ],
        "type": "object"
      },
      "actions": []
    },
    {
      "name": "submit_feedback",
      "description": "Report friction you hit while working: the layer it is in (runtime, openrig, cloud, seat-context, workspace, other), the room and seat you are, and what happened. The owner reads these grouped by layer.",
      "parameters": {
        "properties": {
          "layer": {
            "description": "[REQUIRED] The layer the friction is in. One of: runtime, openrig, cloud, seat-context, workspace, other",
            "enum": [
              "runtime",
              "openrig",
              "cloud",
              "seat-context",
              "workspace",
              "other"
            ],
            "title": "Layer",
            "type": "string"
          },
          "room": {
            "description": "[REQUIRED] Room slug you are in",
            "title": "Room",
            "type": "string"
          },
          "seat": {
            "description": "[REQUIRED] Seat key you are",
            "title": "Seat",
            "type": "string"
          },
          "session": {
            "default": null,
            "description": "[OPTIONAL] Your full session name, e.g. room-seat@room",
            "title": "Session",
            "type": "string"
          },
          "text": {
            "description": "[REQUIRED] What happened, and what you expected instead",
            "maxLength": 2000,
            "title": "Text",
            "type": "string"
          },
          "user_id": {
            "default": null,
            "description": "[OPTIONAL] ",
            "title": "User Id",
            "type": "string"
          }
        },
        "required": [
          "room",
          "seat",
          "layer",
          "text"
        ],
        "type": "object"
      },
      "actions": []
    },
    {
      "name": "manage_connection",
      "description": "Basic health check endpoint for system monitoring",
      "parameters": {
        "properties": {
          "include_details": {
            "default": true,
            "description": "Whether to include detailed information in health response",
            "title": "Include Details",
            "type": "boolean"
          },
          "user_id": {
            "anyOf": [
              {
                "type": "string"
              },
              {
                "type": "null"
              }
            ],
            "default": null,
            "description": "User identifier for authentication and audit trails",
            "title": "User Id"
          }
        },
        "type": "object"
      },
      "actions": []
    }
  ]
};
