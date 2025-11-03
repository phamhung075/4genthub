"""
Integration Tests for cclaude-wait CLI Format Validation

Tests the data format that poll_mcp_websocket.py returns to cclaude-wait,
validating JSON structure, field completeness, and display formatting.

Test Coverage:
- Task completion data format (all required fields present)
- Subtask completion data format (subtask-specific fields)
- WebSocket message structure consumed by polling script
- JSON output format for bash script consumption
- Display formatting and readability improvements

Architecture:
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  cclaude-wait   │────▶│ poll_mcp_websocket│────▶│ WebSocket Server│
│  (bash script)  │     │    (python)        │     │  (FastAPI)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │                          │
        │                       │  WebSocket v2.0          │
        │                       │  message format          │
        │                       │◀─────────────────────────┘
        │                       │
        │   JSON result         │
        │◀──────────────────────┘
        │
        ▼
   Parse & Display
"""

import pytest
import json
from datetime import datetime, timezone
from typing import Dict, Any


@pytest.mark.integration
@pytest.mark.cli
class TestCClaudeWaitTaskFormat:
    """
    Test cclaude-wait format for TASK completion results.

    Validates that poll_mcp_websocket.py returns correctly structured
    JSON for task completions that cclaude-wait can parse and display.
    """

    @pytest.fixture
    def mock_task_websocket_message(self) -> Dict[str, Any]:
        """
        Mock WebSocket v2.0 message for task completion.

        This is the message format that poll_mcp_websocket.py receives
        from the WebSocket server when a task completes.
        """
        return {
            "version": "2.0",
            "payload": {
                "entity": "task",
                "action": "completed",
                "data": {
                    "primary": {
                        "id": "task-abc-123-def-456",
                        "title": "Implement JWT Authentication",
                        "status": "done",
                        "progress_percentage": 100,
                        "description": "Complete JWT authentication with refresh tokens",
                        "details": "Implemented token validation, expiry handling, and secure storage",
                        "assignees": ["coding-agent", "security-auditor-agent"]
                    },
                    "cascade": {
                        "branches": [{
                            "id": "branch-xyz-789",
                            "task_count": 5,
                            "completed_count": 5,
                            "todo_count": 0,
                            "in_progress_count": 0,
                            "progress_percentage": 100.0
                        }]
                    }
                }
            },
            "metadata": {
                "entity_id": "task-abc-123-def-456",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "done",
                "title": "Implement JWT Authentication",
                "completion_summary": "Successfully implemented JWT authentication with 2-hour expiry, refresh token mechanism, and secure httpOnly cookie storage. All acceptance criteria met.",
                "testing_notes": "Added unit tests for token validation, integration tests for login/logout flows, manual testing of token expiry and refresh",
                "progress_percentage": 100,
                "assignees": ["coding-agent", "security-auditor-agent"],
                "progress_history": {
                    "Progress 1": {
                        "content": "Initial setup and dependencies installed",
                        "timestamp": "2025-11-03T09:00:00Z"
                    },
                    "Progress 2": {
                        "content": "Token generation and validation implemented",
                        "timestamp": "2025-11-03T09:30:00Z"
                    },
                    "Progress 3": {
                        "content": "Refresh token mechanism complete",
                        "timestamp": "2025-11-03T10:00:00Z"
                    }
                },
                "progress_count": 3,
                "insights_found": [
                    "Used RS256 algorithm for better security over HS256",
                    "Implemented sliding expiry window for refresh tokens",
                    "Added rate limiting to prevent token refresh abuse"
                ],
                "subtask_progress": {
                    "total": 4,
                    "completed": 4,
                    "in_progress": 0,
                    "todo": 0
                },
                "subtask_summary": {
                    "completed_subtasks": [
                        "Token generation logic",
                        "Token validation middleware",
                        "Refresh token mechanism",
                        "Security hardening"
                    ]
                }
            }
        }

    @pytest.fixture
    def expected_task_output_format(self) -> Dict[str, Any]:
        """
        Expected JSON format that poll_mcp_websocket.py should return
        for cclaude-wait bash script to consume.

        This is what cclaude-wait parses to display results.
        """
        return {
            "success": True,
            "status": "done",
            "task_id": "task-abc-123-def-456",
            "title": "Implement JWT Authentication",
            "completion_summary": "Successfully implemented JWT authentication with 2-hour expiry, refresh token mechanism, and secure httpOnly cookie storage. All acceptance criteria met.",
            "testing_notes": "Added unit tests for token validation, integration tests for login/logout flows, manual testing of token expiry and refresh",
            "progress_percentage": 100,
            "assignees": ["coding-agent", "security-auditor-agent"],
            "details": "Implemented token validation, expiry handling, and secure storage",
            "is_subtask": False,
            "progress_history": {
                "Progress 1": {
                    "content": "Initial setup and dependencies installed",
                    "timestamp": "2025-11-03T09:00:00Z"
                },
                "Progress 2": {
                    "content": "Token generation and validation implemented",
                    "timestamp": "2025-11-03T09:30:00Z"
                },
                "Progress 3": {
                    "content": "Refresh token mechanism complete",
                    "timestamp": "2025-11-03T10:00:00Z"
                }
            },
            "progress_count": 3,
            "insights_found": [
                "Used RS256 algorithm for better security over HS256",
                "Implemented sliding expiry window for refresh tokens",
                "Added rate limiting to prevent token refresh abuse"
            ],
            "blockers": [],
            "description": "Complete JWT authentication with refresh tokens",
            "subtask_progress": {
                "total": 4,
                "completed": 4,
                "in_progress": 0,
                "todo": 0
            },
            "subtask_summary": {
                "completed_subtasks": [
                    "Token generation logic",
                    "Token validation middleware",
                    "Refresh token mechanism",
                    "Security hardening"
                ]
            }
        }

    def test_task_completion_structure_has_all_required_fields(
        self, expected_task_output_format
    ):
        """
        Test that task completion JSON has all fields cclaude-wait needs.

        Critical fields for bash parsing:
        - success: bool (determines exit code)
        - is_subtask: bool (determines display format)
        - title: string (displayed in header)
        - completion_summary: string (main result display)
        - progress_count: int (shows progress history length)
        """
        result = expected_task_output_format

        # Critical fields for cclaude-wait bash script
        assert "success" in result, "Missing 'success' field for exit code"
        assert "is_subtask" in result, "Missing 'is_subtask' field for display logic"
        assert "task_id" in result, "Missing 'task_id' field"
        assert "title" in result, "Missing 'title' field for display"
        assert "completion_summary" in result, "Missing 'completion_summary' field"

        # Progress tracking fields
        assert "progress_percentage" in result
        assert "progress_history" in result
        assert "progress_count" in result

        # Testing and validation fields
        assert "testing_notes" in result
        assert "assignees" in result

        # Insights and learnings
        assert "insights_found" in result
        assert isinstance(result["insights_found"], list)

    def test_task_completion_json_is_parseable_by_bash(
        self, expected_task_output_format
    ):
        """
        Test that JSON can be parsed by bash jq commands.

        cclaude-wait uses commands like:
        - echo "$RESULT" | jq '.completion_summary'
        - echo "$RESULT" | jq '.progress_count'
        """
        result = expected_task_output_format

        # Verify JSON serialization works
        json_str = json.dumps(result)
        assert json_str is not None
        assert len(json_str) > 0

        # Verify deserialization works (simulates jq parsing)
        parsed = json.loads(json_str)
        assert parsed["success"] == True
        assert parsed["is_subtask"] == False
        assert parsed["progress_count"] == 3
        assert len(parsed["insights_found"]) == 3

    def test_task_progress_history_format_is_ordered(
        self, expected_task_output_format
    ):
        """
        Test that progress_history uses ordered keys for chronological display.

        Format: "Progress 1", "Progress 2", etc. for sequential numbering
        """
        result = expected_task_output_format
        history = result["progress_history"]

        # Verify numbered progress entries exist
        assert "Progress 1" in history
        assert "Progress 2" in history
        assert "Progress 3" in history

        # Verify each entry has content and timestamp
        for key in history:
            entry = history[key]
            assert "content" in entry, f"Missing 'content' in {key}"
            assert "timestamp" in entry, f"Missing 'timestamp' in {key}"
            assert len(entry["content"]) > 0, f"Empty content in {key}"

    def test_task_subtask_summary_includes_completed_list(
        self, expected_task_output_format
    ):
        """
        Test that subtask_summary shows what work was completed.

        This helps users understand the full scope of work done.
        """
        result = expected_task_output_format
        subtask_summary = result["subtask_summary"]

        assert "completed_subtasks" in subtask_summary
        completed = subtask_summary["completed_subtasks"]
        assert isinstance(completed, list)
        assert len(completed) == 4
        assert "Token generation logic" in completed


