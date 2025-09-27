"""
Unit tests for the Semantic Matcher
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock, call

from fastmcp.task_management.domain.services.intelligence.semantic_matcher import (
    SemanticMatcher,
    ContextItem,
    SimilarityResult,
    MockSentenceTransformer,
    HAS_NUMPY,
    HAS_FAISS,
    HAS_SENTENCE_TRANSFORMERS
)


# Test fixtures
@pytest.fixture
def temp_cache_dir():
    """Create a temporary cache directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def semantic_matcher(temp_cache_dir):
    """Create a SemanticMatcher instance"""
    return SemanticMatcher(
        model_name="all-MiniLM-L6-v2",
        similarity_threshold=0.5,
        cache_embeddings=True,
        cache_dir=temp_cache_dir,
        faiss_index_type="flat"
    )


@pytest.fixture
def sample_context_items():
    """Create sample context items"""
    return [
        ContextItem(
            id="ctx_1",
            content="Implement user authentication with JWT tokens",
            context_type="task",
            metadata={"priority": "high"}
        ),
        ContextItem(
            id="ctx_2", 
            content="Create database schema for user management",
            context_type="task",
            metadata={"priority": "high"}
        ),
        ContextItem(
            id="ctx_3",
            content="Design API endpoints for product catalog",
            context_type="branch",
            metadata={"priority": "medium"}
        ),
        ContextItem(
            id="ctx_4",
            content="Setup CI/CD pipeline with GitHub Actions",
            context_type="project",
            metadata={"priority": "low"}
        )
    ]


