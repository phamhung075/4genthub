package seedlibrary

// Packet 6 step 1 (b): the ten overlay ops a room creation would carry are `add guide-<seat>@1.0.0`,
// one per seat. This measures the EFFECT of each one with the library's own block - the seat's
// rendered AGENTS.md carries that seat's guide, verbatim and exactly once, and the guidance channel
// does not carry it at all - so the payload is proven without a room, without a cloud and without a
// hand-built fixture. The renderer's fixtures pin the SPLIT; this pins that the real shelf feeds it.
//
// It lives in package seedlibrary because the per-seat blocks are reachable only through the shelf's
// own loader; the loader must never import anything that reaches seatrenderer, which is why the
// import direction here is test-only (the cycle step 1 refused is written at validateBlockContent).

import (
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/seatrenderer"
)

func TestEverySeatGuideBlockRendersIntoTheSeatsAgentsMD(t *testing.T) {
	blocks, err := loadBlocks(embedded)
	if err != nil {
		t.Fatalf("loadBlocks: %v", err)
	}
	for _, seat := range guideSeats {
		slug := "guide-" + seat
		block, ok := blocks[slug]
		if !ok {
			t.Errorf("%s: not in the shelf", slug)
			continue
		}
		if block.Kind != resolver.KindInstruction {
			t.Errorf("%s: kind = %q, want %q", slug, block.Kind, resolver.KindInstruction)
			continue
		}

		// The seat's resolution would carry this block after the overlay op adds it; a resolved seat
		// carrying nothing else isolates the guide's own effect.
		spec, err := seatrenderer.RenderSeat(resolver.ResolvedSeat{
			SeatType:        seat,
			SeatTypeVersion: "1.0.0",
			Runtime:         resolver.RuntimeOmp,
			Modules: []resolver.ResolvedModule{{
				Slug: block.Slug, Version: "1.0.0", Kind: block.Kind, Content: block.Content,
			}},
		}, "https://api.4genthub.com/mcp")
		if err != nil {
			t.Errorf("%s: RenderSeat: %v", slug, err)
			continue
		}

		var agents, guidance string
		for _, f := range spec.Files {
			switch f.Path {
			case "AGENTS.md":
				agents = f.Content
			case "guidance/role.md":
				guidance = f.Content
			}
		}
		if agents == "" {
			t.Errorf("%s: a seat carrying this guide rendered no AGENTS.md", slug)
			continue
		}
		// Verbatim: the renderer adds a provenance header and strips trailing newlines, nothing else.
		if want := strings.TrimRight(block.Content, "\n"); !strings.Contains(agents, want) {
			t.Errorf("%s: AGENTS.md does not carry the block's own text verbatim", slug)
		}
		if got := strings.Count(agents, "## Guide: "+seat); got != 1 {
			t.Errorf("%s: its own heading appears %d times, want exactly 1", slug, got)
		}
		if strings.Contains(guidance, "## Guide: "+seat) {
			t.Errorf("%s: the guide also reached guidance/role.md - a guide has ONE destination", slug)
		}
	}
}
