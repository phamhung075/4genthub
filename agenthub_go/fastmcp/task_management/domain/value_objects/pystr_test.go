package value_objects

import "testing"

func TestPyStrMatchesPython(t *testing.T) {
	a, b := 0.1, 0.2 // runtime sum, not constant-folded
	for want, in := range map[string]any{
		"1e+16": 1e16, "1.5e-05": 1.5e-5, "it's": "it's", "0.30000000000000004": a + b,
		"True": true, "['a', 1]": []any{"a", 1}, "{'a': 1}": map[string]any{"a": 1}, "None": nil, "1.0": 1.0,
	} {
		if got := PyStr(in); got != want {
			t.Errorf("%v: got %q want %q", in, got, want)
		}
	}
	if got := PyRepr("it's"); got != `"it's"` {
		t.Error(got)
	}
}
