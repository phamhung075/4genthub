"""
Runtime Response Validation Middleware

This middleware intercepts ALL HTTP responses and validates them against expected schemas.
It logs discrepancies to help identify missing or incorrect properties that contract tests miss.

Purpose:
- Validate actual runtime responses against DTO schemas
- Log missing, null, or incorrectly typed fields
- Capture real-world data issues that unit tests don't catch
- Provide detailed validation reports for debugging

Environment Variables:
- VALIDATE_RESPONSES: Enable/disable validation (default: True in dev)
- VALIDATION_LOG_LEVEL: error|warning|info|debug (default: warning)
- VALIDATION_SAMPLE_RATE: Percentage of requests to validate (default: 100)
"""

import json
import logging
import os
import random
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

logger = logging.getLogger(__name__)

# Configuration from environment
VALIDATE_RESPONSES = os.getenv("VALIDATE_RESPONSES", "true").lower() in ("true", "1", "yes")
VALIDATION_LOG_LEVEL = os.getenv("VALIDATION_LOG_LEVEL", "warning").lower()
VALIDATION_SAMPLE_RATE = int(os.getenv("VALIDATION_SAMPLE_RATE", "100"))


class ValidationIssue:
    """Represents a validation issue found in a response"""

    def __init__(
        self,
        severity: str,
        field_path: str,
        issue_type: str,
        expected: Any,
        actual: Any,
        message: str
    ):
        self.severity = severity  # error, warning, info
        self.field_path = field_path
        self.issue_type = issue_type  # missing, null, wrong_type, wrong_value
        self.expected = expected
        self.actual = actual
        self.message = message
        self.timestamp = datetime.now(timezone.utc).isoformat()


