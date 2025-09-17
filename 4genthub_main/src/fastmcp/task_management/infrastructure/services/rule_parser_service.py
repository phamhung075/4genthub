"""
Rule Parser Infrastructure Service
Generated from enhanced_rule_orchestrator.py refactoring
Date: 2025-01-27

This file contains the infrastructure implementation for rule parsing following DDD principles.
"""

import json
import yaml
import re
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from abc import ABC, abstractmethod

from ...domain.entities.rule_entity import RuleContent, RuleMetadata
from ...domain.enums.rule_enums import RuleFormat, RuleType


class IRuleParserService(ABC):
    """Interface for rule parser service"""
    
    @abstractmethod
    def parse_rule_file(self, file_path: Path) -> RuleContent:
        """Parse a rule file and return structured content"""
        pass
    
    @abstractmethod
    def detect_format(self, file_path: Path) -> RuleFormat:
        """Detect the format of a rule file"""
        pass


class RuleParserService(IRuleParserService):
    """Infrastructure service for parsing rule files"""
    
    def __init__(self):
        self.format_parsers = {
            RuleFormat.MDC: self._parse_mdc,
            RuleFormat.MD: self._parse_markdown,
            RuleFormat.JSON: self._parse_json,
            RuleFormat.YAML: self._parse_yaml,
            RuleFormat.TXT: self._parse_text
        }
    
    def parse_rule_file(self, file_path: Path) -> RuleContent:
        """Parse a rule file and return structured content"""
        if not file_path.exists():
            raise FileNotFoundError(f"Rule file not found: {file_path}")
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
        except Exception as e:
            raise ValueError(f"Failed to read rule file {file_path}: {str(e)}")
        
        # Detect format
        format_type = self.detect_format(file_path)
        
        # Generate metadata
        metadata = self._generate_metadata(file_path, format_type, raw_content)
        
        # Parse content based on format
        parser = self.format_parsers.get(format_type, self._parse_text)
        parsed_content, sections, references, variables = parser(raw_content)
        
        return RuleContent(
            metadata=metadata,
            raw_content=raw_content,
            parsed_content=parsed_content,
            sections=sections,
            references=references,
            variables=variables
        )
    
    def detect_format(self, file_path: Path) -> RuleFormat:
        """Detect the format of a rule file"""
        suffix = file_path.suffix.lower()
        
        format_mapping = {
            '.mdc': RuleFormat.MDC,
            '.md': RuleFormat.MD,
            '.markdown': RuleFormat.MD,
            '.json': RuleFormat.JSON,
            '.yaml': RuleFormat.YAML,
            '.yml': RuleFormat.YAML,
            '.txt': RuleFormat.TXT
        }
        
        return format_mapping.get(suffix, RuleFormat.TXT)
    
    def _generate_metadata(self, file_path: Path, format_type: RuleFormat, content: str) -> RuleMetadata:
        """Generate metadata for a rule file"""
        stat = file_path.stat()
        
        # Generate checksum
        checksum = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        # Extract dependencies
        dependencies = self._extract_dependencies(content)
        
        # Classify rule type
        rule_type = self._classify_rule_type(file_path, content)
        
        return RuleMetadata(
            path=str(file_path),
            format=format_type,
            type=rule_type,
            size=stat.st_size,
            modified=stat.st_mtime,
            checksum=checksum,
            dependencies=dependencies,
            version="1.0",
            author="rule_parser",  # Static parser service - no user context
            description=self._extract_description(content),
            tags=self._extract_tags(content)
        )
    
    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract dependencies from rule content"""
        dependencies = []
        
        # Look for @import, @include, or similar patterns
        import_patterns = [
            r'@import\s+["\']([^"\']+)["\']',
            r'@include\s+["\']([^"\']+)["\']',
            r'import\s+["\']([^"\']+)["\']',
            r'require\s+["\']([^"\']+)["\']'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            dependencies.extend(matches)
        
        # Look for file references
        file_ref_pattern = r'(?:file|path):\s*["\']([^"\']+)["\']'
        file_refs = re.findall(file_ref_pattern, content, re.IGNORECASE)
        dependencies.extend(file_refs)
        
        return list(set(dependencies))  # Remove duplicates
    
    def _classify_rule_type(self, file_path: Path, content: str) -> RuleType:
        """Classify the type of rule based on path and content"""
        path_str = str(file_path).lower()
        content_lower = content.lower()
        
        # Check path-based classification
        if 'core' in path_str or 'system' in path_str:
            return RuleType.CORE
        elif 'workflow' in path_str or 'process' in path_str:
            return RuleType.WORKFLOW
        elif 'agent' in path_str:
            return RuleType.AGENT
        elif 'project' in path_str:
            return RuleType.PROJECT
        elif 'context' in path_str:
            return RuleType.CONTEXT
        
        # Check content-based classification
        if any(keyword in content_lower for keyword in ['core', 'system', 'essential']):
            return RuleType.CORE
        elif any(keyword in content_lower for keyword in ['workflow', 'process', 'pipeline']):
            return RuleType.WORKFLOW
        elif any(keyword in content_lower for keyword in ['agent', 'bot', 'assistant']):
            return RuleType.AGENT
        elif any(keyword in content_lower for keyword in ['project', 'repository']):
            return RuleType.PROJECT
        elif any(keyword in content_lower for keyword in ['context', 'environment']):
            return RuleType.CONTEXT
        
        return RuleType.CUSTOM
    
    def _extract_description(self, content: str) -> str:
        """Extract description from content"""
        lines = content.split('\n')
        
        # Look for description in YAML frontmatter
        if content.startswith('---'):
            in_frontmatter = True
            for line in lines[1:]:
                if line.strip() == '---':
                    break
                if line.strip().startswith('description:'):
                    return line.split(':', 1)[1].strip().strip('"\'')
        
        # Look for first comment or paragraph
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('//'):
                if len(line) > 20:  # Likely a description
                    return line[:200] + '...' if len(line) > 200 else line
        
        return ""
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract tags from content"""
        tags = []
        
        # Look for tags in YAML frontmatter
        if content.startswith('---'):
            lines = content.split('\n')
            in_frontmatter = True
            for line in lines[1:]:
                if line.strip() == '---':
                    break
                if line.strip().startswith('tags:'):
                    tag_line = line.split(':', 1)[1].strip()
                    if tag_line.startswith('[') and tag_line.endswith(']'):
                        # Parse as JSON array
                        try:
                            tags = json.loads(tag_line)
                        except:
                            pass
        
        # Look for hashtags in content
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, content)
        tags.extend(hashtags)
        
        return list(set(tags))  # Remove duplicates
    
    def _parse_mdc(self, content: str) -> Tuple[Dict[str, Any], Dict[str, str], List[str], Dict[str, Any]]:
        """Parse MDC format content"""
        # MDC is essentially markdown with metadata
        return self._parse_markdown(content)
    
    def _parse_markdown(self, content: str) -> Tuple[Dict[str, Any], Dict[str, str], List[str], Dict[str, Any]]:
        """Parse Markdown format content"""
        parsed_content = {}
        sections = {}
        references = []
        variables = {}
        
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        # Parse YAML frontmatter if present
        if content.startswith('---'):
            frontmatter_end = -1
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    frontmatter_end = i
                    break
            
            if frontmatter_end > 0:
                frontmatter_content = '\n'.join(lines[1:frontmatter_end])
                try:
                    frontmatter_data = yaml.safe_load(frontmatter_content)
                    if isinstance(frontmatter_data, dict):
                        parsed_content.update(frontmatter_data)
                        variables.update(frontmatter_data.get('variables', {}))
                except:
                    pass
                
                lines = lines[frontmatter_end + 1:]
        
        # Parse sections
        for line in lines:
            # Check for section headers
            if line.startswith('#'):
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                
                # Start new section
                current_section = line.lstrip('#').strip()
                current_content = []
            else:
                if current_section:
                    current_content.append(line)
                
                # Extract references
                if '[[' in line and ']]' in line:
                    refs = re.findall(r'\[\[([^\]]+)\]\]', line)
                    references.extend(refs)
                
                # Extract variables ({{variable}})
                if '{{' in line and '}}' in line:
                    vars_found = re.findall(r'\{\{([^}]+)\}\}', line)
                    for var in vars_found:
                        variables[var.strip()] = None  # Placeholder
        
        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        # If no sections found, treat entire content as one section
        if not sections:
            sections['content'] = content
        
        parsed_content['sections'] = sections
        parsed_content['variables'] = variables
        
        return parsed_content, sections, references, variables
    
    def _parse_json(self, content: str) -> Tuple[Dict[str, Any], Dict[str, str], List[str], Dict[str, Any]]:
        """Parse JSON format content"""
        try:
            parsed_content = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON content: {str(e)}")
        
        sections = parsed_content.get('sections', {})
        variables = parsed_content.get('variables', {})
        references = []
        
        # Extract references from all values
        def extract_refs(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    extract_refs(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for item in obj:
                    extract_refs(item, path)
            elif isinstance(obj, str):
                if '[[' in obj and ']]' in obj:
                    refs = re.findall(r'\[\[([^\]]+)\]\]', obj)
                    references.extend(refs)
        
        extract_refs(parsed_content)
        
        return parsed_content, sections, references, variables
    
    def _parse_yaml(self, content: str) -> Tuple[Dict[str, Any], Dict[str, str], List[str], Dict[str, Any]]:
        """Parse YAML format content"""
        try:
            parsed_content = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML content: {str(e)}")
        
        if not isinstance(parsed_content, dict):
            parsed_content = {'content': parsed_content}
        
        sections = parsed_content.get('sections', {})
        variables = parsed_content.get('variables', {})
        references = []
        
        # Extract references from all values
        def extract_refs(obj):
            if isinstance(obj, dict):
                for value in obj.values():
                    extract_refs(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_refs(item)
            elif isinstance(obj, str):
                if '[[' in obj and ']]' in obj:
                    refs = re.findall(r'\[\[([^\]]+)\]\]', obj)
                    references.extend(refs)
        
        extract_refs(parsed_content)
        
        return parsed_content, sections, references, variables
    
    def _parse_text(self, content: str) -> Tuple[Dict[str, Any], Dict[str, str], List[str], Dict[str, Any]]:
        """Parse plain text format content"""
        parsed_content = {'content': content}
        sections = {'content': content}
        references = []
        variables = {}
        
        # Extract references
        if '[[' in content and ']]' in content:
            references = re.findall(r'\[\[([^\]]+)\]\]', content)
        
        # Extract simple variables (key=value)
        var_pattern = r'^(\w+)\s*=\s*(.+)$'
        for line in content.split('\n'):
            match = re.match(var_pattern, line.strip())
            if match:
                key, value = match.groups()
                variables[key] = value.strip().strip('"\'')
        
        return parsed_content, sections, references, variables 