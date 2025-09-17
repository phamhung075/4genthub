"""Test suite for MLDependencyPredictor infrastructure service"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastmcp.task_management.infrastructure.ai_services.ml_dependency_predictor import (
    MLDependencyPredictor, MLModelPersistence, TrainingDataCollector
)
from fastmcp.task_management.domain.services.intelligence.pattern_recognition_engine import (
    DependencyPattern, PatternType, PatternPrediction
)


class TestMLModelPersistence:
    """Test cases for MLModelPersistence"""
    
    @pytest.fixture
    def temp_model_dir(self):
        """Create temporary directory for model storage"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def persistence(self, temp_model_dir):
        """Create MLModelPersistence instance with temp directory"""
        return MLModelPersistence(model_dir=temp_model_dir)
    
    @pytest.fixture
    def sample_patterns(self):
        """Create sample patterns for testing"""
        return {
            "pattern_1": DependencyPattern(
                pattern_id="pattern_1",
                pattern_type=PatternType.SEQUENTIAL,
                source_features={"title_keywords": ["api", "rest"]},
                target_features={"title_keywords": ["model", "database"]},
                confidence=0.85,
                support_count=10,
                success_rate=0.9,
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                metadata={"project_id": "proj_1"}
            ),
            "pattern_2": DependencyPattern(
                pattern_id="pattern_2",
                pattern_type=PatternType.AGENT_BASED,
                source_features={"agents": ["dev1", "dev2"]},
                target_features={"agents": ["dev1"]},
                confidence=0.75,
                support_count=5,
                success_rate=0.8,
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                metadata={"project_id": "proj_2"}
            )
        }
    
    def test_save_patterns(self, persistence, sample_patterns):
        """Test saving patterns to disk"""
        model_version = "test_v1"
        file_path = persistence.save_patterns(sample_patterns, model_version)
        
        assert file_path.endswith(f"patterns_{model_version}.json")
        assert Path(file_path).exists()
        
        # Check file content
        with open(file_path, 'r') as f:
            saved_data = json.load(f)
        
        assert len(saved_data) == 2
        assert "pattern_1" in saved_data
        assert saved_data["pattern_1"]["confidence"] == 0.85
        assert saved_data["pattern_1"]["pattern_type"] == "sequential"
        
        # Check metadata file
        metadata_file = Path(persistence.model_dir) / f"metadata_{model_version}.json"
        assert metadata_file.exists()
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        assert metadata["model_version"] == model_version
        assert metadata["pattern_count"] == 2
        assert "saved_at" in metadata
        assert "file_size" in metadata
    
    def test_load_patterns(self, persistence, sample_patterns):
        """Test loading patterns from disk"""
        model_version = "test_v2"
        persistence.save_patterns(sample_patterns, model_version)
        
        loaded_patterns = persistence.load_patterns(model_version)
        
        assert len(loaded_patterns) == 2
        assert "pattern_1" in loaded_patterns
        assert isinstance(loaded_patterns["pattern_1"], DependencyPattern)
        assert loaded_patterns["pattern_1"].confidence == 0.85
        assert loaded_patterns["pattern_1"].pattern_type == PatternType.SEQUENTIAL
        assert isinstance(loaded_patterns["pattern_1"].created_at, datetime)
    
    def test_load_nonexistent_patterns(self, persistence):
        """Test loading patterns that don't exist"""
        patterns = persistence.load_patterns("nonexistent_version")
        assert patterns == {}
    
    def test_get_available_versions(self, persistence, sample_patterns):
        """Test getting list of available model versions"""
        # Save multiple versions
        persistence.save_patterns(sample_patterns, "v1")
        persistence.save_patterns(sample_patterns, "v2")
        persistence.save_patterns(sample_patterns, "v3")
        
        versions = persistence.get_available_versions()
        
        assert len(versions) == 3
        assert "v1" in versions
        assert "v2" in versions
        assert "v3" in versions
        # Should be sorted in reverse order (most recent first)
        assert versions == ["v3", "v2", "v1"]
    
    def test_cleanup_old_versions(self, persistence, sample_patterns):
        """Test cleaning up old model versions"""
        # Save many versions
        for i in range(8):
            persistence.save_patterns(sample_patterns, f"v{i}")
        
        # Should have 8 versions
        assert len(persistence.get_available_versions()) == 8
        
        # Clean up, keeping only 5
        persistence.cleanup_old_versions(keep_versions=5)
        
        # Should have only 5 versions left
        versions = persistence.get_available_versions()
        assert len(versions) == 5
        
        # Should keep the most recent ones
        assert "v7" in versions
        assert "v6" in versions
        assert "v5" in versions
        assert "v4" in versions
        assert "v3" in versions
        
        # Old versions should be deleted
        assert "v2" not in versions
        assert "v1" not in versions
        assert "v0" not in versions


