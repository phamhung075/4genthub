package seatrenderer

// Packet 6, step 1: the fixtures in renderer_test.go pin that a guide goes to AGENTS.md and to nothing
// else. This pins the other half - that what that document delivers is the text the LIBRARY actually
// ships, not a fixture that happens to look like it. A render path tested only against hand-built blocks
// cannot tell you the real guide survives being parsed, resolved and rendered.

import (
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/seedlibrary"
)

func TestTheLibrarysOwnSharedGuideRendersIntoAgentsMD(t *testing.T) {
	seeds, err := seedlibrary.Load()
	if err != nil {
		t.Fatalf("seedlibrary.Load: %v", err)
	}
	if len(seeds) == 0 {
		t.Fatal("no seat types loaded")
	}

	// Every seat type carries the shared guide, so the first seed's copy is the library's own text.
	var guide *resolver.ResolvedModule
	for i, m := range seeds[0].Modules {
		if m.Slug == "guide-common" {
			copied := m
			guide = &resolver.ResolvedModule{Slug: copied.Slug, Version: copied.Version, Kind: copied.Kind, Content: copied.Content}
			_ = i
			break
		}
	}
	if guide == nil {
		t.Fatalf("the library's shared guide is not mounted on seat type %q", seeds[0].SeatTypeSlug)
	}
	if guide.Kind != resolver.KindInstruction {
		t.Fatalf("guide-common kind = %q, want %q", guide.Kind, resolver.KindInstruction)
	}

	seat := resolver.ResolvedSeat{
		SeatType:        seeds[0].SeatTypeSlug,
		SeatTypeVersion: seeds[0].Version,
		Runtime:         resolver.RuntimeOmp,
		Modules:         []resolver.ResolvedModule{*guide},
	}
	spec, err := RenderSeat(seat, "https://api.4genthub.com/mcp")
	if err != nil {
		t.Fatalf("RenderSeat: %v", err)
	}

	agents := fileContent(t, spec, "AGENTS.md")
	if agents == "" {
		t.Fatal("AGENTS.md was not rendered for a seat carrying the library's shared guide")
	}
	// Two headings that exist in the shipped file and nowhere in a fixture, so this cannot pass by
	// rendering an empty or invented block.
	for _, want := range []string{"Working procedure", "How to call a tool", "The loop"} {
		if !strings.Contains(agents, want) {
			t.Errorf("AGENTS.md lacks %q, which the shipped guide carries", want)
		}
	}
	// The guide's own words, not a summary of them: one real sentence from the shipped text.
	if !strings.Contains(agents, "Write a JSON object to the device path") {
		t.Error("AGENTS.md does not carry the shipped guide's own sentence about calling a tool")
	}
	// And the one-destination rule survives the real content: the shipped guide lands in the one
	// document and in NO other file at all, which is what the retired guidance channel leaves behind.
	for _, f := range spec.Files {
		if f.Path != "AGENTS.md" && strings.Contains(f.Content, "Working procedure") {
			t.Errorf("%s carries the shared guide too: a guide has ONE destination", f.Path)
		}
	}
	// The guide is also the whole render for this seat: it carries no server block, so a runtime file
	// appearing here would be an mcp document for a seat that mounts none.
	if got := filePaths(spec); !reflect.DeepEqual(got, []string{"AGENTS.md"}) {
		t.Errorf("a seat carrying only the shared guide rendered %v, want just AGENTS.md", got)
	}
}
