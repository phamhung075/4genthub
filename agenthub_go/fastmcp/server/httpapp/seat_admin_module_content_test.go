package httpapp

// The module publish route refuses, by kind, a content the seat renderer cannot read. The rule
// itself lives in domain/modulecontent; these tests hold the route to it, because the route is the
// last moment the refusal can happen: a module version is immutable, so a version published with an
// unrenderable content stays unrenderable and every seat that reaches it fails on its next read.

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/skillblock"
)

// testSkillBlock builds a skill block the renderer accepts, through the parser's own marshaller
// so a test cannot drift from the block shape.
func testSkillBlock(t *testing.T, markdown string) string {
	t.Helper()
	block, err := skillblock.Marshal(skillblock.Block{
		Content:    markdown,
		SourcePath: "skills/test/SKILL.md",
		SHA256:     strings.Repeat("a", 64),
	})
	if err != nil {
		t.Fatalf("Marshal skill block: %v", err)
	}
	return block
}

// testModuleBody encodes a publish body, so a test never hand-writes JSON escaping.
func testModuleBody(t *testing.T, kind, content string) string {
	t.Helper()
	body, err := json.Marshal(map[string]string{"kind": kind, "content": content})
	if err != nil {
		t.Fatalf("marshal body: %v", err)
	}
	return string(body)
}

const (
	testMCPServer = `{"name":"test-server","type":"http","url":"https://example.test/mcp"}`
	testToolJSON  = `{"permissions":{"deny":["Bash(git push:*)"]}}`
)

// The three kinds whose content a renderer parses are refused at publish, legibly, and nothing is
// stored: the writer learns here instead of a seat's read failing later.
func TestSeatAdminPutModuleVersionRefusesUnrenderableContent(t *testing.T) {
	cases := []struct {
		name    string
		kind    string
		content string
		want    string
	}{
		{"skill is not a block", "skill", "# not a block\n\nplain markdown\n", "skill content: content is not one JSON value"},
		{"mcp is not a server object", "mcp", "not json", "mcp content: content is not one JSON value"},
		{"mcp object without a type", "mcp", `{"name":"test-server"}`, "mcp content: field type must be"},
		{"tool is not a settings object", "tool", "not json", "tool content: content is not a JSON object"},
		{"tool is json but not an object", "tool", `[]`, "tool content: content is not a JSON object"},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			fake := newFakeSeatAdmin()
			mux := seatAdminTestMux(t, fake)
			body := testModuleBody(t, c.kind, c.content)

			rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/bad/versions/1.0.0", body)
			if rec.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want 400: %s", rec.Code, rec.Body.String())
			}
			if !strings.Contains(rec.Body.String(), c.want) {
				t.Errorf("detail %s does not contain %q", rec.Body.String(), c.want)
			}
			t.Logf("refused %s: %d %s", c.name, rec.Code, strings.TrimSpace(rec.Body.String()))
			if _, stored := fake.moduleVersions["bad@1.0.0"]; stored {
				t.Errorf("a refused content was stored: %+v", fake.moduleVersions["bad@1.0.0"])
			}
		})
	}
}

// Every kind still publishes a content its renderer can read, so this validation cannot pass by
// refusing everything.
func TestSeatAdminPutModuleVersionAcceptsRenderableContentPerKind(t *testing.T) {
	fake := newFakeSeatAdmin()
	mux := seatAdminTestMux(t, fake)
	cases := map[string]string{
		"instr":    "any text at all\n",
		"doc":      "any text at all\n",
		"mem":      "any text at all\n",
		"skill":    testSkillBlock(t, "# A skill\n"),
		"mcp-mod":  testMCPServer,
		"tool-mod": testToolJSON,
	}
	kinds := map[string]string{
		"instr": "instruction", "doc": "document", "mem": "memory",
		"skill": "skill", "mcp-mod": "mcp", "tool-mod": "tool",
	}
	for slug, content := range cases {
		rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/"+slug+"/versions/1.0.0",
			testModuleBody(t, kinds[slug], content))
		if rec.Code != http.StatusOK {
			t.Errorf("%s (%s): status = %d, want 200: %s", slug, kinds[slug], rec.Code, rec.Body.String())
		}
	}
	if len(fake.moduleVersions) != len(cases) {
		t.Errorf("stored versions = %d, want %d: %+v", len(fake.moduleVersions), len(cases), fake.moduleVersions)
	}
}

// The positive path end to end: a module published through the route, added by a seat overlay,
// resolves and renders — the read that used to fail when the content was unrenderable.
func TestSeatAdminPublishedModuleResolvesInASeat(t *testing.T) {
	fake := newFakeSeatAdmin()
	fake.seedSeatType("coder", "1.0.0")
	fake.seatTypes["coder"].ModuleRefs = []resolver.ModuleRef{{Slug: "base", Version: "1.0.0"}}
	fake.seatTypes["coder"].DefaultRuntime = "omp"
	fake.moduleVersions["base@1.0.0"] = &repositories.ModuleVersion{
		Slug: "base", Version: "1.0.0", Kind: resolver.KindInstruction, Content: "base guidance\n",
	}
	room := fake.seedRoom("dev")
	fake.seats = append(fake.seats, &repositories.Seat{
		ID: "seat-a", RoomID: room.ID, SeatKey: "alice", SeatTypeID: "st-coder",
		PermissionPolicy: "standard", Runtime: "omp",
	})
	mux := seatAdminTestMux(t, fake)

	const markdown = "# Good skill\n\nrendered from the module version\n"
	rec := doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/modules/good-skill/versions/1.0.0",
		testModuleBody(t, "skill", testSkillBlock(t, markdown)))
	if rec.Code != http.StatusOK {
		t.Fatalf("publish: %d %s", rec.Code, rec.Body.String())
	}

	rec = doTestRequest(t, mux, http.MethodPut, "/api/v2/openrig/rooms/dev/seats/alice/overlay",
		`{"ops":[{"kind":"add","slug":"good-skill","version":"1.0.0"}]}`)
	if rec.Code != http.StatusOK {
		t.Fatalf("overlay add: %d %s", rec.Code, rec.Body.String())
	}

	resolved, err := fakeResolutionService(fake).ResolveSeat(context.Background(), "u", "dev", "alice")
	if err != nil {
		t.Fatalf("ResolveSeat: %v", err)
	}
	rendered := ""
	for _, f := range resolved.Files {
		if f.Path == "skills/good-skill/SKILL.md" {
			rendered = f.Content
		}
	}
	if strings.TrimSpace(rendered) != strings.TrimSpace(markdown) {
		t.Errorf("rendered SKILL.md = %q, want the module version's content %q", rendered, markdown)
	}
}