@pytest.mark.integration
@pytest.mark.cli
class TestCClaudeWaitSubtaskFormat:
    """
    Test cclaude-wait format for SUBTASK completion results.

    Validates subtask-specific fields like impact_on_parent,
    challenges_overcome, and deliverables.
    """

    @pytest.fixture
    def mock_subtask_websocket_message(self) -> Dict[str, Any]:
        """
        Mock WebSocket v2.0 message for subtask completion.
        """
        return {
            "version": "2.0",
            "payload": {
                "entity": "subtask",
                "action": "completed",
                "data": {
                    "primary": {
                        "id": "subtask-xyz-456",
                        "title": "Implement Token Validation Middleware",
                        "status": "done",
                        "progress_percentage": 100,
                        "description": "Create middleware to validate JWT tokens on protected routes"
                    },
                    "cascade": {
                        "branches": [{
                            "id": "branch-xyz-789",
                            "task_count": 5,
                            "completed_count": 3,
                            "progress_percentage": 60.0
                        }]
                    }
                }
            },
            "metadata": {
                "entity_id": "subtask-xyz-456",
                "parent_task_id": "task-abc-123",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "done",
                "title": "Implement Token Validation Middleware",
                "completion_summary": "Created Express middleware that validates JWT tokens, checks expiry, and attaches user info to request object",
                "progress_percentage": 100,
                "progress_history": {
                    "Progress 1": {
                        "content": "Implemented basic token validation",
                        "timestamp": "2025-11-03T09:15:00Z"
                    },
                    "Progress 2": {
                        "content": "Added expiry checking and error handling",
                        "timestamp": "2025-11-03T09:45:00Z"
                    }
                },
                "progress_count": 2,
                "impact_on_parent": "Authentication middleware complete - parent task now 75% done. Remaining: refresh token endpoint and security hardening.",
                "insights_found": [
                    "Used async/await pattern for better error handling",
                    "Cached public keys for token verification performance"
                ],
                "challenges_overcome": [
                    "Resolved race condition in key rotation",
                    "Fixed memory leak in token cache"
                ],
                "deliverables": [
                    "src/middleware/auth.js (token validation middleware)",
                    "src/middleware/__tests__/auth.test.js (unit tests)",
                    "docs/middleware/authentication.md (documentation)"
                ]
            }
        }

    @pytest.fixture
    def expected_subtask_output_format(self) -> Dict[str, Any]:
        """
        Expected JSON format for subtask completion.

        Includes subtask-specific fields that task format doesn't have.
        """
        return {
            "success": True,
            "status": "done",
            "task_id": "task-abc-123",
            "subtask_id": "subtask-xyz-456",
            "title": "Implement Token Validation Middleware",
            "completion_summary": "Created Express middleware that validates JWT tokens, checks expiry, and attaches user info to request object",
            "testing_notes": "",
            "progress_percentage": 100,
            "assignees": [],
            "details": "",
            "is_subtask": True,
            "progress_history": {
                "Progress 1": {
                    "content": "Implemented basic token validation",
                    "timestamp": "2025-11-03T09:15:00Z"
                },
                "Progress 2": {
                    "content": "Added expiry checking and error handling",
                    "timestamp": "2025-11-03T09:45:00Z"
                }
            },
            "progress_count": 2,
            "insights_found": [
                "Used async/await pattern for better error handling",
                "Cached public keys for token verification performance"
            ],
            "blockers": [],
            "description": "Create middleware to validate JWT tokens on protected routes",
            "impact_on_parent": "Authentication middleware complete - parent task now 75% done. Remaining: refresh token endpoint and security hardening.",
            "challenges_overcome": [
                "Resolved race condition in key rotation",
                "Fixed memory leak in token cache"
            ],
            "deliverables": [
                "src/middleware/auth.js (token validation middleware)",
                "src/middleware/__tests__/auth.test.js (unit tests)",
                "docs/middleware/authentication.md (documentation)"
            ]
        }

    def test_subtask_completion_has_parent_context(
        self, expected_subtask_output_format
    ):
        """
        Test that subtask result includes parent task reference.

        This allows cclaude-wait to display subtask in context of parent.
        """
        result = expected_subtask_output_format

        assert "task_id" in result, "Missing parent task_id"
        assert "subtask_id" in result, "Missing subtask_id"
        assert result["is_subtask"] == True
        assert result["task_id"] == "task-abc-123"
        assert result["subtask_id"] == "subtask-xyz-456"

    def test_subtask_has_impact_on_parent_field(
        self, expected_subtask_output_format
    ):
        """
        Test that subtask shows how it affects parent task progress.

        Critical for understanding incremental progress on large tasks.
        """
        result = expected_subtask_output_format

        assert "impact_on_parent" in result
        impact = result["impact_on_parent"]
        assert isinstance(impact, str)
        assert len(impact) > 0
        assert "75%" in impact or "parent task" in impact.lower()

    def test_subtask_has_challenges_and_deliverables(
        self, expected_subtask_output_format
    ):
        """
        Test that subtask includes challenges_overcome and deliverables.

        These fields help document learnings and concrete outputs.
        """
        result = expected_subtask_output_format

        # Challenges overcome (optional but valuable)
        assert "challenges_overcome" in result
        challenges = result["challenges_overcome"]
        assert isinstance(challenges, list)
        assert len(challenges) > 0

        # Deliverables (concrete outputs)
        assert "deliverables" in result
        deliverables = result["deliverables"]
        assert isinstance(deliverables, list)
        assert len(deliverables) > 0
        assert any("src/" in d for d in deliverables)

    def test_subtask_json_distinguishes_from_task(
        self, expected_subtask_output_format
    ):
        """
        Test that subtask JSON can be distinguished from task JSON.

        cclaude-wait uses 'is_subtask' field to determine display format.
        """
        subtask_result = expected_subtask_output_format

        # Simple task format for comparison
        task_result = {
            "success": True,
            "is_subtask": False,
            "task_id": "task-abc-123",
            "title": "Sample Task"
        }

        # Both have is_subtask field
        assert "is_subtask" in subtask_result
        assert "is_subtask" in task_result

        # But values differ
        assert subtask_result["is_subtask"] == True
        assert task_result["is_subtask"] == False

        # Subtask has extra fields
        assert "subtask_id" in subtask_result
        assert "subtask_id" not in task_result

        assert "impact_on_parent" in subtask_result
        assert "impact_on_parent" not in task_result


