package value_objects

import (
	"bytes"
	"encoding/json"
	"os"
	"strings"
	"testing"
)

// numberize turns json.Number into int64 or float64 the way Python's json.loads types it.
func numberize(v any) any {
	switch x := v.(type) {
	case json.Number:
		if strings.ContainsAny(string(x), ".eE") {
			f, _ := x.Float64()
			return f
		}
		n, _ := x.Int64()
		return n
	case []any:
		for i := range x {
			x[i] = numberize(x[i])
		}
	case map[string]any:
		for k := range x {
			x[k] = numberize(x[k])
		}
	}
	return v
}

type orderedPairs struct {
	keys []string
	vals map[string]any
}

func (o orderedPairs) KeysAny() []string   { return o.keys }
func (o orderedPairs) GetAny(k string) any { return o.vals[k] }

func TestPyJSONDumpsMatchesPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/pyjson_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	var cases []struct {
		V  any    `json:"v"`
		I2 string `json:"i2"`
		I0 string `json:"i0"`
	}
	if err := dec.Decode(&cases); err != nil {
		t.Fatal(err)
	}
	for _, c := range cases {
		v := numberize(c.V)
		if got, err := PyJSONDumps(v, 2); err != nil || got != c.I2 {
			t.Errorf("indent=2 %v:\n got %q\nwant %q (%v)", v, got, c.I2, err)
		}
		if got, err := PyJSONDumps(v, -1); err != nil || got != c.I0 {
			t.Errorf("indent=None %v:\n got %q\nwant %q (%v)", v, got, c.I0, err)
		}
	}
}

func TestPyJSONDumpsOrderedAnyKeepsInsertionOrder(t *testing.T) {
	o := orderedPairs{[]string{"b", "a"}, map[string]any{"a": int64(1), "b": []any{}}}
	got, _ := PyJSONDumps(o, 2)
	if want := "{\n  \"b\": [],\n  \"a\": 1\n}"; got != want {
		t.Fatalf("got %q want %q", got, want)
	}
	if PyRepr(o) != "{'b': [], 'a': 1}" {
		t.Fatalf("repr %q", PyRepr(o))
	}
}

func TestPyJSONDumpsRejectsUnsupportedTypes(t *testing.T) {
	if _, err := PyJSONDumps(struct{ X int }{1}, 2); err == nil {
		t.Fatal("expected error")
	}
}

func TestPyJSONTypedNilOrderedIsNull(t *testing.T) {
	var m *ptrOrdered
	got, err := PyJSONDumps(map[string]any{"task": m}, -1)
	if err != nil || got != `{"task": null}` {
		t.Fatalf("got %q err %v", got, err)
	}
}

type ptrOrdered struct{ keys []string }

func (p *ptrOrdered) KeysAny() []string { return p.keys }
func (p *ptrOrdered) GetAny(string) any { return nil }
