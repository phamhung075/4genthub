"""Tests for scripts/openrig_watch_tools.py: how a session log line becomes a feed line."""

import importlib.util
import json
from pathlib import Path

import pytest

# Self-contained; must not spin up the test database.
pytestmark = pytest.mark.unit

MODULE_PATH = Path(__file__).resolve().parents[4] / "scripts" / "openrig_watch_tools.py"


def load_module():
    spec = importlib.util.spec_from_file_location("openrig_watch_tools", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


watch = load_module()


def line(role: str, content, **extra) -> str:
    return json.dumps({"message": {"role": role, "content": content, **extra}})


def test_a_tool_call_shows_its_name_and_the_main_argument():
    call = [
        {
            "type": "toolCall",
            "name": "bash",
            "arguments": {"command": "git status", "cwd": "/x"},
        }
    ]
    (text,) = watch.events(line("assistant", call), 200)
    assert "bash" in text and "command=git status" in text and "+cwd" in text


def test_only_a_real_policy_refusal_is_marked_blocked():
    refusal = 'Tool "bash" is blocked by tool policy. Reason: Blocked by bash pattern: git push*'
    quoted = "POLICY=BLOCKED (Blocked by bash pattern: git push*)"
    (blocked,) = watch.events(
        line("toolResult", [{"type": "text", "text": refusal}]), 200
    )
    (plain,) = watch.events(line("toolResult", [{"type": "text", "text": quoted}]), 200)
    assert "BLOCKED" in blocked
    assert "BLOCKED" not in plain.split("POLICY=")[0]


def test_lines_that_are_not_tool_events_or_not_json_produce_nothing():
    assert list(watch.events("not json", 200)) == []
    assert (
        list(watch.events(line("assistant", [{"type": "text", "text": "hi"}]), 200))
        == []
    )


def test_mcp_tools_get_their_own_colour():
    call = [
        {
            "type": "toolCall",
            "name": "mcp__deepseek_agent",
            "arguments": {"prompt": "x"},
        }
    ]
    (text,) = watch.events(line("assistant", call), 200)
    assert watch.fg(watch.MCP_COLOR) in text


def test_detail_adds_reasoning_what_the_agent_says_and_what_it_is_told_and_nothing_else_does():
    thinking = line(
        "assistant", [{"type": "thinking", "thinking": "weigh the two options"}]
    )
    said = line("assistant", [{"type": "text", "text": "I will run the tests now"}])
    told = line("user", [{"type": "text", "text": "please review packet 5"}])
    for entry, marker in ((thinking, "think"), (said, "say"), (told, "in")):
        assert list(watch.events(entry, 200)) == []
        (text,) = watch.events(entry, 200, detail=True)
        assert marker in text


def test_a_single_character_reply_is_not_shown_as_something_said():
    dot = line("assistant", [{"type": "text", "text": "."}])
    assert list(watch.events(dot, 200, detail=True)) == []
