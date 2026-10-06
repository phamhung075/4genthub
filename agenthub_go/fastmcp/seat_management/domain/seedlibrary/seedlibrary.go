// Package seedlibrary loads the seat types embedded in the binary.
package seedlibrary

import (
	"bytes"
	"crypto/sha256"
	"embed"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"path"
	"regexp"
	"sort"
	"strings"

	"agenthub/fastmcp/seat_management/domain/mcpblock"
	"agenthub/fastmcp/seat_management/domain/repositories"
	"agenthub/fastmcp/seat_management/domain/resolver"
	"agenthub/fastmcp/seat_management/domain/secretscan"
	"agenthub/fastmcp/seat_management/domain/seedmap"
	"agenthub/fastmcp/seat_management/domain/skillblock"

	"gopkg.in/yaml.v3"
)

//go:embed seat-types/*.yaml shared-modules/* blocks/*
var embedded embed.FS

const (
	seatTypesDir     = "seat-types"
	sharedModulesDir = "shared-modules"
	blocksDir        = "blocks"
)

// sharedModuleFiles lists the modules every seat type carries: slug, kind and the file in
// shared-modules/ that holds the content. comm-guard is the Claude settings fragment that
// denies direct messaging commands; comm-guard-skill tells the seat what to use instead.
//
// A skill module's content is a block, not raw markdown, so the file it is built from needs a
// provenance path: the repository-relative path of that same file, which the drift check
// re-reads and re-hashes. The path includes agenthub_go/ because the drift check resolves it
// against the repository root, not the Go module root.
var sharedModuleFiles = []struct {
	slug       string
	kind       resolver.ModuleKind
	file       string
	sourcePath string
}{
	{"comm-guard", resolver.KindTool, "comm-guard.json", ""},
	{
		"comm-guard-skill", resolver.KindSkill, "comm-guard-skill.md",
		"agenthub_go/fastmcp/seat_management/domain/seedlibrary/shared-modules/comm-guard-skill.md",
	},
	// The seat's MCP guidance: what the platform's own server is FOR, and the two tools a seat is
	// expected to reach for. Carried by every seat type because a seat type that mounts no server is
	// told so by the render (no file, no tools) rather than by this text being absent — and because a
	// seat whose blocks change should not need a second edit here to learn what to do with them.
	{"mcp-usage", resolver.KindInstruction, "mcp-usage.md", ""},
	// The working procedure every seat follows, as the library's own content rather than a script
	// that writes each seat's AGENTS.md by hand (packet 6, step 1). It is SHARED, so every seat
	// type carries it; the per-seat guides are blocks the shelf holds for a seat to mount.
	{"guide-common", resolver.KindInstruction, "guide-common.md", ""},
}

var (
	slugPattern = regexp.MustCompile(`^[a-z][a-z0-9-]*$`)
)

type ruleFile struct {
	Name    string `yaml:"name"`
	Content string `yaml:"content"`
}

type seatTypeFile struct {
	Slug           string     `yaml:"slug"`
	Name           string     `yaml:"name"`
	Description    string     `yaml:"description"`
	DefaultRuntime string     `yaml:"default_runtime"`
	MCPBlocks      []string   `yaml:"mcp_blocks"`
	ModuleRefs     []string   `yaml:"module_refs"`
	Role           string     `yaml:"role"`
	Rules          []ruleFile `yaml:"rules"`
	OutputFormat   string     `yaml:"output_format"`
}

// Load returns the seeds of the embedded seat types, sorted by slug. It first checks the shelf's
// recorded provenance pairing, so a library whose bytes no longer match what the lock says is
// refused here rather than discovered by a drift check that would then be comparing against a
// pairing already known to be wrong.
func Load() ([]seedmap.Seed, error) {
	if err := VerifyGuidePairing(); err != nil {
		return nil, err
	}
	return LoadFS(embedded)
}

// LoadFS parses every seat-types/*.yaml of fsys; slugs must be unique across files. The
// shared modules and the published MCP blocks come from the same filesystem.
func LoadFS(fsys fs.FS) ([]seedmap.Seed, error) {
	names, err := fs.Glob(fsys, seatTypesDir+"/*.yaml")
	if err != nil {
		return nil, err
	}
	shared, err := loadSharedModules(fsys)
	if err != nil {
		return nil, err
	}
	blocks, err := loadBlocks(fsys)
	if err != nil {
		return nil, err
	}
	seeds := make([]seedmap.Seed, 0, len(names))
	owner := make(map[string]string, len(names))
	for _, name := range names {
		data, err := fs.ReadFile(fsys, name)
		if err != nil {
			return nil, err
		}
		seed, err := Parse(name, data, shared, blocks)
		if err != nil {
			return nil, err
		}
		if previous, ok := owner[seed.SeatTypeSlug]; ok {
			return nil, fmt.Errorf("%s: slug %q already defined in %s", name, seed.SeatTypeSlug, previous)
		}
		owner[seed.SeatTypeSlug] = name
		seeds = append(seeds, seed)
	}
	sort.Slice(seeds, func(i, j int) bool { return seeds[i].SeatTypeSlug < seeds[j].SeatTypeSlug })
	return seeds, nil
}

