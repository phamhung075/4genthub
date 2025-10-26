"""
Unit tests for GitBranchNameValidator domain service
"""

import pytest
from unittest.mock import Mock, AsyncMock

from fastmcp.task_management.domain.services.git_branch_name_validator import GitBranchNameValidator
from fastmcp.task_management.domain.exceptions.base_exceptions import ValidationException


class MockBranch:
    """Mock git branch entity for testing"""
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name


@pytest.fixture
def mock_git_branch_repository():
    """Create a mock git branch repository"""
    repository = Mock()
    repository.find_all_by_project = AsyncMock(return_value=[])
    return repository


@pytest.fixture
def validator(mock_git_branch_repository):
    """Create a git branch name validator instance"""
    return GitBranchNameValidator(mock_git_branch_repository)


class TestGitBranchNameValidator:
    """Test suite for GitBranchNameValidator"""

    # validate_name_format tests

    @pytest.mark.asyncio
    async def test_validate_name_format_empty_name(self, validator):
        """Test that empty names are rejected"""
        with pytest.raises(ValidationException, match="Branch name cannot be empty"):
            await validator.validate_name_format("")

        with pytest.raises(ValidationException, match="Branch name cannot be empty"):
            await validator.validate_name_format("   ")

        with pytest.raises(ValidationException, match="Branch name cannot be empty"):
            await validator.validate_name_format(None)

    @pytest.mark.asyncio
    async def test_validate_name_format_too_long(self, validator):
        """Test that names exceeding 100 characters are rejected"""
        long_name = "a" * 101
        with pytest.raises(ValidationException, match="Branch name cannot exceed 100 characters"):
            await validator.validate_name_format(long_name)

    @pytest.mark.asyncio
    async def test_validate_name_format_forbidden_chars(self, validator):
        """Test that forbidden characters are rejected"""
        forbidden_tests = [
            ("name with spaces", "spaces"),
            ("name~tilde", "~"),
            ("name^caret", "^"),
            ("name:colon", ":"),
            ("name\\backslash", "\\\\"),
            ("name*asterisk", "*"),
            ("name?question", "?"),
            ("name[bracket", "["),
            ("name.dot", "."),
            ("name@{brace", "@{"),
        ]

        for test_name, expected_char in forbidden_tests:
            if expected_char == "spaces":
                with pytest.raises(ValidationException, match="cannot contain spaces"):
                    await validator.validate_name_format(test_name)
            elif expected_char:
                with pytest.raises(ValidationException, match=f"cannot contain the character"):
                    await validator.validate_name_format(test_name)

    @pytest.mark.asyncio
    async def test_validate_name_format_invalid_start(self, validator):
        """Test that names starting with invalid characters are rejected"""
        # Test slash and hyphen which are checked for start position
        with pytest.raises(ValidationException, match="cannot start with"):
            await validator.validate_name_format("/branch")
        
        with pytest.raises(ValidationException, match="cannot start with"):
            await validator.validate_name_format("-branch")
        
        # Dot is handled by forbidden chars, not start position
        with pytest.raises(ValidationException, match="cannot contain the character"):
            await validator.validate_name_format(".branch")

    @pytest.mark.asyncio
    async def test_validate_name_format_invalid_end(self, validator):
        """Test that names ending with invalid characters are rejected"""
        # Test slash which is checked for end position
        with pytest.raises(ValidationException, match="cannot end with"):
            await validator.validate_name_format("branch/")
        
        # Dot is handled by forbidden chars, not end position
        with pytest.raises(ValidationException, match="cannot contain the character"):
            await validator.validate_name_format("branch.")

    @pytest.mark.asyncio
    async def test_validate_name_format_consecutive_dots(self, validator):
        """Test that names with consecutive dots are rejected"""
        # Note: Since '.' is in forbidden chars, this will be caught before consecutive dots check
        with pytest.raises(ValidationException, match="cannot contain the character"):
            await validator.validate_name_format("branch..name")

    @pytest.mark.asyncio
    async def test_validate_unique_name_empty_after_trim(self, validator):
        """Test line 57 - empty name after trim in validate_unique_name"""
        # This tests a defensive check after trim - though line 47 catches it first
        with pytest.raises(ValidationException, match="Branch name cannot be empty|must be at least 1 character"):
            await validator.validate_unique_name("", "project123")

    @pytest.mark.asyncio
    async def test_validate_unique_name_too_long(self, validator):
        """Test line 60 - name exceeds 100 chars in validate_unique_name"""
        long_name = "a" * 101
        with pytest.raises(ValidationException, match="cannot exceed 100 characters"):
            await validator.validate_unique_name(long_name, "project123")

    @pytest.mark.asyncio
    async def test_validate_name_format_empty_after_trim(self, validator):
        """Test line 98 - empty name after trim in validate_name_format"""
        # Test that whitespace-only string is caught after trim
        with pytest.raises(ValidationException, match="Branch name cannot be empty|must be at least 1 character"):
            await validator.validate_name_format(" ")

    @pytest.mark.asyncio
    async def test_validate_name_format_slash_boundaries(self, validator):
        """Test line 126 - name starts or ends with slash"""
        # Test starting with slash
        with pytest.raises(ValidationException, match="cannot start"):
            await validator.validate_name_format("/branch")

        # Test ending with slash
        with pytest.raises(ValidationException, match="cannot end"):
            await validator.validate_name_format("branch/")

    @pytest.mark.asyncio
    async def test_validate_name_format_valid_names(self, validator):
        """Test that valid branch names are accepted"""
        valid_names = [
            "main",
            "develop",
            "feature/user-auth",
            "hotfix-123",
            "release_v1_0_0",  # Changed dots to underscores
            "bug_fix_456",
            "FEATURE-789",
            "feature/add-login-functionality",
            "a",  # minimum length
            "a" * 100,  # maximum length
        ]

        for name in valid_names:
            # Should not raise any exception
            await validator.validate_name_format(name)

    # validate_unique_name tests

    @pytest.mark.asyncio
    async def test_validate_unique_name_empty_inputs(self, validator):
        """Test that empty inputs are rejected"""
        with pytest.raises(ValidationException, match="Branch name cannot be empty"):
            await validator.validate_unique_name("", "project-123")

        with pytest.raises(ValidationException, match="Project ID is required"):
            await validator.validate_unique_name("branch-name", "")

    @pytest.mark.asyncio
    async def test_validate_unique_name_no_duplicates(self, validator, mock_git_branch_repository):
        """Test that unique names are accepted"""
        mock_git_branch_repository.find_all_by_project.return_value = []
        
        # Should not raise any exception
        await validator.validate_unique_name("new-branch", "project-123")

    @pytest.mark.asyncio
    async def test_validate_unique_name_with_existing_branches(self, validator, mock_git_branch_repository):
        """Test that unique names are accepted when other branches exist"""
        existing_branches = [
            MockBranch("branch-1", "main"),
            MockBranch("branch-2", "develop"),
            MockBranch("branch-3", "feature/auth"),
        ]
        mock_git_branch_repository.find_all_by_project.return_value = existing_branches
        
        # Should not raise any exception
        await validator.validate_unique_name("feature/new-feature", "project-123")

    @pytest.mark.asyncio
    async def test_validate_unique_name_duplicate_found(self, validator, mock_git_branch_repository):
        """Test that duplicate names are rejected"""
        existing_branches = [
            MockBranch("branch-1", "main"),
            MockBranch("branch-2", "develop"),
        ]
        mock_git_branch_repository.find_all_by_project.return_value = existing_branches
        
        with pytest.raises(ValidationException, match="already exists in this project"):
            await validator.validate_unique_name("main", "project-123")

    @pytest.mark.asyncio
    async def test_validate_unique_name_exclude_self(self, validator, mock_git_branch_repository):
        """Test that a branch can keep its own name during update"""
        existing_branches = [
            MockBranch("branch-1", "main"),
            MockBranch("branch-2", "develop"),
        ]
        mock_git_branch_repository.find_all_by_project.return_value = existing_branches
        
        # Should not raise exception when excluding the same branch
        await validator.validate_unique_name("main", "project-123", exclude_branch_id="branch-1")

    @pytest.mark.asyncio
    async def test_validate_unique_name_duplicate_with_different_exclude(self, validator, mock_git_branch_repository):
        """Test that duplicate names are still rejected when excluding a different branch"""
        existing_branches = [
            MockBranch("branch-1", "main"),
            MockBranch("branch-2", "develop"),
        ]
        mock_git_branch_repository.find_all_by_project.return_value = existing_branches
        
        with pytest.raises(ValidationException, match="already exists in this project"):
            await validator.validate_unique_name("main", "project-123", exclude_branch_id="branch-2")

    @pytest.mark.asyncio
    async def test_validate_unique_name_trimmed(self, validator, mock_git_branch_repository):
        """Test that names are trimmed before validation"""
        existing_branches = [MockBranch("branch-1", "main")]
        mock_git_branch_repository.find_all_by_project.return_value = existing_branches
        
        # Should match after trimming
        with pytest.raises(ValidationException, match="already exists in this project"):
            await validator.validate_unique_name("  main  ", "project-123")

    # validate_branch_name tests (comprehensive validation)

    @pytest.mark.asyncio
    async def test_validate_branch_name_valid(self, validator, mock_git_branch_repository):
        """Test comprehensive validation for valid branch names"""
        mock_git_branch_repository.find_all_by_project.return_value = []
        
        valid_names = [
            "main",
            "feature/user-authentication",
            "hotfix-critical-bug",
            "release/v2_0_0",  # Changed dots to underscores
        ]

        for name in valid_names:
            # Should not raise any exception
            await validator.validate_branch_name(name, "project-123")

    @pytest.mark.asyncio
    async def test_validate_branch_name_invalid_format(self, validator, mock_git_branch_repository):
        """Test that format validation runs first"""
        mock_git_branch_repository.find_all_by_project.return_value = []
        
        # Format error should be raised before uniqueness check
        with pytest.raises(ValidationException, match="cannot contain spaces"):
            await validator.validate_branch_name("invalid name", "project-123")

    @pytest.mark.asyncio
    async def test_validate_branch_name_duplicate(self, validator, mock_git_branch_repository):
        """Test that uniqueness validation runs after format validation"""
        existing_branches = [MockBranch("branch-1", "main")]
        mock_git_branch_repository.find_all_by_project.return_value = existing_branches
        
        # Should pass format but fail uniqueness
        with pytest.raises(ValidationException, match="already exists in this project"):
            await validator.validate_branch_name("main", "project-123")

    @pytest.mark.asyncio
    async def test_validate_branch_name_with_exclude(self, validator, mock_git_branch_repository):
        """Test comprehensive validation with exclusion for updates"""
        existing_branches = [
            MockBranch("branch-1", "main"),
            MockBranch("branch-2", "develop"),
        ]
        mock_git_branch_repository.find_all_by_project.return_value = existing_branches
        
        # Should allow keeping the same name during update
        await validator.validate_branch_name("main", "project-123", exclude_branch_id="branch-1")
        
        # Should not allow taking another branch's name
        with pytest.raises(ValidationException, match="already exists in this project"):
            await validator.validate_branch_name("develop", "project-123", exclude_branch_id="branch-1")

    @pytest.mark.asyncio
    async def test_repository_call_parameters(self, validator, mock_git_branch_repository):
        """Test that repository is called with correct parameters"""
        mock_git_branch_repository.find_all_by_project.return_value = []
        
        await validator.validate_unique_name("new-branch", "project-123")
        
        # Verify repository was called correctly
        mock_git_branch_repository.find_all_by_project.assert_called_once_with("project-123")