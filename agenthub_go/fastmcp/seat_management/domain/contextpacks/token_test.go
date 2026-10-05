package contextpacks

import "testing"

func TestEstimateTokensFromBytes(t *testing.T) {
	cases := map[int]int{0: 0, 1: 1, 3: 1, 4: 1, 5: 2, 8: 2, 9: 3}
	for bytes, want := range cases {
		if got := EstimateTokensFromBytes(bytes); got != want {
			t.Errorf("EstimateTokensFromBytes(%d) = %d, want %d", bytes, got, want)
		}
	}
}

// The estimate is monotonic in content: more content never estimates fewer tokens.
func TestEstimateTokensIsMonotonicInContent(t *testing.T) {
	content := ""
	previous := 0
	for i := 1; i <= 200; i++ {
		content += "x"
		got := EstimateTokensOf(content)
		if got < previous {
			t.Fatalf("estimate dropped from %d to %d at %d bytes", previous, got, i)
		}
		previous = got
	}
	if previous == 0 {
		t.Fatal("200 bytes estimated zero tokens")
	}
	// A byte-length projection, not a rune count: a multi-byte rune costs its bytes.
	if EstimateTokensOf("é") != EstimateTokensFromBytes(2) {
		t.Errorf("multi-byte rune estimated %d, want %d (byte projection)", EstimateTokensOf("é"), EstimateTokensFromBytes(2))
	}
}
