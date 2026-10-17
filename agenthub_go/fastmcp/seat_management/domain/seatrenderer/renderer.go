// Package seatrenderer renders a resolved seat snapshot into a deterministic document set: the seat's
// runtime fragments, its guide and limits document (AGENTS.md), and the limits' own config document.
//
// THE HUB'S FILE HALF IS RETIRED (ruling RULING-seat-context-delivery-model.md, R1). This package used to
// also emit `agent.yaml` (with a skills list and a runtime-resource declaration), `startup.files` and
// `guidance/role.md`. Nothing wrote any of them into a seat's launch directory - measured on all five seat
// dirs of this room - and two of the three had no reader anywhere: the seat's role is the client skill
// tree's seat tier (`skills/rooms/<room>/<seat>/<seat>-role`), the seat's skills are installed by the
// runtime (`install_seat_skills`), and the seat's `mcp.json` is written by the runtime at start. What the
// hub still says about a seat is its POLICY: runtime, permission policy, MCP blocks, module refs, and the
// resolution record with its hash (R4: a record, never a delivery check).
package seatrenderer

import (
	"encoding/json"
	"fmt"
	"slices"
	"strings"

	"agenthub/fastmcp/seat_management/domain/mcpblock"
	"agenthub/fastmcp/seat_management/domain/resolver"
)

const (
	// agentsMDPath is the seat's guide document, the file omp loads into every session from the
	// agent directory. Packet 6 step 1 moved the guides out of a script that wrote it by hand and
	// into library blocks, so the render writes it from those blocks; a seat whose resolution carries
	// no guide block gets NO file, the same absence rule as the MCP document.
	agentsMDPath = "AGENTS.md"
	// guideSlugPrefix is what makes a block a guide: the guides are `instruction` modules named
	// `guide-common` and `guide-<seat>`, and their destination is AGENTS.md rather than the guidance
	// channel. One destination per module - a guide in both places would be the same text twice.
	guideSlugPrefix      = "guide-"
	mcpFragmentPath      = "runtime/claude-mcp.fragment.json"
	settingsFragmentPath = "runtime/claude-settings.fragment.json"
	codexRulesPath       = "runtime/codex.rules"
	ompMCPPath           = "runtime/omp-mcp.json"
	ompConfigPath        = "runtime/omp-config.yml"
)

