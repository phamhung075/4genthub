"""Test suite for PatternRecognitionEngine"""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from fastmcp.task_management.domain.services.intelligence.pattern_recognition_engine import (
    PatternRecognitionEngine, PatternLearner, FeatureExtractor, 
    TaskVector, DependencyPattern, PatternPrediction, PatternType
)


class TestTaskVector:
    """Test cases for TaskVector dataclass"""
    
    def test_create_task_vector(self):
        """Test creating a task vector"""
        vector = TaskVector(
            task_id="task_123",
            title_tokens=["implement", "authentication"],
            description_tokens=["create", "jwt", "token", "validation"],
            agents=["auth-agent", "security-agent"],
            priority="high",
            estimated_effort="8h",
            file_references=["src/auth.py", "src/jwt.py"],
            technical_entities=["AuthService", "TokenValidator"],
            creation_time=datetime.now(timezone.utc),
            completion_time=None
        )
        
        assert vector.task_id == "task_123"
        assert len(vector.title_tokens) == 2
        assert "jwt" in vector.description_tokens
        assert len(vector.agents) == 2
        assert vector.priority == "high"
        assert len(vector.file_references) == 2
        assert "AuthService" in vector.technical_entities


class TestFeatureExtractor:
    """Test cases for FeatureExtractor"""
    
    @pytest.fixture
    def extractor(self):
        """Create FeatureExtractor instance"""
        return FeatureExtractor()
    
    @pytest.fixture
    def mock_task(self):
        """Create a mock task for testing"""
        task = Mock()
        task.id = "task_001"
        task.title = "Implement User Authentication Service"
        task.description = "Create AuthService class to handle JWT token validation"
        task.details = "Must implement POST /api/auth endpoint and connect to users table"
        task.assignees = ["dev1", "dev2"]
        task.priority = Mock(value="high")
        task.estimated_effort = "12h"
        task.created_at = datetime.now(timezone.utc)
        return task
    
    def test_extract_task_vector(self, extractor, mock_task):
        """Test extracting task vector from a task"""
        vector = extractor.extract_task_vector(mock_task)
        
        assert vector.task_id == "task_001"
        assert "implement" in vector.title_tokens
        assert "user" in vector.title_tokens
        assert "authentication" in vector.title_tokens
        assert "service" in vector.title_tokens
        
        assert "authservice" in vector.description_tokens
        assert "jwt" in vector.description_tokens
        assert "token" in vector.description_tokens
        
        assert vector.agents == ["dev1", "dev2"]
        assert vector.priority == "high"
        assert vector.estimated_effort == "12h"
        
        # Check entities and files
        assert any("AuthService" in e for e in vector.technical_entities)
        assert any("/api/auth" in e for e in vector.technical_entities)
    
    def test_tokenize_text(self, extractor):
        """Test text tokenization"""
        text = "Implement the User Authentication Service for JWT tokens"
        tokens = extractor._tokenize_text(text)
        
        assert "implement" in tokens
        assert "user" in tokens
        assert "authentication" in tokens
        assert "service" in tokens
        assert "jwt" in tokens
        assert "tokens" in tokens
        
        # Stop words should be filtered out
        assert "the" not in tokens
        assert "for" not in tokens
        
        # Short tokens should be filtered out
        assert all(len(token) > 2 for token in tokens)
    
    def test_extract_file_references(self, extractor):
        """Test file reference extraction"""
        text = """
        Update src/auth/login.py and config/auth.yaml files.
        Also modify tests/auth_test.py and docs/auth.md
        """
        
        files = extractor._extract_file_references(text)
        
        assert "src/auth/login.py" in files
        assert "config/auth.yaml" in files
        assert "tests/auth_test.py" in files
        assert "docs/auth.md" in files
        assert len(files) >= 4
    
    def test_extract_technical_entities(self, extractor):
        """Test technical entity extraction"""
        text = """
        Create UserService class and AuthController.
        Implement POST /api/users and GET /api/users/{id} endpoints.
        Create table users_auth in the database.
        """
        
        entities = extractor._extract_technical_entities(text)
        
        # Should find service and controller
        assert any("UserService" in e for e in entities)
        assert any("AuthController" in e for e in entities)
        
        # Should find API endpoints
        assert any("POST /api/users" in e for e in entities)
        assert any("GET /api/users/{id}" in e for e in entities)
        
        # Should find database objects
        assert any("users_auth" in e for e in entities)
    
    def test_extract_task_vector_error_handling(self, extractor):
        """Test error handling in task vector extraction"""
        # Task with missing attributes
        bad_task = Mock()
        bad_task.id = "bad_task"
        bad_task.title = None
        bad_task.description = None
        bad_task.created_at = datetime.now(timezone.utc)
        
        # Should return minimal vector without crashing
        vector = extractor.extract_task_vector(bad_task)
        
        assert vector.task_id == "bad_task"
        assert vector.title_tokens == []
        assert vector.description_tokens == []
        assert vector.priority == "medium"


