"""Test suite for RequirementAnalyzer domain service"""

import pytest
from fastmcp.ai_task_planning.domain.services.requirement_analyzer import (
    RequirementAnalyzer, RequirementPattern, AnalyzedRequirement
)
from fastmcp.ai_task_planning.domain.entities.planning_request import RequirementItem, ComplexityLevel


class TestRequirementAnalyzer:
    """Test cases for RequirementAnalyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create a RequirementAnalyzer instance"""
        return RequirementAnalyzer()
    
    def test_detect_crud_pattern(self, analyzer):
        """Test detection of CRUD operations pattern"""
        requirement = RequirementItem(
            id="req_1",
            description="Create user management interface with ability to add, edit and delete users",
            priority="high"
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        assert RequirementPattern.CRUD_OPERATIONS in result.detected_patterns
        assert 'coding-agent' in result.suggested_agents
        assert result.estimated_effort_hours > 0
    
    def test_detect_authentication_pattern(self, analyzer):
        """Test detection of authentication pattern"""
        requirement = RequirementItem(
            id="req_2",
            description="Implement JWT-based login system with secure password storage",
            acceptance_criteria=[
                "User can login with email/password",
                "JWT tokens expire after 1 hour",
                "Passwords are hashed with bcrypt"
            ]
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        assert RequirementPattern.USER_AUTHENTICATION in result.detected_patterns
        assert 'coding-agent' in result.suggested_agents
        assert 'security-auditor-agent' in result.suggested_agents
        assert any("security" in risk.lower() for risk in result.risk_factors)
    
    def test_detect_multiple_patterns(self, analyzer):
        """Test detection of multiple patterns in single requirement"""
        requirement = RequirementItem(
            id="req_3",
            description="Create API endpoints for user authentication with comprehensive test coverage",
            acceptance_criteria=[
                "REST API with login/logout endpoints",
                "Unit tests with 90% coverage",
                "Integration tests for auth flow"
            ]
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        detected_pattern_types = set(result.detected_patterns)
        assert RequirementPattern.API_INTEGRATION in detected_pattern_types
        assert RequirementPattern.USER_AUTHENTICATION in detected_pattern_types
        assert RequirementPattern.TESTING_REQUIREMENT in detected_pattern_types
        assert 'test-orchestrator-agent' in result.suggested_agents
    
    def test_complexity_analysis(self, analyzer):
        """Test complexity analysis based on various indicators"""
        # Simple requirement
        simple_req = RequirementItem(
            id="req_simple",
            description="Add a simple button to the homepage"
        )
        
        # Complex requirement
        complex_req = RequirementItem(
            id="req_complex",
            description="Build complex distributed system with advanced caching and scalable architecture",
            acceptance_criteria=[
                "Support 1M concurrent users",
                "Sub-100ms response time",
                "99.99% uptime",
                "Auto-scaling capabilities",
                "Multi-region deployment",
                "Real-time data synchronization"
            ],
            constraints=[
                "Must use microservices",
                "Kubernetes deployment required",
                "Zero downtime deployments"
            ]
        )
        
        simple_result = analyzer.analyze_requirement(simple_req)
        complex_result = analyzer.analyze_requirement(complex_req)
        
        assert simple_result.complexity_indicators['keyword_complexity'] == 'low'
        assert complex_result.complexity_indicators['keyword_complexity'] == 'high'
        assert complex_result.estimated_effort_hours > simple_result.estimated_effort_hours
        assert complex_result.complexity_indicators['criteria_count'] == 6
        assert complex_result.complexity_indicators['constraints_count'] == 3
    
    def test_ui_component_pattern(self, analyzer):
        """Test detection of UI component patterns"""
        requirement = RequirementItem(
            id="req_4",
            description="Create React dashboard component with data visualization",
            acceptance_criteria=[
                "Interactive charts and graphs",
                "Responsive design",
                "Real-time data updates"
            ]
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        assert RequirementPattern.UI_COMPONENT in result.detected_patterns
        assert 'ui-specialist-agent' in result.suggested_agents
        assert 'design-system-agent' in result.suggested_agents
    
    def test_database_schema_pattern(self, analyzer):
        """Test detection of database schema patterns"""
        requirement = RequirementItem(
            id="req_5",
            description="Design database schema for user profiles with proper indexes and foreign keys",
            acceptance_criteria=[
                "User table with profile fields",
                "Proper indexing for performance",
                "Foreign key relationships"
            ]
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        assert RequirementPattern.DATABASE_SCHEMA in result.detected_patterns
        assert 'system-architect-agent' in result.suggested_agents
        assert any("migration" in risk.lower() for risk in result.risk_factors)
        assert any("backup" in consideration.lower() for consideration in result.technical_considerations)
    
    def test_performance_requirement_pattern(self, analyzer):
        """Test detection of performance requirements"""
        requirement = RequirementItem(
            id="req_6",
            description="Optimize API response time and implement caching for better performance",
            constraints=["Response time must be under 200ms", "Support 10K requests per second"]
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        assert RequirementPattern.PERFORMANCE_REQUIREMENT in result.detected_patterns
        assert 'performance-load-tester-agent' in result.suggested_agents
        assert 'efficiency-optimization-agent' in result.suggested_agents
        assert any("caching" in consideration.lower() for consideration in result.technical_considerations)
    
    def test_security_requirement_pattern(self, analyzer):
        """Test detection of security requirements"""
        requirement = RequirementItem(
            id="req_7",
            description="Implement secure data encryption and GDPR compliance measures",
            acceptance_criteria=[
                "All sensitive data encrypted at rest",
                "HTTPS enforcement",
                "GDPR data deletion capabilities"
            ]
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        assert RequirementPattern.SECURITY_REQUIREMENT in result.detected_patterns
        assert 'security-auditor-agent' in result.suggested_agents
        assert any("owasp" in consideration.lower() for consideration in result.technical_considerations)
        assert any("security" in risk.lower() for risk in result.risk_factors)
    
    def test_bug_fix_pattern(self, analyzer):
        """Test detection of bug fix patterns"""
        requirement = RequirementItem(
            id="req_8",
            description="Fix login error causing application crash when password contains special characters"
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        assert RequirementPattern.BUG_FIX in result.detected_patterns
        assert 'debugger-agent' in result.suggested_agents
        assert 'root-cause-analysis-agent' in result.suggested_agents
    
    def test_deployment_pattern(self, analyzer):
        """Test detection of deployment patterns"""
        requirement = RequirementItem(
            id="req_9",
            description="Setup CI/CD pipeline with Docker and Kubernetes deployment to production",
            acceptance_criteria=[
                "Automated testing in pipeline",
                "Docker image building",
                "Kubernetes deployment configs"
            ]
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        assert RequirementPattern.DEPLOYMENT in result.detected_patterns
        assert 'devops-agent' in result.suggested_agents
    
    def test_risk_identification(self, analyzer):
        """Test risk identification based on patterns and keywords"""
        requirement = RequirementItem(
            id="req_10",
            description="Integrate with third-party payment API for real-time transaction processing",
            acceptance_criteria=[
                "Connect to external payment gateway",
                "Handle live transactions",
                "Support data migration from old system"
            ]
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        # Should identify multiple risks
        assert len(result.risk_factors) >= 3
        assert any("external" in risk.lower() for risk in result.risk_factors)
        assert any("real-time" in risk.lower() for risk in result.risk_factors)
        assert any("migration" in risk.lower() for risk in result.risk_factors)
    
    def test_dependency_inference(self, analyzer):
        """Test inference of dependencies between requirements"""
        requirement = RequirementItem(
            id="req_11",
            description="Create frontend UI component for displaying user data from API"
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        # UI components typically depend on API and database
        assert RequirementPattern.UI_COMPONENT in result.detected_patterns
        assert RequirementPattern.API_INTEGRATION.value in result.dependencies or 'api_integration' in result.dependencies
    
    def test_effort_estimation(self, analyzer):
        """Test effort estimation with different complexity levels"""
        # Test increasing complexity
        req1 = RequirementItem(
            id="req_e1",
            description="Add simple text label"
        )
        
        req2 = RequirementItem(
            id="req_e2",
            description="Create user interface with forms",
            acceptance_criteria=["Form validation", "Error handling"]
        )
        
        req3 = RequirementItem(
            id="req_e3",
            description="Build complex authentication system with advanced security",
            acceptance_criteria=[
                "Multi-factor authentication",
                "OAuth integration",
                "Session management",
                "Password policies",
                "Account lockout"
            ]
        )
        
        result1 = analyzer.analyze_requirement(req1)
        result2 = analyzer.analyze_requirement(req2)
        result3 = analyzer.analyze_requirement(req3)
        
        # Effort should increase with complexity
        assert result1.estimated_effort_hours < result2.estimated_effort_hours
        assert result2.estimated_effort_hours < result3.estimated_effort_hours
    
    def test_analyze_requirements_batch(self, analyzer):
        """Test batch analysis with cross-requirement dependencies"""
        requirements = [
            RequirementItem(
                id="req_b1",
                description="Create REST API endpoints for user management"
            ),
            RequirementItem(
                id="req_b2",
                description="Build frontend UI to consume user management API"
            ),
            RequirementItem(
                id="req_b3",
                description="Write comprehensive tests for user management features"
            )
        ]
        
        results = analyzer.analyze_requirements_batch(requirements)
        
        assert len(results) == 3
        
        # UI should depend on API
        ui_result = next(r for r in results if "req_b2" in r.original_requirement.id)
        assert any("req_b1" in dep for dep in ui_result.dependencies)
        
        # Tests should depend on implementation
        test_result = next(r for r in results if "req_b3" in r.original_requirement.id)
        assert len(test_result.dependencies) > 0
    
    def test_generate_planning_insights(self, analyzer):
        """Test generation of high-level planning insights"""
        requirements = [
            RequirementItem(
                id="req_i1",
                description="Design database schema for new features"
            ),
            RequirementItem(
                id="req_i2",
                description="Implement CRUD operations for user management"
            ),
            RequirementItem(
                id="req_i3",
                description="Create comprehensive test suite with high coverage"
            ),
            RequirementItem(
                id="req_i4",
                description="Setup deployment pipeline with Docker"
            )
        ]
        
        analyzed = analyzer.analyze_requirements_batch(requirements)
        insights = analyzer.generate_planning_insights(analyzed)
        
        assert insights['total_requirements'] == 4
        assert insights['total_estimated_hours'] > 0
        assert len(insights['pattern_distribution']) > 0
        assert len(insights['agent_recommendations']) > 0
        assert 'architecture' in insights['suggested_phases']
        assert 'implementation' in insights['suggested_phases']
        assert 'testing' in insights['suggested_phases']
        assert 'deployment' in insights['suggested_phases']
    
    def test_technical_considerations(self, analyzer):
        """Test identification of technical considerations"""
        requirement = RequirementItem(
            id="req_t1",
            description="Implement high-performance API with security measures and proper database design",
            acceptance_criteria=[
                "Response time under 100ms",
                "Secure authentication",
                "Optimized database queries"
            ]
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        # Should have considerations for performance, security, and database
        assert len(result.technical_considerations) > 0
        assert any("caching" in consideration.lower() for consideration in result.technical_considerations)
        assert any("owasp" in consideration.lower() or "security" in consideration.lower() 
                  for consideration in result.technical_considerations)
        assert any("index" in consideration.lower() or "query" in consideration.lower() 
                  for consideration in result.technical_considerations)
    
    def test_empty_requirement_handling(self, analyzer):
        """Test handling of minimal/empty requirements"""
        requirement = RequirementItem(
            id="req_empty",
            description="Fix bug"
        )
        
        result = analyzer.analyze_requirement(requirement)
        
        # Should still provide some analysis
        assert len(result.detected_patterns) > 0  # Should detect bug fix pattern
        assert len(result.suggested_agents) > 0
        assert result.estimated_effort_hours > 0
        assert RequirementPattern.BUG_FIX in result.detected_patterns