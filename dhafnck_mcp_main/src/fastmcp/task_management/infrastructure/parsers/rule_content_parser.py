"""Rule Content Parser

This parser handles various rule file formats and extracts structured content
following infrastructure layer responsibilities in DDD architecture.
"""

from typing import Dict, Any, List, Tuple
from pathlib import Path
import re
import json
import yaml
import hashlib
import logging

from ...domain.entities.rule_content import (
    RuleContent, RuleMetadata, RuleFormat, RuleType
)

logger = logging.getLogger(__name__)


class RuleContentParser:
    """Advanced parser for rule content with format detection and validation"""
    
    def __init__(self):
        self.format_handlers = {
            RuleFormat.MDC: self._parse_mdc,
            RuleFormat.MD: self._parse_markdown,
            RuleFormat.JSON: self._parse_json,
            RuleFormat.YAML: self._parse_yaml,
            RuleFormat.TXT: self._parse_text
        }
    
    def parse_rule_file(self, file_path: Path) -> RuleContent:
        """Parse a rule file and extract structured content"""
        try:
            # Detect format
            format_type = self._detect_format(file_path)
            
            # Read content
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            
            # Generate metadata
            metadata = self._generate_metadata(file_path, format_type, raw_content)
            
            # Parse content based on format
            handler = self.format_handlers.get(format_type, self._parse_text)
            parsed_content, sections, references, variables = handler(raw_content)
            
            return RuleContent(
                metadata=metadata,
                raw_content=raw_content,
                parsed_content=parsed_content,
                sections=sections,
                references=references,
                variables=variables
            )
            
        except Exception as e:
            logger.error(f"Failed to parse rule file {file_path}: {e}")
            raise
    
    def _detect_format(self, file_path: Path) -> RuleFormat:
        """Detect rule file format from extension and content"""
        suffix = file_path.suffix.lower()
        
        format_map = {
            '.mdc': RuleFormat.MDC,
            '.md': RuleFormat.MD,
            '.json': RuleFormat.JSON,
            '.yaml': RuleFormat.YAML,
            '.yml': RuleFormat.YAML,
            '.txt': RuleFormat.TXT
        }
        
        return format_map.get(suffix, RuleFormat.TXT)
    
    def _generate_metadata(self, file_path: Path, format_type: RuleFormat, content: str) -> RuleMetadata:
        """Generate metadata for rule file"""
        stat = file_path.stat()
        checksum = hashlib.md5(content.encode()).hexdigest()
        
        # Extract dependencies from content
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
            dependencies=dependencies
        )
    
    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract rule dependencies from content"""
        dependencies = []
        
        # Look for common dependency patterns
        patterns = [
            r'\[([^\]]+)\]\(mdc:([^)]+)\)',  # MDC references
            r'@import\s+"([^"]+)"',          # Import statements
            r'include:\s*([^\n]+)',          # Include directives
            r'depends_on:\s*\[([^\]]+)\]'    # Explicit dependencies
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            dependencies.extend([match[1] if isinstance(match, tuple) else match for match in matches])
        
        return list(set(dependencies))  # Remove duplicates
    
    def _classify_rule_type(self, file_path: Path, content: str) -> RuleType:
        """Classify rule type based on path and content"""
        path_str = str(file_path).lower()
        content_lower = content.lower()

        # Check for specific rule types in order of test expectations
        if 'task' in path_str or 'task' in content_lower:
            return RuleType.TASK
        elif 'context' in path_str or 'context' in content_lower:
            return RuleType.CONTEXT
        elif 'agent' in path_str:
            return RuleType.AGENT
        elif 'agent' in content_lower:
            # Only classify as AGENT if not also config
            if 'config' not in path_str and 'configuration' not in path_str and 'config' not in content_lower and 'configuration' not in content_lower:
                return RuleType.AGENT
        # Only classify as CONFIG if path or content clearly indicate config section/directive
        config_section_patterns = [
            r'^\s*config:',
            r'^\s*configuration:',
            r'^\s*\[?config\]?\s*$',
            r'^\s*\[?configuration\]?\s*$'
        ]
        if (
            'config' in path_str or 'configuration' in path_str or
            any(re.search(pat, content_lower, re.MULTILINE) for pat in config_section_patterns)
        ):
            return RuleType.CONFIG
        # Otherwise, treat as GENERAL
        return RuleType.GENERAL
    
    def _parse_mdc(self, content: str) -> Tuple[Dict[str, Any], Dict[str, str], List[str], Dict[str, Any]]:
        """Parse MDC (Markdown with directives) content"""
        return self._parse_markdown(content)  # MDC uses markdown structure
    
    def _parse_markdown(self, content: str) -> Tuple[Dict[str, Any], Dict[str, str], List[str], Dict[str, Any]]:
        """Parse markdown content and extract structure"""
        sections = {}
        references = []
        variables = {}
        
        # Split content by headers
        lines = content.split('\n')
        current_section = 'content'
        current_content = []
        
        for line in lines:
            # Check for headers
            if line.startswith('#'):
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                current_section = line.strip('# ').lower().replace(' ', '_')
                current_content = []
            else:
                current_content.append(line)
                
                # Extract references
                ref_matches = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', line)
                references.extend([match[1] for match in ref_matches])
                
                # Extract variables (simple pattern: {{variable}})
                var_matches = re.findall(r'\{\{([^}]+)\}\}', line)
                for var in var_matches:
                    variables[var] = var  # Placeholder value
        
        # Save last section
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        parsed_content = {
            'type': 'markdown',
            'sections': sections,
            'references': references,
            'variables': variables
        }
        
        return parsed_content, sections, references, variables
    
    def _parse_json(self, content: str) -> Tuple[Dict[str, Any], Dict[str, str], List[str], Dict[str, Any]]:
        """Parse JSON content"""
        try:
            parsed = json.loads(content)
            sections = {}
            references = []
            variables = {}
            
            def extract_refs(obj, path=""):
                """Recursively extract references from JSON"""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path}.{key}" if path else key
                        if key == 'reference' and isinstance(value, str):
                            references.append(value)
                        elif key == 'variables' and isinstance(value, dict):
                            variables.update(value)
                        else:
                            extract_refs(value, new_path)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        extract_refs(item, f"{path}[{i}]")
            
            extract_refs(parsed)
            
            # Convert top-level keys to sections
            for key, value in parsed.items():
                sections[key] = str(value) if not isinstance(value, (dict, list)) else json.dumps(value, indent=2)
            
            return parsed, sections, references, variables
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {}, {}, [], {}
    
    def _parse_yaml(self, content: str) -> Tuple[Dict[str, Any], Dict[str, str], List[str], Dict[str, Any]]:
        """Parse YAML content"""
        try:
            parsed = yaml.safe_load(content)
            sections = {}
            references = []
            variables = {}
            
            def extract_refs(obj):
                """Recursively extract references from YAML"""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key == 'reference' and isinstance(value, str):
                            references.append(value)
                        elif key == 'variables' and isinstance(value, dict):
                            variables.update(value)
                        else:
                            extract_refs(value)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_refs(item)
            
            if isinstance(parsed, dict):
                extract_refs(parsed)
                
                # Convert top-level keys to sections
                for key, value in parsed.items():
                    sections[key] = str(value) if not isinstance(value, (dict, list)) else yaml.dump(value)
            
            return parsed or {}, sections, references, variables
            
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML: {e}")
            return {}, {}, [], {}
    
    def _parse_text(self, content: str) -> Tuple[Dict[str, Any], Dict[str, str], List[str], Dict[str, Any]]:
        """Parse plain text content"""
        sections = {'content': content}
        references = []
        variables = {}
        
        # Extract basic references (URLs, file paths)
        ref_patterns = [
            r'https?://[^\s]+',
            r'file://[^\s]+',
            r'[a-zA-Z0-9_-]+\.[a-zA-Z]{2,4}'
        ]
        
        for pattern in ref_patterns:
            matches = re.findall(pattern, content)
            references.extend(matches)
        
        # Extract simple variables
        var_matches = re.findall(r'\$\{([^}]+)\}', content)
        for var in var_matches:
            variables[var] = var
        
        parsed_content = {
            'type': 'text',
            'content': content,
            'lines': len(content.split('\n')),
            'characters': len(content)
        }
        
        return parsed_content, sections, references, variables