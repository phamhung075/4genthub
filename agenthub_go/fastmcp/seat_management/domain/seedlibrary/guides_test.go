package seedlibrary

// Packet 6, step 1: the seat guides the interim script wrote by hand are now library content.
// These tests hold the LIBRARY half: the guides load as instruction blocks, the shared one is
// carried by every seat type, and a block the publish route would refuse is refused at load too —
// so neither an empty guide nor a credential-shaped one can reach a seat by the library path.

import (
	"strings"
	"testing"
	"testing/fstest"

	"agenthub/fastmcp/seat_management/domain/resolver"
)

// guideSeats are the seats whose own guide ships as blocks/guide-<seat>.md. The shared guide is
// shared-modules/guide-common.md and is asserted separately, because it reaches seats by a
// different route (every seat type carries it) than the per-seat ones.
var guideSeats = []string{
	"context-dev", "fe-dev", "feedback-dev", "go-dev",
	"lead", "reviewer", "skills-dev", "web-dev", "writer",
}

func TestEmbeddedSeatGuidesLoadAsInstructionBlocks(t *testing.T) {
	blocks, err := loadBlocks(embedded)
	if err != nil {
		t.Fatalf("loadBlocks: %v", err)
	}
	for _, seat := range guideSeats {
		slug := "guide-" + seat
		block, ok := blocks[slug]
		if !ok {
			t.Errorf("blocks/%s.md did not load", slug)
			continue
		}
		if block.Kind != resolver.KindInstruction {
			t.Errorf("%s: kind = %q, want %q", slug, block.Kind, resolver.KindInstruction)
		}
		if !strings.Contains(block.Content, "## Guide: "+seat) {
			t.Errorf("%s: content does not carry its own guide heading", slug)
		}
	}
}

func TestGuideCommonIsCarriedByEverySeatType(t *testing.T) {
	seeds, err := Load()
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if len(seeds) == 0 {
		t.Fatal("no seat types loaded")
	}
	for _, seed := range seeds {
		seen := 0
		for _, m := range seed.Modules {
			if m.Slug != "guide-common" {
				continue
			}
			seen++
			if m.Kind != resolver.KindInstruction {
				t.Errorf("%s: guide-common kind = %q, want %q", seed.SeatTypeSlug, m.Kind, resolver.KindInstruction)
			}
			if !strings.Contains(m.Content, "Working procedure") {
				t.Errorf("%s: guide-common does not carry the shared working procedure", seed.SeatTypeSlug)
			}
		}
		if seen != 1 {
			t.Errorf("%s: guide-common mounted %d times, want exactly 1", seed.SeatTypeSlug, seen)
		}
	}
}

// The loader refuses a block whose kind it cannot name, rather than skipping the file: a skipped
// file is a block that sits in the shelf with nothing able to load it.
func TestLoadBlocksRefusesAnExtensionItCannotName(t *testing.T) {
	fsys := fstest.MapFS{"blocks/mystery.txt": &fstest.MapFile{Data: []byte("hello\n")}}
	_, err := loadBlocks(fsys)
	if err == nil {
		t.Fatal("a .txt block was accepted")
	}
	if !strings.Contains(err.Error(), ".json (mcp) or .md (instruction)") {
		t.Fatalf("refusal does not name the extensions: %v", err)
	}
}

// The route refuses an empty content in its own preamble, so the library refuses one too. Without
// this the shelf would hold a guide that renders as nothing.
func TestLoadBlocksRefusesAnEmptyGuide(t *testing.T) {
	fsys := fstest.MapFS{"blocks/guide-empty.md": &fstest.MapFile{Data: []byte("  \n\t\n")}}
	_, err := loadBlocks(fsys)
	if err == nil {
		t.Fatal("an empty instruction block was accepted")
	}
	if !strings.Contains(err.Error(), "block is empty") {
		t.Fatalf("refusal does not say the block is empty: %v", err)
	}
}

// The spec's rule is that secrets are never rendered into a module, and the route enforces it with
// secretscan before the kind's parse. An instruction block accepts any text, so without this check
// the library path would be the way a credential reached a seat's guidance.
func TestLoadBlocksRefusesAGuideCarryingACredential(t *testing.T) {
	fsys := fstest.MapFS{"blocks/guide-leaky.md": &fstest.MapFile{Data: []byte("export TOKEN=abcdef123456\n")}}
	_, err := loadBlocks(fsys)
	if err == nil {
		t.Fatal("a credential-shaped instruction block was accepted")
	}
	if !strings.Contains(err.Error(), "credential-shaped") {
		t.Fatalf("refusal does not name the credential: %v", err)
	}
}
