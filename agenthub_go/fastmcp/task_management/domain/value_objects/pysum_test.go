package value_objects

import (
	"encoding/json"
	"math"
	"os"
	"testing"
)

func TestPySumMatchesPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/pysum_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []struct {
		Xs  []float64 `json:"xs"`
		Sum float64   `json:"sum"`
	}
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	plainDiffers := 0
	for _, c := range cases {
		if got := PySum(c.Xs); math.Float64bits(got) != math.Float64bits(c.Sum) {
			t.Errorf("PySum(%v) = %v want %v", c.Xs, got, c.Sum)
		}
		plain := 0.0
		for _, x := range c.Xs {
			plain += x
		}
		if plain != c.Sum {
			plainDiffers++
		}
	}
	t.Logf("plain left-to-right summation differs from Python in %d of %d cases", plainDiffers, len(cases))
}