// RenderSeat renders a resolved seat as a SeatSpec: the runtime fragments the
// seat's runtime supports, the seat's guide and limits document, and the config
// document the client installs.
func RenderSeat(seat resolver.ResolvedSeat, mcpURL string) (*SeatSpec, error) {
	if err := resolver.CheckRuntime(seat.Runtime); err != nil {
		return nil, err
	}

	// A tool module is a Claude settings fragment: a seat on another runtime does not apply it
	// (a seat can switch runtime while its pinned seat type version keeps the tool module).
	toolModules := modulesOfKind(seat.Modules, resolver.KindTool)
	// An mcp module mounts one MCP server. The seat's mcp blocks decide which servers mount;
	// a seat with none mounts no server and no fragment is rendered.
	mcpModules := modulesOfKind(seat.Modules, resolver.KindMCP)

	var mcpFragment, settingsFragment string
	// ONE MCP DOCUMENT, TWO DESTINATIONS, and neither is a declaration any more: claude-code and omp
	// each get the fragment as a plain FILE, and the client has no reason to be told a path twice. omp
	// DOES read an MCP document — measured 2026-10-06 on the real runtime: it reads a project
	// `.mcp.json` at startup, expands ${VAR} in a header and in a stdio server's `env`, and reads
	// `$PI_CODING_AGENT_DIR/.mcp.json` for the agent itself, which is where the client installs this
	// file so each seat carries its own server set without a per-seat cwd and without touching the
	// operator's rig-root file.
	if len(mcpModules) > 0 && (receivesClaudeFragments(seat.Runtime) || seat.Runtime == resolver.RuntimeOmp) {
		fragment, err := renderMCPFragment(seat, mcpURL)
		if err != nil {
			return nil, err
		}
		mcpFragment = fragment
	}
	if receivesClaudeFragments(seat.Runtime) && len(toolModules) > 0 {
		settings, err := mergeToolModules(toolModules)
		if err != nil {
			return nil, err
		}
		settingsFragment, err = renderSettingsFragment(settings)
		if err != nil {
			return nil, err
		}
	}

	// A codex seat gets the seat's Bash deny list as a codex execpolicy rules file. the client has no
	// codex rules runtime-resource type to install it (its only codex fragment type merges a TOML
	// fragment into ~/.codex/config.toml, and config.toml cannot express a per-command deny), so
	// the file travels with the render and the client installs it into a rules/ folder of an
	// active codex config layer. See NEXT_GEN (G3, owner decision 2026-10-05).
	var codexRules string
	if seat.Runtime == resolver.RuntimeCodex && len(toolModules) > 0 {
		merged, err := mergeToolModules(toolModules)
		if err != nil {
			return nil, err
		}
		codexRules = renderCodexRules(merged)
	}

	// ONE FOLD, TWO EMISSIONS: the same parsed set produces the document the runtime reads and the
	// words the seat reads, so a rule and its plain-language line cannot drift apart.
	policySet, err := FoldPolicies(seat.Modules)
	if err != nil {
		return nil, err
	}

	// WHAT IS LEFT IS WHAT HAS A READER: the seat's guide and limits document, the runtime fragments
	// and the client's config document. `agent.yaml`, `startup.files`, the `skills/<slug>/SKILL.md`
	// list and `guidance/role.md` are retired (R1): the skill files existed to be reached through
	// `agent.yaml`'s declaration, which is gone with them.
	var files []SeatSpecFile
	if len(guideModules(seat)) > 0 || policySet.Role != "" {
		// The guides AND the limits text, in the one document omp loads into a session. A seat with
		// limits but no guide gets it too: the limits are words the seat must read, not a decoration
		// on the guides. A seat with neither still gets NO file, which is the absence rule.
		files = append(files, SeatSpecFile{Path: agentsMDPath, Content: renderAgentsMD(seat, policySet)})
	}
	if receivesClaudeFragments(seat.Runtime) {
		if mcpFragment != "" {
			files = append(files, SeatSpecFile{Path: mcpFragmentPath, Content: mcpFragment})
		}
		if settingsFragment != "" {
			files = append(files, SeatSpecFile{Path: settingsFragmentPath, Content: settingsFragment})
		}
	}
	if codexRules != "" {
		// Deliberately a plain file and NOT a runtime resource: the client has no codex resource type
		// that installs rules, and declaring an invented type would be a format the platform does
		// not understand. The client installs this file; see the G3 note.
		files = append(files, SeatSpecFile{Path: codexRulesPath, Content: codexRules})
	}
	if seat.Runtime == resolver.RuntimeOmp && (mcpFragment != "" || policySet.Role != "") {
		// Same shape as the codex rules file and for the same reason. The client installs it as
		// `<seat agent dir>/.mcp.json`; a seat with no mcp block gets NO file, which is the
		// acceptance's "a seat with no mcp block gets none".
		if mcpFragment != "" {
			files = append(files, SeatSpecFile{Path: ompMCPPath, Content: mcpFragment})
		}
		// AND THE SETTING THAT MAKES THE ENTRY MOUNT, in the same delivery because either half
		// alone fails the seat: see ompMCPStartupTimeoutConfig for the measured root cause.
		//
		// A POLICY BLOCK SUPERSEDES THE CONSTANT rather than adding a second document for the same
		// file: the fold's document carries the startup setting when a block speaks about it AND the
		// rules, so the client installs one document and no precedence rule is needed.
		configDoc := ompMCPStartupTimeoutConfig
		if policySet.Role != "" {
			configDoc, err = RenderPolicyConfig(policySet)
			if err != nil {
				return nil, err
			}
		}
		files = append(files, SeatSpecFile{Path: ompConfigPath, Content: configDoc})
	}

	return &SeatSpec{
		Slug:    seat.SeatType,
		Name:    seat.SeatType,
		Version: seat.SeatTypeVersion,
		Files:   files,
	}, nil
}

