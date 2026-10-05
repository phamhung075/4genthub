package skillblock

import (
	"encoding/json"
	"strings"
	"testing"
)

const digest = "581372434f27b1994d516e144be1324c7c5981cacf64fef6f09d1a57017faa08"

func TestParseValid(t *testing.T) {
	content := `{"content":"# Skill\nbody\n","source_path":"skills/_canonical/core/x/SKILL.md","sha256":"` + digest + `"}`
	block, err := Parse(content)
	if err != nil {
		t.Fatal(err)
	}
	if block.Content != "# Skill\nbody\n" || block.SourcePath != "skills/_canonical/core/x/SKILL.md" || block.SHA256 != digest {
		t.Fatalf("unexpected block: %+v", block)
	}
	if block.MirrorPath != "" || block.MirrorSHA256 != "" {
		t.Fatalf("unexpected mirror: %+v", block)
	}
}

func TestParseValidWithMirror(t *testing.T) {
	content := `{"content":"body","source_path":"a/SKILL.md","sha256":"` + digest + `","mirror_path":"b/SKILL.md","mirror_sha256":"` + digest + `"}`
	block, err := Parse(content)
	if err != nil {
		t.Fatal(err)
	}
	if block.MirrorPath != "b/SKILL.md" || block.MirrorSHA256 != digest {
		t.Fatalf("unexpected mirror: %+v", block)
	}
}

func TestParseErrors(t *testing.T) {
	cases := map[string]struct{ content, want string }{
		"not json":          {`# raw markdown`, "not one JSON value"},
		"array":             {`[1,2,3]`, "not a skill block"},
		"unknown field":     {`{"content":"x","source_path":"a/SKILL.md","sha256":"` + digest + `","extra":1}`, "unknown field"},
		"empty content":     {`{"content":"  ","source_path":"a/SKILL.md","sha256":"` + digest + `"}`, "field content is required"},
		"no source":         {`{"content":"x","sha256":"` + digest + `"}`, "field source_path is required"},
		"absolute source":   {`{"content":"x","source_path":"/a/SKILL.md","sha256":"` + digest + `"}`, "must be relative"},
		"bad digest":        {`{"content":"x","source_path":"a/SKILL.md","sha256":"xyz"}`, "sha256"},
		"mirror half open":  {`{"content":"x","source_path":"a/SKILL.md","sha256":"` + digest + `","mirror_path":"b/SKILL.md"}`, "must be set together"},
		"bad mirror digest": {`{"content":"x","source_path":"a/SKILL.md","sha256":"` + digest + `","mirror_path":"b/SKILL.md","mirror_sha256":"nope"}`, "mirror_sha256"},
	}
	for name, c := range cases {
		if _, err := Parse(c.content); err == nil || !strings.Contains(err.Error(), c.want) {
			t.Errorf("%s: err = %v, want %q", name, err, c.want)
		}
	}
}

// A credential-shaped literal is refused by the block parser too, so a skill block authored as
// an overlay override cannot slip a secret past the publish path's scan.
func TestParseRefusesSecret(t *testing.T) {
	content := `{"content":"token Bearer sk-abcdefghijklmnopqrstuvwxyz012345","source_path":"a/SKILL.md","sha256":"` + digest + `"}`
	if _, err := Parse(content); err == nil || !strings.Contains(err.Error(), "credential-shaped") {
		t.Fatalf("err = %v, want a credential-shaped error", err)
	}
}

func TestMarshalRoundTripsAndKeepsTextReadable(t *testing.T) {
	block := Block{Content: "# Skill <tag>\nbody\n", SourcePath: "skills/x/SKILL.md", SHA256: digest}
	content, err := Marshal(block)
	if err != nil {
		t.Fatal(err)
	}
	// HTML escaping would turn "<tag>" into "\u003ctag\u003e"; the stored SKILL.md text stays readable.
	if !strings.Contains(content, "<tag>") {
		t.Fatalf("Marshal escaped the text: %s", content)
	}
	parsed, err := Parse(content)
	if err != nil {
		t.Fatal(err)
	}
	if parsed != block {
		t.Fatalf("round trip = %+v, want %+v", parsed, block)
	}
	if json.Valid([]byte(content)) != true {
		t.Fatalf("Marshal produced invalid JSON: %s", content)
	}
}