class TestPatternLearner:
    """Test cases for PatternLearner"""
    
    @pytest.fixture
    def learner(self):
        """Create PatternLearner instance"""
        return PatternLearner()
    
    @pytest.fixture
    def sample_project_data(self):
        """Create sample project data for testing"""
        return [
            {
                'id': 'proj_1',
                'domain': 'authentication',
                'tasks': [
                    {
                        'id': 'task_1',
                        'title': 'Create User Model',
                        'description': 'Database model for users',
                        'assignees': ['dev1'],
                        'priority': 'high',
                        'dependencies': [],
                        'created_at': datetime.now(timezone.utc) - timedelta(days=5)
                    },
                    {
                        'id': 'task_2',
                        'title': 'Implement Auth Service',
                        'description': 'Service for user authentication',
                        'assignees': ['dev1', 'dev2'],
                        'priority': 'high',
                        'dependencies': ['task_1'],  # Depends on User Model
                        'created_at': datetime.now(timezone.utc) - timedelta(days=3)
                    },
                    {
                        'id': 'task_3',
                        'title': 'Create Login API',
                        'description': 'POST /api/login endpoint',
                        'assignees': ['dev2'],
                        'priority': 'medium',
                        'dependencies': ['task_2'],  # Depends on Auth Service
                        'created_at': datetime.now(timezone.utc) - timedelta(days=1)
                    }
                ]
            }
        ]
    
    def test_learn_from_project_history(self, learner, sample_project_data):
        """Test learning patterns from project history"""
        patterns = learner.learn_from_project_history(sample_project_data)
        
        assert len(patterns) > 0
        
        # Check pattern properties
        for pattern in patterns:
            assert isinstance(pattern, DependencyPattern)
            assert pattern.pattern_id.startswith("pattern_")
            assert pattern.pattern_type in PatternType
            assert 0 <= pattern.confidence <= 1
            assert pattern.support_count == 1
            assert pattern.success_rate == 1.0
    
    def test_analyze_project_patterns(self, learner, sample_project_data):
        """Test analyzing patterns within a project"""
        project = sample_project_data[0]
        patterns = learner._analyze_project_patterns(project)
        
        # Should find 2 dependencies: task_2 -> task_1, task_3 -> task_2
        assert len(patterns) == 2
        
        # Check pattern metadata
        for pattern in patterns:
            assert 'project_id' in pattern.metadata
            assert pattern.metadata['project_id'] == 'proj_1'
            assert 'source_task_id' in pattern.metadata
            assert 'target_task_id' in pattern.metadata
    
    def test_identify_pattern_type(self, learner):
        """Test pattern type identification"""
        # Create mock vectors
        source = TaskVector(
            task_id="task_new",
            title_tokens=["implement", "feature"],
            description_tokens=[],
            agents=["dev1"],
            priority="medium",
            estimated_effort="4h",
            file_references=[],
            technical_entities=[],
            creation_time=datetime.now(timezone.utc)
        )
        
        target = TaskVector(
            task_id="task_old",
            title_tokens=["create", "model"],
            description_tokens=[],
            agents=["dev1"],  # Same agent
            priority="high",
            estimated_effort="2h",
            file_references=[],
            technical_entities=[],
            creation_time=datetime.now(timezone.utc) - timedelta(days=2)  # Earlier
        )
        
        pattern_type = learner._identify_pattern_type(source, target, {}, [])
        
        # Should identify as sequential (source created after target)
        assert pattern_type == PatternType.SEQUENTIAL
        
        # Test agent-based pattern
        source.agents = ["dev1", "dev2"]
        target.agents = ["dev2", "dev3"]  # Overlapping agents
        
        pattern_type = learner._identify_pattern_type(source, target, {}, [])
        assert pattern_type == PatternType.AGENT_BASED
    
    def test_extract_pattern_features(self, learner):
        """Test pattern feature extraction"""
        vector = TaskVector(
            task_id="task_123",
            title_tokens=["implement", "user", "authentication", "service"],
            description_tokens=["create", "jwt", "token", "validation", "secure", "api"],
            agents=["auth-dev", "security-dev"],
            priority="high",
            estimated_effort="16h",
            file_references=["src/auth.py", "src/jwt.py", "config/auth.yaml"],
            technical_entities=["AuthService", "TokenValidator", "UserModel"],
            creation_time=datetime.now(timezone.utc)
        )
        
        features = learner._extract_pattern_features(vector)
        
        assert 'title_keywords' in features
        assert 'implement' in features['title_keywords'] or 'user' in features['title_keywords']
        
        assert 'description_keywords' in features
        assert len(features['description_keywords']) > 0
        
        assert features['agents'] == ["auth-dev", "security-dev"]
        assert features['priority'] == "high"
        assert features['has_files'] is True
        assert 'py' in features['file_types']
        assert 'yaml' in features['file_types']
        assert features['has_entities'] is True
        assert 'service' in features['entity_types']
        assert 'model' in features['entity_types']
    
    def test_calculate_pattern_confidence(self, learner):
        """Test pattern confidence calculation"""
        # Similar features should have high confidence
        source_features = {
            'title_keywords': ['implement', 'user', 'auth'],
            'description_keywords': ['jwt', 'token', 'secure'],
            'agents': ['dev1', 'dev2'],
            'priority': 'high',
            'file_types': ['py', 'yaml'],
            'entity_types': ['service', 'model']
        }
        
        target_features = {
            'title_keywords': ['create', 'user', 'model'],
            'description_keywords': ['database', 'table', 'schema'],
            'agents': ['dev1'],  # Overlapping agent
            'priority': 'high',  # Same priority
            'file_types': ['py', 'sql'],  # Overlapping file type
            'entity_types': ['model', 'database']  # Overlapping entity type
        }
        
        confidence = learner._calculate_pattern_confidence(source_features, target_features)
        
        assert 0 < confidence < 1
        assert confidence > 0.3  # Should have reasonable confidence due to overlaps