// receivesClaudeFragments reports whether a runtime takes the Claude MCP and settings fragments.
// Only claude-code does; codex takes a rules file, omp takes the MCP document and its config, and agy
// takes no rendered file at all (its skills and its guidance come from the client tree). Stated
// positively so a runtime added later defaults to no Claude fragment instead of silently receiving one.
func receivesClaudeFragments(runtime string) bool {
	return runtime == resolver.RuntimeClaudeCode
}

// guideModules returns the seat's guide blocks, in resolution order.
func guideModules(seat resolver.ResolvedSeat) []resolver.ResolvedModule {
	var out []resolver.ResolvedModule
	for _, m := range modulesOfKind(seat.Modules, resolver.KindInstruction) {
		if strings.HasPrefix(m.Slug, guideSlugPrefix) {
			out = append(out, m)
		}
	}
	return out
}

// renderAgentsMD lays the seat's guides out as the one document omp loads into every session.
//
// The blocks already carry their own headings (each guide is written as `## Guide: <seat>`), so this
// adds provenance and separating newlines and NOT a second heading - a renderer that re-heads a block
// that heads itself is the duplication this step exists to remove.
func renderAgentsMD(seat resolver.ResolvedSeat, policySet *PolicySet) string {
	var b strings.Builder
	fmt.Fprintf(&b, "<!-- seat-hash: %s -->\n", seat.Hash)
	fmt.Fprintf(&b, "<!-- seat-type-version: %s -->\n", seat.SeatTypeVersion)
	b.WriteString("<!-- rendered from this seat's guide blocks; edits here are overwritten -->\n")
	for _, m := range guideModules(seat) {
		b.WriteString("\n")
		b.WriteString(strings.TrimRight(m.Content, "\n"))
		b.WriteString("\n")
	}
	if policySet != nil && policySet.Role != "" {
		// The limits, from the SAME fold that produced the config document.
		b.WriteString("\n")
		b.WriteString(RenderPolicyLimits(policySet))
	}
	return b.String()
}

// permissionListKeys are the permissions lists that tool modules add to rather than replace,
// so a later module cannot drop another module's deny rule.
var permissionListKeys = []string{"deny", "allow", "ask"}

// renderCodexRules renders the seat's Bash deny list as a codex execpolicy file (Starlark).
// Codex reads `prefix_rule` entries from a `.rules` file in a `rules/` folder of an active config
// layer and applies the most restrictive decision, so `forbidden` blocks a matching command
// without prompting (https://developers.openai.com/codex/exec-policy, "Rules"). The pattern is
// matched against the command's argument list, so a command hidden inside a shell wrapper is a
// limitation of the documented mechanism itself, not of this file.
func renderCodexRules(merged map[string]any) string {
	patterns, skipped := codexBashDenyPatterns(merged)
	var b strings.Builder
	b.WriteString("# Comm-guard for codex (execpolicy). Generated from the seat's tool modules.\n")
	b.WriteString("# Codex loads this file only when it sits in `rules/` inside an active config layer, for\n")
	b.WriteString("# example ~/.codex/rules/ or a trusted project's .codex/rules/. Rules are experimental.\n")
	b.WriteString("# The most restrictive decision wins: forbidden > prompt > allow.\n")
	for _, pattern := range patterns {
		b.WriteString("\nprefix_rule(\n")
		b.WriteString("    pattern = [" + quotedPattern(pattern) + "],\n")
		b.WriteString("    decision = \"forbidden\",\n")
		b.WriteString("    justification = \"Use `4genteam send`, the audited send path, instead of a direct command.\",\n")
		b.WriteString(")\n")
	}
	if len(skipped) > 0 {
		b.WriteString("\n# Not expressible as a command-prefix rule; listed rather than dropped:\n")
		for _, entry := range skipped {
			b.WriteString("#   " + entry + "\n")
		}
	}
	return b.String()
}

// codexBashDenyPatterns turns the merged `permissions.deny` entries into codex command prefixes.
// Only `Bash(<command>:*)` can be expressed; anything else comes back as skipped so the caller
// keeps it visible instead of silently dropping a policy the seat believes it carries.
func codexBashDenyPatterns(merged map[string]any) (patterns [][]string, skipped []string) {
	permissions, _ := merged["permissions"].(map[string]any)
	deny, _ := permissions["deny"].([]any)
	seen := make(map[string]bool, len(deny))
	for _, raw := range deny {
		entry, ok := raw.(string)
		if !ok || seen[entry] {
			continue
		}
		seen[entry] = true
		pattern, ok := codexPatternFromBashEntry(entry)
		if !ok {
			skipped = append(skipped, entry)
			continue
		}
		patterns = append(patterns, pattern)
	}
	return patterns, skipped
}

