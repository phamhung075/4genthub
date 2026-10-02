// Package intelligence ports domain/services/intelligence.
package intelligence

import (
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"math/rand"
	"os"
	"path/filepath"
	"time"
)

// Embedder turns texts into embedding vectors (Python's sentence-transformers model).
type Embedder interface {
	Dimension() int
	Encode(texts []string) [][]float64
}

// MockSentenceTransformer returns random 384-dimensional vectors in [0, 1), the
// fallback Python uses when sentence_transformers is not installed (the production
// environment: neither sentence_transformers nor faiss is installed).
type MockSentenceTransformer struct{ ModelName string }

func (MockSentenceTransformer) Dimension() int { return 384 }

func (MockSentenceTransformer) Encode(texts []string) [][]float64 {
	out := make([][]float64, len(texts))
	for i := range out {
		out[i] = make([]float64, 384)
		for j := range out[i] {
			out[i][j] = rand.Float64()
		}
	}
	return out
}

// ContextItem is a context item for semantic matching. Embedding nil = None.
type ContextItem struct {
	ID          string
	Content     string
	ContextType string // 'task', 'branch', 'project', 'global'
	Metadata    map[string]any
	Embedding   []float64
	LastUpdated time.Time
}

// NewContextItem applies the Python defaults (empty metadata, last_updated now UTC).
func NewContextItem(id, content, contextType string) *ContextItem {
	return &ContextItem{ID: id, Content: content, ContextType: contextType,
		Metadata: map[string]any{}, LastUpdated: time.Now().UTC()}
}

// SimilarityResult is a result of semantic similarity search.
type SimilarityResult struct {
	Item            *ContextItem
	SimilarityScore float64
	Rank            int
}

// SemanticMatcher is the semantic matching engine. FAISS is not installed in the
// production environment, so (like Python there) no vector index is ever built:
// FindSimilarContexts always returns no results and index_size is 0.
type SemanticMatcher struct {
	ModelName           string
	SimilarityThreshold float64
	CacheEmbeddings     bool
	FaissIndexType      string
	embedder            Embedder
	EmbeddingDim        int
	CacheDir            string
	ContextItems        []*ContextItem
	itemIDToIndex       map[string]int
}

// NewSemanticMatcher builds a matcher; embedder nil = the mock; cacheDir "" =
// <cwd>/.cache/embeddings (created).
func NewSemanticMatcher(modelName string, similarityThreshold float64, cacheEmbeddings bool, cacheDir, faissIndexType string, embedder Embedder) (*SemanticMatcher, error) {
	if embedder == nil {
		embedder = MockSentenceTransformer{ModelName: modelName}
	}
	if cacheDir == "" {
		cwd, err := os.Getwd()
		if err != nil {
			return nil, err
		}
		cacheDir = filepath.Join(cwd, ".cache", "embeddings")
	}
	if err := os.MkdirAll(cacheDir, 0o755); err != nil {
		return nil, err
	}
	return &SemanticMatcher{ModelName: modelName, SimilarityThreshold: similarityThreshold, CacheEmbeddings: cacheEmbeddings,
		FaissIndexType: faissIndexType, embedder: embedder, EmbeddingDim: embedder.Dimension(), CacheDir: cacheDir,
		itemIDToIndex: map[string]int{}}, nil
}

// DefaultSemanticMatcher uses Python's defaults.
func DefaultSemanticMatcher() (*SemanticMatcher, error) {
	return NewSemanticMatcher("all-MiniLM-L6-v2", 0.5, true, "", "flat", nil)
}

func (m *SemanticMatcher) cacheKey(content string) string {
	sum := md5.Sum([]byte(content))
	return hex.EncodeToString(sum[:])
}

// The cache holds JSON float arrays (Python pickles numpy arrays, which Go cannot read).
func (m *SemanticMatcher) cacheFile(content string) string {
	return filepath.Join(m.CacheDir, m.cacheKey(content)+".json")
}

func (m *SemanticMatcher) loadCachedEmbedding(content string) []float64 {
	if !m.CacheEmbeddings {
		return nil
	}
	raw, err := os.ReadFile(m.cacheFile(content))
	if err != nil {
		return nil
	}
	var emb []float64
	if json.Unmarshal(raw, &emb) != nil {
		return nil
	}
	return emb
}

func (m *SemanticMatcher) saveCachedEmbedding(content string, emb []float64) {
	if !m.CacheEmbeddings {
		return
	}
	if raw, err := json.Marshal(emb); err == nil {
		_ = os.WriteFile(m.cacheFile(content), raw, 0o644)
	}
}