class TestSemanticMatcher:
    """Test the main SemanticMatcher class"""
    
    def test_initialization(self, semantic_matcher):
        """Test matcher initialization"""
        assert semantic_matcher.model_name == "all-MiniLM-L6-v2"
        assert semantic_matcher.similarity_threshold == 0.5
        assert semantic_matcher.cache_embeddings is True
        assert semantic_matcher.faiss_index_type == "flat"
        assert semantic_matcher.embedding_dim > 0
        assert len(semantic_matcher.context_items) == 0
    
    def test_initialization_without_cache_dir(self):
        """Test initialization without cache directory"""
        matcher = SemanticMatcher(cache_embeddings=True)
        assert matcher.cache_dir.exists()
        assert ".cache" in str(matcher.cache_dir)
    
    def test_get_cache_key(self, semantic_matcher):
        """Test cache key generation"""
        content = "Test content for caching"
        key1 = semantic_matcher._get_cache_key(content)
        key2 = semantic_matcher._get_cache_key(content)
        key3 = semantic_matcher._get_cache_key("Different content")
        
        assert key1 == key2  # Same content produces same key
        assert key1 != key3  # Different content produces different key
        assert len(key1) == 32  # MD5 hex digest length
    
    def test_generate_embedding(self, semantic_matcher):
        """Test single embedding generation"""
        content = "Test content for embedding"
        embedding = semantic_matcher.generate_embedding(content)
        
        assert embedding is not None
        if HAS_NUMPY:
            assert len(embedding) == semantic_matcher.embedding_dim
        else:
            # List fallback
            assert isinstance(embedding, (list, tuple))
    
    def test_generate_embedding_with_cache(self, semantic_matcher):
        """Test embedding generation with caching"""
        content = "Cached test content"
        
        # First call generates and caches
        embedding1 = semantic_matcher.generate_embedding(content)
        
        # Second call should load from cache
        with patch.object(semantic_matcher, '_load_cached_embedding', return_value=embedding1) as mock_load:
            embedding2 = semantic_matcher.generate_embedding(content)
            mock_load.assert_called_once()
        
        if HAS_NUMPY:
            import numpy as np
            assert np.array_equal(embedding1, embedding2)
        else:
            assert embedding1 == embedding2
    
    def test_generate_embeddings_batch(self, semantic_matcher):
        """Test batch embedding generation"""
        contents = [
            "First content",
            "Second content", 
            "Third content"
        ]
        
        embeddings = semantic_matcher.generate_embeddings_batch(contents)
        
        assert len(embeddings) == len(contents)
        assert all(e is not None for e in embeddings)
        
        if HAS_NUMPY:
            assert all(len(e) == semantic_matcher.embedding_dim for e in embeddings)
    
    def test_generate_embeddings_batch_with_cache(self, semantic_matcher):
        """Test batch generation with some cached items"""
        contents = ["Content A", "Content B", "Content C"]
        
        # Pre-cache one item
        cached_embedding = semantic_matcher.generate_embedding(contents[0])
        
        # Generate batch - should only encode uncached items
        with patch.object(semantic_matcher.model, 'encode') as mock_encode:
            # Mock encode to return appropriate embeddings
            if HAS_NUMPY:
                import numpy as np
                mock_encode.return_value = np.random.random((2, semantic_matcher.embedding_dim))
            else:
                mock_encode.return_value = [[0.1] * semantic_matcher.embedding_dim, 
                                           [0.2] * semantic_matcher.embedding_dim]
            
            embeddings = semantic_matcher.generate_embeddings_batch(contents)
            
            # Should only encode the 2 uncached items
            mock_encode.assert_called_once()
            assert len(mock_encode.call_args[0][0]) == 2
    
    def test_add_context_items(self, semantic_matcher, sample_context_items):
        """Test adding context items"""
        semantic_matcher.add_context_items(sample_context_items)
        
        assert len(semantic_matcher.context_items) == len(sample_context_items)
        assert all(item.embedding is not None for item in semantic_matcher.context_items)
        assert len(semantic_matcher.item_id_to_index) == len(sample_context_items)
        
        # Check index mapping
        for i, item in enumerate(sample_context_items):
            assert semantic_matcher.item_id_to_index[item.id] == i
    
    def test_add_context_items_with_existing_embeddings(self, semantic_matcher):
        """Test adding items that already have embeddings"""
        if HAS_NUMPY:
            import numpy as np
            existing_embedding = np.random.random(semantic_matcher.embedding_dim)
        else:
            existing_embedding = [0.5] * semantic_matcher.embedding_dim
        
        item_with_embedding = ContextItem(
            id="pre_embedded",
            content="Already has embedding",
            context_type="task",
            embedding=existing_embedding
        )
        
        # Should not regenerate embedding
        semantic_matcher.add_context_items([item_with_embedding])
        
        # Verify the item was added with existing embedding
        assert len(semantic_matcher.context_items) == 1
        assert semantic_matcher.context_items[0].embedding is existing_embedding
    
    @pytest.mark.skipif(not HAS_FAISS, reason="FAISS not installed")
    def test_find_similar_contexts(self, semantic_matcher, sample_context_items):
        """Test finding similar contexts"""
        semantic_matcher.add_context_items(sample_context_items)
        
        query = "user authentication JWT implementation"
        results = semantic_matcher.find_similar_contexts(query, top_k=3)
        
        assert isinstance(results, list)
        assert len(results) <= 3
        assert all(isinstance(r, SimilarityResult) for r in results)
        
        # Check results are sorted by similarity
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].similarity_score >= results[i+1].similarity_score
    
    @pytest.mark.skipif(not HAS_FAISS, reason="FAISS not installed") 
    def test_find_similar_contexts_with_threshold(self, semantic_matcher, sample_context_items):
        """Test similarity search with custom threshold"""
        semantic_matcher.add_context_items(sample_context_items)
        
        query = "random unrelated query"
        
        # High threshold should return fewer results
        results_high = semantic_matcher.find_similar_contexts(query, top_k=10, min_similarity=0.9)
        results_low = semantic_matcher.find_similar_contexts(query, top_k=10, min_similarity=0.1)
        
        assert len(results_high) <= len(results_low)
    
    def test_find_similar_contexts_empty_index(self, semantic_matcher):
        """Test similarity search with no indexed items"""
        results = semantic_matcher.find_similar_contexts("test query")
        assert results == []
    
    def test_update_context_item(self, semantic_matcher, sample_context_items):
        """Test updating a context item"""
        semantic_matcher.add_context_items(sample_context_items)
        
        # Update an item
        new_content = "Updated authentication implementation with OAuth support"
        success = semantic_matcher.update_context_item("ctx_1", new_content)
        
        assert success is True
        updated_item = semantic_matcher.context_items[0]
        assert updated_item.content == new_content
        assert updated_item.embedding is not None
        # The timestamp should be updated (or at least not less than the original)
        assert updated_item.last_updated >= sample_context_items[0].last_updated
    
    def test_update_nonexistent_item(self, semantic_matcher):
        """Test updating non-existent item"""
        success = semantic_matcher.update_context_item("nonexistent", "new content")
        assert success is False
    
    def test_remove_context_item(self, semantic_matcher, sample_context_items):
        """Test removing a context item"""
        semantic_matcher.add_context_items(sample_context_items)
        initial_count = len(semantic_matcher.context_items)
        
        # Remove an item
        success = semantic_matcher.remove_context_item("ctx_2")
        
        assert success is True
        assert len(semantic_matcher.context_items) == initial_count - 1
        assert "ctx_2" not in semantic_matcher.item_id_to_index
        
        # Check index mapping is updated correctly
        assert semantic_matcher.item_id_to_index["ctx_1"] == 0
        assert semantic_matcher.item_id_to_index["ctx_3"] == 1  # Shifted down
        assert semantic_matcher.item_id_to_index["ctx_4"] == 2  # Shifted down
    
    def test_remove_nonexistent_item(self, semantic_matcher):
        """Test removing non-existent item"""
        success = semantic_matcher.remove_context_item("nonexistent")
        assert success is False
    
    def test_get_stats(self, semantic_matcher, sample_context_items):
        """Test getting matcher statistics"""
        semantic_matcher.add_context_items(sample_context_items)
        
        stats = semantic_matcher.get_stats()
        
        assert stats["total_context_items"] == len(sample_context_items)
        assert stats["embedding_dimension"] == semantic_matcher.embedding_dim
        assert stats["model_name"] == "all-MiniLM-L6-v2"
        assert stats["similarity_threshold"] == 0.5
        assert stats["faiss_index_type"] == "flat"
        assert stats["cache_enabled"] is True
        assert "cache_dir" in stats
    
    @pytest.mark.skipif(not (HAS_FAISS and HAS_NUMPY), reason="FAISS/numpy not installed")
    def test_get_context_similarity_matrix(self, semantic_matcher, sample_context_items):
        """Test similarity matrix generation"""
        semantic_matcher.add_context_items(sample_context_items)
        
        matrix = semantic_matcher.get_context_similarity_matrix()
        
        import numpy as np
        assert isinstance(matrix, np.ndarray)
        assert matrix.shape == (len(sample_context_items), len(sample_context_items))
        
        # Diagonal should be ~1.0 (self-similarity)
        for i in range(len(sample_context_items)):
            assert matrix[i, i] > 0.99
        
        # Matrix should be symmetric
        assert np.allclose(matrix, matrix.T)