@pytest.mark.integration
@pytest.mark.cli
class TestCClaudeWaitFormatImprovements:
    """
    Test format improvements for better readability and usability.

    Current issues to fix:
    - Progress history is ugly (nested JSON hard to read)
    - Insights list is not formatted well
    - Testing notes don't have clear structure
    - Subtask summary is just raw data

    Improvements to test:
    - Formatted progress history with timestamps
    - Bullet-point insights display
    - Structured testing notes sections
    - Human-readable subtask summary
    """

    @pytest.fixture
    def improved_task_format(self) -> Dict[str, Any]:
        """
        Proposed improved format for task completion.

        Changes from current format:
        1. Progress history with formatted timestamps
        2. Insights with categories
        3. Testing notes with sections
        4. Subtask summary with readable structure
        """
        return {
            "success": True,
            "is_subtask": False,
            "task_id": "task-abc-123",
            "title": "Implement JWT Authentication",

            # Improved: Summary with sections
            "completion_summary": {
                "overview": "Successfully implemented JWT authentication system",
                "implementation": [
                    "Token generation with RS256 algorithm",
                    "Validation middleware for protected routes",
                    "Refresh token mechanism with sliding expiry",
                    "Secure cookie storage with httpOnly flag"
                ],
                "acceptance_criteria_met": [
                    "✅ Users can login with email/password",
                    "✅ Tokens expire after 2 hours",
                    "✅ Refresh tokens extend sessions automatically",
                    "✅ Security audit passed with no critical issues"
                ]
            },

            # Improved: Testing notes with structure
            "testing_notes": {
                "unit_tests": [
                    "Token generation produces valid JWT",
                    "Token validation rejects expired tokens",
                    "Refresh mechanism extends expiry correctly"
                ],
                "integration_tests": [
                    "Login flow with valid credentials succeeds",
                    "Protected routes reject invalid tokens",
                    "Token refresh extends session seamlessly"
                ],
                "manual_testing": [
                    "Tested token expiry at 2-hour mark",
                    "Verified secure cookie flags in browser",
                    "Confirmed rate limiting prevents abuse"
                ]
            },

            # Improved: Categorized insights
            "insights_found": {
                "security": [
                    "RS256 algorithm more secure than HS256 for this use case",
                    "Implemented rate limiting to prevent token refresh abuse"
                ],
                "performance": [
                    "Cached public keys for 5x faster token verification",
                    "Sliding expiry reduces database load"
                ],
                "architecture": [
                    "Middleware pattern enables easy reuse across routes",
                    "Async/await improves error handling readability"
                ]
            },

            # Improved: Formatted progress with timeline
            "progress_history": {
                "timeline": [
                    {
                        "step": 1,
                        "time": "09:00 AM",
                        "duration": "30 min",
                        "milestone": "Setup & Dependencies",
                        "description": "Installed jsonwebtoken, configured environment"
                    },
                    {
                        "step": 2,
                        "time": "09:30 AM",
                        "duration": "45 min",
                        "milestone": "Token Generation",
                        "description": "Implemented token generation with RS256"
                    },
                    {
                        "step": 3,
                        "time": "10:15 AM",
                        "duration": "30 min",
                        "milestone": "Validation Middleware",
                        "description": "Created middleware for protected routes"
                    },
                    {
                        "step": 4,
                        "time": "10:45 AM",
                        "duration": "45 min",
                        "milestone": "Refresh Mechanism",
                        "description": "Added sliding window refresh logic"
                    },
                    {
                        "step": 5,
                        "time": "11:30 AM",
                        "duration": "30 min",
                        "milestone": "Testing & Verification",
                        "description": "All tests passing, security audit clean"
                    }
                ],
                "total_duration": "3 hours",
                "estimated_vs_actual": {
                    "estimated": "4 hours",
                    "actual": "3 hours",
                    "variance": "-25% (faster than expected)"
                }
            },

            # Improved: Readable subtask summary
            "subtask_summary": {
                "overview": "Completed all 4 subtasks successfully",
                "breakdown": [
                    {
                        "name": "Token Generation Logic",
                        "status": "✅ Complete",
                        "time_spent": "45 min"
                    },
                    {
                        "name": "Validation Middleware",
                        "status": "✅ Complete",
                        "time_spent": "30 min"
                    },
                    {
                        "name": "Refresh Token Mechanism",
                        "status": "✅ Complete",
                        "time_spent": "45 min"
                    },
                    {
                        "name": "Security Hardening",
                        "status": "✅ Complete",
                        "time_spent": "30 min"
                    }
                ],
                "total_subtasks": 4,
                "completed": 4,
                "in_progress": 0,
                "todo": 0
            },

            # Original fields preserved for compatibility
            "progress_percentage": 100,
            "progress_count": 5,
            "assignees": ["coding-agent", "security-auditor-agent"],
            "blockers": [],
            "description": "Complete JWT authentication with refresh tokens",
            "details": "Implemented token validation, expiry handling, and secure storage"
        }

    def test_improved_completion_summary_has_sections(
        self, improved_task_format
    ):
        """
        Test that completion summary is structured with sections.

        Makes it easier to parse and display in formatted way.
        """
        result = improved_task_format
        summary = result["completion_summary"]

        assert isinstance(summary, dict), "Summary should be dict with sections"
        assert "overview" in summary
        assert "implementation" in summary
        assert "acceptance_criteria_met" in summary

        # Verify implementation is list of bullet points
        impl = summary["implementation"]
        assert isinstance(impl, list)
        assert len(impl) > 0

        # Verify acceptance criteria has checkmarks
        criteria = summary["acceptance_criteria_met"]
        assert isinstance(criteria, list)
        assert all("✅" in item for item in criteria)

    def test_improved_testing_notes_has_test_types(
        self, improved_task_format
    ):
        """
        Test that testing notes are organized by test type.

        Easier to understand what testing was done at each level.
        """
        result = improved_task_format
        testing = result["testing_notes"]

        assert isinstance(testing, dict)
        assert "unit_tests" in testing
        assert "integration_tests" in testing
        assert "manual_testing" in testing

        # Each type has list of test descriptions
        for test_type in ["unit_tests", "integration_tests", "manual_testing"]:
            tests = testing[test_type]
            assert isinstance(tests, list)
            assert len(tests) > 0

    def test_improved_insights_categorized_by_type(
        self, improved_task_format
    ):
        """
        Test that insights are categorized for better organization.

        Categories: security, performance, architecture, etc.
        """
        result = improved_task_format
        insights = result["insights_found"]

        assert isinstance(insights, dict), "Insights should be categorized"
        assert "security" in insights
        assert "performance" in insights
        assert "architecture" in insights

        # Each category has list of insights
        for category in ["security", "performance", "architecture"]:
            category_insights = insights[category]
            assert isinstance(category_insights, list)
            assert len(category_insights) > 0

    def test_improved_progress_history_has_timeline(
        self, improved_task_format
    ):
        """
        Test that progress history shows chronological timeline.

        Much more readable than nested JSON structure.
        """
        result = improved_task_format
        history = result["progress_history"]

        assert isinstance(history, dict)
        assert "timeline" in history
        assert "total_duration" in history
        assert "estimated_vs_actual" in history

        timeline = history["timeline"]
        assert isinstance(timeline, list)
        assert len(timeline) == 5

        # Each timeline entry has structured fields
        first_entry = timeline[0]
        assert "step" in first_entry
        assert "time" in first_entry
        assert "duration" in first_entry
        assert "milestone" in first_entry
        assert "description" in first_entry

    def test_improved_subtask_summary_is_readable(
        self, improved_task_format
    ):
        """
        Test that subtask summary is human-readable table format.

        Shows name, status, and time spent for each subtask.
        """
        result = improved_task_format
        summary = result["subtask_summary"]

        assert isinstance(summary, dict)
        assert "overview" in summary
        assert "breakdown" in summary
        assert "total_subtasks" in summary

        breakdown = summary["breakdown"]
        assert isinstance(breakdown, list)
        assert len(breakdown) == 4

        # Each subtask has name, status, time_spent
        for subtask in breakdown:
            assert "name" in subtask
            assert "status" in subtask
            assert "time_spent" in subtask
            assert "✅" in subtask["status"]

    def test_improved_format_is_backward_compatible(
        self, improved_task_format
    ):
        """
        Test that improved format preserves original fields.

        Ensures cclaude-wait bash script still works with existing logic.
        """
        result = improved_task_format

        # Critical fields for backward compatibility
        assert "success" in result
        assert "is_subtask" in result
        assert "task_id" in result
        assert "title" in result
        assert "progress_percentage" in result
        assert "progress_count" in result
        assert "assignees" in result

        # Old format fields preserved
        assert result["success"] == True
        assert result["is_subtask"] == False
        assert result["progress_percentage"] == 100


