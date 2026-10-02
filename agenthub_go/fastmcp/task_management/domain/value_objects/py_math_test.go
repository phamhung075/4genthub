package value_objects

import (
	"encoding/json"
	"math"
	"os"
	"testing"
)

func TestPyLogPyExpMatchPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/pymath_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var fx struct {
		Log [][2]float64 `json:"log"`
		Exp [][2]float64 `json:"exp"`
	}
	if err := json.Unmarshal(raw, &fx); err != nil {
		t.Fatal(err)
	}
	badLog, badExp, nativeLog, nativeExp := 0, 0, 0, 0
	for _, c := range fx.Log {
		if PyLog(c[0]) != c[1] {
			badLog++
		}
		if math.Log(c[0]) != c[1] {
			nativeLog++
		}
	}
	for _, c := range fx.Exp {
		if PyExp(c[0]) != c[1] {
			badExp++
		}
		if math.Exp(c[0]) != c[1] {
			nativeExp++
		}
	}
	t.Logf("log: PyLog %d / math.Log %d mismatches of %d; exp: PyExp %d / math.Exp %d of %d",
		badLog, nativeLog, len(fx.Log), badExp, nativeExp, len(fx.Exp))
	if badLog > len(fx.Log)/200 || badExp > len(fx.Exp)/200 {
		t.Fatalf("PyLog %d / PyExp %d mismatches exceed 0.5%%", badLog, badExp)
	}
}

func TestPyLogPyExpEdges(t *testing.T) {
	if PyLog(1) != 0 || PyExp(0) != 1 || !math.IsInf(PyExp(1000), 1) || PyExp(-1000) != 0 || !math.IsNaN(PyLog(math.NaN())) {
		t.Fatal("edge cases")
	}
	if PyLog(2) != math.Ln2 || PyLog(math.E) != 1 {
		t.Fatalf("PyLog(2)=%v PyLog(e)=%v", PyLog(2), PyLog(math.E))
	}
}
