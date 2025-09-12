"""Test suite for ContentAnalyzer domain service"""

import pytest
from fastmcp.task_management.domain.services.content_analyzer import (
    ContentAnalyzer, ContentFeature, EntityMatch, AnalysisType
)


class TestContentFeature:
    """Test cases for ContentFeature dataclass"""
    
    def test_create_content_feature(self):
        """Test creating a content feature"""
        feature = ContentFeature(
            feature_type=AnalysisType.KEYWORD,
            value="database schema",
            confidence=0.85,
            position=50,
            context="after database schema is ready",
            metadata={"pattern": "after", "full_match": "after database schema"}
        )
        
        assert feature.feature_type == AnalysisType.KEYWORD
        assert feature.value == "database schema"
        assert feature.confidence == 0.85
        assert feature.position == 50
        assert "after database schema" in feature.context
        assert feature.metadata["pattern"] == "after"


class TestEntityMatch:
    """Test cases for EntityMatch dataclass"""
    
    def test_create_entity_match(self):
        """Test creating an entity match"""
        match = EntityMatch(
            entity="UserModel",
            source_task_id="task_001",
            target_task_id="task_002",
            match_type="entity_extraction_entity_extraction",
            confidence=0.9,
            evidence=["Source: class UserModel", "Target: UserModel implementation"]
        )
        
        assert match.entity == "UserModel"
        assert match.source_task_id == "task_001"
        assert match.target_task_id == "task_002"
        assert match.confidence == 0.9
        assert len(match.evidence) == 2


