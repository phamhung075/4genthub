"""Semantic Matcher - Embedding-based Context Similarity

Implements the semantic matching engine using sentence transformers for 
context similarity scoring and FAISS for efficient vector search.

Key Features:
- Generates embeddings for context items (titles, descriptions, technical notes)
- Fast vector similarity search using FAISS
- Configurable similarity thresholds  
- Batch processing for efficiency
- Caching for performance optimization
"""

import logging
from typing import List, Dict, Any, Tuple, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
import pickle
import hashlib
from pathlib import Path

# Optional ML dependencies with fallbacks
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    import array
    np = None
    HAS_NUMPY = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    SentenceTransformer = None
    HAS_SENTENCE_TRANSFORMERS = False

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    faiss = None
    HAS_FAISS = False

logger = logging.getLogger(__name__)


class MockSentenceTransformer:
    """Mock sentence transformer for testing when dependencies are not available."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        
    def get_sentence_embedding_dimension(self) -> int:
        """Return a standard embedding dimension for testing."""
        return 384
        
    def encode(self, texts: List[str], **kwargs) -> 'np.ndarray':
        """Return mock embeddings for testing."""
        if HAS_NUMPY:
            return np.random.random((len(texts), 384))
        else:
            # Fallback to simple list of lists
            import random
            return [[random.random() for _ in range(384)] for _ in range(len(texts))]


@dataclass
class ContextItem:
    """Represents a context item for semantic matching."""
    id: str
    content: str  # Combined text for embedding
    context_type: str  # 'task', 'branch', 'project', 'global'
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[Any] = None  # np.ndarray when numpy available, list otherwise
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass 
class SimilarityResult:
    """Results from semantic similarity search."""
    item: ContextItem
    similarity_score: float
    rank: int


class SemanticMatcher:
    """
    Semantic matching engine using sentence transformers and FAISS.
    
    Implements the core similarity matching component as specified in Phase 3:
    - Generate embeddings for context items
    - Build similarity scoring algorithm  
    - Create relevance thresholds
    - Optimize for speed and accuracy
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",  # Lightweight but effective
        similarity_threshold: float = 0.5,
        cache_embeddings: bool = True,
        cache_dir: Optional[str] = None,
        faiss_index_type: str = "flat"  # or "ivf" for large datasets
    ):
        """
        Initialize semantic matcher.
        
        Args:
            model_name: Sentence transformer model name
            similarity_threshold: Minimum similarity score (0-1)
            cache_embeddings: Whether to cache embeddings to disk
            cache_dir: Directory for caching (None = use temp)
            faiss_index_type: FAISS index type ('flat' or 'ivf')
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.cache_embeddings = cache_embeddings
        self.faiss_index_type = faiss_index_type
        
        # Initialize model
        logger.info(f"Loading sentence transformer model: {model_name}")
        if HAS_SENTENCE_TRANSFORMERS:
            self.model = SentenceTransformer(model_name)
        else:
            logger.warning("sentence_transformers not available, using mock for testing")
            self.model = MockSentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        
        # Setup caching
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path.cwd() / ".cache" / "embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize FAISS index
        self.faiss_index: Optional[Any] = None  # faiss.Index when available
        self.context_items: List[ContextItem] = []
        self.item_id_to_index: Dict[str, int] = {}
        
        logger.info(f"SemanticMatcher initialized with {self.embedding_dim}D embeddings")

    
    def _get_cache_key(self, content: str) -> str:
        """Generate cache key for content."""
        return hashlib.md5(content.encode()).hexdigest()
    
    
    def _load_cached_embedding(self, content: str) -> Optional[Any]:
        """Load cached embedding if available."""
        if not self.cache_embeddings:
            return None
            
        cache_key = self._get_cache_key(content)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cached embedding: {e}")
        
        return None
    
    
    def _save_cached_embedding(self, content: str, embedding: Any) -> None:
        """Save embedding to cache."""
        if not self.cache_embeddings:
            return
            
        cache_key = self._get_cache_key(content)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(embedding, f)
        except Exception as e:
            logger.warning(f"Failed to save cached embedding: {e}")
    
    
    def generate_embedding(self, content: str) -> Any:
        """
        Generate embedding for text content.
        
        Args:
            content: Text content to embed
            
        Returns:
            Embedding vector as numpy array
        """
        # Check cache first
        cached_embedding = self._load_cached_embedding(content)
        if cached_embedding is not None:
            return cached_embedding
        
        # Generate new embedding
        embedding = self.model.encode([content])[0]
        
        # Cache for future use
        self._save_cached_embedding(content, embedding)
        
        return embedding
    
    
    def generate_embeddings_batch(self, contents: List[str]) -> List[Any]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            contents: List of text contents
            
        Returns:
            List of embedding vectors
        """
        uncached_contents = []
        uncached_indices = []
        embeddings = [None] * len(contents)
        
        # Check cache for each content
        for i, content in enumerate(contents):
            cached = self._load_cached_embedding(content)
            if cached is not None:
                embeddings[i] = cached
            else:
                uncached_contents.append(content)
                uncached_indices.append(i)
        
        # Generate embeddings for uncached content in batch
        if uncached_contents:
            batch_embeddings = self.model.encode(uncached_contents)
            
            for i, embedding in enumerate(batch_embeddings):
                original_index = uncached_indices[i]
                embeddings[original_index] = embedding
                
                # Cache the embedding
                content = uncached_contents[i]
                self._save_cached_embedding(content, embedding)
        
        return embeddings
    
    
    def _build_faiss_index(self) -> Optional[Any]:
        """Build FAISS index from current context items."""
        if not HAS_FAISS:
            logger.warning("FAISS not available, using fallback similarity search")
            return None
            
        if not self.context_items:
            logger.warning("No context items to index")
            return faiss.IndexFlatIP(self.embedding_dim)  # Empty index
        
        # Collect embeddings
        embeddings = []
        for item in self.context_items:
            if item.embedding is not None:
                embeddings.append(item.embedding)
            else:
                logger.warning(f"Context item {item.id} missing embedding")
                # Generate embedding on-demand
                item.embedding = self.generate_embedding(item.content)
                embeddings.append(item.embedding)
        
        if HAS_NUMPY:
            embeddings_matrix = np.array(embeddings).astype('float32')
        else:
            # Simple fallback without numpy
            embeddings_matrix = embeddings
        
        # Build appropriate index
        if self.faiss_index_type == "flat":
            index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product (cosine similarity)
            if HAS_NUMPY:
                index.add(embeddings_matrix)
        elif self.faiss_index_type == "ivf":
            # For larger datasets - requires training
            nlist = min(100, len(embeddings) // 10)  # Number of clusters
            quantizer = faiss.IndexFlatIP(self.embedding_dim)
            index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, nlist)
            if HAS_NUMPY:
                index.train(embeddings_matrix)
                index.add(embeddings_matrix)
        else:
            raise ValueError(f"Unsupported FAISS index type: {self.faiss_index_type}")
        
        logger.info(f"Built FAISS index with {index.ntotal} vectors")
        return index
    
    
    def add_context_items(self, items: List[ContextItem]) -> None:
        """
        Add context items to the matcher.
        
        Args:
            items: List of context items to add
        """
        # Generate embeddings for new items
        contents = [item.content for item in items if item.embedding is None]
        if contents:
            embeddings = self.generate_embeddings_batch(contents)
            embedding_idx = 0
            
            for item in items:
                if item.embedding is None:
                    item.embedding = embeddings[embedding_idx]
                    embedding_idx += 1
        
        # Add to collection
        start_index = len(self.context_items)
        self.context_items.extend(items)
        
        # Update index mapping
        for i, item in enumerate(items):
            self.item_id_to_index[item.id] = start_index + i
        
        # Rebuild FAISS index
        self.faiss_index = self._build_faiss_index()
        
        logger.info(f"Added {len(items)} context items. Total: {len(self.context_items)}")
    
    
    def find_similar_contexts(
        self, 
        query: str, 
        top_k: int = 10,
        min_similarity: Optional[float] = None
    ) -> List[SimilarityResult]:
        """
        Find contexts similar to the query.
        
        Args:
            query: Query text
            top_k: Maximum number of results
            min_similarity: Minimum similarity threshold (overrides default)
            
        Returns:
            List of similarity results ordered by similarity score
        """
        if not self.context_items or self.faiss_index is None:
            logger.warning("No context items indexed")
            return []
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query)

        # Handle both numpy arrays and lists
        if HAS_NUMPY and hasattr(query_embedding, 'reshape'):
            query_vector = query_embedding.reshape(1, -1).astype('float32')
        else:
            # Convert list to proper format for FAISS
            if isinstance(query_embedding, list):
                if HAS_NUMPY:
                    query_vector = np.array([query_embedding], dtype='float32')
                else:
                    # If no numpy and no FAISS, this shouldn't be reachable
                    # but provide fallback just in case
                    query_vector = [query_embedding]
            else:
                query_vector = query_embedding
        
        # Search with FAISS
        similarity_scores, indices = self.faiss_index.search(query_vector, top_k)
        similarity_scores = similarity_scores[0]  # Remove batch dimension
        indices = indices[0]
        
        # Apply threshold
        threshold = min_similarity if min_similarity is not None else self.similarity_threshold
        
        results = []
        for i, (score, idx) in enumerate(zip(similarity_scores, indices)):
            if idx >= 0 and score >= threshold:  # FAISS returns -1 for invalid indices
                context_item = self.context_items[idx]
                result = SimilarityResult(
                    item=context_item,
                    similarity_score=float(score),
                    rank=i + 1
                )
                results.append(result)
        
        logger.info(f"Found {len(results)} similar contexts for query (threshold: {threshold:.2f})")
        return results
    
    
    def get_context_similarity_matrix(self) -> Any:
        """
        Get similarity matrix between all context items.
        
        Returns:
            NxN similarity matrix where N is number of context items
        """
        if not self.context_items:
            return np.array([])
        
        embeddings = np.array([item.embedding for item in self.context_items])
        
        # Compute cosine similarity matrix
        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized_embeddings = embeddings / norms
        
        # Compute similarity matrix
        similarity_matrix = np.dot(normalized_embeddings, normalized_embeddings.T)
        
        return similarity_matrix
    
    
    def update_context_item(self, item_id: str, new_content: str) -> bool:
        """
        Update a context item with new content.
        
        Args:
            item_id: ID of context item to update
            new_content: New content for the item
            
        Returns:
            True if updated successfully
        """
        if item_id not in self.item_id_to_index:
            logger.warning(f"Context item {item_id} not found")
            return False
        
        # Update the item
        idx = self.item_id_to_index[item_id]
        item = self.context_items[idx]
        item.content = new_content
        item.embedding = self.generate_embedding(new_content)
        item.last_updated = datetime.now(timezone.utc)
        
        # Rebuild index (could be optimized for single updates)
        self.faiss_index = self._build_faiss_index()
        
        logger.info(f"Updated context item {item_id}")
        return True
    
    
    def remove_context_item(self, item_id: str) -> bool:
        """
        Remove a context item.
        
        Args:
            item_id: ID of context item to remove
            
        Returns:
            True if removed successfully
        """
        if item_id not in self.item_id_to_index:
            logger.warning(f"Context item {item_id} not found")
            return False
        
        # Remove from list
        idx = self.item_id_to_index[item_id]
        del self.context_items[idx]
        del self.item_id_to_index[item_id]
        
        # Update indices for remaining items
        for item_id_key, item_idx in self.item_id_to_index.items():
            if item_idx > idx:
                self.item_id_to_index[item_id_key] = item_idx - 1
        
        # Rebuild index
        self.faiss_index = self._build_faiss_index()
        
        logger.info(f"Removed context item {item_id}")
        return True
    
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the semantic matcher."""
        return {
            "total_context_items": len(self.context_items),
            "embedding_dimension": self.embedding_dim,
            "model_name": self.model_name,
            "similarity_threshold": self.similarity_threshold,
            "faiss_index_type": self.faiss_index_type,
            "cache_enabled": self.cache_embeddings,
            "cache_dir": str(self.cache_dir),
            "index_size": self.faiss_index.ntotal if self.faiss_index else 0
        }