class TestTrainingDataCollector:
    """Test cases for TrainingDataCollector"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create mock task repository"""
        return Mock()
    
    @pytest.fixture
    def collector(self, mock_task_repository):
        """Create TrainingDataCollector instance"""
        return TrainingDataCollector(mock_task_repository)
    
    @pytest.fixture
    def sample_tasks(self):
        """Create sample tasks for testing"""
        tasks = []
        
        # Task 1
        task1 = Mock()
        task1.id = "task_1"
        task1.title = "Database Schema"
        task1.description = "Create user tables"
        task1.details = ""
        task1.assignees = ["db-dev"]
        task1.priority = Mock(value="high")
        task1.status = Mock(value="completed")
        task1.estimated_effort = "4h"
        task1.created_at = datetime.now(timezone.utc) - timedelta(days=10)
        task1.updated_at = datetime.now(timezone.utc) - timedelta(days=8)
        task1.git_branch_id = "feature/auth"
        task1.get_dependency_ids = Mock(return_value=[])
        tasks.append(task1)
        
        # Task 2
        task2 = Mock()
        task2.id = "task_2"
        task2.title = "User Model"
        task2.description = "ORM model for users"
        task2.details = ""
        task2.assignees = ["backend-dev"]
        task2.priority = Mock(value="high")
        task2.status = Mock(value="completed")
        task2.estimated_effort = "6h"
        task2.created_at = datetime.now(timezone.utc) - timedelta(days=8)
        task2.updated_at = datetime.now(timezone.utc) - timedelta(days=6)
        task2.git_branch_id = "feature/auth"
        task2.get_dependency_ids = Mock(return_value=["task_1"])
        tasks.append(task2)
        
        # Task 3
        task3 = Mock()
        task3.id = "task_3"
        task3.title = "User API"
        task3.description = "REST API endpoints"
        task3.details = ""
        task3.assignees = ["backend-dev"]
        task3.priority = Mock(value="medium")
        task3.status = Mock(value="in_progress")
        task3.estimated_effort = "8h"
        task3.created_at = datetime.now(timezone.utc) - timedelta(days=5)
        task3.updated_at = datetime.now(timezone.utc) - timedelta(days=3)
        task3.git_branch_id = "feature/auth"
        task3.get_dependency_ids = Mock(return_value=["task_2"])
        tasks.append(task3)
        
        return tasks
    
    def test_collect_project_history(self, collector, mock_task_repository, sample_tasks):
        """Test collecting project history for training"""
        mock_task_repository.find_all.return_value = sample_tasks
        
        projects = collector.collect_project_history()
        
        assert len(projects) == 1  # One project (feature/auth branch)
        project = projects[0]
        
        assert project['id'] == "feature/auth"
        assert project['task_count'] == 3
        assert project['dependency_count'] == 2  # task_2->task_1, task_3->task_2
        assert len(project['tasks']) == 3
        assert 'collected_at' in project
    
    def test_collect_project_history_no_tasks(self, collector, mock_task_repository):
        """Test collecting when no tasks exist"""
        mock_task_repository.find_all.return_value = []
        
        projects = collector.collect_project_history()
        
        assert projects == []
    
    def test_collect_project_history_with_limit(self, collector, mock_task_repository):
        """Test collecting with project limit"""
        # Create tasks for multiple projects
        tasks = []
        for i in range(3):
            for j in range(3):
                task = Mock()
                task.id = f"task_{i}_{j}"
                task.title = f"Task {j} in Project {i}"
                task.description = ""
                task.details = ""
                task.assignees = []
                task.priority = Mock(value="medium")
                task.status = Mock(value="done")
                task.estimated_effort = "2h"
                task.created_at = datetime.now(timezone.utc)
                task.updated_at = datetime.now(timezone.utc)
                task.git_branch_id = f"project_{i}"
                task.get_dependency_ids = Mock(return_value=["some_dep"] if j > 0 else [])
                tasks.append(task)
        
        mock_task_repository.find_all.return_value = tasks
        
        projects = collector.collect_project_history(limit=2)
        
        assert len(projects) == 2  # Limited to 2 projects
    
    def test_infer_project_domain(self, collector):
        """Test inferring project domain from task content"""
        # Web domain tasks
        web_tasks = [
            {'title': 'Frontend UI', 'description': 'React components', 'details': ''},
            {'title': 'Backend API', 'description': 'REST endpoints', 'details': ''}
        ]
        assert collector._infer_project_domain(web_tasks) == 'web'
        
        # Mobile domain tasks
        mobile_tasks = [
            {'title': 'Android App', 'description': 'Mobile application', 'details': ''},
            {'title': 'iOS Features', 'description': 'Flutter implementation', 'details': ''}
        ]
        assert collector._infer_project_domain(mobile_tasks) == 'mobile'
        
        # General domain (no clear indicators)
        general_tasks = [
            {'title': 'Task 1', 'description': 'Do something', 'details': ''},
            {'title': 'Task 2', 'description': 'Do something else', 'details': ''}
        ]
        assert collector._infer_project_domain(general_tasks) == 'general'