class TestPatternRecognitionEngine:
    """Test cases for PatternRecognitionEngine"""
    
    @pytest.fixture
    def engine(self):
        """Create PatternRecognitionEngine instance"""
        return PatternRecognitionEngine()
    
    @pytest.fixture
    def training_data(self):
        """Create training data for the engine"""
        return [
            {
                'id': 'proj_1',
                'tasks': [
                    {
                        'id': '1',
                        'title': 'Database Schema',
                        'description': 'Create user table',
                        'assignees': ['db-dev'],
                        'priority': 'high',
                        'dependencies': [],
                        'created_at': datetime.now(timezone.utc) - timedelta(days=10)
                    },
                    {
                        'id': '2',
                        'title': 'User Model',
                        'description': 'ORM model for users',
                        'assignees': ['backend-dev'],
                        'priority': 'high',
                        'dependencies': ['1'],
                        'created_at': datetime.now(timezone.utc) - timedelta(days=8)
                    },
                    {
                        'id': '3',
                        'title': 'User API',
                        'description': 'REST API for users',
                        'assignees': ['backend-dev'],
                        'priority': 'medium',
                        'dependencies': ['2'],
                        'created_at': datetime.now(timezone.utc) - timedelta(days=5)
                    }
                ]
            }
        ]
    
    def test_train_from_historical_data(self, engine, training_data):
        """Test training the engine from historical data"""
        summary = engine.train_from_historical_data(training_data)
        
        assert engine.trained is True
        assert summary['total_projects'] == 1
        assert summary['patterns_learned'] > 0
        assert 'pattern_types' in summary
        assert 'average_confidence' in summary
        assert summary['average_confidence'] > 0
        assert 'training_completed_at' in summary
    
    def test_predict_dependencies_untrained(self, engine):
        """Test prediction with untrained engine"""
        task = Mock(id="new_task")
        available_tasks = [Mock(id="task_1"), Mock(id="task_2")]
        
        predictions = engine.predict_dependencies(task, available_tasks)
        
        assert predictions == []  # Should return empty list when not trained
    
    def test_predict_dependencies_trained(self, engine, training_data):
        """Test dependency prediction with trained engine"""
        # Train the engine first
        engine.train_from_historical_data(training_data)
        
        # Create a new task similar to training data
        new_task = Mock()
        new_task.id = "new_api_task"
        new_task.title = "Create Product API"
        new_task.description = "REST API for products"
        new_task.details = ""
        new_task.assignees = ["backend-dev"]
        new_task.priority = Mock(value="medium")
        new_task.estimated_effort = "8h"
        new_task.created_at = datetime.now(timezone.utc)
        
        # Available tasks that could be dependencies
        model_task = Mock()
        model_task.id = "product_model"
        model_task.title = "Product Model"
        model_task.description = "ORM model for products"
        model_task.details = ""
        model_task.assignees = ["backend-dev"]
        model_task.priority = Mock(value="high")
        model_task.estimated_effort = "4h"
        model_task.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        
        unrelated_task = Mock()
        unrelated_task.id = "ui_task"
        unrelated_task.title = "Build UI Component"
        unrelated_task.description = "Frontend component"
        unrelated_task.details = ""
        unrelated_task.assignees = ["frontend-dev"]
        unrelated_task.priority = Mock(value="low")
        unrelated_task.estimated_effort = "2h"
        unrelated_task.created_at = datetime.now(timezone.utc)
        
        predictions = engine.predict_dependencies(new_task, [model_task, unrelated_task])
        
        # Should predict dependency on model task (similar to training pattern)
        assert len(predictions) > 0
        assert predictions[0].source_task_id == "new_api_task"
        assert predictions[0].target_task_id == "product_model"
        assert predictions[0].confidence > 0
        assert len(predictions[0].pattern_ids) > 0
        assert predictions[0].reasoning != ""
    
    def test_find_matching_patterns(self, engine):
        """Test finding matching patterns"""
        # Add a test pattern to the engine
        pattern = DependencyPattern(
            pattern_id="test_pattern",
            pattern_type=PatternType.SEQUENTIAL,
            source_features={
                'title_keywords': ['api', 'rest'],
                'agents': ['backend-dev'],
                'priority': 'medium'
            },
            target_features={
                'title_keywords': ['model', 'orm'],
                'agents': ['backend-dev'],
                'priority': 'high'
            },
            confidence=0.8,
            support_count=5,
            success_rate=0.9,
            created_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc)
        )
        engine.patterns['test_pattern'] = pattern
        
        # Test features that should match
        source_features = {
            'title_keywords': ['create', 'api', 'endpoint'],
            'agents': ['backend-dev'],
            'priority': 'medium'
        }
        
        target_features = {
            'title_keywords': ['database', 'model'],
            'agents': ['backend-dev'],
            'priority': 'high'
        }
        
        matching = engine._find_matching_patterns(source_features, target_features)
        
        assert len(matching) > 0
        assert matching[0].pattern_id == "test_pattern"
    
    def test_match_features(self, engine):
        """Test feature matching logic"""
        features1 = {
            'title_keywords': ['user', 'auth', 'service'],
            'agents': ['dev1', 'dev2'],
            'priority': 'high',
            'file_types': ['py', 'yaml'],
            'entity_types': ['service', 'model']
        }
        
        features2 = {
            'title_keywords': ['user', 'model', 'database'],
            'agents': ['dev1'],
            'priority': 'high',
            'file_types': ['py', 'sql'],
            'entity_types': ['model']
        }
        
        similarity = engine._match_features(features1, features2)
        
        assert 0 <= similarity <= 1
        assert similarity > 0  # Should have some similarity due to overlaps
    
    def test_create_prediction(self, engine):
        """Test creating a prediction from patterns"""
        patterns = [
            DependencyPattern(
                pattern_id="p1",
                pattern_type=PatternType.SEQUENTIAL,
                source_features={},
                target_features={},
                confidence=0.8,
                support_count=10,
                success_rate=0.9,
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                metadata={'current_match_score': 0.85}
            ),
            DependencyPattern(
                pattern_id="p2",
                pattern_type=PatternType.AGENT_BASED,
                source_features={},
                target_features={},
                confidence=0.7,
                support_count=5,
                success_rate=0.8,
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                metadata={'current_match_score': 0.75}
            )
        ]
        
        prediction = engine._create_prediction("task_1", "task_2", patterns)
        
        assert prediction.source_task_id == "task_1"
        assert prediction.target_task_id == "task_2"
        assert len(prediction.pattern_ids) == 2
        assert prediction.confidence > 0
        assert "sequential" in prediction.reasoning
        assert len(prediction.features_matched) > 0
    
    def test_get_engine_stats(self, engine, training_data):
        """Test getting engine statistics"""
        # Stats before training
        stats = engine.get_engine_stats()
        assert stats['status'] == 'not_trained'
        assert stats['patterns'] == 0
        
        # Train the engine
        engine.train_from_historical_data(training_data)
        
        # Stats after training
        stats = engine.get_engine_stats()
        assert stats['status'] == 'trained'
        assert stats['total_patterns'] > 0
        assert 'pattern_types' in stats
        assert stats['average_confidence'] > 0
        assert stats['average_support'] > 0
        assert stats['last_updated'] is not None