// codexPatternFromBashEntry converts `Bash(4genteam send:*)` to ["4genteam", "send"]. The `:*` suffix means
// "any arguments", which is what a codex prefix rule matches.
func codexPatternFromBashEntry(entry string) ([]string, bool) {
	const prefix = "Bash("
	if !strings.HasPrefix(entry, prefix) || !strings.HasSuffix(entry, ")") {
		return nil, false
	}
	command := strings.TrimSuffix(strings.TrimPrefix(entry, prefix), ")")
	command = strings.TrimSuffix(command, ":*")
	fields := strings.Fields(command)
	if len(fields) == 0 {
		return nil, false
	}
	return fields, true
}

func quotedPattern(fields []string) string {
	quoted := make([]string, len(fields))
	for i, field := range fields {
		quoted[i] = fmt.Sprintf("%q", field)
	}
	return strings.Join(quoted, ", ")
}

// ParseToolSettings reads one tool module's content: the settings object the runtime's settings
// fragment merges. mergeToolModules below calls it, and so does the module publish validator
// (domain/modulecontent) — exported here, rather than re-implemented there, so the rule a tool
// module is held to at the store and the parse the renderer performs cannot drift, exactly as the
// skill and mcp kinds delegate to skillblock.Parse and mcpblock.Parse. A change to what the tool
// renderer accepts therefore changes the publish rule with it.
func ParseToolSettings(content string) (map[string]any, error) {
	var obj map[string]any
	if err := json.Unmarshal([]byte(content), &obj); err != nil {
		return nil, fmt.Errorf("content is not a JSON object: %w", err)
	}
	return obj, nil
}

// mergeToolModules merges tool module JSON objects in module order. A top-level key present
// in several modules takes the later value, except `permissions`: its deny, allow and ask lists
// are the deduplicated union in order of appearance, and its other keys follow later-wins.
func mergeToolModules(modules []resolver.ResolvedModule) (map[string]any, error) {
	merged := make(map[string]any)
	for _, m := range modules {
		obj, err := ParseToolSettings(m.Content)
		if err != nil {
			return nil, fmt.Errorf("tool module %q: %w", m.Slug, err)
		}
		for key, value := range obj {
			if key != "permissions" {
				merged[key] = value
				continue
			}
			permissions, err := mergePermissions(merged[key], value)
			if err != nil {
				return nil, fmt.Errorf("tool module %q: %w", m.Slug, err)
			}
			merged[key] = permissions
		}
	}
	return merged, nil
}

func mergePermissions(current, incoming any) (map[string]any, error) {
	next, ok := incoming.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("permissions must be a JSON object")
	}
	out := make(map[string]any)
	if previous, ok := current.(map[string]any); ok {
		for key, value := range previous {
			out[key] = value
		}
	}
	for key, value := range next {
		if !slices.Contains(permissionListKeys, key) {
			out[key] = value
			continue
		}
		list, err := stringList(value)
		if err != nil {
			return nil, fmt.Errorf("permissions.%s: %w", key, err)
		}
		union, ok := out[key].([]any)
		if !ok {
			union = []any{}
		}
		for _, entry := range list {
			if !slices.Contains(union, any(entry)) {
				union = append(union, entry)
			}
		}
		out[key] = union
	}
	return out, nil
}

func stringList(value any) ([]string, error) {
	items, ok := value.([]any)
	if !ok {
		return nil, fmt.Errorf("must be an array of strings")
	}
	out := make([]string, len(items))
	for i, item := range items {
		str, ok := item.(string)
		if !ok {
			return nil, fmt.Errorf("must be an array of strings")
		}
		out[i] = str
	}
	return out, nil
}