class ResponseValidator:
    """Validates response payloads against expected schemas"""

    # Expected schema for task responses
    TASK_SCHEMA = {
        "id": {"type": str, "required": True},
        "title": {"type": str, "required": True},
        "status": {"type": str, "required": True},
        "priority": {"type": str, "required": True},
        "assignees": {"type": list, "required": True, "default": []},
        "labels": {"type": list, "required": True, "default": []},
        "subtask_count": {"type": int, "required": True, "default": 0},
        "completed_subtasks": {"type": int, "required": True, "default": 0},
        "progress_percentage": {"type": int, "required": True, "default": 0},
        "progress_count": {"type": int, "required": True, "default": 0},
        "created_at": {"type": str, "required": True},
        "updated_at": {"type": str, "required": True},
        "git_branch_id": {"type": str, "required": False},
        "project_id": {"type": str, "required": False},
        "description": {"type": str, "required": False},
        "details": {"type": str, "required": False},
        "context_data": {"type": dict, "required": False},
        "has_dependencies": {"type": bool, "required": False},
        "has_context": {"type": bool, "required": False},
    }

    # Expected schema for subtask responses
    SUBTASK_SCHEMA = {
        "id": {"type": str, "required": True},
        "title": {"type": str, "required": True},
        "status": {"type": str, "required": True},
        "priority": {"type": str, "required": True},
        "assignees": {"type": list, "required": True, "default": []},
        "progress_percentage": {"type": int, "required": True, "default": 0},
        "created_at": {"type": str, "required": True},
        "updated_at": {"type": str, "required": True},
        "parent_task_id": {"type": str, "required": True},
    }

    # WebSocket message schema
    WEBSOCKET_MESSAGE_SCHEMA = {
        "event": {"type": str, "required": True},
        "data": {"type": dict, "required": True},
        "timestamp": {"type": str, "required": False},
    }

    @staticmethod
    def validate_field(
        field_path: str,
        value: Any,
        schema_def: Dict[str, Any],
        issues: List[ValidationIssue]
    ) -> None:
        """Validate a single field against its schema definition"""

        expected_type = schema_def.get("type")
        is_required = schema_def.get("required", False)
        default_value = schema_def.get("default")

        # Check if field is missing
        if value is None:
            if is_required and default_value is None:
                issues.append(ValidationIssue(
                    severity="error",
                    field_path=field_path,
                    issue_type="missing",
                    expected=expected_type.__name__ if expected_type else "any",
                    actual=None,
                    message=f"Required field '{field_path}' is missing or null"
                ))
            elif is_required and default_value is not None:
                issues.append(ValidationIssue(
                    severity="warning",
                    field_path=field_path,
                    issue_type="null",
                    expected=default_value,
                    actual=None,
                    message=f"Field '{field_path}' is null but should default to {default_value}"
                ))
            return

        # Check type
        if expected_type and not isinstance(value, expected_type):
            issues.append(ValidationIssue(
                severity="error",
                field_path=field_path,
                issue_type="wrong_type",
                expected=expected_type.__name__,
                actual=type(value).__name__,
                message=f"Field '{field_path}' has wrong type: expected {expected_type.__name__}, got {type(value).__name__}"
            ))

    @classmethod
    def validate_object(
        cls,
        obj: Dict[str, Any],
        schema: Dict[str, Dict[str, Any]],
        parent_path: str = ""
    ) -> List[ValidationIssue]:
        """Validate an object against a schema"""
        issues = []

        # Check all schema fields
        for field_name, field_schema in schema.items():
            field_path = f"{parent_path}.{field_name}" if parent_path else field_name
            value = obj.get(field_name)
            cls.validate_field(field_path, value, field_schema, issues)

        # Check for unexpected fields (might indicate schema drift)
        schema_fields = set(schema.keys())
        object_fields = set(obj.keys())
        unexpected_fields = object_fields - schema_fields

        if unexpected_fields:
            for unexpected_field in unexpected_fields:
                issues.append(ValidationIssue(
                    severity="info",
                    field_path=f"{parent_path}.{unexpected_field}" if parent_path else unexpected_field,
                    issue_type="unexpected",
                    expected="not in schema",
                    actual=type(obj[unexpected_field]).__name__,
                    message=f"Unexpected field '{unexpected_field}' not in schema (possible schema drift)"
                ))

        return issues

    @classmethod
    def validate_task_response(cls, task_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate a task response"""
        return cls.validate_object(task_data, cls.TASK_SCHEMA, "task")

    @classmethod
    def validate_subtask_response(cls, subtask_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate a subtask response"""
        return cls.validate_object(subtask_data, cls.SUBTASK_SCHEMA, "subtask")

    @classmethod
    def validate_list_response(
        cls,
        items: List[Dict[str, Any]],
        item_schema: Dict[str, Dict[str, Any]],
        item_type: str = "item"
    ) -> List[ValidationIssue]:
        """Validate a list of items"""
        all_issues = []

        for idx, item in enumerate(items):
            issues = cls.validate_object(item, item_schema, f"{item_type}[{idx}]")
            all_issues.extend(issues)

        return all_issues


class ResponseValidatorMiddleware(BaseHTTPMiddleware):
    """Middleware that validates all HTTP responses"""

    def __init__(self, app):
        super().__init__(app)
        self.validation_stats = {
            "total_requests": 0,
            "validated_requests": 0,
            "issues_found": 0,
            "errors": 0,
            "warnings": 0,
        }
        logger.info(f"ResponseValidatorMiddleware initialized (enabled={VALIDATE_RESPONSES}, sample_rate={VALIDATION_SAMPLE_RATE}%)")

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and validate response"""

        self.validation_stats["total_requests"] += 1

        # Skip validation if disabled or not sampled
        if not VALIDATE_RESPONSES or random.randint(1, 100) > VALIDATION_SAMPLE_RATE:
            return await call_next(request)

        # Skip validation for non-API endpoints
        if not self._should_validate_path(request.url.path):
            return await call_next(request)

        # Process request
        response = await call_next(request)

        # Only validate JSON responses
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        # Validate response
        try:
            await self._validate_response(request, response)
            self.validation_stats["validated_requests"] += 1
        except Exception as e:
            logger.error(f"Error during response validation: {e}", exc_info=True)

        return response

    def _should_validate_path(self, path: str) -> bool:
        """Check if this path should be validated"""
        # Validate MCP tool responses and API endpoints
        validate_prefixes = [
            "/mcp/",
            "/api/tasks",
            "/api/subtasks",
            "/api/projects",
            "/api/branches",
            "/api/context",
        ]
        return any(path.startswith(prefix) for prefix in validate_prefixes)

    async def _validate_response(self, request: Request, response: Response) -> None:
        """Validate response body against expected schema"""

        # Read response body
        if isinstance(response, StreamingResponse):
            # Can't validate streaming responses
            return

        try:
            # Get response body
            body = response.body
            if not body:
                return

            # Parse JSON
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse response JSON for {request.url.path}")
                return

            # Determine what to validate based on endpoint
            path = request.url.path
            issues = []

            if "/tasks" in path or "/mcp/" in path:
                issues = self._validate_task_endpoint(data, path)
            elif "/subtasks" in path:
                issues = self._validate_subtask_endpoint(data, path)

            # Log issues
            if issues:
                self._log_validation_issues(request, issues)
                self.validation_stats["issues_found"] += len(issues)

                # Count by severity
                for issue in issues:
                    if issue.severity == "error":
                        self.validation_stats["errors"] += 1
                    elif issue.severity == "warning":
                        self.validation_stats["warnings"] += 1

        except Exception as e:
            logger.error(f"Error validating response: {e}", exc_info=True)

    def _validate_task_endpoint(self, data: Dict[str, Any], path: str) -> List[ValidationIssue]:
        """Validate task-related endpoint responses"""
        issues = []

        # Check if it's a list response
        if isinstance(data, dict):
            # Single task or wrapped response
            if "task" in data:
                issues.extend(ResponseValidator.validate_task_response(data["task"]))
            elif "tasks" in data and isinstance(data["tasks"], list):
                issues.extend(ResponseValidator.validate_list_response(
                    data["tasks"],
                    ResponseValidator.TASK_SCHEMA,
                    "task"
                ))
            elif "data" in data and isinstance(data["data"], dict):
                if "task" in data["data"]:
                    issues.extend(ResponseValidator.validate_task_response(data["data"]["task"]))
                elif "tasks" in data["data"]:
                    issues.extend(ResponseValidator.validate_list_response(
                        data["data"]["tasks"],
                        ResponseValidator.TASK_SCHEMA,
                        "task"
                    ))

        return issues

    def _validate_subtask_endpoint(self, data: Dict[str, Any], path: str) -> List[ValidationIssue]:
        """Validate subtask-related endpoint responses"""
        issues = []

        if isinstance(data, dict):
            if "subtask" in data:
                issues.extend(ResponseValidator.validate_subtask_response(data["subtask"]))
            elif "subtasks" in data and isinstance(data["subtasks"], list):
                issues.extend(ResponseValidator.validate_list_response(
                    data["subtasks"],
                    ResponseValidator.SUBTASK_SCHEMA,
                    "subtask"
                ))

        return issues

    def _log_validation_issues(self, request: Request, issues: List[ValidationIssue]) -> None:
        """Log validation issues with appropriate severity"""

        error_issues = [i for i in issues if i.severity == "error"]
        warning_issues = [i for i in issues if i.severity == "warning"]
        info_issues = [i for i in issues if i.severity == "info"]

        if error_issues:
            logger.error(
                f"🚨 VALIDATION ERRORS in {request.method} {request.url.path}\n" +
                "\n".join([f"  - {issue.message}" for issue in error_issues])
            )

        if warning_issues and VALIDATION_LOG_LEVEL in ("warning", "info", "debug"):
            logger.warning(
                f"⚠️  VALIDATION WARNINGS in {request.method} {request.url.path}\n" +
                "\n".join([f"  - {issue.message}" for issue in warning_issues])
            )

        if info_issues and VALIDATION_LOG_LEVEL in ("info", "debug"):
            logger.info(
                f"ℹ️  VALIDATION INFO in {request.method} {request.url.path}\n" +
                "\n".join([f"  - {issue.message}" for issue in info_issues])
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            **self.validation_stats,
            "validation_rate": (
                f"{(self.validation_stats['validated_requests'] / max(self.validation_stats['total_requests'], 1)) * 100:.1f}%"
            )
        }
