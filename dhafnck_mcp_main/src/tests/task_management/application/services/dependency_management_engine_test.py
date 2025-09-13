"""Test suite for DependencyManagementEngine"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastmcp.task_management.application.services.dependency_management_engine import (
    DependencyManagementEngine, ContentAnalyzer, DependencyHint, DependencySuggestion,
    EnhancedDependencyRelationships, SuggestionType, SuggestionStatus
)
from fastmcp.task_management.application.dtos.task.dependency_info import (
    DependencyInfo, DependencyRelationships
)
from fastmcp.task_management.domain.value_objects.task_id import TaskId
from fastmcp.task_management.domain.exceptions.task_exceptions import TaskNotFoundError


class TestDependencyHint:
    """Test cases for DependencyHint"""
    
    def test_create_valid_dependency_hint(self):
        """Test creating a valid dependency hint"""
        hint = DependencyHint(
            task_id="task_123",
            suggested_dependency_id="task_456",
            confidence_score=0.85,
            suggestion_reason="Found 'requires' keyword near task reference",
            suggestion_type=SuggestionType.CONTENT,
            evidence={"keyword": "requires", "proximity": 50}
        )
        
        assert hint.task_id == "task_123"
        assert hint.suggested_dependency_id == "task_456"
        assert hint.confidence_score == 0.85
        assert hint.suggestion_type == SuggestionType.CONTENT
        assert hint.evidence["keyword"] == "requires"
    
    def test_invalid_confidence_score(self):
        """Test that invalid confidence scores raise ValueError"""
        with pytest.raises(ValueError) as exc_info:
            DependencyHint(
                task_id="task_123",
                suggested_dependency_id="task_456",
                confidence_score=1.5,  # Invalid: > 1.0
                suggestion_reason="Test",
                suggestion_type=SuggestionType.CONTENT
            )
        assert "Confidence score must be between 0 and 1" in str(exc_info.value)
        
        with pytest.raises(ValueError):
            DependencyHint(
                task_id="task_123",
                suggested_dependency_id="task_456",
                confidence_score=-0.1,  # Invalid: < 0.0
                suggestion_reason="Test",
                suggestion_type=SuggestionType.CONTENT
            )


class TestContentAnalyzer:
    """Test cases for ContentAnalyzer"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create mock task repository"""
        return Mock()
    
    @pytest.fixture
    def analyzer(self, mock_task_repository):
        """Create ContentAnalyzer instance"""
        return ContentAnalyzer(mock_task_repository)
    
    @pytest.fixture
    def sample_task(self):
        """Create a sample task for testing"""
        task = Mock()
        task.id = TaskId("task-001")
        task.title = "Implement Authentication"
        task.description = "This task requires the User Model to be completed first"
        task.details = "Must implement JWT tokens after database schema is ready"
        task.assignees = ["dev1", "dev2"]
        task.created_at = datetime.now(timezone.utc)
        return task
    
    @pytest.fixture
    def related_tasks(self):
        """Create related tasks for testing"""
        task1 = Mock()
        task1.id = TaskId("task-002")
        task1.title = "User Model"
        task1.description = "Create user database model"
        task1.details = ""
        task1.assignees = ["dev1"]
        task1.created_at = datetime.now(timezone.utc)
        
        task2 = Mock()
        task2.id = TaskId("task-003")
        task2.title = "Database Schema"
        task2.description = "Setup initial database schema"
        task2.details = ""
        task2.assignees = ["dev2", "dev3"]
        task2.created_at = datetime.now(timezone.utc)
        
        return [task1, task2]
    
    def test_analyze_task_content_keywords(self, analyzer, sample_task, related_tasks, mock_task_repository):
        """Test keyword-based dependency detection"""
        mock_task_repository.find_all.return_value = [sample_task] + related_tasks
        
        hints = analyzer.analyze_task_content(sample_task)
        
        # Should find dependency on User Model (mentioned with "requires" or "after")
        user_model_hints = [h for h in hints if h.suggested_dependency_id == "task-002"]
        assert len(user_model_hints) > 0
        assert user_model_hints[0].suggestion_type == SuggestionType.CONTENT
        # Should find either "requires" or "after" keyword
        reason_lower = user_model_hints[0].suggestion_reason.lower()
        assert "requires" in reason_lower or "after" in reason_lower
        assert user_model_hints[0].confidence_score > 0.3
        
        # Should find dependency on Database Schema (mentioned with "after")
        db_schema_hints = [h for h in hints if h.suggested_dependency_id == "task-003"]
        assert len(db_schema_hints) > 0
        assert db_schema_hints[0].suggestion_type == SuggestionType.CONTENT
        assert "after" in db_schema_hints[0].suggestion_reason.lower()
    
    def test_analyze_file_dependencies(self, analyzer, mock_task_repository):
        """Test file-based dependency detection"""
        task1 = Mock()
        task1.id = TaskId("task-101")
        task1.title = "Update User API"
        task1.description = "Modify src/api/users.py and src/models/user.py"
        task1.details = ""
        task1.assignees = []
        
        task2 = Mock()
        task2.id = TaskId("task-102")
        task2.title = "User Model Refactor"
        task2.description = "Refactor src/models/user.py for better performance"
        task2.details = ""
        task2.assignees = []
        
        mock_task_repository.find_all.return_value = [task1, task2]
        
        hints = analyzer.analyze_task_content(task1)
        
        # Should find dependency due to shared file reference
        file_hints = [h for h in hints if h.suggested_dependency_id == "task-102"]
        assert len(file_hints) > 0
        assert file_hints[0].suggestion_type == SuggestionType.CONTENT
        assert "file references" in file_hints[0].suggestion_reason
        assert "src/models/user.py" in str(file_hints[0].evidence["shared_files"])
    
    def test_analyze_agent_dependencies(self, analyzer, mock_task_repository):
        """Test agent-based dependency detection"""
        task1 = Mock()
        task1.id = TaskId("task-201")
        task1.title = "Frontend Feature"
        task1.description = "Build new UI component"
        task1.details = ""
        task1.assignees = ["dev1", "dev2"]
        task1.created_at = datetime.now(timezone.utc)
        
        task2 = Mock()
        task2.id = TaskId("task-202")
        task2.title = "Backend API"
        task2.description = "Create API endpoint"
        task2.details = ""
        task2.assignees = ["dev1", "dev3"]  # Shares dev1
        task2.created_at = datetime.now(timezone.utc) - timedelta(hours=1)  # Earlier task
        
        mock_task_repository.find_all.return_value = [task1, task2]
        
        hints = analyzer.analyze_task_content(task1)
        
        # Should find dependency due to shared agent
        agent_hints = [h for h in hints if h.suggested_dependency_id == "task-202"]
        assert len(agent_hints) > 0
        assert agent_hints[0].suggestion_type == SuggestionType.RESOURCE
        assert "dev1" in agent_hints[0].suggestion_reason
        assert agent_hints[0].confidence_score > 0.3
    
    def test_extract_text_content(self, analyzer, sample_task):
        """Test text content extraction"""
        content = analyzer._extract_text_content(sample_task)
        
        assert "implement authentication" in content
        assert "requires the user model" in content
        assert "jwt tokens after database schema" in content
    
    def test_analyze_task_content_error_handling(self, analyzer, sample_task, mock_task_repository):
        """Test error handling in content analysis"""
        mock_task_repository.find_all.side_effect = Exception("Database error")
        
        hints = analyzer.analyze_task_content(sample_task)
        
        # Should return empty list on error
        assert hints == []