// renderMCPFragment merges the seat's mounted mcp blocks, in the seat's resolved order, into
// one MCP fragment: one block is one whole server, keyed by the server name its payload names.
// The platform placeholder in a block's url is resolved from mcpURL; every other ${VAR} is
// left for the client runtime to expand. No block renders no server.
func renderMCPFragment(seat resolver.ResolvedSeat, mcpURL string) (string, error) {
	modules := modulesOfKind(seat.Modules, resolver.KindMCP)
	servers := make(map[string]any, len(modules))
	for _, m := range modules {
		server, err := mcpblock.Parse(m.Content)
		if err != nil {
			return "", fmt.Errorf("mcp module %q: %w", m.Slug, err)
		}
		if _, mounted := servers[server.Name]; mounted {
			return "", fmt.Errorf("mcp module %q: server %q is already mounted by another block", m.Slug, server.Name)
		}
		server = server.WithPlatformURL(mcpURL)
		if server.Type == mcpblock.TypeHTTP {
			// THE SEAT'S OWN IDENTITY, stamped OVER whatever the block carried: attribution must not
			// be claimable by the thing being attributed, the same reason a seat-scoped overlay may
			// not grant itself a block. A seat without an identity gets no header and no server,
			// rather than one that claims to be nobody.
			if seat.RoomSlug == "" || seat.SeatKey == "" {
				return "", fmt.Errorf("mcp module %q: the seat has no room/seat identity, so a call through this block could not say who made it", m.Slug)
			}
			if server.Headers == nil {
				server.Headers = make(map[string]string, 1)
			}
			server.Headers[mcpblock.SeatHeader] = mcpblock.SeatValue(seat.RoomSlug, seat.SeatKey)
			if err := mcpblock.CheckURL(server.URL); err != nil {
				return "", fmt.Errorf("mcp module %q: %w", m.Slug, err)
			}
		}
		servers[server.Name] = server.Fragment()
	}
	return marshalJSON(map[string]any{"mcpServers": servers}, "mcp fragment")
}

// ompMCPStartupTimeoutConfig is installed by the client as `<seat agent dir>/config.yml`. It is HALF
// THE DELIVERY: the rendered `runtime/omp-mcp.json` declares the server, and this setting is what
// makes the seat WAIT for it.
//
// THE MEASURED ROOT CAUSE (2026-10-06, owner-found and verified on the live rig): `mcp.startupTimeoutMs`
// defaults to 250 ms — "wait this many milliseconds for initial MCP tool discovery; 0 waits until
// connections settle". A LOCAL stdio server (the deepseek bridge) connects inside that window; a
// REMOTE HTTPS server does not, so a seat's first turn started with the local server only and its
// device list showed no agenthub tools. **THE DEFAULT DELAYS THE MOUNT RATHER THAN PREVENTING IT**
// (measured on the reviewer's own seat: the device appeared between two attempts with NO relaunch), so
// this setting is what makes a seat WAIT for its connections at STARTUP — DETERMINISTIC INSTEAD OF
// EVENTUAL — and the relaunch is what makes an already-RUNNING seat read the setting at all, because
// the config file is read when the process starts.
//
// 0 is the value that means WAIT UNTIL CONNECTIONS SETTLE; it is not "no timeout" and it is not a
// disabled setting.
//
// IT MUST LIVE IN THE AGENT DIRECTORY AND NOT THE ENVIRONMENT: the runner hands the runtime an
// allowlist of environment variables that is DENY BY DEFAULT, so an `MCP_STARTUP_TIMEOUT_MS` variable
// never reaches the process (measured: 14 names reach it, and this is not among them). The agent dir
// is the only per-seat place the runtime reads settings from.
const ompMCPStartupTimeoutConfig = "mcp:\n  startupTimeoutMs: 0\n"

// renderSettingsFragment writes a JSON settings fragment, the shape claude-code takes.
func renderSettingsFragment(settings map[string]any) (string, error) {
	return marshalJSON(settings, "settings fragment")
}

func marshalJSON(v any, label string) (string, error) {
	out, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return "", fmt.Errorf("encode %s: %w", label, err)
	}
	return string(out) + "\n", nil
}

func modulesOfKind(modules []resolver.ResolvedModule, kind resolver.ModuleKind) []resolver.ResolvedModule {
	out := make([]resolver.ResolvedModule, 0)
	for _, m := range modules {
		if m.Kind == kind {
			out = append(out, m)
		}
	}
	return out
}