class TestMLDependencyPredictor:
    """Test cases for MLDependencyPredictor"""
    
    @pytest.fixture
    def mock_task_repository(self):
        """Create mock task repository"""
        return Mock()
    
    @pytest.fixture
    def temp_model_dir(self):
        """Create temporary directory for model storage"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def predictor(self, mock_task_repository, temp_model_dir):
        """Create MLDependencyPredictor instance"""
        return MLDependencyPredictor(mock_task_repository, model_dir=temp_model_dir)
    
    def test_train_model_success(self, predictor, mock_task_repository):
        """Test successful model training"""
        # Mock training data
        training_data = [
            {
                'id': 'proj_1',
                'tasks': [
                    {
                        'id': '1',
                        'title': 'Task 1',
                        'description': 'First task description',
                        'details': 'Task details',
                        'assignees': ['developer'],
                        'priority': 'medium',
                        'status': 'done',
                        'estimated_effort': '2 hours',
                        'created_at': '2024-01-01T00:00:00Z',
                        'updated_at': '2024-01-01T01:00:00Z',
                        'dependencies': []
                    },
                    {
                        'id': '2',
                        'title': 'Task 2',
                        'description': 'Second task description',
                        'details': 'Task details',
                        'assignees': ['developer'],
                        'priority': 'high',
                        'status': 'done',
                        'estimated_effort': '4 hours',
                        'created_at': '2024-01-01T01:00:00Z',
                        'updated_at': '2024-01-01T05:00:00Z',
                        'dependencies': ['1']
                    }
                ]
            }
        ]
        
        with patch.object(predictor.data_collector, 'collect_project_history', return_value=training_data):
            result = predictor.train_model(save_model=False)
        
        assert result['status'] == 'completed'
        assert result['training_data_projects'] == 1
        assert 'patterns_learned' in result
        assert predictor.pattern_engine.trained
    
    def test_train_model_no_data(self, predictor, mock_task_repository):
        """Test model training with no data"""
        with patch.object(predictor.data_collector, 'collect_project_history', return_value=[]):
            result = predictor.train_model()
        
        assert result['status'] == 'failed'
        assert result['error'] == 'No training data available'
    
    def test_train_model_with_save(self, predictor, mock_task_repository, temp_model_dir):
        """Test model training with saving"""
        training_data = [
            {
                'id': 'proj_1',
                'tasks': [
                    {
                        'id': '1',
                        'title': 'Task 1',
                        'description': 'First task description',
                        'details': 'Task details',
                        'assignees': ['developer'],
                        'priority': 'medium',
                        'status': 'done',
                        'estimated_effort': '2 hours',
                        'created_at': '2024-01-01T00:00:00Z',
                        'updated_at': '2024-01-01T01:00:00Z',
                        'dependencies': []
                    },
                    {
                        'id': '2',
                        'title': 'Task 2',
                        'description': 'Second task description',
                        'details': 'Task details',
                        'assignees': ['developer'],
                        'priority': 'high',
                        'status': 'done',
                        'estimated_effort': '4 hours',
                        'created_at': '2024-01-01T01:00:00Z',
                        'updated_at': '2024-01-01T05:00:00Z',
                        'dependencies': ['1']
                    }
                ]
            }
        ]
        
        with patch.object(predictor.data_collector, 'collect_project_history', return_value=training_data):
            result = predictor.train_model(save_model=True)
        
        assert result['status'] == 'completed'
        assert 'model_saved' in result
        assert 'model_version' in result
        
        # Check that model was saved
        versions = predictor.persistence.get_available_versions()
        assert len(versions) > 0
    
    def test_predict_dependencies_untrained(self, predictor):
        """Test prediction with untrained model"""
        task = Mock(id="new_task")
        candidates = [Mock(id="task_1"), Mock(id="task_2")]
        
        predictions = predictor.predict_dependencies(task, candidates)
        
        assert predictions == []
    
    def test_predict_dependencies_trained(self, predictor):
        """Test prediction with trained model"""
        # Mock a trained engine
        predictor.pattern_engine.trained = True
        
        mock_predictions = [
            PatternPrediction(
                source_task_id="new_task",
                target_task_id="task_1",
                pattern_ids=["pattern_1"],
                confidence=0.85,
                reasoning="Test prediction",
                features_matched=["sequential pattern"]
            ),
            PatternPrediction(
                source_task_id="new_task",
                target_task_id="task_2",
                pattern_ids=["pattern_2"],
                confidence=0.3,  # Below threshold
                reasoning="Low confidence prediction",
                features_matched=[]
            )
        ]
        
        with patch.object(predictor.pattern_engine, 'predict_dependencies', return_value=mock_predictions):
            task = Mock(id="new_task")
            candidates = [Mock(id="task_1"), Mock(id="task_2")]
            
            predictions = predictor.predict_dependencies(task, candidates)
        
        # Should filter out low confidence prediction
        assert len(predictions) == 1
        assert predictions[0].target_task_id == "task_1"
        assert predictions[0].confidence >= 0.4
    
    def test_get_model_info(self, predictor, temp_model_dir):
        """Test getting model information"""
        info = predictor.get_model_info()
        
        assert 'trained' in info
        assert 'available_versions' in info
        assert 'model_directory' in info
        assert info['model_directory'] == str(Path(temp_model_dir))
        
        # When not trained
        assert info['trained'] is False
        assert info['current_stats'] is None
    
    def test_get_model_info_with_trained_model(self, predictor):
        """Test getting model info with trained model"""
        # Mock trained model
        predictor.pattern_engine.trained = True
        predictor.pattern_engine.patterns = {"p1": Mock()}
        
        with patch.object(predictor.pattern_engine, 'get_engine_stats', return_value={'patterns': 1}):
            info = predictor.get_model_info()
        
        assert info['trained'] is True
        assert info['current_stats'] == {'patterns': 1}
    
    def test_update_pattern_feedback_accepted(self, predictor):
        """Test updating pattern with positive feedback"""
        # Create a pattern
        pattern = DependencyPattern(
            pattern_id="test_pattern",
            pattern_type=PatternType.SEQUENTIAL,
            source_features={},
            target_features={},
            confidence=0.8,
            support_count=10,
            success_rate=0.8,
            created_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc)
        )
        predictor.pattern_engine.patterns["test_pattern"] = pattern
        
        success = predictor.update_pattern_feedback("test_pattern", accepted=True)
        
        assert success is True
        assert pattern.support_count == 11
        assert pattern.success_rate > 0.8  # Should increase
    
    def test_update_pattern_feedback_rejected(self, predictor):
        """Test updating pattern with negative feedback"""
        pattern = DependencyPattern(
            pattern_id="test_pattern",
            pattern_type=PatternType.SEQUENTIAL,
            source_features={},
            target_features={},
            confidence=0.8,
            support_count=10,
            success_rate=0.8,
            created_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc)
        )
        predictor.pattern_engine.patterns["test_pattern"] = pattern
        
        success = predictor.update_pattern_feedback("test_pattern", accepted=False)
        
        assert success is True
        assert pattern.support_count == 11
        assert pattern.success_rate < 0.8  # Should decrease
    
    def test_update_pattern_feedback_nonexistent(self, predictor):
        """Test updating feedback for non-existent pattern"""
        success = predictor.update_pattern_feedback("nonexistent_pattern", accepted=True)
        assert success is False
    
    def test_retrain_model(self, predictor):
        """Test model retraining"""
        with patch.object(predictor, 'train_model', return_value={'status': 'completed'}) as mock_train:
            result = predictor.retrain_model()
        
        assert result['status'] == 'completed'
        mock_train.assert_called_once_with(save_model=True)
    
    def test_load_latest_model(self, predictor, temp_model_dir):
        """Test loading latest model on initialization"""
        # Save a test model
        patterns = {
            "p1": DependencyPattern(
                pattern_id="p1",
                pattern_type=PatternType.SEQUENTIAL,
                source_features={},
                target_features={},
                confidence=0.8,
                support_count=5,
                success_rate=0.9,
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc)
            )
        }
        predictor.persistence.save_patterns(patterns, "test_version")
        
        # Create new predictor instance - should load the model
        new_predictor = MLDependencyPredictor(predictor.task_repository, model_dir=temp_model_dir)
        
        assert new_predictor.pattern_engine.trained
        assert len(new_predictor.pattern_engine.patterns) == 1
        assert "p1" in new_predictor.pattern_engine.patterns