// GenerateEmbedding returns the (cached) embedding of content.
func (m *SemanticMatcher) GenerateEmbedding(content string) []float64 {
	if cached := m.loadCachedEmbedding(content); cached != nil {
		return cached
	}
	emb := m.embedder.Encode([]string{content})[0]
	m.saveCachedEmbedding(content, emb)
	return emb
}

// GenerateEmbeddingsBatch embeds many texts, encoding only the uncached ones.
func (m *SemanticMatcher) GenerateEmbeddingsBatch(contents []string) [][]float64 {
	out := make([][]float64, len(contents))
	var uncached []string
	var indices []int
	for i, c := range contents {
		if cached := m.loadCachedEmbedding(c); cached != nil {
			out[i] = cached
		} else {
			uncached = append(uncached, c)
			indices = append(indices, i)
		}
	}
	if len(uncached) > 0 {
		for i, emb := range m.embedder.Encode(uncached) {
			out[indices[i]] = emb
			m.saveCachedEmbedding(uncached[i], emb)
		}
	}
	return out
}

// AddContextItems adds items, embedding those without an embedding.
func (m *SemanticMatcher) AddContextItems(items []*ContextItem) {
	var contents []string
	for _, it := range items {
		if it.Embedding == nil {
			contents = append(contents, it.Content)
		}
	}
	if len(contents) > 0 {
		embs := m.GenerateEmbeddingsBatch(contents)
		n := 0
		for _, it := range items {
			if it.Embedding == nil {
				it.Embedding = embs[n]
				n++
			}
		}
	}
	start := len(m.ContextItems)
	m.ContextItems = append(m.ContextItems, items...)
	for i, it := range items {
		m.itemIDToIndex[it.ID] = start + i
	}
}

// FindSimilarContexts returns no results: without FAISS Python never builds an index
// and returns [] ("No context items indexed").
func (m *SemanticMatcher) FindSimilarContexts(query string, topK int, minSimilarity *float64) []SimilarityResult {
	return []SimilarityResult{}
}

// GetContextSimilarityMatrix is the cosine similarity matrix between all items. It
// errors when an item has no embedding (numpy fails on an object array).
func (m *SemanticMatcher) GetContextSimilarityMatrix() ([][]float64, error) {
	n := len(m.ContextItems)
	norm := make([][]float64, n)
	for i, it := range m.ContextItems {
		if it.Embedding == nil {
			return nil, fmt.Errorf("context item %s has no embedding", it.ID)
		}
		s := 0.0
		for _, x := range it.Embedding {
			s += float64(x * x)
		}
		nv := math.Sqrt(s)
		norm[i] = make([]float64, len(it.Embedding))
		for j, x := range it.Embedding {
			norm[i][j] = x / nv
		}
	}
	out := make([][]float64, n)
	for i := range out {
		out[i] = make([]float64, n)
		for j := range out[i] {
			d := 0.0
			for k := range norm[i] {
				d += float64(norm[i][k] * norm[j][k])
			}
			out[i][j] = d
		}
	}
	return out, nil
}

// UpdateContextItem replaces an item's content and embedding.
func (m *SemanticMatcher) UpdateContextItem(itemID, newContent string) bool {
	idx, ok := m.itemIDToIndex[itemID]
	if !ok {
		return false
	}
	it := m.ContextItems[idx]
	it.Content = newContent
	it.Embedding = m.GenerateEmbedding(newContent)
	it.LastUpdated = time.Now().UTC()
	return true
}

// RemoveContextItem removes an item and shifts the indices of later items.
func (m *SemanticMatcher) RemoveContextItem(itemID string) bool {
	idx, ok := m.itemIDToIndex[itemID]
	if !ok {
		return false
	}
	m.ContextItems = append(m.ContextItems[:idx], m.ContextItems[idx+1:]...)
	delete(m.itemIDToIndex, itemID)
	for k, v := range m.itemIDToIndex {
		if v > idx {
			m.itemIDToIndex[k] = v - 1
		}
	}
	return true
}

// GetStats returns statistics about the matcher.
func (m *SemanticMatcher) GetStats() map[string]any {
	return map[string]any{
		"total_context_items": len(m.ContextItems), "embedding_dimension": m.EmbeddingDim, "model_name": m.ModelName,
		"similarity_threshold": m.SimilarityThreshold, "faiss_index_type": m.FaissIndexType,
		"cache_enabled": m.CacheEmbeddings, "cache_dir": m.CacheDir, "index_size": 0,
	}
}
