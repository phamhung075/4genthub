"""
Unit tests for Agent Doc Generator Infrastructure Service
Generated from agent_doc_generator.py analysis
Date: 2025-09-26

Tests the agent documentation generator that converts YAML agent definitions to MDC format.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from fastmcp.task_management.infrastructure.services.agent_doc_generator import (
    AgentDocGenerator,
    _find_project_root,
    clear_agents_output_dir,
    convert_yaml_to_mdc,
    generate_agent_docs,
    generate_docs_for_assignees,
)


class TestFindProjectRoot:
    """Test suite for _find_project_root function"""

    def test_find_project_root_exists_in_parent(self):
        """Test finding project root when agenthub_main exists in parent"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create project structure
            project_root = Path(temp_dir) / "project"
            agenthub_dir = project_root / "agenthub_main"
            agenthub_dir.mkdir(parents=True)

            # Create a file deep in the structure
            deep_file = agenthub_dir / "src" / "services" / "test.py"
            deep_file.parent.mkdir(parents=True)
            deep_file.touch()

            # Mock __file__ to point to the deep file
            with patch(
                "fastmcp.task_management.infrastructure.services.agent_doc_generator.__file__",
                str(deep_file),
            ):
                # Also patch cwd check to return a different directory
                with patch("pathlib.Path.cwd", return_value=Path("/other/dir")):
                    result = _find_project_root()

                    # Should find project root
                    assert result == project_root

    def test_find_project_root_in_cwd(self):
        """Test finding project root in current working directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            agenthub_dir = project_root / "agenthub_main"
            agenthub_dir.mkdir()

            with patch("pathlib.Path.cwd", return_value=project_root):
                with patch(
                    "fastmcp.task_management.infrastructure.services.agent_doc_generator.__file__",
                    "/some/other/path.py",
                ):
                    result = _find_project_root()
                    assert result == project_root

    def test_find_project_root_is_agenthub_main(self):
        """Test when the current directory is agenthub_main itself"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agenthub_main = Path(temp_dir) / "agenthub_main"
            agenthub_main.mkdir()

            file_path = agenthub_main / "services" / "test.py"
            file_path.parent.mkdir()

            with patch(
                "fastmcp.task_management.infrastructure.services.agent_doc_generator.__file__",
                str(file_path),
            ):
                result = _find_project_root()
                assert result == Path(temp_dir)  # Parent of agenthub_main

    def test_find_project_root_fallback_to_env_var(self):
        """Test fallback to environment variable"""

        def custom_exists(path):
            # Return True only for the custom data path, False for paths with agenthub_main
            path_str = str(path)
            if path_str == "/custom/data":
                return True
            return "agenthub_main" not in path_str and path_str != "/custom/data"

        with patch.dict(os.environ, {"AGENTHUB_DATA_PATH": "/custom/data"}):
            with patch("os.path.exists", side_effect=custom_exists):
                with patch("pathlib.Path.cwd", return_value=Path("/no/agenthub")):
                    with patch(
                        "fastmcp.task_management.infrastructure.services.agent_doc_generator.__file__",
                        "/random/path.py",
                    ):
                        result = _find_project_root()
                        assert result == Path("/custom/data")


