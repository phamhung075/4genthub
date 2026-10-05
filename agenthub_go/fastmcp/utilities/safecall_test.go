package utilities

import "testing"

func TestSafeCallRecoversPanics(t *testing.T) {
	var m map[string]int
	if rec := SafeCall(func() { m["a"] = 1 }); rec == nil {
		t.Fatal("a nil-map write must be recovered")
	}
	ran := false
	if rec := SafeCall(func() { ran = true }); rec != nil || !ran {
		t.Fatalf("normal completion: rec=%v ran=%v", rec, ran)
	}
}
