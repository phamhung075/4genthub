package pyyaml

import (
	"encoding/json"
	"os"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestDumpParity(t *testing.T) {
	raw, err := os.ReadFile("testdata/dump_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []struct {
		In   string
		Sort bool
		Out  string
	}
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	bad := 0
	for _, c := range cases {
		v, err := entities.DecodeJSON([]byte(c.In))
		if err != nil {
			t.Fatal(err)
		}
		got, err := Dump(v, c.Sort)
		if err != nil || got != c.Out {
			if bad++; bad <= 10 {
				t.Errorf("in=%s sort=%v\n got: %q (%v)\nwant: %q", c.In, c.Sort, got, err, c.Out)
			}
		}
	}
	if bad > 0 {
		t.Fatalf("%d of %d cases differ", bad, len(cases))
	}
}