func loadSharedModules(fsys fs.FS) ([]seedmap.SeedModule, error) {
	modules := make([]seedmap.SeedModule, 0, len(sharedModuleFiles))
	for _, f := range sharedModuleFiles {
		data, err := fs.ReadFile(fsys, sharedModulesDir+"/"+f.file)
		if err != nil {
			return nil, err
		}
		content := string(data)
		if f.kind == resolver.KindSkill {
			// A skill module is a block, not raw markdown. This seed authors its skill in-tree,
			// so the provenance is the committed file itself: its repository-relative path and
			// the sha256 of the bytes just read. Marshalling here means the block's text and
			// its digest come from one read and cannot drift apart in the repository.
			block, err := skillblock.Marshal(skillblock.Block{
				Content:    content,
				SourcePath: f.sourcePath,
				SHA256:     sha256Hex(data),
			})
			if err != nil {
				return nil, fmt.Errorf("%s: %w", f.file, err)
			}
			content = block
		}
		modules = append(modules, seedmap.SeedModule{Slug: f.slug, Kind: f.kind, Content: content})
	}
	return modules, nil
}

// sha256Hex is the lowercase hex sha256 of data, the digest rule skill blocks record.
func sha256Hex(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

// loadBlocks reads the library's published blocks, one file per block, the file name without its
// extension being the module slug. The extension states the kind: .json is an MCP block whose
// content is one server in the mcpblock payload shape, .md is an instruction block whose content
// is the text a seat renders into its guidance. A block is validated HERE, by the very rule its
// kind's renderer runs, before it is ever stored or seeded, so a malformed, secret-carrying or
// (for a guide) empty block is refused at load time and never reaches a seat.
func loadBlocks(fsys fs.FS) (map[string]seedmap.SeedModule, error) {
	names, err := fs.Glob(fsys, blocksDir+"/*")
	if err != nil {
		return nil, err
	}
	blocks := make(map[string]seedmap.SeedModule, len(names))
	for _, name := range names {
		kind, err := kindOfBlockFile(name)
		if err != nil {
			// A file whose kind the loader cannot name is refused rather than skipped: skipping is
			// how a block sits in the shelf with nothing able to load it, which is the same silent
			// absence the per-kind rule exists to prevent.
			return nil, err
		}
		slug := strings.TrimSuffix(path.Base(name), path.Ext(name))
		if !slugPattern.MatchString(slug) {
			return nil, fmt.Errorf("%s: block file name %q must match %s", name, slug, slugPattern)
		}
		data, err := fs.ReadFile(fsys, name)
		if err != nil {
			return nil, err
		}
		if err := validateBlockContent(kind, name, string(data)); err != nil {
			return nil, err
		}
		blocks[slug] = seedmap.SeedModule{Slug: slug, Kind: kind, Content: string(data)}
	}
	return blocks, nil
}

// validateBlockContent runs the checks the publish route runs, in the route's order, for the two
// kinds a block FILE can carry. It deliberately does not call modulecontent.Validate: that package
// maps every kind to its rule, including the tool kind, whose rule lives in seatrenderer — and
// seatrenderer's own test imports THIS package, so importing it back would close an import cycle.
// The cost is stated rather than hidden: a third kind given an extension here must state its rule
// here too, and the switch below refuses one that does not.
func validateBlockContent(kind resolver.ModuleKind, name, content string) error {
	if len(strings.TrimSpace(content)) == 0 {
		return fmt.Errorf("%s: block is empty", name)
	}
	// The spec's rule is that secrets are never rendered into a module, and the route enforces it
	// with secretscan BEFORE the kind's parse. An instruction block accepts any text, so without
	// this the library path would be how a credential reached a seat's guidance.
	if secretscan.Contains(content) {
		return fmt.Errorf("%s: block carries a credential-shaped value", name)
	}
	switch kind {
	case resolver.KindMCP:
		if _, err := mcpblock.Parse(content); err != nil {
			return fmt.Errorf("%s: %w", name, err)
		}
	case resolver.KindInstruction:
		// Rendered verbatim into the seat's guidance, so the text itself is the whole rule.
	default:
		return fmt.Errorf("%s: no content rule for kind %q", name, kind)
	}
	return nil
}

// blockSlugs lists a block catalog's slugs in sorted order, for an error that names what the
// seat type could have asked for.
func blockSlugs(blocks map[string]seedmap.SeedModule) []string {
	slugs := make([]string, 0, len(blocks))
	for slug := range blocks {
		slugs = append(slugs, slug)
	}
	sort.Strings(slugs)
	return slugs
}

// Parse decodes one seat-type file strictly and builds its seed, which also carries the shared
// modules and the MCP blocks the file names in mcp_blocks; errors name the file and field.
func Parse(name string, data []byte, shared []seedmap.SeedModule, blocks map[string]seedmap.SeedModule) (seedmap.Seed, error) {
	var file seatTypeFile
	decoder := yaml.NewDecoder(bytes.NewReader(data))
	decoder.KnownFields(true)
	if err := decoder.Decode(&file); err != nil {
		if errors.Is(err, io.EOF) {
			return seedmap.Seed{}, fmt.Errorf("%s: file is empty", name)
		}
		return seedmap.Seed{}, fmt.Errorf("%s: %w", name, err)
	}
	if !slugPattern.MatchString(file.Slug) {
		return seedmap.Seed{}, fmt.Errorf("%s: field slug %q must match %s", name, file.Slug, slugPattern)
	}
	if strings.TrimSpace(file.Name) == "" {
		return seedmap.Seed{}, fmt.Errorf("%s: field name is empty", name)
	}
	if err := resolver.CheckRuntime(file.DefaultRuntime); err != nil {
		return seedmap.Seed{}, fmt.Errorf("%s: field default_runtime: %w", name, err)
	}
	spec := seedmap.Spec{
		Slug: file.Slug, Name: file.Name, Description: file.Description, DefaultRuntime: file.DefaultRuntime,
		Role: file.Role, OutputFormat: file.OutputFormat, Shared: shared,
	}
	for i, rule := range file.Rules {
		if strings.TrimSpace(rule.Content) == "" {
			return seedmap.Seed{}, fmt.Errorf("%s: field rules[%d].content is empty", name, i)
		}
		spec.Rules = append(spec.Rules, seedmap.Rule{Name: rule.Name, Content: rule.Content})
	}

	// module_refs are the curated catalog skills this seat type is composed from, carried as
	// concrete slug@version refs; the seed authors their content elsewhere (the publish path
	// pushes it), so here they only pin which versions the seat arrives with.
	for i, ref := range file.ModuleRefs {
		parsed, err := repositories.ParseModuleRef(ref)
		if err != nil {
			return seedmap.Seed{}, fmt.Errorf("%s: field module_refs[%d]: %w", name, i, err)
		}
		spec.ExtraRefs = append(spec.ExtraRefs, parsed)
	}

	// Each mcp_blocks entry mounts one whole server; a block is one of the files in blocks/.
	// One server mounted twice would be a block that silently does nothing, so the duplicate
	// is refused here rather than at render time.
	selected := make(map[string]string, len(file.MCPBlocks))
	mounted := make(map[string]string, len(file.MCPBlocks))
	for i, slug := range file.MCPBlocks {
		if previous, ok := selected[slug]; ok {
			return seedmap.Seed{}, fmt.Errorf("%s: field mcp_blocks[%d]: block %q already listed at mcp_blocks[%s]", name, i, slug, previous)
		}
		block, ok := blocks[slug]
		if !ok {
			return seedmap.Seed{}, fmt.Errorf("%s: field mcp_blocks[%d]: unknown block %q (available: %s)", name, i, slug, strings.Join(blockSlugs(blocks), ", "))
		}
		server, err := mcpblock.Parse(block.Content)
		if err != nil {
			return seedmap.Seed{}, fmt.Errorf("%s: field mcp_blocks[%d]: block %q: %w", name, i, slug, err)
		}
		if previous, ok := mounted[server.Name]; ok {
			return seedmap.Seed{}, fmt.Errorf("%s: field mcp_blocks[%d]: server %q is already mounted by block %q", name, i, server.Name, previous)
		}
		selected[slug] = fmt.Sprintf("%d", i)
		mounted[server.Name] = slug
		spec.Blocks = append(spec.Blocks, block)
	}

	seed, err := seedmap.FromSpec(spec)
	if err != nil {
		return seedmap.Seed{}, fmt.Errorf("%s: %w", name, err)
	}
	return seed, nil
}
