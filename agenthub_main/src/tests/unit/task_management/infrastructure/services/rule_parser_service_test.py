"""
Unit tests for Rule Parser Infrastructure Service
Generated from rule_parser_service.py analysis
Date: 2025-09-26

Tests the rule parsing service that handles various file formats and extracts structured content.
"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import os

from fastmcp.task_management.infrastructure.services.rule_parser_service import (
    RuleParserService,
    IRuleParserService
)
from fastmcp.task_management.domain.entities.rule_entity import RuleContent, RuleMetadata
from fastmcp.task_management.domain.enums.rule_enums import RuleFormat, RuleType


class TestRuleParserService:
    """Test suite for RuleParserService infrastructure service"""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance for testing"""
        return RuleParserService()
    
    def test_interface_implementation(self):
        """Test that RuleParserService implements IRuleParserService"""
        assert isinstance(RuleParserService(), IRuleParserService)
    
    def test_format_parsers_initialization(self, parser):
        """Test that format parsers are properly initialized"""
        expected_formats = [
            RuleFormat.MDC,
            RuleFormat.MD,
            RuleFormat.JSON,
            RuleFormat.YAML,
            RuleFormat.TXT
        ]
        
        for format_type in expected_formats:
            assert format_type in parser.format_parsers
            assert callable(parser.format_parsers[format_type])
    
    # detect_format tests
    def test_detect_format_by_extension(self, parser):
        """Test format detection based on file extension"""
        test_cases = [
            ("rule.mdc", RuleFormat.MDC),
            ("rule.md", RuleFormat.MD),
            ("rule.markdown", RuleFormat.MD),
            ("rule.json", RuleFormat.JSON),
            ("rule.yaml", RuleFormat.YAML),
            ("rule.yml", RuleFormat.YAML),
            ("rule.txt", RuleFormat.TXT),
            ("rule.unknown", RuleFormat.TXT),  # Default to TXT
            ("rule", RuleFormat.TXT),  # No extension
        ]
        
        for filename, expected_format in test_cases:
            path = Path(filename)
            assert parser.detect_format(path) == expected_format
    
    def test_detect_format_case_insensitive(self, parser):
        """Test format detection is case insensitive"""
        test_cases = [
            ("rule.MDC", RuleFormat.MDC),
            ("rule.MD", RuleFormat.MD),
            ("rule.JSON", RuleFormat.JSON),
            ("rule.YAML", RuleFormat.YAML),
        ]
        
        for filename, expected_format in test_cases:
            path = Path(filename)
            assert parser.detect_format(path) == expected_format
    
    # parse_rule_file tests
    def test_parse_rule_file_not_found(self, parser):
        """Test parsing non-existent file raises FileNotFoundError"""
        non_existent_path = Path("/non/existent/file.md")
        
        with pytest.raises(FileNotFoundError, match="Rule file not found"):
            parser.parse_rule_file(non_existent_path)
    
    @patch("builtins.open", side_effect=IOError("Permission denied"))
    @patch("pathlib.Path.exists", return_value=True)
    def test_parse_rule_file_read_error(self, mock_exists, mock_open, parser):
        """Test parsing file with read error raises ValueError"""
        path = Path("rule.md")
        
        with pytest.raises(ValueError, match="Failed to read rule file"):
            parser.parse_rule_file(path)
    
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.stat")
    def test_parse_rule_file_markdown_with_frontmatter(self, mock_stat, mock_exists, parser):
        """Test parsing markdown file with YAML frontmatter"""
        content = """---
description: Test rule description
tags:
  - test
  - rule
  - markdown
variables:
  version: 1.0
  author: test_user
---

# Section One

This is content for section one.

# Section Two

Content with [[reference1]] and [[reference2]].
Using variable {{version}}.
"""
        mock_stat.return_value = Mock(st_size=len(content), st_mtime=1234567890)
        
        with patch("builtins.open", mock_open(read_data=content)):
            result = parser.parse_rule_file(Path("rule.md"))
        
        assert isinstance(result, RuleContent)
        assert result.metadata.format == RuleFormat.MD
        assert result.metadata.description == "Test rule description"
        # Tags from YAML frontmatter (no hashtags in this content)
        assert set(result.metadata.tags) == {"test", "rule", "markdown"}
        assert len(result.sections) == 2
        assert "Section One" in result.sections
        assert "Section Two" in result.sections
        assert result.references == ["reference1", "reference2"]
        assert "version" in result.variables
    
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.stat")
    def test_parse_rule_file_json(self, mock_stat, mock_exists, parser):
        """Test parsing JSON rule file"""
        content = json.dumps({
            "name": "test_rule",
            "sections": {
                "config": {"key": "value"},
                "data": {"items": [1, 2, 3]}
            },
            "variables": {
                "env": "test"
            }
        })
        
        mock_stat.return_value = Mock(st_size=len(content), st_mtime=1234567890)
        
        with patch("builtins.open", mock_open(read_data=content)):
            result = parser.parse_rule_file(Path("rule.json"))
        
        assert isinstance(result, RuleContent)
        assert result.metadata.format == RuleFormat.JSON
        assert "config" in result.sections
        assert "data" in result.sections
        assert result.variables.get("env") == "test"
    
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.stat")
    def test_parse_rule_file_yaml(self, mock_stat, mock_exists, parser):
        """Test parsing YAML rule file"""
        content = yaml.dump({
            "name": "test_rule",
            "sections": {
                "config": {"timeout": 30},
                "rules": ["rule1", "rule2"]
            },
            "variables": {
                "mode": "production"
            }
        })
        
        mock_stat.return_value = Mock(st_size=len(content), st_mtime=1234567890)
        
        with patch("builtins.open", mock_open(read_data=content)):
            result = parser.parse_rule_file(Path("rule.yaml"))
        
        assert isinstance(result, RuleContent)
        assert result.metadata.format == RuleFormat.YAML
        assert "config" in result.sections
        assert result.variables.get("mode") == "production"
    
    # _extract_dependencies tests
    def test_extract_dependencies_imports(self, parser):
        """Test extracting dependencies from import statements"""
        content = """
@import "base_rules.mdc"
@include "common/utils.md"
import 'helpers.js'
require "config.yaml"
"""
        dependencies = parser._extract_dependencies(content)
        
        assert "base_rules.mdc" in dependencies
        assert "common/utils.md" in dependencies
        assert "helpers.js" in dependencies
        assert "config.yaml" in dependencies
        assert len(dependencies) == 4
    
    def test_extract_dependencies_file_references(self, parser):
        """Test extracting dependencies from file references"""
        content = """
file: "data/config.json"
path: 'templates/main.html'
"""
        dependencies = parser._extract_dependencies(content)
        
        assert "data/config.json" in dependencies
        assert "templates/main.html" in dependencies
        assert len(dependencies) == 2
    
    def test_extract_dependencies_removes_duplicates(self, parser):
        """Test that duplicate dependencies are removed"""
        content = """
@import "common.md"
@import "common.md"
@include "common.md"
"""
        dependencies = parser._extract_dependencies(content)
        
        assert dependencies.count("common.md") == 1
        assert len(dependencies) == 1
    
    # _classify_rule_type tests
    def test_classify_rule_type_by_path(self, parser):
        """Test rule type classification based on file path"""
        test_cases = [
            ("core/system.md", RuleType.CORE),
            ("system_config.yaml", RuleType.CORE),
            ("workflow/process.json", RuleType.WORKFLOW),
            ("agent/bot.md", RuleType.AGENT),
            ("project/setup.yaml", RuleType.PROJECT),
            ("context/env.json", RuleType.CONTEXT),
            ("custom/rule.txt", RuleType.CUSTOM),
        ]
        
        for path_str, expected_type in test_cases:
            path = Path(path_str)
            result = parser._classify_rule_type(path, "")
            assert result == expected_type
    
    def test_classify_rule_type_by_content(self, parser):
        """Test rule type classification based on content"""
        test_cases = [
            ("This is a core system rule", RuleType.CORE),
            ("Essential configuration", RuleType.CORE),
            ("Workflow pipeline definition", RuleType.WORKFLOW),
            ("Agent behavior configuration", RuleType.AGENT),
            ("Project repository settings", RuleType.PROJECT),
            ("Context environment setup", RuleType.CONTEXT),
            ("Some random content", RuleType.CUSTOM),
        ]
        
        for content, expected_type in test_cases:
            path = Path("unknown/path.txt")
            result = parser._classify_rule_type(path, content)
            assert result == expected_type
    
    def test_classify_rule_type_path_priority(self, parser):
        """Test that path classification takes priority over content"""
        path = Path("core/rule.md")
        content = "This is about workflow processes"
        
        result = parser._classify_rule_type(path, content)
        assert result == RuleType.CORE  # Path takes priority
    
    # _extract_description tests
    def test_extract_description_from_frontmatter(self, parser):
        """Test extracting description from YAML frontmatter"""
        content = """---
description: This is the rule description
other: value
---
Content here"""
        
        description = parser._extract_description(content)
        assert description == "This is the rule description"
    
    def test_extract_description_from_first_paragraph(self, parser):
        """Test extracting description from first paragraph"""
        content = """# Title

This is a long paragraph that serves as a description of the rule.

More content here.
"""
        description = parser._extract_description(content)
        assert "This is a long paragraph" in description
    
    def test_extract_description_truncates_long_text(self, parser):
        """Test that long descriptions are truncated"""
        long_text = "A" * 300
        content = f"# Title\n\n{long_text}"
        
        description = parser._extract_description(content)
        assert len(description) == 203  # 200 + "..."
        assert description.endswith("...")
    
    def test_extract_description_skips_comments(self, parser):
        """Test that comments are skipped when extracting description"""
        content = """# Comment line
// Another comment

This is the actual description.
"""
        description = parser._extract_description(content)
        assert description == "This is the actual description."
    
    # _extract_tags tests
    def test_extract_tags_from_frontmatter(self, parser):
        """Test extracting tags from YAML frontmatter"""
        content = """---
tags: ["rule", "test", "example"]
---
Content"""
        
        tags = parser._extract_tags(content)
        assert "rule" in tags
        assert "test" in tags
        assert "example" in tags
        assert len(tags) == 3
    
    def test_extract_tags_from_hashtags(self, parser):
        """Test extracting tags from hashtags in content"""
        content = """
This is a #test rule with #multiple #tags.
Another line with #test again.
"""
        
        tags = parser._extract_tags(content)
        assert "test" in tags
        assert "multiple" in tags
        assert "tags" in tags
        assert len(tags) == 3  # Duplicates removed
    
    # _parse_markdown tests
    def test_parse_markdown_sections(self, parser):
        """Test parsing markdown sections"""
        content = """# Section One

Content for section one.

## Subsection 1.1

Subsection content.

# Section Two

Content for section two."""
        
        parsed, sections, refs, vars = parser._parse_markdown(content)
        
        assert len(sections) == 3
        assert "Section One" in sections
        assert "Subsection 1.1" in sections
        assert "Section Two" in sections
        assert sections["Section One"] == "Content for section one."
    
    def test_parse_markdown_references(self, parser):
        """Test parsing markdown references"""
        content = """
See [[Reference One]] and [[Reference Two]].
Also check [[Reference One]] again.
"""
        
        parsed, sections, refs, vars = parser._parse_markdown(content)
        
        assert "Reference One" in refs
        assert "Reference Two" in refs
        assert refs.count("Reference One") == 2  # Duplicates kept in list
    
    def test_parse_markdown_variables(self, parser):
        """Test parsing markdown variables"""
        content = """
Version: {{version}}
Author: {{author}}
Using {{version}} again.
"""
        
        parsed, sections, refs, vars = parser._parse_markdown(content)
        
        assert "version" in vars
        assert "author" in vars
        assert vars["version"] is None  # Placeholder value
    
    def test_parse_markdown_empty_content(self, parser):
        """Test parsing empty markdown content"""
        content = ""
        
        parsed, sections, refs, vars = parser._parse_markdown(content)
        
        assert sections == {"content": ""}
        assert refs == []
        assert vars == {}
    
    # _parse_json tests
    def test_parse_json_valid(self, parser):
        """Test parsing valid JSON content"""
        content = json.dumps({
            "sections": {"intro": "Introduction", "main": "Main content"},
            "references": ["ref1", "ref2"],
            "variables": {"key": "value"}
        })
        
        parsed, sections, refs, vars = parser._parse_json(content)
        
        assert sections == {"intro": "Introduction", "main": "Main content"}
        assert refs == []  # References are extracted from content, not from a direct field
        assert vars == {"key": "value"}
    
    def test_parse_json_invalid(self, parser):
        """Test parsing invalid JSON content"""
        content = "{ invalid json"
        
        # Should raise ValueError on parse error
        with pytest.raises(ValueError, match="Invalid JSON content"):
            parser._parse_json(content)
    
    # _parse_yaml tests  
    def test_parse_yaml_valid(self, parser):
        """Test parsing valid YAML content"""
        content = yaml.dump({
            "sections": {"setup": "Setup instructions", "config": "Configuration"},
            "references": ["doc1", "doc2"],
            "variables": {"env": "prod"}
        })
        
        parsed, sections, refs, vars = parser._parse_yaml(content)
        
        assert sections == {"setup": "Setup instructions", "config": "Configuration"}
        assert refs == []  # References are extracted from content, not from a direct field
        assert vars == {"env": "prod"}
    
    def test_parse_yaml_invalid(self, parser):
        """Test parsing invalid YAML content"""
        content = "invalid: yaml: content: :"
        
        # Should raise ValueError on parse error
        with pytest.raises(ValueError, match="Invalid YAML content"):
            parser._parse_yaml(content)
    
    # _parse_text tests
    def test_parse_text_simple(self, parser):
        """Test parsing plain text content"""
        content = "This is plain text content.\nWith multiple lines."
        
        parsed, sections, refs, vars = parser._parse_text(content)
        
        assert sections == {"content": content}
        assert refs == []
        assert vars == {}
    
    # Integration tests
    def test_parse_complex_markdown_file(self, parser):
        """Test parsing a complex markdown file with all features"""
        content = """---
description: Complex rule file
tags: [integration, test]
variables:
  version: "2.0"
  mode: development
---

# Overview

This is a complex rule that references [[Core Rules]] and [[Base Config]].

## Configuration

Set version to {{version}} and mode to {{mode}}.

### Dependencies

@import "base.md"
@include "utils.yaml"

## Implementation

Detailed implementation with [[API Reference]].

#integration #testing #rules
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            result = parser.parse_rule_file(temp_path)
            
            # Check metadata
            assert result.metadata.format == RuleFormat.MD
            # Type is CORE because content contains "Core Rules"
            assert result.metadata.type == RuleType.CORE
            assert result.metadata.description == "Complex rule file"
            # Tags include those from frontmatter and hashtags in content
            assert "integration" in result.metadata.tags  # From frontmatter and hashtag
            assert "test" in result.metadata.tags  # From frontmatter
            assert "testing" in result.metadata.tags  # From hashtag
            assert "rules" in result.metadata.tags  # From hashtag
            assert set(result.metadata.dependencies) == {"base.md", "utils.yaml"}
            
            # Check content
            assert len(result.sections) >= 3
            assert "Overview" in result.sections
            assert "Configuration" in result.sections
            assert "Implementation" in result.sections
            
            # Check references
            assert "Core Rules" in result.references
            assert "Base Config" in result.references
            assert "API Reference" in result.references
            
            # Check variables
            assert result.variables["version"] == "2.0"
            assert result.variables["mode"] == "development"
            
        finally:
            os.unlink(temp_path)
    
    def test_parse_json_file_integration(self, parser):
        """Test parsing a JSON rule file end-to-end"""
        content = json.dumps({
            "name": "json_rule",
            "sections": {
                "config": {"timeout": 30, "retries": 3},
                "endpoints": ["/api/v1", "/api/v2"]
            },
            "references": ["api_spec.json", "schema.json"],
            "variables": {
                "api_key": "{{API_KEY}}",
                "base_url": "https://example.com"
            }
        }, indent=2)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            result = parser.parse_rule_file(temp_path)
            
            assert result.metadata.format == RuleFormat.JSON
            assert len(result.sections) == 2
            # References are extracted from content, not from direct field
            assert len(result.references) == 0  # No [[refs]] in the content
            assert result.variables["base_url"] == "https://example.com"
            
        finally:
            os.unlink(temp_path)