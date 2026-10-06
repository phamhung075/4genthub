"""Tests for scripts/openrig_seat_policy.py.

They render and apply to a temporary state root; no seat, daemon or omp process is needed.
"""

import importlib.util
from pathlib import Path

import pytest
import yaml

# These tests are self-contained and must not spin up the test database.
pytestmark = pytest.mark.unit

MODULE_PATH = Path(__file__).resolve().parents[4] / "scripts" / "openrig_seat_policy.py"
RIG = "4genthub-min"


def load_module():
    spec = importlib.util.spec_from_file_location("openrig_seat_policy", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy = load_module()


def parsed(seat: str) -> dict:
    return yaml.safe_load(policy.render_config(seat, policy.SEAT_ROLES[RIG][seat]))


def deny_patterns(config: dict) -> list[str]:
    assert all(rule["approval"] == "deny" for rule in config["bash"]["patterns"])
    return [rule["match"] for rule in config["bash"]["patterns"]]


def tools_denied(config: dict) -> list[str]:
    return sorted(config.get("tools", {}).get("approval", {}))


def test_every_seat_waits_for_mcp_and_checks_compound_commands():
    for seat in policy.SEAT_ROLES[RIG]:
        config = parsed(seat)
        assert config["mcp"]["startupTimeoutMs"] == 0
        assert config["bash"]["allowCompoundCommands"] is True


def test_every_seat_including_the_lead_is_denied_push_amend_and_production_access():
    for seat in policy.SEAT_ROLES[RIG]:
        patterns = deny_patterns(parsed(seat))
        for rule in (
            "git push*",
            "git commit*--amend*",
            "git add -A*",
            "git reset --hard*",
            "ssh *",
            "tmux kill-*",
        ):
            assert rule in patterns, f"{seat} is not denied {rule}"


def test_only_the_lead_keeps_rig_launch_and_the_agent_seat_connection_tools():
    lead = parsed("lead")
    assert "rig launch*" not in deny_patterns(lead)
    assert tools_denied(lead) == []
    for seat in policy.SEAT_ROLES[RIG]:
        if seat == "lead":
            continue
        config = parsed(seat)
        assert "rig launch*" in deny_patterns(config)
        assert {
            "mcp__agenthub_http_manage_agent",
            "mcp__agenthub_http_manage_connection",
            "mcp__agenthub_http_manage_seat",
        } <= set(tools_denied(config))


def test_the_context_sync_tools_are_never_denied():
    for seat in policy.SEAT_ROLES[RIG]:
        denied = tools_denied(parsed(seat))
        for tool in (
            "manage_task",
            "manage_subtask",
            "manage_context",
            "manage_project",
            "manage_git_branch",
            "call_seat",
        ):
            assert f"mcp__agenthub_http_{tool}" not in denied
        assert not any("deepseek" in name for name in denied)


def test_only_the_reviewer_loses_the_edit_tools():
    for seat in policy.SEAT_ROLES[RIG]:
        denied = tools_denied(parsed(seat))
        assert (("edit" in denied) and ("ast_edit" in denied)) == (seat == "reviewer")


def test_an_unlisted_rig_or_seat_has_no_permissive_default(tmp_path):
    with pytest.raises(SystemExit):
        policy.seat_roles("unknown-rig")
    assert policy.main(["show", "nobody", "--rig", RIG]) == policy.EXIT_USAGE


def seed_state(root: Path) -> None:
    for seat in policy.SEAT_ROLES[RIG]:
        policy.config_path(root, RIG, seat).parent.mkdir(parents=True)


def test_apply_writes_every_seat_is_idempotent_and_check_reports_drift(tmp_path):
    seed_state(tmp_path)
    args = ["--rig", RIG, "--state-root", str(tmp_path)]
    assert policy.main(["apply", *args, "--check"]) == policy.EXIT_DRIFT
    assert not policy.config_path(tmp_path, RIG, "lead").exists()

    assert policy.main(["apply", *args]) == policy.EXIT_OK
    for seat, role in policy.SEAT_ROLES[RIG].items():
        assert policy.config_path(
            tmp_path, RIG, seat
        ).read_text() == policy.render_config(seat, role)

    assert policy.main(["apply", *args, "--check"]) == policy.EXIT_OK
    policy.config_path(tmp_path, RIG, "writer").write_text("tools: {}\n")
    assert policy.main(["apply", *args, "--check"]) == policy.EXIT_DRIFT


def test_apply_refuses_a_seat_that_was_never_launched(tmp_path):
    assert (
        policy.main(["apply", "--rig", RIG, "--state-root", str(tmp_path)])
        == policy.EXIT_USAGE
    )


def test_check_tolerates_keys_the_policy_does_not_define_and_still_catches_a_broken_rule(
    tmp_path,
):
    """The pipeline MERGES this document into the runtime's file, so `--check` compares the policy's
    own keys rather than the whole file - and still reports a rule that is actually wrong."""
    seed_state(tmp_path)
    args = ["--rig", RIG, "--state-root", str(tmp_path)]
    assert policy.main(["apply", *args]) == policy.EXIT_OK
    path = policy.config_path(tmp_path, RIG, "go-dev")

    path.write_text(path.read_text() + "\nmodel: something-else\n")
    assert policy.main(["apply", *args, "--check"]) == policy.EXIT_OK

    path.write_text(path.read_text().replace('"git push*"', '"git pull*"'))
    assert policy.main(["apply", *args, "--check"]) == policy.EXIT_DRIFT