class TestDependencyManagementEngine:
    """Test cases for DependencyManagementEngine"""
    
    @pytest.fixture
    def mock_dependency_resolver(self):
        """Create mock dependency resolver"""
        resolver = Mock()
        resolver.with_user = Mock(return_value=resolver)
        resolver.resolve_dependencies = Mock(return_value=DependencyRelationships(
            task_id="test_task",
            depends_on=[],
            blocks=[],
            upstream_chains=[],
            downstream_chains=[],
            total_dependencies=0,
            completed_dependencies=0,
            blocked_dependencies=0,
            can_start=True,
            is_blocked=False,
            is_blocking_others=False,
            dependency_summary="No dependencies",
            next_actions=[],
            blocking_reasons=[]
        ))
        return resolver
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create mock task repository"""
        return Mock()
    
    @pytest.fixture
    def engine(self, mock_dependency_resolver, mock_task_repository):
        """Create DependencyManagementEngine instance"""
        return DependencyManagementEngine(
            mock_dependency_resolver,
            mock_task_repository,
            user_id="test_user"
        )
    
    def test_with_user(self, engine):
        """Test creating user-scoped engine instance"""
        user_engine = engine.with_user("user_123")
        
        assert isinstance(user_engine, DependencyManagementEngine)
        assert user_engine.user_id == "user_123"
        assert engine.dependency_resolver.with_user.called
    
    @pytest.mark.asyncio
    async def test_resolve_dependencies_with_ai_success(self, engine, mock_dependency_resolver):
        """Test successful AI-enhanced dependency resolution"""
        # Setup mocks
        mock_task = Mock()
        mock_task.id = TaskId("task-123")
        mock_task.title = "Test Task"
        mock_task.description = "Test description"
        mock_task.details = ""
        mock_task.assignees = []
        
        engine.task_repository.find_by_id.return_value = mock_task
        engine.task_repository.find_all.return_value = [mock_task]
        
        result = await engine.resolve_dependencies_with_ai("task-123")
        
        assert isinstance(result, EnhancedDependencyRelationships)
        assert result.basic_relationships is not None
        assert isinstance(result.ai_suggestions, list)
        assert result.optimization_score >= 0.0
        assert "analysis_time" in result.performance_metrics
    
    @pytest.mark.asyncio
    async def test_resolve_dependencies_with_ai_error_fallback(self, engine, mock_dependency_resolver):
        """Test fallback to basic resolution on AI error"""
        engine.task_repository.find_by_id.side_effect = Exception("Task not found")
        
        result = await engine.resolve_dependencies_with_ai("task-123")
        
        assert isinstance(result, EnhancedDependencyRelationships)
        assert result.basic_relationships is not None
        assert result.ai_suggestions == []
        assert "No AI suggestions available" in result.suggestion_summary
        # Performance metrics should still be present even on error
        assert "analysis_time" in result.performance_metrics
    
    def test_suggest_dependencies_success(self, engine):
        """Test successful dependency suggestion generation"""
        # Setup task
        task = Mock()
        task.id = TaskId("task-123")
        task.title = "Implement Feature"
        task.description = "This depends on the API task"
        task.details = ""
        task.assignees = ["dev1"]
        
        # Setup dependency task
        dep_task = Mock()
        dep_task.id = TaskId("task-456")
        dep_task.title = "API Task"
        dep_task.description = "Create API endpoint"
        dep_task.details = ""
        dep_task.assignees = ["dev2"]
        dep_task.status = Mock(value="in_progress")
        dep_task.priority = Mock(value="high")
        dep_task.overall_progress = 50
        dep_task.estimated_effort = "4h"
        dep_task.updated_at = datetime.now(timezone.utc)
        
        engine.task_repository.find_by_id.side_effect = lambda tid: task if str(tid) == "task-123" else dep_task
        engine.task_repository.find_all.return_value = [task, dep_task]
        
        suggestions = engine.suggest_dependencies("task-123")
        
        assert len(suggestions) > 0
        assert isinstance(suggestions[0], DependencySuggestion)
        assert suggestions[0].target_task_info is not None
        assert suggestions[0].target_task_info.task_id == "task-456"
    
    def test_suggest_dependencies_task_not_found(self, engine):
        """Test dependency suggestions when task not found"""
        engine.task_repository.find_by_id.return_value = None
        
        suggestions = engine.suggest_dependencies("nonexistent_task")
        
        assert suggestions == []
    
    def test_calculate_optimization_score(self, engine):
        """Test optimization score calculation"""
        basic_relationships = DependencyRelationships(
            task_id="test_task",
            depends_on=[DependencyInfo("dep1", "Dep 1", "completed", "high", 100, False, False, None, [], None)],
            blocks=[],
            upstream_chains=[],
            downstream_chains=[],
            total_dependencies=1,
            completed_dependencies=1,
            blocked_dependencies=0,
            can_start=True,
            is_blocked=False,
            is_blocking_others=False,
            dependency_summary="1 dependency completed",
            next_actions=[],
            blocking_reasons=[]
        )
        
        suggestions = [
            DependencySuggestion(
                hint=DependencyHint("task1", "dep2", 0.9, "High confidence", SuggestionType.CONTENT)
            ),
            DependencySuggestion(
                hint=DependencyHint("task1", "dep3", 0.8, "High confidence", SuggestionType.CONTENT)
            ),
            DependencySuggestion(
                hint=DependencyHint("task1", "dep4", 0.3, "Low confidence", SuggestionType.CONTENT)
            )
        ]
        
        score = engine._calculate_optimization_score(basic_relationships, suggestions)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be relatively high due to high confidence suggestions
    
    def test_generate_suggestion_summary(self, engine):
        """Test suggestion summary generation"""
        # High confidence suggestions
        suggestions = [
            DependencySuggestion(hint=DependencyHint("t1", "d1", 0.9, "Test", SuggestionType.CONTENT)),
            DependencySuggestion(hint=DependencyHint("t1", "d2", 0.8, "Test", SuggestionType.CONTENT)),
            DependencySuggestion(hint=DependencyHint("t1", "d3", 0.5, "Test", SuggestionType.CONTENT))
        ]
        
        summary = engine._generate_suggestion_summary(suggestions)
        
        assert "3 AI suggestions" in summary
        assert "2 high-confidence" in summary
        assert "1 medium-confidence" in summary
        
        # No suggestions
        empty_summary = engine._generate_suggestion_summary([])
        assert empty_summary == "No AI suggestions available"
    
    def test_performance_metrics(self, engine):
        """Test performance metrics tracking"""
        initial_metrics = engine.get_performance_metrics()
        
        assert initial_metrics["analysis_time"] == 0.0
        assert initial_metrics["suggestions_generated"] == 0
        assert initial_metrics["suggestions_accepted"] == 0
        
        # Modify metrics
        engine.performance_metrics["suggestions_generated"] = 5
        
        updated_metrics = engine.get_performance_metrics()
        assert updated_metrics["suggestions_generated"] == 5
        
        # Reset metrics
        engine.reset_performance_metrics()
        reset_metrics = engine.get_performance_metrics()
        assert reset_metrics["suggestions_generated"] == 0