class TestContentAnalyzer:
    """Test cases for ContentAnalyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create ContentAnalyzer instance"""
        return ContentAnalyzer()
    
    def test_extract_keyword_features(self, analyzer):
        """Test keyword feature extraction"""
        content = """
        This task requires the User Model to be completed first.
        It depends on the API Gateway task and blocks the Frontend task.
        After Database Migration is done, we can proceed.
        """
        
        features = analyzer.extract_features(content)
        keyword_features = [f for f in features if f.feature_type == AnalysisType.KEYWORD]
        
        assert len(keyword_features) > 0
        
        # Check for specific keywords
        values = [f.value for f in keyword_features]
        assert any("user model" in v.lower() for v in values)
        assert any("api gateway" in v.lower() for v in values)
        assert any("frontend" in v.lower() for v in values)
        assert any("database migration" in v.lower() for v in values)
        
        # Check confidence scores
        requires_features = [f for f in keyword_features if "requires" in f.metadata.get("full_match", "").lower()]
        assert any(f.confidence >= 0.9 for f in requires_features)
    
    def test_extract_file_features(self, analyzer):
        """Test file reference feature extraction"""
        content = """
        Update the following files:
        - src/models/user.py
        - src/api/auth.js
        - config/database.yaml
        - tests/unit/test_user.py
        - migrations/001_create_users.sql
        """
        
        features = analyzer.extract_features(content)
        file_features = [f for f in features if f.feature_type == AnalysisType.FILE_REFERENCE]
        
        assert len(file_features) >= 5
        
        # Check file paths
        file_paths = [f.value for f in file_features]
        assert "src/models/user.py" in file_paths
        assert "src/api/auth.js" in file_paths
        assert "config/database.yaml" in file_paths
        assert "tests/unit/test_user.py" in file_paths
        assert "migrations/001_create_users.sql" in file_paths
        
        # Check file type metadata
        py_features = [f for f in file_features if f.metadata.get("extension") == "py"]
        assert len(py_features) == 2
    
    def test_extract_entity_features(self, analyzer):
        """Test technical entity extraction"""
        content = """
        Create table users with proper indexes.
        Implement POST /api/users endpoint.
        Create class UserService extends BaseService.
        Import from auth.models module.
        Build UserProfileComponent for the UI.
        """
        
        features = analyzer.extract_features(content)
        entity_features = [f for f in features if f.feature_type == AnalysisType.ENTITY_EXTRACTION]
        
        assert len(entity_features) > 0
        
        # Check entity types
        entities = [(f.value, f.metadata.get("entity_type")) for f in entity_features]
        
        # Database objects
        assert any("users" in e[0].lower() and e[1] == "database_objects" for e in entities)
        
        # API endpoints
        assert any("/api/users" in e[0] and e[1] == "api_endpoints" for e in entities)
        
        # Class references
        assert any("UserService" in e[0] and e[1] == "class_references" for e in entities)
        
        # Component names
        assert any("UserProfileComponent" in e[0] and e[1] == "component_names" for e in entities)
    
    def test_extract_temporal_features(self, analyzer):
        """Test temporal pattern extraction"""
        content = """
        Step 1: Setup database schema
        Step 2: Implement backend API
        Phase 3: Build frontend
        This is the first step in the process.
        The last step is deployment.
        """
        
        features = analyzer.extract_features(content)
        temporal_features = [f for f in features if f.feature_type == AnalysisType.TEMPORAL_PATTERN]
        
        assert len(temporal_features) > 0
        
        # Check temporal values
        values = [f.value for f in temporal_features]
        assert "1" in values
        assert "2" in values
        assert "3" in values
        assert any("first" in v.lower() for v in values)
        assert any("last" in v.lower() for v in values)
    
    def test_find_content_matches(self, analyzer):
        """Test finding matches between content features"""
        source_content = "This task requires the User Model and updates src/models/user.py"
        target_content = "Create User Model class in src/models/user.py file"
        
        source_features = analyzer.extract_features(source_content)
        matches = analyzer.find_content_matches(source_features, target_content)
        
        assert len(matches) > 0
        
        # Should find matches for both User Model and file path
        entity_matches = [m for m in matches if "user model" in m.entity.lower()]
        assert len(entity_matches) > 0
        
        file_matches = [m for m in matches if "src/models/user.py" in m.entity]
        assert len(file_matches) > 0
        
        # Check confidence scores
        assert all(m.confidence > 0.3 for m in matches)
    
    def test_calculate_string_similarity(self, analyzer):
        """Test string similarity calculation"""
        # Exact match
        assert analyzer._calculate_string_similarity("test", "test") == 1.0
        
        # Case insensitive
        assert analyzer._calculate_string_similarity("Test", "test") == 1.0
        
        # Substring match
        similarity = analyzer._calculate_string_similarity("user", "user_model")
        assert 0.4 < similarity < 0.6
        
        # Token-based similarity
        similarity = analyzer._calculate_string_similarity("user model", "model user")
        assert similarity > 0.9
        
        # No match
        assert analyzer._calculate_string_similarity("abc", "xyz") == 0.0
    
    def test_analyze_task_relationships(self, analyzer):
        """Test analyzing relationships between multiple tasks"""
        task_contents = {
            "task_001": "Create User Model with authentication methods",
            "task_002": "Implement login API that uses User Model for authentication",
            "task_003": "Build user profile UI component",
            "task_004": "Write tests for User Model authentication"
        }
        
        relationships = analyzer.analyze_task_relationships(task_contents)
        
        assert len(relationships) == 4
        
        # Task 2 should have relationship with Task 1 (User Model)
        task2_matches = relationships["task_002"]
        assert any(m.target_task_id == "task_001" for m in task2_matches)
        
        # Task 4 should have relationship with Task 1 (User Model)
        task4_matches = relationships["task_004"]
        assert any(m.target_task_id == "task_001" for m in task4_matches)
    
    def test_get_analysis_summary(self, analyzer):
        """Test analysis summary generation"""
        content = """
        Create UserService class that depends on AuthService.
        Update src/services/user.py and src/auth/auth.py files.
        Implement POST /api/users endpoint.
        This is step 1 of the implementation.
        """
        
        features = analyzer.extract_features(content)
        summary = analyzer.get_analysis_summary(features)
        
        assert summary['total_features'] > 0
        assert len(summary['feature_types']) > 0
        assert summary['avg_confidence'] > 0
        assert len(summary['extracted_entities']) > 0
        assert len(summary['file_references']) > 0
        
        # Check specific counts
        assert AnalysisType.KEYWORD.value in summary['feature_types']
        assert AnalysisType.FILE_REFERENCE.value in summary['feature_types']
        assert AnalysisType.ENTITY_EXTRACTION.value in summary['feature_types']
        
        # Check entities and files
        assert any("UserService" in e for e in summary['extracted_entities'])
        assert any("src/services/user.py" in f for f in summary['file_references'])
    
    def test_complex_dependency_patterns(self, analyzer):
        """Test complex dependency pattern extraction"""
        content = """
        This feature extends the BaseAuthentication system.
        It inherits from AbstractUserModel and implements IUserInterface.
        The implementation is based on the existing AuthModule.
        First implement the database layer, then the API layer.
        """
        
        features = analyzer.extract_features(content)
        keyword_features = [f for f in features if f.feature_type == AnalysisType.KEYWORD]
        
        # Check various dependency patterns
        extends_features = [f for f in keyword_features if "extends" in f.metadata.get("full_match", "").lower()]
        assert len(extends_features) > 0
        
        inherits_features = [f for f in keyword_features if "inherits" in f.metadata.get("full_match", "").lower()]
        assert len(inherits_features) > 0
        
        implements_features = [f for f in keyword_features if "implements" in f.metadata.get("full_match", "").lower()]
        assert len(implements_features) > 0
    
    def test_edge_cases(self, analyzer):
        """Test edge cases in content analysis"""
        # Empty content
        features = analyzer.extract_features("")
        assert len(features) == 0
        
        # Content with no patterns
        features = analyzer.extract_features("This is just a simple task description.")
        assert len(features) == 0 or all(f.confidence < 0.5 for f in features)
        
        # Content with special characters
        content = "Update @user_model! and #auth-service$"
        features = analyzer.extract_features(content)
        # Should still extract some features despite special characters
        assert isinstance(features, list)
    
    def test_confidence_scoring(self, analyzer):
        """Test confidence scoring in feature extraction"""
        content = """
        This definitely blocks the deployment task.
        It might use some authentication service.
        There's a table called users in the database.
        """
        
        features = analyzer.extract_features(content)
        
        # "blocks" should have high confidence
        blocks_features = [f for f in features if "blocks" in f.metadata.get("full_match", "").lower()]
        assert any(f.confidence >= 0.9 for f in blocks_features)
        
        # "use" should have lower confidence
        use_features = [f for f in features if "use" in f.metadata.get("full_match", "").lower()]
        assert all(f.confidence < 0.7 for f in use_features)
        
        # Database objects should have high confidence
        db_features = [f for f in features if f.metadata.get("entity_type") == "database_objects"]
        assert any(f.confidence >= 0.8 for f in db_features)