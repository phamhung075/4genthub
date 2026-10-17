package seatrenderer

// R1 of RULING-seat-context-delivery-model.md: the render is a RESOLUTION RECORD, not a DELIVERY. The
// hub keeps the seat's runtime, permission policy, MCP blocks and the snapshot record, and it stops
// rendering `agent.yaml`, a `startup.files` list, a `skills/<slug>/SKILL.md` list and `guidance/role.md`.
// Measured before the ruling: nothing wrote any of them into a seat's launch directory - no `agent.yaml`,
// no `role.md`, no `guidance/` anywhere under the room root, five launch dirs - so the file half was a
// delivery surface with no delivery, and a path nothing installs is a second source of truth (the seat's
// skills come from the client tree, its role from the seat-tier skill that tree installs).
//
// THE VACUITY GUARD MATTERS AS MUCH AS THE ASSERTION, the same way it does in
// `manage_agent_absent_test.go`: a render that produced nothing at all would satisfy "no retired path"
// while proving nothing. So each runtime is rendered with a full module stack, and its LIVE files must
// appear first - the guide in AGENTS.md with its own words in it, and the per-runtime documents.

import (
	"strings"
	"testing"

	"agenthub/fastmcp/seat_management/domain/resolver"
)

func TestRenderSeatWritesNoRetiredFileHalf(t *testing.T) {
	// A guide (the one module kind whose text reaches a file), a tool module (so codex has a deny list
	// to render) and the platform's mcp block (so each runtime has a server document). The fixture's
	// document, skill and memory modules ride along: they are exactly the kinds the retired half used to
	// write, so they are the ones a regression would reappear through.
	extra := []resolver.ResolvedModule{
		guideModule("guide-fixture", "## Guide: fixture\n\nthe guide's own words\n"),
		{Slug: "comm-guard", Version: "1.0.0", Kind: resolver.KindTool,
			Content: `{"permissions":{"deny":["Bash(4genteam send:*)"],"allow":["Bash(4genteam whoami:*)"]}}`},
		mcpPlatformModule(),
	}
	landmarks := map[string][]string{
		resolver.RuntimeClaudeCode: {agentsMDPath, mcpFragmentPath, settingsFragmentPath},
		resolver.RuntimeCodex:      {agentsMDPath, codexRulesPath},
		resolver.RuntimeOmp:        {agentsMDPath, ompMCPPath, ompConfigPath},
		resolver.RuntimeAgy:        {agentsMDPath},
	}
	for runtime, want := range landmarks {
		spec, err := RenderSeat(withMCP(seatFixture(runtime), extra...), testMCPURL)
		if err != nil {
			t.Fatalf("%s: RenderSeat: %v", runtime, err)
		}
		rendered := map[string]bool{}
		for _, path := range filePaths(spec) {
			rendered[path] = true
		}
		for _, path := range want {
			if !rendered[path] {
				t.Fatalf("%s: the render no longer writes %q, so the absence below is not read on the render it thinks it is (%v)",
					runtime, path, filePaths(spec))
			}
		}
		// The AGENTS.md landmark is real text, not an empty file: if the guide stopped arriving, the
		// absence check would still pass while the seat's one delivered document had gone blank.
		if agents := fileContent(t, spec, agentsMDPath); !strings.Contains(agents, "the guide's own words") {
			t.Fatalf("%s: AGENTS.md does not carry the guide's own words:\n%s", runtime, agents)
		}
		for _, path := range filePaths(spec) {
			if path == "agent.yaml" || path == "startup.files" ||
				strings.HasPrefix(path, "guidance/") || strings.HasPrefix(path, "skills/") {
				t.Errorf("%s: the render still writes the retired path %q", runtime, path)
			}
		}
	}
}