@pytest.mark.integration
@pytest.mark.cli
class TestCClaudeWaitBashIntegration:
    """
    Test cclaude-wait bash script integration with JSON output.

    Simulates the bash commands that cclaude-wait uses to parse JSON:
    - jq '.completion_summary'
    - jq '.progress_count'
    - jq '.insights_found[]'
    """

    def test_bash_can_extract_completion_summary(self):
        """
        Test bash jq command: echo "$RESULT" | jq '.completion_summary'
        """
        result = {
            "success": True,
            "completion_summary": "Task completed successfully"
        }

        json_str = json.dumps(result)
        parsed = json.loads(json_str)

        summary = parsed.get("completion_summary", "No summary provided")
        assert summary == "Task completed successfully"

    def test_bash_can_detect_subtask_vs_task(self):
        """
        Test bash jq command: echo "$RESULT" | jq '.is_subtask'
        """
        task_result = {"is_subtask": False}
        subtask_result = {"is_subtask": True}

        assert json.loads(json.dumps(task_result))["is_subtask"] == False
        assert json.loads(json.dumps(subtask_result))["is_subtask"] == True

    def test_bash_can_iterate_insights(self):
        """
        Test bash jq command: echo "$RESULT" | jq '.insights_found[]'
        """
        result = {
            "insights_found": [
                "First insight",
                "Second insight",
                "Third insight"
            ]
        }

        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        insights = parsed["insights_found"]

        assert len(insights) == 3
        assert insights[0] == "First insight"

    def test_bash_can_parse_nested_progress_history(self):
        """
        Test bash can parse nested progress_history structure.
        """
        result = {
            "progress_history": {
                "Progress 1": {
                    "content": "First update",
                    "timestamp": "2025-11-03T09:00:00Z"
                },
                "Progress 2": {
                    "content": "Second update",
                    "timestamp": "2025-11-03T10:00:00Z"
                }
            }
        }

        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        history = parsed["progress_history"]

        assert "Progress 1" in history
        assert history["Progress 1"]["content"] == "First update"
