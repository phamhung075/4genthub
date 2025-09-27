"""Requirement Analyzer Domain Service

Analyzes requirements and planning contexts to extract structured information
that can be used for intelligent task planning.
"""

import re
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum

from ..entities.planning_request import RequirementItem, ComplexityLevel, PlanningContext

class RequirementPattern(Enum):
    """Common patterns found in requirements"""
    CRUD_OPERATIONS = "crud_operations"
    USER_AUTHENTICATION = "user_authentication" 
    API_INTEGRATION = "api_integration"
    UI_COMPONENT = "ui_component"
    DATABASE_SCHEMA = "database_schema"
    TESTING_REQUIREMENT = "testing_requirement"
    SECURITY_REQUIREMENT = "security_requirement"
    PERFORMANCE_REQUIREMENT = "performance_requirement"
    DOCUMENTATION_REQUIREMENT = "documentation_requirement"
    BUG_FIX = "bug_fix"
    REFACTORING = "refactoring"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"

@dataclass
class AnalyzedRequirement:
    """Result of requirement analysis"""
    original_requirement: RequirementItem
    detected_patterns: List[RequirementPattern]
    complexity_indicators: Dict[str, Any]
    suggested_agents: List[str]
    estimated_effort_hours: float
    risk_factors: List[str]
    dependencies: List[str]  # Inferred dependencies on other requirements
    technical_considerations: List[str]
    