class TestContextItem:
    """Test ContextItem dataclass"""
    
    def test_context_item_creation(self):
        """Test creating a context item"""
        item = ContextItem(
            id="test_id",
            content="Test content",
            context_type="task"
        )
        
        assert item.id == "test_id"
        assert item.content == "Test content"
        assert item.context_type == "task"
        assert item.metadata == {}
        assert item.embedding is None
        assert isinstance(item.last_updated, datetime)
    
    def test_context_item_with_metadata(self):
        """Test context item with metadata"""
        metadata = {"priority": "high", "tags": ["auth", "security"]}
        item = ContextItem(
            id="test_id",
            content="Test content",
            context_type="task",
            metadata=metadata
        )
        
        assert item.metadata == metadata


class TestMockSentenceTransformer:
    """Test the mock sentence transformer"""
    
    def test_mock_transformer_initialization(self):
        """Test mock transformer initialization"""
        mock_model = MockSentenceTransformer("test-model")
        assert mock_model.model_name == "test-model"
        assert mock_model.get_sentence_embedding_dimension() == 384
    
    def test_mock_transformer_encode(self):
        """Test mock transformer encoding"""
        mock_model = MockSentenceTransformer("test-model")
        texts = ["Text 1", "Text 2", "Text 3"]
        
        embeddings = mock_model.encode(texts)
        
        assert len(embeddings) == len(texts)
        if HAS_NUMPY:
            import numpy as np
            assert isinstance(embeddings, np.ndarray)
            assert embeddings.shape == (3, 384)
        else:
            assert isinstance(embeddings, list)
            assert len(embeddings[0]) == 384


class TestEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_cache_load_failure(self, semantic_matcher):
        """Test handling cache load failures"""
        with patch('builtins.open', side_effect=IOError("Read error")):
            # Should return None on cache load failure
            embedding = semantic_matcher._load_cached_embedding("test content")
            assert embedding is None
    
    def test_cache_save_failure(self, semantic_matcher):
        """Test handling cache save failures"""
        with patch('builtins.open', side_effect=IOError("Write error")):
            # Should continue without error
            semantic_matcher._save_cached_embedding("test content", [0.1, 0.2, 0.3])
            # No assertion needed - just shouldn't raise
    
    def test_empty_context_similarity_matrix(self, semantic_matcher):
        """Test similarity matrix with no items"""
        if HAS_NUMPY:
            import numpy as np
            matrix = semantic_matcher.get_context_similarity_matrix()
            assert isinstance(matrix, np.ndarray)
            assert matrix.size == 0
    
    @pytest.mark.skipif(not HAS_FAISS, reason="FAISS not installed")
    def test_ivf_index_type(self, temp_cache_dir):
        """Test IVF index type"""
        matcher = SemanticMatcher(
            cache_dir=temp_cache_dir,
            faiss_index_type="ivf"
        )
        
        # Need enough items for IVF clustering
        items = []
        for i in range(200):
            items.append(ContextItem(
                id=f"item_{i}",
                content=f"Content for item {i} with some variation",
                context_type="task"
            ))
        
        matcher.add_context_items(items)
        assert matcher.faiss_index is not None
    
    def test_unsupported_index_type(self, temp_cache_dir):
        """Test unsupported FAISS index type"""
        matcher = SemanticMatcher(
            cache_dir=temp_cache_dir,
            faiss_index_type="unsupported"
        )
        
        with pytest.raises(ValueError, match="Unsupported FAISS index type"):
            matcher.add_context_items([ContextItem(
                id="test",
                content="test",
                context_type="task"
            )])
    
    def test_similarity_search_without_faiss(self):
        """Test behavior when FAISS is not available"""
        with patch('fastmcp.task_management.domain.services.intelligence.semantic_matcher.HAS_FAISS', False):
            matcher = SemanticMatcher()
            items = [ContextItem(id="1", content="test", context_type="task")]
            
            # Should handle gracefully
            matcher.add_context_items(items)
            results = matcher.find_similar_contexts("query")
            assert results == []  # Falls back to empty results