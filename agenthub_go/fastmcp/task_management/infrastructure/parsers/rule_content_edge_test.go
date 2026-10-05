package parsers

import (
	"crypto/md5"
	"encoding/hex"
	"os"
	"path/filepath"
	"testing"
)

func writeRule(t *testing.T, name string, data []byte) string {
	p := filepath.Join(t.TempDir(), name)
	if err := os.WriteFile(p, data, 0o644); err != nil {
		t.Fatal(err)
	}
	return p
}

func TestParseRuleFileUniversalNewlines(t *testing.T) {
	p := writeRule(t, "a.txt", []byte("one\r\ntwo\rthree\n"))
	rc, err := NewRuleContentParser().ParseRuleFile(p)
	if err != nil {
		t.Fatal(err)
	}
	if rc.RawContent != "one\ntwo\nthree\n" {
		t.Fatalf("raw %q", rc.RawContent)
	}
	sum := md5.Sum([]byte(rc.RawContent))
	if rc.Metadata.Checksum != hex.EncodeToString(sum[:]) {
		t.Fatal("checksum must hash the normalised text")
	}
}

func TestParseRuleFileRejections(t *testing.T) {
	parser := NewRuleContentParser()
	for name, data := range map[string][]byte{
		"empty.txt":   {},
		"bad.txt":     {0xff, 0xfe},
		"list.json":   []byte(`[1,2]`),
		"null.json":   []byte(`null`),
		"scalar.json": []byte(`5`),
	} {
		if _, err := parser.ParseRuleFile(writeRule(t, name, data)); err == nil {
			t.Errorf("%s: expected an error", name)
		}
	}
}
