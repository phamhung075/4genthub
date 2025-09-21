"""
Rule Composition Domain Service
Generated from enhanced_rule_orchestrator.py refactoring
Date: 2025-01-27

This file contains the core business logic for rule composition following DDD principles.
"""

from typing import Dict, Any, List, Optional, Tuple
from abc import ABC, abstractmethod

from ..entities.rule_entity import RuleContent, RuleInheritance
from ..value_objects.rule_value_objects import CompositionResult
from ..enums.rule_enums import RuleFormat, ConflictResolution, InheritanceType


class IRuleCompositionService(ABC):
    """Interface for rule composition domain service"""
    
    @abstractmethod
    def compose_rules(self, rules: List[RuleContent], output_format: RuleFormat, 
                     composition_strategy: str) -> CompositionResult:
        """Compose multiple rules into a single result"""
        pass
    
    @abstractmethod
    def resolve_conflicts(self, rules: List[RuleContent]) -> Dict[str, Any]:
        """Resolve conflicts between rules"""
        pass
    
    @abstractmethod
    def merge_section_content(self, content1: str, content2: str) -> str:
        """Merge content from two sections"""
        pass


class RuleCompositionService(IRuleCompositionService):
    """Domain service for rule composition business logic"""
    
    def __init__(self, conflict_strategy: ConflictResolution = ConflictResolution.MERGE):
        self.conflict_strategy = conflict_strategy
        self.composition_strategies = {
            "intelligent": self._intelligent_composition,
            "sequential": self._sequential_composition,
            "priority_merge": self._priority_merge_composition
        }
    
    def compose_rules(self, rules: List[RuleContent], output_format: RuleFormat = RuleFormat.MDC, 
                     composition_strategy: str = "intelligent") -> CompositionResult:
        """Compose multiple rules into a single result"""
        if not rules:
            return CompositionResult(
                composed_content="",
                source_rules=[],
                inheritance_chain=[],
                conflicts_resolved=[],
                composition_metadata={},
                success=False,
                warnings=["No rules provided for composition"]
            )
        
        # Sort rules by priority
        sorted_rules = self._sort_rules_by_priority(rules)
        
        # Get composition strategy
        strategy_func = self.composition_strategies.get(
            composition_strategy, 
            self._intelligent_composition
        )
        
        try:
            # Execute composition
            composed_content, conflicts_resolved, warnings = strategy_func(
                sorted_rules, output_format
            )
            
            # Build inheritance chain
            inheritance_chain = self._build_inheritance_chain(sorted_rules)
            
            # Create metadata
            composition_metadata = {
                "strategy": composition_strategy,
                "total_rules": len(rules),
                "conflicts_resolved": len(conflicts_resolved),
                "output_format": output_format.value,
                "timestamp": self._get_current_timestamp()
            }
            
            return CompositionResult(
                composed_content=composed_content,
                source_rules=[rule.rule_path for rule in sorted_rules],
                inheritance_chain=inheritance_chain,
                conflicts_resolved=conflicts_resolved,
                composition_metadata=composition_metadata,
                success=True,
                warnings=warnings
            )
            
        except Exception as e:
            return CompositionResult(
                composed_content="",
                source_rules=[rule.rule_path for rule in rules],
                inheritance_chain=[],
                conflicts_resolved=[],
                composition_metadata={"error": str(e)},
                success=False,
                warnings=[f"Composition failed: {str(e)}"]
            )
    
    def resolve_conflicts(self, rules: List[RuleContent]) -> Dict[str, Any]:
        """Resolve conflicts between rules"""
        conflicts = []
        resolution_log = []
        
        for i, rule1 in enumerate(rules):
            for j, rule2 in enumerate(rules[i+1:], i+1):
                rule_conflicts = self._detect_rule_conflicts(rule1, rule2)
                for conflict in rule_conflicts:
                    resolved = self._resolve_single_rule_conflict(conflict)
                    conflicts.append(conflict)
                    resolution_log.append(resolved)
        
        return {
            "total_conflicts": len(conflicts),
            "conflicts": conflicts,
            "resolutions": resolution_log,
            "strategy_used": self.conflict_strategy.value
        }
    
    def merge_section_content(self, content1: str, content2: str) -> str:
        """Merge content from two sections"""
        if not content1:
            return content2
        if not content2:
            return content1
        
        # Simple merge strategy - can be enhanced
        if content1 == content2:
            return content1
        
        # Try to merge intelligently
        lines1 = content1.strip().split('\n')
        lines2 = content2.strip().split('\n')
        
        merged_lines = []
        merged_lines.extend(lines1)
        
        for line in lines2:
            if line not in lines1:
                merged_lines.append(line)
        
        return '\n'.join(merged_lines)
    
    def _sort_rules_by_priority(self, rules: List[RuleContent]) -> List[RuleContent]:
        """Sort rules by priority score"""
        def get_priority_score(rule: RuleContent) -> int:
            score = 0
            # Check if rule_type exists before accessing its value
            if rule.rule_type is not None:
                # Core rules have highest priority
                if rule.rule_type.value == "core":
                    score += 1000
                # Workflow rules have high priority
                elif rule.rule_type.value == "workflow":
                    score += 500
            # Add metadata-based priority
            if hasattr(rule.metadata, 'priority'):
                priority_value = getattr(rule.metadata, 'priority', 0)
                # Ensure priority is a valid integer
                if isinstance(priority_value, (int, float)):
                    score += int(priority_value)
            return score

        return sorted(rules, key=get_priority_score, reverse=True)
    
    def _intelligent_composition(self, rules: List[RuleContent], output_format: RuleFormat) -> Tuple[str, List[str], List[str]]:
        """Intelligent composition strategy"""
        merged_sections = {}
        merged_variables = {}
        merged_metadata = {}
        conflicts_resolved = []
        warnings = []
        
        for rule in rules:
            # Merge sections
            for section_name, content in rule.sections.items():
                if section_name in merged_sections:
                    # Conflict detected, resolve it based on strategy
                    existing_content = merged_sections[section_name]
                    if self.conflict_strategy == ConflictResolution.MERGE:
                        merged_content = self.merge_section_content(existing_content, content)
                        merged_sections[section_name] = merged_content
                        conflicts_resolved.append(f"Section '{section_name}' merged from {rule.rule_path}")
                    elif self.conflict_strategy == ConflictResolution.OVERRIDE:
                        merged_sections[section_name] = content
                        conflicts_resolved.append(f"Section '{section_name}' overridden from {rule.rule_path}")
                    else:
                        # Default to merge
                        merged_content = self.merge_section_content(existing_content, content)
                        merged_sections[section_name] = merged_content
                        conflicts_resolved.append(f"Section '{section_name}' merged from {rule.rule_path}")
                else:
                    merged_sections[section_name] = content
            
            # Merge variables
            for var_name, value in rule.variables.items():
                if var_name in merged_variables:
                    if merged_variables[var_name] != value:
                        warnings.append(f"Variable '{var_name}' conflict in {rule.rule_path}")
                        # Use latest value
                        merged_variables[var_name] = value
                        conflicts_resolved.append(f"Variable '{var_name}' resolved from {rule.rule_path}")
                else:
                    merged_variables[var_name] = value
            
            # Merge metadata
            for key, value in rule.parsed_content.items():
                if key not in ["sections", "variables"]:
                    merged_metadata[key] = value
        
        # Generate composed content
        composed_content = self._generate_composed_content(
            merged_sections, merged_variables, merged_metadata, output_format
        )
        
        return composed_content, conflicts_resolved, warnings
    
    def _sequential_composition(self, rules: List[RuleContent], output_format: RuleFormat) -> Tuple[str, List[str], List[str]]:
        """Sequential composition strategy - append content in order"""
        all_content = []
        conflicts_resolved = []
        warnings = []
        
        for rule in rules:
            all_content.append(f"# From {rule.rule_path}")
            all_content.append(rule.raw_content)
            all_content.append("")  # Add separator
        
        composed_content = '\n'.join(all_content)
        return composed_content, conflicts_resolved, warnings
    
    def _priority_merge_composition(self, rules: List[RuleContent], output_format: RuleFormat) -> Tuple[str, List[str], List[str]]:
        """Priority-based merge composition"""
        # Use the highest priority rule as base
        if not rules:
            return "", [], []
        
        base_rule = rules[0]  # Already sorted by priority
        merged_sections = base_rule.sections.copy()
        merged_variables = base_rule.variables.copy()
        conflicts_resolved = []
        warnings = []
        
        # Merge lower priority rules
        for rule in rules[1:]:
            for section_name, content in rule.sections.items():
                if section_name not in merged_sections:
                    merged_sections[section_name] = content
                    conflicts_resolved.append(f"Added section '{section_name}' from {rule.rule_path}")
            
            for var_name, value in rule.variables.items():
                if var_name not in merged_variables:
                    merged_variables[var_name] = value
                    conflicts_resolved.append(f"Added variable '{var_name}' from {rule.rule_path}")
        
        # Generate composed content
        composed_content = self._generate_composed_content(
            merged_sections, merged_variables, base_rule.parsed_content, output_format
        )
        
        return composed_content, conflicts_resolved, warnings
    
    def _detect_rule_conflicts(self, rule1: RuleContent, rule2: RuleContent) -> List[Dict[str, Any]]:
        """Detect conflicts between two rules"""
        conflicts = []
        
        # Check section conflicts
        for section_name in rule1.sections:
            if section_name in rule2.sections:
                if rule1.sections[section_name] != rule2.sections[section_name]:
                    conflicts.append({
                        "type": "section",
                        "name": section_name,
                        "rule1_path": rule1.rule_path,
                        "rule2_path": rule2.rule_path,
                        "rule1_content": rule1.sections[section_name],
                        "rule2_content": rule2.sections[section_name]
                    })
        
        # Check variable conflicts
        for var_name in rule1.variables:
            if var_name in rule2.variables:
                if rule1.variables[var_name] != rule2.variables[var_name]:
                    conflicts.append({
                        "type": "variable",
                        "name": var_name,
                        "rule1_path": rule1.rule_path,
                        "rule2_path": rule2.rule_path,
                        "rule1_value": rule1.variables[var_name],
                        "rule2_value": rule2.variables[var_name]
                    })
        
        return conflicts
    
    def _resolve_single_rule_conflict(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a single rule conflict"""
        resolution = {
            "conflict": conflict,
            "strategy": self.conflict_strategy.value,
            "resolved_value": None,
            "resolution_reason": ""
        }
        
        if self.conflict_strategy == ConflictResolution.MERGE:
            if conflict["type"] == "section":
                resolved = self.merge_section_content(
                    conflict["rule1_content"], 
                    conflict["rule2_content"]
                )
                resolution["resolved_value"] = resolved
                resolution["resolution_reason"] = "Merged section content"
            elif conflict["type"] == "variable":
                # For variables, use the latest (rule2) value
                resolution["resolved_value"] = conflict["rule2_value"]
                resolution["resolution_reason"] = "Used latest variable value"
        
        elif self.conflict_strategy == ConflictResolution.OVERRIDE:
            resolution["resolved_value"] = conflict["rule2_content"] if conflict["type"] == "section" else conflict["rule2_value"]
            resolution["resolution_reason"] = "Override with latest value"
        
        return resolution
    
    def _build_inheritance_chain(self, rules: List[RuleContent]) -> List[RuleInheritance]:
        """Build inheritance chain from rules"""
        inheritance_chain = []
        
        for i, rule in enumerate(rules[:-1]):
            next_rule = rules[i + 1]
            inheritance = RuleInheritance(
                parent_path=rule.rule_path,
                child_path=next_rule.rule_path,
                inheritance_type=InheritanceType.CONTENT,
                inherited_sections=list(rule.sections.keys()),
                overridden_sections=[],
                merged_variables=rule.variables.copy(),
                inheritance_depth=i + 1,
                conflicts=[]
            )
            inheritance_chain.append(inheritance)
        
        return inheritance_chain
    
    def _generate_composed_content(self, sections: Dict[str, str], variables: Dict[str, Any], 
                                 metadata: Dict[str, Any], output_format: RuleFormat) -> str:
        """Generate composed content in the specified format"""
        if output_format == RuleFormat.MDC:
            return self._generate_mdc_content(sections, variables, metadata)
        elif output_format == RuleFormat.MD:
            return self._generate_markdown_content(sections, variables, metadata)
        elif output_format == RuleFormat.JSON:
            return self._generate_json_content(sections, variables, metadata)
        else:
            # Default to markdown
            return self._generate_markdown_content(sections, variables, metadata)
    
    def _generate_mdc_content(self, sections: Dict[str, str], variables: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Generate MDC format content"""
        content_parts = []
        
        # Add metadata header
        if metadata:
            content_parts.append("---")
            for key, value in metadata.items():
                if key not in ["sections", "variables"]:
                    content_parts.append(f"{key}: {value}")
            content_parts.append("---")
            content_parts.append("")
        
        # Add variables section
        if variables:
            content_parts.append("## Variables")
            for key, value in variables.items():
                content_parts.append(f"- {key}: {value}")
            content_parts.append("")
        
        # Add content sections
        for section_name, content in sections.items():
            content_parts.append(f"## {section_name}")
            content_parts.append(content)
            content_parts.append("")
        
        return '\n'.join(content_parts)
    
    def _generate_markdown_content(self, sections: Dict[str, str], variables: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Generate Markdown format content"""
        content_parts = []
        
        # Add title from metadata
        title = metadata.get("title", "Composed Rule")
        content_parts.append(f"# {title}")
        content_parts.append("")
        
        # Add variables if any
        if variables:
            content_parts.append("## Configuration")
            for key, value in variables.items():
                content_parts.append(f"- **{key}**: {value}")
            content_parts.append("")
        
        # Add sections
        for section_name, content in sections.items():
            content_parts.append(f"## {section_name}")
            content_parts.append(content)
            content_parts.append("")
        
        return '\n'.join(content_parts)
    
    def _generate_json_content(self, sections: Dict[str, str], variables: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Generate JSON format content"""
        import json
        
        composed_data = {
            "metadata": metadata,
            "variables": variables,
            "sections": sections
        }
        
        return json.dumps(composed_data, indent=2)
    
    def _get_current_timestamp(self) -> float:
        """Get current timestamp"""
        import time
        return time.time() 