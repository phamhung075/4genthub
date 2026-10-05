package intelligence

import (
	"math"
	"testing"
)

type fixedEmbedder struct{ calls int }

func (*fixedEmbedder) Dimension() int { return 3 }
func (f *fixedEmbedder) Encode(texts []string) [][]float64 {
	f.calls++
	out := make([][]float64, len(texts))
	for i, t := range texts {
		out[i] = []float64{float64(len(t)), 1, 0}
	}
	return out
}

func newTestMatcher(t *testing.T, cache bool) (*SemanticMatcher, *fixedEmbedder) {
	e := &fixedEmbedder{}
	m, err := NewSemanticMatcher("m", 0.5, cache, t.TempDir(), "flat", e)
	if err != nil {
		t.Fatal(err)
	}
	return m, e
}

func TestCacheKeyIsMD5HexOfContent(t *testing.T) {
	m, _ := newTestMatcher(t, true)
	// python: hashlib.md5("héllo".encode()).hexdigest()
	if got := m.cacheKey("héllo"); got != "be50e8478cf24ff3595bc7307fb91b50" {
		t.Fatalf("got %s", got)
	}
}

func TestEmbeddingsAreCachedAndBatchEncodesOnlyUncached(t *testing.T) {
	m, e := newTestMatcher(t, true)
	a := m.GenerateEmbedding("abc")
	if got := m.GenerateEmbedding("abc"); got[0] != a[0] || e.calls != 1 {
		t.Fatalf("calls=%d got=%v", e.calls, got)
	}
	out := m.GenerateEmbeddingsBatch([]string{"abc", "de"})
	if e.calls != 2 || out[0][0] != 3 || out[1][0] != 2 {
		t.Fatalf("calls=%d out=%v", e.calls, out)
	}
}

func TestNoCacheEncodesEveryTime(t *testing.T) {
	m, e := newTestMatcher(t, false)
	m.GenerateEmbedding("abc")
	m.GenerateEmbedding("abc")
	if e.calls != 2 {
		t.Fatalf("calls=%d", e.calls)
	}
}

func TestAddUpdateRemoveContextItems(t *testing.T) {
	m, _ := newTestMatcher(t, false)
	pre := NewContextItem("pre", "x", "task")
	pre.Embedding = []float64{9, 9, 9}
	m.AddContextItems([]*ContextItem{NewContextItem("a", "aa", "task"), pre, NewContextItem("c", "cccc", "task")})
	if len(m.ContextItems) != 3 || m.ContextItems[0].Embedding[0] != 2 || pre.Embedding[0] != 9 || m.ContextItems[2].Embedding[0] != 4 {
		t.Fatalf("items %+v", m.ContextItems)
	}
	if !m.UpdateContextItem("pre", "abcde") || pre.Embedding[0] != 5 || pre.Content != "abcde" {
		t.Fatal("update failed")
	}
	if m.UpdateContextItem("zzz", "x") || m.RemoveContextItem("zzz") {
		t.Fatal("missing ids must return false")
	}
	if !m.RemoveContextItem("a") || m.itemIDToIndex["pre"] != 0 || m.itemIDToIndex["c"] != 1 || len(m.ContextItems) != 2 {
		t.Fatalf("index map %v", m.itemIDToIndex)
	}
	if got := m.FindSimilarContexts("q", 10, nil); got == nil || len(got) != 0 {
		t.Fatal("find must return an empty list without FAISS")
	}
	stats := m.GetStats()
	if stats["total_context_items"] != 2 || stats["embedding_dimension"] != 3 || stats["index_size"] != 0 ||
		stats["faiss_index_type"] != "flat" || stats["cache_enabled"] != false {
		t.Fatalf("stats %v", stats)
	}
}

func TestSimilarityMatrix(t *testing.T) {
	m, _ := newTestMatcher(t, false)
	if got, err := m.GetContextSimilarityMatrix(); err != nil || len(got) != 0 {
		t.Fatalf("empty: %v %v", got, err)
	}
	a, b := NewContextItem("a", "", "task"), NewContextItem("b", "", "task")
	a.Embedding, b.Embedding = []float64{1, 0, 0}, []float64{1, 1, 0}
	m.AddContextItems([]*ContextItem{a, b})
	got, _ := m.GetContextSimilarityMatrix()
	if math.Abs(got[0][0]-1) > 1e-12 || math.Abs(got[0][1]-1/math.Sqrt2) > 1e-12 || got[0][1] != got[1][0] {
		t.Fatalf("matrix %v", got)
	}
	a.Embedding = nil
	if _, err := m.GetContextSimilarityMatrix(); err == nil {
		t.Fatal("expected error for a missing embedding")
	}
}

func TestMockEmbedderShape(t *testing.T) {
	out := MockSentenceTransformer{}.Encode([]string{"a", "b"})
	if len(out) != 2 || len(out[0]) != 384 || out[0][0] < 0 || out[0][0] >= 1 {
		t.Fatal("bad mock embedding")
	}
}
