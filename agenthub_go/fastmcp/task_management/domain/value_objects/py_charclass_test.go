package value_objects

import (
	"encoding/json"
	"os"
	"testing"
)

// pyCharClassSkew counts code points whose class differs because Python 3.14 uses
// Unicode 16 and Go 1.23 Unicode 15 (all additions); pinned like pyLowerUnicodeSkew.
const pyCharClassSkewMax = 30

func TestPyCharClassesMatchPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/pycharclass_ranges.json")
	if err != nil {
		t.Fatal(err)
	}
	var d map[string][][2]rune
	if err := json.Unmarshal(raw, &d); err != nil {
		t.Fatal(err)
	}
	for name, fn := range map[string]func(rune) bool{"upper": PyIsUpper, "lower": PyIsLower, "digit": PyIsDigit} {
		want := map[rune]bool{}
		for _, r := range d[name] {
			for c := r[0]; c <= r[1]; c++ {
				want[c] = true
			}
		}
		diff := 0
		for c := rune(0); c < 0x110000; c++ {
			if c >= 0xD800 && c <= 0xDFFF {
				continue
			}
			if fn(c) != want[c] {
				diff++
			}
		}
		if diff > pyCharClassSkewMax {
			t.Fatalf("%s: %d code points differ from Python", name, diff)
		}
		t.Logf("%s: %d differing code points (Unicode version skew)", name, diff)
	}
}