class TestAgentDocGenerator:
    """Test suite for AgentDocGenerator class"""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            # Create directories
            agent_lib = project_root / "agenthub_main" / "agent-library"
            agent_lib.mkdir(parents=True)

            agents_output = project_root / ".cursor" / "rules" / "agents"
            agents_output.mkdir(parents=True)

            yield project_root

    @pytest.fixture
    def mock_project_root(self, temp_project_dir):
        """Mock _find_project_root to return temp directory"""
        with patch(
            "fastmcp.task_management.infrastructure.services.agent_doc_generator._find_project_root",
            return_value=temp_project_dir,
        ):
            yield temp_project_dir

    def test_init_default_paths(self, mock_project_root):
        """Test initialization with default paths"""
        generator = AgentDocGenerator()

        assert generator.project_root == mock_project_root
        assert (
            generator.agent_yaml_lib
            == mock_project_root / "agenthub_main" / "agent-library"
        )
        assert (
            generator.agents_output_dir
            == mock_project_root / ".cursor" / "rules" / "agents"
        )

    def test_init_custom_paths(self, mock_project_root):
        """Test initialization with custom paths"""
        custom_yaml = Path("/custom/yaml")
        custom_output = Path("/custom/output")

        generator = AgentDocGenerator(
            agent_yaml_lib=custom_yaml, agents_output_dir=custom_output
        )

        assert generator.agent_yaml_lib == custom_yaml
        assert generator.agents_output_dir == custom_output

    def test_init_relative_paths(self, mock_project_root):
        """Test initialization with relative paths resolved to project root"""
        generator = AgentDocGenerator(
            agent_yaml_lib="relative/yaml", agents_output_dir="relative/output"
        )

        assert generator.agent_yaml_lib == mock_project_root / "relative" / "yaml"
        assert generator.agents_output_dir == mock_project_root / "relative" / "output"

    def test_init_env_variables(self, mock_project_root):
        """Test initialization from environment variables"""
        with patch.dict(
            os.environ,
            {"AGENT_LIBRARY_DIR_PATH": "env/yaml", "AGENTS_OUTPUT_DIR": "env/output"},
        ):
            generator = AgentDocGenerator()

            assert generator.agent_yaml_lib == mock_project_root / "env" / "yaml"
            assert generator.agents_output_dir == mock_project_root / "env" / "output"

    def test_clear_agents_output_dir(self, mock_project_root):
        """Test clearing output directory"""
        generator = AgentDocGenerator()

        # Create some files in output dir
        output_dir = generator.agents_output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        file1 = output_dir / "agent1.mdc"
        file2 = output_dir / "agent2.mdc"
        subdir = output_dir / "subdir"

        file1.touch()
        file2.touch()
        subdir.mkdir()

        # Clear directory
        generator.clear_agents_output_dir()

        # Files should be gone, but directory remains
        assert output_dir.exists()
        assert not file1.exists()
        assert not file2.exists()
        assert subdir.exists()  # Subdirectories not removed

    def test_clear_agents_output_dir_nonexistent(self, mock_project_root):
        """Test clearing non-existent directory"""
        generator = AgentDocGenerator()
        generator.agents_output_dir = Path("/nonexistent/dir")

        # Should not raise error
        generator.clear_agents_output_dir()

    def test_convert_yaml_to_mdc_success(self):
        """Test successful YAML to MDC conversion"""
        generator = AgentDocGenerator()

        yaml_content = {
            "name": "Test Agent",
            "role": "Testing",
            "capabilities": ["test1", "test2"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(yaml_content, f)
            temp_file = Path(f.name)

        try:
            result = generator.convert_yaml_to_mdc(temp_file)

            # Result should be YAML dump of content
            parsed_result = yaml.safe_load(result)
            assert parsed_result == yaml_content
        finally:
            temp_file.unlink()

    def test_convert_yaml_to_mdc_error(self):
        """Test YAML conversion with error"""
        generator = AgentDocGenerator()

        # Non-existent file
        result = generator.convert_yaml_to_mdc(Path("/nonexistent/file.yaml"))

        assert result.startswith("(Error converting")
        assert "file.yaml" in result

    def test_generate_single_agent_doc(self, mock_project_root):
        """Test generating documentation for a single agent"""
        generator = AgentDocGenerator()

        # Create agent directory structure
        agent_dir = generator.agent_yaml_lib / "test_agent"
        agent_dir.mkdir(parents=True)

        job_desc = {
            "name": "Test Agent",
            "slug": "test-agent",
            "role_definition": "A test agent for testing",
            "when_to_use": "When you need to test",
            "groups": ["testing", "qa"],
        }

        job_desc_file = agent_dir / "job_desc.yaml"
        with open(job_desc_file, "w") as f:
            yaml.dump(job_desc, f)

        # Create subdirectories with content
        contexts_dir = agent_dir / "contexts"
        contexts_dir.mkdir()
        context_file = contexts_dir / "context1.yaml"
        with open(context_file, "w") as f:
            yaml.dump({"context": "test"}, f)

        # Generate doc
        generator._generate_single_agent_doc(agent_dir)

        # Check output file
        output_file = generator.agents_output_dir / "test_agent.mdc"
        assert output_file.exists()

        content = output_file.read_text()
        assert "# Test Agent" in content
        assert "**Slug:** `test-agent`" in content
        assert "**Role Definition:** A test agent for testing" in content
        assert "**When to Use:** When you need to test" in content
        assert "**Groups:** testing, qa" in content
        assert "## Contexts" in content
        assert "### context1" in content

    def test_generate_single_agent_doc_no_job_desc(self, mock_project_root):
        """Test generating doc when job_desc.yaml is missing"""
        generator = AgentDocGenerator()

        agent_dir = generator.agent_yaml_lib / "test_agent"
        agent_dir.mkdir(parents=True)

        # No job_desc.yaml file
        generator._generate_single_agent_doc(agent_dir)

        # Should not create output file
        output_file = generator.agents_output_dir / "test_agent.mdc"
        assert not output_file.exists()

    def test_generate_agent_docs_single(self, mock_project_root):
        """Test generating docs for a single agent"""
        generator = AgentDocGenerator()

        # Create test agent
        agent_dir = generator.agent_yaml_lib / "test_agent"
        agent_dir.mkdir(parents=True)
        job_desc_file = agent_dir / "job_desc.yaml"
        with open(job_desc_file, "w") as f:
            yaml.dump({"name": "Test Agent"}, f)

        # Generate docs
        generator.generate_agent_docs(agent_name="test_agent")

        # Check output
        output_file = generator.agents_output_dir / "test_agent.mdc"
        assert output_file.exists()

    def test_generate_agent_docs_all(self, mock_project_root):
        """Test generating docs for all agents"""
        generator = AgentDocGenerator()

        # Create multiple agents
        for i in range(3):
            agent_dir = generator.agent_yaml_lib / f"test{i}_agent"
            agent_dir.mkdir(parents=True)
            job_desc_file = agent_dir / "job_desc.yaml"
            with open(job_desc_file, "w") as f:
                yaml.dump({"name": f"Test Agent {i}"}, f)

        # Create non-agent directory (should be ignored)
        other_dir = generator.agent_yaml_lib / "not_an_agent"
        other_dir.mkdir()

        # Generate all docs
        generator.generate_agent_docs()

        # Check outputs
        for i in range(3):
            output_file = generator.agents_output_dir / f"test{i}_agent.mdc"
            assert output_file.exists()

        # Non-agent should not have output
        non_agent_file = generator.agents_output_dir / "not_an_agent.mdc"
        assert not non_agent_file.exists()

    def test_generate_agent_docs_clear_all(self, mock_project_root):
        """Test generating docs with clear_all option"""
        generator = AgentDocGenerator()

        # Create existing file
        generator.agents_output_dir.mkdir(parents=True, exist_ok=True)
        existing_file = generator.agents_output_dir / "old_agent.mdc"
        existing_file.touch()

        # Create new agent
        agent_dir = generator.agent_yaml_lib / "new_agent"
        agent_dir.mkdir(parents=True)
        job_desc_file = agent_dir / "job_desc.yaml"
        with open(job_desc_file, "w") as f:
            yaml.dump({"name": "New Agent"}, f)

        # Generate with clear_all
        generator.generate_agent_docs(agent_name="new_agent", clear_all=True)

        # Old file should be gone
        assert not existing_file.exists()

        # New file should exist
        new_file = generator.agents_output_dir / "new_agent.mdc"
        assert new_file.exists()

    def test_generate_agent_docs_nonexistent(self, mock_project_root):
        """Test generating docs for non-existent agent"""
        generator = AgentDocGenerator()

        with patch("builtins.print") as mock_print:
            generator.generate_agent_docs(agent_name="nonexistent_agent")
            mock_print.assert_called_with(
                "Agent directory 'nonexistent_agent' not found."
            )

    def test_generate_docs_for_assignees(self, mock_project_root):
        """Test generating docs for list of assignees"""
        generator = AgentDocGenerator()

        # Create agents
        for name in ["coding_agent", "testing_agent"]:
            agent_dir = generator.agent_yaml_lib / name
            agent_dir.mkdir(parents=True)
            job_desc_file = agent_dir / "job_desc.yaml"
            with open(job_desc_file, "w") as f:
                yaml.dump({"name": name}, f)

        # Test various assignee formats
        assignees = [
            "@coding",  # With @, without _agent
            "testing_agent",  # Without @, with _agent
            "@coding",  # Duplicate (should be skipped)
            "nonexistent",  # Non-existent agent
        ]

        generator.generate_docs_for_assignees(assignees)

        # Check outputs
        assert (generator.agents_output_dir / "coding_agent.mdc").exists()
        assert (generator.agents_output_dir / "testing_agent.mdc").exists()

    def test_generate_docs_for_assignees_empty(self, mock_project_root):
        """Test generating docs with empty assignees list"""
        generator = AgentDocGenerator()

        # Should not raise error
        generator.generate_docs_for_assignees([])
        generator.generate_docs_for_assignees(None)


class TestModuleFunctions:
    """Test suite for module-level functions"""

    @patch(
        "fastmcp.task_management.infrastructure.services.agent_doc_generator.AgentDocGenerator"
    )
    def test_clear_agents_output_dir_function(self, mock_generator_class):
        """Test module-level clear_agents_output_dir function"""
        mock_instance = Mock()
        mock_generator_class.return_value = mock_instance

        clear_agents_output_dir()

        mock_instance.clear_agents_output_dir.assert_called_once()

    @patch(
        "fastmcp.task_management.infrastructure.services.agent_doc_generator.AgentDocGenerator"
    )
    def test_convert_yaml_to_mdc_function(self, mock_generator_class):
        """Test module-level convert_yaml_to_mdc function"""
        mock_instance = Mock()
        mock_instance.convert_yaml_to_mdc.return_value = "converted"
        mock_generator_class.return_value = mock_instance

        yaml_file = Path("test.yaml")
        result = convert_yaml_to_mdc(yaml_file)

        assert result == "converted"
        mock_instance.convert_yaml_to_mdc.assert_called_once_with(yaml_file)

    @patch(
        "fastmcp.task_management.infrastructure.services.agent_doc_generator.AgentDocGenerator"
    )
    @patch(
        "fastmcp.task_management.infrastructure.services.agent_doc_generator.AGENT_YAML_LIB",
        Path("/mock/yaml"),
    )
    @patch(
        "fastmcp.task_management.infrastructure.services.agent_doc_generator.AGENTS_OUTPUT_DIR",
        Path("/mock/output"),
    )
    def test_generate_agent_docs_function(self, mock_generator_class):
        """Test module-level generate_agent_docs function"""
        mock_instance = Mock()
        mock_generator_class.return_value = mock_instance

        generate_agent_docs(agent_name="test", clear_all=True)

        mock_generator_class.assert_called_once_with(
            agent_yaml_lib=Path("/mock/yaml"), agents_output_dir=Path("/mock/output")
        )
        mock_instance.generate_agent_docs.assert_called_once_with("test", True)

    @patch(
        "fastmcp.task_management.infrastructure.services.agent_doc_generator.AgentDocGenerator"
    )
    @patch("logging.getLogger")
    def test_generate_docs_for_assignees_error_handling(
        self, mock_logger, mock_generator_class
    ):
        """Test error handling in generate_docs_for_assignees function"""
        # Make generator raise exception
        mock_generator_class.side_effect = Exception("Test error")

        mock_log_instance = Mock()
        mock_logger.return_value = mock_log_instance

        # Should not raise, but log warning
        generate_docs_for_assignees(["test_agent"])

        mock_log_instance.warning.assert_called_once()
        warning_msg = mock_log_instance.warning.call_args[0][0]
        assert "Could not generate agent ai_docs" in warning_msg
        assert "test_agent" in warning_msg
