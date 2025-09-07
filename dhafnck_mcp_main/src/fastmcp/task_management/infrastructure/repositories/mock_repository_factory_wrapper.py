"""Mock Repository Factory Wrapper - Imports from test fixtures

This is a wrapper that imports mock implementations from the test fixtures.
The actual implementations are maintained in tests/fixtures/mocks/repositories/
for better organization and to clearly indicate they are for testing.
"""

import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Add tests directory to path to import mocks from fixtures
project_root = Path(__file__).resolve().parents[6]
tests_dir = project_root / "tests"
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

try:
    # Import from test fixtures
    from fixtures.mocks.repositories import (
        MockProjectRepository,
        MockGitBranchRepository,
        MockTaskRepository,
        MockSubtaskRepository,
        MockAgentRepository,
        create_mock_repositories
    )
    
    logger.info("Mock repositories imported from test fixtures")
    
except ImportError as e:
    logger.warning(f"Could not import mocks from test fixtures: {e}")
    logger.warning("Falling back to local mock implementations")
    
    # Fall back to the local implementation if test fixtures not available
    from .mock_repository_factory import (
        MockProjectRepository,
        MockGitBranchRepository,
        MockTaskRepository,
        MockSubtaskRepository,
        MockAgentRepository,
        create_mock_repositories
    )

# Export all mock classes
__all__ = [
    'MockProjectRepository',
    'MockGitBranchRepository',
    'MockTaskRepository',
    'MockSubtaskRepository',
    'MockAgentRepository',
    'create_mock_repositories'
]