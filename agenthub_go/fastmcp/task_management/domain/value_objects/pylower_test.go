package value_objects

import (
	"encoding/json"
	"os"
	"strconv"
	"testing"
)

type pyLowerFixture struct {
	Table map[string]string `json:"table"`
	Sigma [][2]string       `json:"sigma"`
}

func loadPyLower(t *testing.T) pyLowerFixture {
	raw, err := os.ReadFile("testdata/pylower_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var fx pyLowerFixture
	if err := json.Unmarshal(raw, &fx); err != nil {
		t.Fatal(err)
	}
	return fx
}

func TestPyLowerFinalSigmaMatchesPython(t *testing.T) {
	for _, c := range loadPyLower(t).Sigma {
		if got := PyLower(c[0]); got != c[1] {
			t.Errorf("PyLower(%q) = %q want %q", c[0], got, c[1])
		}
	}
}

// pyLowerUnicodeSkew pins the code points whose lowercase differs between Python 3.14
// (Unicode 16.0) and Go 1.23 (Unicode 15.0): letters assigned in 16.0.
const pyLowerUnicodeSkew = 27

func TestPyLowerEveryCodePointMatchesPython(t *testing.T) {
	table := loadPyLower(t).Table
	skew := 0
	for cp := rune(0); cp <= 0x10FFFF; cp++ {
		if cp >= 0xD800 && cp <= 0xDFFF || cp == 0x3a3 {
			continue
		}
		want, ok := table[strconv.Itoa(int(cp))]
		if !ok {
			want = string(cp)
		}
		if got := PyLower(string(cp)); got != want {
			skew++
		}
	}
	if skew != pyLowerUnicodeSkew {
		t.Fatalf("code points whose lowercase differs from Python: %d (pinned %d)", skew, pyLowerUnicodeSkew)
	}
}
