#!/usr/bin/env python3
"""
Categorize unused pytest fixtures by risk level
"""

from pathlib import Path

# Fixture analysis from previous scan
unused_fixtures = {
    "tests/conftest.py": [
        ("cleanup_env_vars_example", 1775, "Example fixture - safe to remove"),
        ("cleanup_integration_test_example", 1783, "Example fixture - safe to remove"),
        ("postgresql_test_db", 1603, "Manual check - might be used in specific tests"),
        ("postgresql_session_db", 1635, "Manual check - might be used in specific tests"),
        ("module_test_db", 1723, "Manual check - might be used in specific tests"),
    ],

    "tests/utils/example_polluting_patterns.py": [
        ("cleanup_custom_singleton", 124, "Example file - all fixtures safe to remove"),
        ("cleanup_for_parameterized", 246, "Example file - all fixtures safe to remove"),
        ("auto_cleanup_all_tests", 275, "Example file - all fixtures safe to remove"),
        ("old_cleanup", 341, "Example file - all fixtures safe to remove"),
        ("new_cleanup", 370, "Example file - all fixtures safe to remove"),
    ],

    "tests/utils/test_patterns.py": [
        ("database_test_pattern", 356, "Pattern documentation - safe to remove if not used"),
        ("mcp_tool_test_pattern", 362, "Pattern documentation - safe to remove if not used"),
        ("integration_test_pattern", 370, "Pattern documentation - safe to remove if not used"),
        ("performance_test_pattern", 378, "Pattern documentation - safe to remove if not used"),
    ],

    "tests/fixtures/tool_fixtures.py": [
        ("sample_project_entity", 56, "Factory fixture - keep for test development"),
        ("sample_subtask_entity", 121, "Factory fixture - keep for test development"),
        ("sample_agent_data", 134, "Factory fixture - keep for test development"),
        ("sample_template_data", 155, "Factory fixture - keep for test development"),
        ("sample_connection_data", 174, "Factory fixture - keep for test development"),
        ("sample_auth_token_data", 197, "Factory fixture - keep for test development"),
        ("sample_health_check_data", 211, "Factory fixture - keep for test development"),
        ("sample_render_result", 229, "Factory fixture - keep for test development"),
        ("sample_agent_call_result", 247, "Factory fixture - keep for test development"),
        ("mock_task_facade", 270, "Mock fixture - keep for test development"),
        ("mock_project_facade", 287, "Mock fixture - keep for test development"),
        ("mock_subtask_facade", 301, "Mock fixture - keep for test development"),
        ("mock_agent_facade", 313, "Mock fixture - keep for test development"),
        ("mock_call_agent_facade", 324, "Mock fixture - keep for test development"),
        ("mock_template_facade", 333, "Mock fixture - keep for test development"),
        ("task_status_values", 362, "Constants fixture - keep for test development"),
        ("task_priority_values", 368, "Constants fixture - keep for test development"),
        ("project_status_values", 374, "Constants fixture - keep for test development"),
        ("template_types", 380, "Constants fixture - keep for test development"),
        ("cache_operations", 392, "Constants fixture - keep for test development"),
        ("common_test_params", 399, "Constants fixture - keep for test development"),
    ],
}

def categorize_fixtures():
    """Categorize unused fixtures by safety level"""

    categories = {
        "HIGH_CONFIDENCE_REMOVABLE": [],  # Example files, clearly unused
        "MODERATE_CONFIDENCE_REMOVABLE": [],  # Potentially unused, needs verification
        "LOW_CONFIDENCE_REMOVABLE": [],  # Might be infrastructure, keep
        "KEEP": []  # Definitely keep - factory/infrastructure fixtures
    }

    # Safe to remove: Example files
    example_files = [
        "tests/utils/example_polluting_patterns.py",
        "tests/utils/test_patterns.py"
    ]

    # Keep: Factory and infrastructure fixtures
    infrastructure_files = [
        "tests/fixtures/tool_fixtures.py",
        "tests/fixtures/mcp_auto_injection_fixtures.py",
        "tests/fixtures/postgresql_isolation.py"
    ]

    # Moderate: Need verification
    verification_needed = [
        "tests/fastmcp/server/server_test.py",
        "tests/fastmcp/server/server_import_mount_test.py",
        "tests/integration/test_database_migrations.py",
        "tests/security/websocket/"
    ]

    print("="*70)
    print("UNUSED FIXTURE CATEGORIZATION")
    print("="*70)
    print()

    print("🔴 HIGH CONFIDENCE REMOVABLE (Example/Demo Files):")
    print("─"*70)
    print("\nFiles that are clearly examples or documentation:")
    print("  • tests/utils/example_polluting_patterns.py (5 fixtures)")
    print("  • tests/utils/test_patterns.py (4 fixtures)")
    print("  • tests/conftest.py (cleanup_env_vars_example, cleanup_integration_test_example)")
    print()
    print("  Total: ~11 fixtures")
    print()

    print("🟡 MODERATE CONFIDENCE REMOVABLE (Needs Verification):")
    print("─"*70)
    print("\nFixtures in active test files that appear unused:")
    print("  • tests/fastmcp/server/server_test.py (5 fixtures: mock managers, basic_server)")
    print("  • tests/fastmcp/server/server_import_mount_test.py (2 fixtures: parent/child servers)")
    print("  • tests/integration/test_database_migrations.py (temp_postgresql_db)")
    print("  • tests/integration/test_database_init.py (temp_sqlite_db_empty)")
    print("  • tests/security/websocket/ (9 fixtures: security testing infrastructure)")
    print("  • Various conftest.py files (postgresql fixtures)")
    print()
    print("  Total: ~25 fixtures")
    print()

    print("🟢 KEEP (Infrastructure & Factory Fixtures):")
    print("─"*70)
    print("\nFixtures that are infrastructure or factory patterns:")
    print("  • tests/fixtures/tool_fixtures.py (22 fixtures: sample data factories)")
    print("  • tests/fixtures/mcp_auto_injection_fixtures.py (4 fixtures: injection helpers)")
    print("  • tests/fixtures/postgresql_isolation.py (1 fixture: DB isolation)")
    print("  • tests/unit/mcp_controllers/conftest.py (10 fixtures: controller helpers)")
    print()
    print("  Total: ~37 fixtures")
    print()

    print("📊 SUMMARY:")
    print("─"*70)
    print(f"  Total unused fixtures: 85")
    print(f"  High confidence removable: ~11 (13%)")
    print(f"  Moderate confidence (verify): ~25 (29%)")
    print(f"  Infrastructure (keep): ~37 (44%)")
    print(f"  Other (case-by-case): ~12 (14%)")
    print()

    print("💡 RECOMMENDATION:")
    print("─"*70)
    print("  1. Remove example files completely (safe)")
    print("  2. Keep all tool_fixtures.py (infrastructure)")
    print("  3. Manual verification needed for server_test.py fixtures")
    print("  4. Most 'unused' fixtures are actually test development infrastructure")
    print()
    print("="*70)

if __name__ == '__main__':
    categorize_fixtures()
