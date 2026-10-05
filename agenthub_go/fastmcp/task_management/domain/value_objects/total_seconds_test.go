package value_objects

import (
	"encoding/json"
	"os"
	"testing"
	"time"
)

func TestPyTotalSecondsMatchesPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/total_seconds_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases [][2]float64
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	for _, c := range cases {
		if got := PyTotalSeconds(time.Duration(int64(c[0])) * time.Microsecond); got != c[1] {
			t.Fatalf("%v us: got %v want %v", c[0], got, c[1])
		}
	}
}