class RequirementAnalyzer:
    """
    Domain service for analyzing requirements and extracting actionable insights.
    
    Uses pattern matching, keyword analysis, and heuristics to understand
    the scope and complexity of requirements.
    """
    
    def __init__(self):
        self.pattern_keywords = {
            RequirementPattern.CRUD_OPERATIONS: [
                'create', 'read', 'update', 'delete', 'crud', 'manage', 'add', 'edit', 'remove'
            ],
            RequirementPattern.USER_AUTHENTICATION: [
                'login', 'logout', 'authenticate', 'authorization', 'auth', 'jwt', 'session', 
                'password', 'user', 'signin', 'signup', 'register'
            ],
            RequirementPattern.API_INTEGRATION: [
                'api', 'endpoint', 'rest', 'graphql', 'integration', 'third-party', 'external',
                'webhook', 'http', 'service'
            ],
            RequirementPattern.UI_COMPONENT: [
                'ui', 'component', 'interface', 'frontend', 'react', 'vue', 'angular', 'button',
                'form', 'modal', 'dashboard', 'page', 'view', 'screen'
            ],
            RequirementPattern.DATABASE_SCHEMA: [
                'database', 'schema', 'table', 'model', 'migration', 'sql', 'postgres', 'mysql',
                'mongodb', 'relation', 'foreign key', 'index'
            ],
            RequirementPattern.TESTING_REQUIREMENT: [
                'test', 'testing', 'unit test', 'integration test', 'e2e', 'spec', 'coverage',
                'assertion', 'mock', 'stub'
            ],
            RequirementPattern.SECURITY_REQUIREMENT: [
                'security', 'secure', 'encryption', 'https', 'ssl', 'vulnerability', 'audit',
                'compliance', 'gdpr', 'owasp'
            ],
            RequirementPattern.PERFORMANCE_REQUIREMENT: [
                'performance', 'speed', 'optimization', 'cache', 'latency', 'throughput',
                'scalability', 'load', 'benchmark'
            ],
            RequirementPattern.DOCUMENTATION_REQUIREMENT: [
                'document', 'documentation', 'readme', 'guide', 'manual', 'wiki', 'help',
                'tutorial', 'api docs'
            ],
            RequirementPattern.BUG_FIX: [
                'bug', 'fix', 'error', 'issue', 'problem', 'defect', 'broken', 'crash',
                'exception', 'failure'
            ],
            RequirementPattern.REFACTORING: [
                'refactor', 'cleanup', 'restructure', 'reorganize', 'improve', 'optimize',
                'modernize', 'technical debt'
            ],
            RequirementPattern.DEPLOYMENT: [
                'deploy', 'deployment', 'production', 'staging', 'ci/cd', 'pipeline',
                'docker', 'kubernetes', 'infrastructure'
            ],
            RequirementPattern.MONITORING: [
                'monitor', 'monitoring', 'logging', 'metrics', 'alerting', 'observability',
                'analytics', 'tracking'
            ]
        }
        
        self.agent_specializations = {
            RequirementPattern.CRUD_OPERATIONS: ['coding-agent'],
            RequirementPattern.USER_AUTHENTICATION: ['coding-agent', 'security-auditor-agent'],
            RequirementPattern.API_INTEGRATION: ['coding-agent', 'system-architect-agent'],
            RequirementPattern.UI_COMPONENT: ['shadcn-ui-expert-agent', 'design-system-agent'],
            RequirementPattern.DATABASE_SCHEMA: ['coding-agent', 'system-architect-agent'],
            RequirementPattern.TESTING_REQUIREMENT: ['test-orchestrator-agent'],
            RequirementPattern.SECURITY_REQUIREMENT: ['security-auditor-agent'],
            RequirementPattern.PERFORMANCE_REQUIREMENT: ['performance-load-tester-agent', 'efficiency-optimization-agent'],
            RequirementPattern.DOCUMENTATION_REQUIREMENT: ['documentation-agent'],
            RequirementPattern.BUG_FIX: ['debugger-agent', 'root-cause-analysis-agent'],
            RequirementPattern.REFACTORING: ['code-reviewer-agent', 'system-architect-agent'],
            RequirementPattern.DEPLOYMENT: ['devops-agent'],
            RequirementPattern.MONITORING: ['health-monitor-agent', 'analytics-setup-agent']
        }
        
        self.complexity_weights = {
            RequirementPattern.CRUD_OPERATIONS: 2.0,
            RequirementPattern.USER_AUTHENTICATION: 4.0,
            RequirementPattern.API_INTEGRATION: 3.0,
            RequirementPattern.UI_COMPONENT: 2.5,
            RequirementPattern.DATABASE_SCHEMA: 3.5,
            RequirementPattern.TESTING_REQUIREMENT: 1.5,
            RequirementPattern.SECURITY_REQUIREMENT: 4.5,
            RequirementPattern.PERFORMANCE_REQUIREMENT: 4.0,
            RequirementPattern.DOCUMENTATION_REQUIREMENT: 1.0,
            RequirementPattern.BUG_FIX: 3.0,
            RequirementPattern.REFACTORING: 3.5,
            RequirementPattern.DEPLOYMENT: 3.0,
            RequirementPattern.MONITORING: 2.5
        }
    
    def analyze_requirement(self, requirement: RequirementItem) -> AnalyzedRequirement:
        """
        Analyze a single requirement and extract insights.
        
        Args:
            requirement: The requirement to analyze
            
        Returns:
            AnalyzedRequirement with detected patterns and recommendations
        """
        text = f"{requirement.description} {' '.join(requirement.acceptance_criteria)} {' '.join(requirement.constraints)}"
        text_lower = text.lower()
        
        # Detect patterns
        detected_patterns = self._detect_patterns(text_lower)
        
        # Analyze complexity 
        complexity_indicators = self._analyze_complexity(requirement, detected_patterns, text_lower)
        
        # Suggest agents
        suggested_agents = self._suggest_agents(detected_patterns)
        
        # Estimate effort
        estimated_effort_hours = self._estimate_effort(detected_patterns, complexity_indicators, len(requirement.acceptance_criteria))
        
        # Identify risks
        risk_factors = self._identify_risks(detected_patterns, text_lower)
        
        # Infer dependencies
        dependencies = self._infer_dependencies(detected_patterns, text_lower)
        
        # Technical considerations
        technical_considerations = self._identify_technical_considerations(detected_patterns, text_lower)
        
        return AnalyzedRequirement(
            original_requirement=requirement,
            detected_patterns=detected_patterns,
            complexity_indicators=complexity_indicators,
            suggested_agents=suggested_agents,
            estimated_effort_hours=estimated_effort_hours,
            risk_factors=risk_factors,
            dependencies=dependencies,
            technical_considerations=technical_considerations
        )
    
    def analyze_requirements_batch(self, requirements: List[RequirementItem]) -> List[AnalyzedRequirement]:
        """
        Analyze multiple requirements and detect cross-requirement patterns.
        
        Args:
            requirements: List of requirements to analyze
            
        Returns:
            List of analyzed requirements with cross-references
        """
        analyzed = [self.analyze_requirement(req) for req in requirements]
        
        # Second pass: detect cross-requirement dependencies and patterns
        for i, analysis in enumerate(analyzed):
            for j, other_analysis in enumerate(analyzed):
                if i != j:
                    # Check for implicit dependencies
                    cross_deps = self._detect_cross_dependencies(analysis, other_analysis)
                    analysis.dependencies.extend(cross_deps)
        
        return analyzed
    
    def _detect_patterns(self, text: str) -> List[RequirementPattern]:
        """Detect requirement patterns based on keywords"""
        detected = []
        
        for pattern, keywords in self.pattern_keywords.items():
            if any(keyword in text for keyword in keywords):
                detected.append(pattern)
        
        return detected
    
    def _analyze_complexity(self, requirement: RequirementItem, patterns: List[RequirementPattern], text: str) -> Dict[str, Any]:
        """Analyze complexity indicators"""
        indicators = {}
        
        # Pattern-based complexity
        pattern_complexity = sum(self.complexity_weights.get(pattern, 1.0) for pattern in patterns)
        indicators['pattern_complexity'] = pattern_complexity
        
        # Text length indicator
        indicators['description_length'] = len(requirement.description)
        indicators['criteria_count'] = len(requirement.acceptance_criteria)
        indicators['constraints_count'] = len(requirement.constraints)
        
        # Keyword complexity indicators
        complexity_keywords = {
            'high': ['complex', 'advanced', 'sophisticated', 'enterprise', 'scalable', 'distributed'],
            'medium': ['integrate', 'configure', 'implement', 'design', 'develop'],
            'low': ['simple', 'basic', 'straightforward', 'minor', 'quick']
        }
        
        for level, keywords in complexity_keywords.items():
            if any(keyword in text for keyword in keywords):
                indicators['keyword_complexity'] = level
                break
        else:
            indicators['keyword_complexity'] = 'medium'
        
        return indicators
    
    def _suggest_agents(self, patterns: List[RequirementPattern]) -> List[str]:
        """Suggest agents based on detected patterns"""
        suggested = set()
        
        for pattern in patterns:
            agents = self.agent_specializations.get(pattern, [])
            suggested.update(agents)
        
        # Default to coding-agent if no specific patterns detected
        if not suggested:
            suggested.add('coding-agent')
        
        return list(suggested)
    
    def _estimate_effort(self, patterns: List[RequirementPattern], complexity_indicators: Dict[str, Any], criteria_count: int) -> float:
        """Estimate effort in hours"""
        base_hours = sum(self.complexity_weights.get(pattern, 1.0) for pattern in patterns)
        
        # Adjust based on complexity indicators
        complexity_multiplier = 1.0
        if complexity_indicators.get('keyword_complexity') == 'high':
            complexity_multiplier = 1.5
        elif complexity_indicators.get('keyword_complexity') == 'low':
            complexity_multiplier = 0.7
        
        # Adjust based on acceptance criteria count
        criteria_multiplier = 1.0 + (criteria_count * 0.1)  # 10% more per criteria
        
        return base_hours * complexity_multiplier * criteria_multiplier
    
    def _identify_risks(self, patterns: List[RequirementPattern], text: str) -> List[str]:
        """Identify potential risks based on patterns and text"""
        risks = []
        
        risk_patterns = {
            RequirementPattern.SECURITY_REQUIREMENT: "Security implementation requires careful review to avoid vulnerabilities",
            RequirementPattern.USER_AUTHENTICATION: "Authentication system must be thoroughly tested to prevent security breaches", 
            RequirementPattern.API_INTEGRATION: "Third-party API integration may have rate limits or availability issues",
            RequirementPattern.DATABASE_SCHEMA: "Database changes require careful migration planning to avoid data loss",
            RequirementPattern.PERFORMANCE_REQUIREMENT: "Performance targets may be difficult to achieve without architecture changes"
        }
        
        for pattern in patterns:
            if pattern in risk_patterns:
                risks.append(risk_patterns[pattern])
        
        # Text-based risk detection
        if 'external' in text or 'third-party' in text:
            risks.append("External dependency may introduce reliability risks")
        
        if 'migration' in text:
            risks.append("Data migration requires backup and rollback planning")
        
        if 'real-time' in text or 'live' in text:
            risks.append("Real-time requirements may need specialized infrastructure")
        
        return risks
    
    def _infer_dependencies(self, patterns: List[RequirementPattern], text: str) -> List[str]:
        """Infer dependencies on other requirements"""
        dependencies = []
        
        # Pattern-based dependencies
        dependency_patterns = {
            RequirementPattern.UI_COMPONENT: [RequirementPattern.API_INTEGRATION, RequirementPattern.DATABASE_SCHEMA],
            RequirementPattern.API_INTEGRATION: [RequirementPattern.DATABASE_SCHEMA],
            RequirementPattern.TESTING_REQUIREMENT: "depends_on_implementation",
            RequirementPattern.DEPLOYMENT: "depends_on_implementation"
        }
        
        for pattern in patterns:
            if pattern in dependency_patterns:
                dep = dependency_patterns[pattern]
                if isinstance(dep, list):
                    dependencies.extend([p.value for p in dep])
                else:
                    dependencies.append(dep)
        
        return dependencies
    
    def _detect_cross_dependencies(self, analysis1: AnalyzedRequirement, analysis2: AnalyzedRequirement) -> List[str]:
        """Detect dependencies between two analyzed requirements"""
        cross_deps = []
        
        # If one is testing and other is implementation, testing depends on implementation
        if (RequirementPattern.TESTING_REQUIREMENT in analysis1.detected_patterns and
            RequirementPattern.TESTING_REQUIREMENT not in analysis2.detected_patterns):
            cross_deps.append(analysis2.original_requirement.id)
        
        # If one is UI and other is API, UI depends on API
        if (RequirementPattern.UI_COMPONENT in analysis1.detected_patterns and
            RequirementPattern.API_INTEGRATION in analysis2.detected_patterns):
            cross_deps.append(analysis2.original_requirement.id)
        
        return cross_deps
    
    def _identify_technical_considerations(self, patterns: List[RequirementPattern], text: str) -> List[str]:
        """Identify technical considerations and constraints"""
        considerations = []
        
        tech_considerations = {
            RequirementPattern.SECURITY_REQUIREMENT: [
                "Follow OWASP security guidelines",
                "Implement proper input validation", 
                "Use secure encryption for sensitive data"
            ],
            RequirementPattern.PERFORMANCE_REQUIREMENT: [
                "Consider caching strategies",
                "Database query optimization may be needed",
                "Load testing required to validate performance"
            ],
            RequirementPattern.API_INTEGRATION: [
                "API documentation review required",
                "Error handling for network failures",
                "Rate limiting considerations"
            ],
            RequirementPattern.DATABASE_SCHEMA: [
                "Database migration strategy needed",
                "Consider indexing for query performance",
                "Backup strategy before schema changes"
            ]
        }
        
        for pattern in patterns:
            if pattern in tech_considerations:
                considerations.extend(tech_considerations[pattern])
        
        return considerations
    
    def generate_planning_insights(self, analyzed_requirements: List[AnalyzedRequirement]) -> Dict[str, Any]:
        """
        Generate high-level insights for the entire planning request.
        
        Args:
            analyzed_requirements: List of analyzed requirements
            
        Returns:
            Dictionary with planning insights and recommendations
        """
        insights = {
            'total_requirements': len(analyzed_requirements),
            'total_estimated_hours': sum(ar.estimated_effort_hours for ar in analyzed_requirements),
            'pattern_distribution': {},
            'agent_recommendations': {},
            'risk_summary': [],
            'complexity_distribution': {},
            'suggested_phases': []
        }
        
        # Pattern distribution
        all_patterns = []
        for ar in analyzed_requirements:
            all_patterns.extend(ar.detected_patterns)
        
        for pattern in RequirementPattern:
            count = all_patterns.count(pattern)
            if count > 0:
                insights['pattern_distribution'][pattern.value] = count
        
        # Agent recommendations
        all_agents = []
        for ar in analyzed_requirements:
            all_agents.extend(ar.suggested_agents)
        
        for agent in set(all_agents):
            insights['agent_recommendations'][agent] = all_agents.count(agent)
        
        # Risk summary
        all_risks = []
        for ar in analyzed_requirements:
            all_risks.extend(ar.risk_factors)
        insights['risk_summary'] = list(set(all_risks))
        
        # Complexity distribution
        complexity_levels = ['low', 'medium', 'high']
        for level in complexity_levels:
            count = sum(1 for ar in analyzed_requirements 
                       if ar.complexity_indicators.get('keyword_complexity') == level)
            insights['complexity_distribution'][level] = count
        
        # Suggested phases based on patterns
        phase_patterns = {
            'planning': [RequirementPattern.DOCUMENTATION_REQUIREMENT],
            'architecture': [RequirementPattern.DATABASE_SCHEMA, RequirementPattern.SECURITY_REQUIREMENT],
            'implementation': [RequirementPattern.CRUD_OPERATIONS, RequirementPattern.UI_COMPONENT, RequirementPattern.API_INTEGRATION],
            'testing': [RequirementPattern.TESTING_REQUIREMENT],
            'deployment': [RequirementPattern.DEPLOYMENT, RequirementPattern.MONITORING]
        }
        
        for phase, patterns in phase_patterns.items():
            if any(pattern in all_patterns for pattern in patterns):
                insights['suggested_phases'].append(phase)
        
        return insights