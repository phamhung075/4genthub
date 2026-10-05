// Package contextpacks ports the OpenRig context-pack algebra
// (packages/daemon/src/domain/context-packs + markdown-address.ts) as pure logic: text in,
// spans and profiles out, with no OS dependency. File reads arrive through the caller
// (ComposeInput.ReadFile, AssembleBundle's reader), which is what lets the same algebra serve
// library packs and configured tree roots.
//
// This file is the markdown addressing core: an address is `name#H2-slug/H3-slug`, exactly one
// form, and a bare address resolves to the section's FULL span. Resolution FAILS LOUD — an
// address that matches nothing is an error naming the miss and the real candidates, never a
// silent empty, because a missing atom must stop a compose rather than thin the walk.
package contextpacks

import (
	"fmt"
	"regexp"
	"strings"
)

// Addressable depth per the Q1 ruling: H2 and H3.
const (
	minLevel = 2
	maxLevel = 3
)

// AddressResolutionError is the fail-loud addressing error.
type AddressResolutionError struct{ Msg string }

func (e *AddressResolutionError) Error() string { return e.Msg }

var (
	markdownEmphasis = strings.NewReplacer("`", "", "*", "", "_", "", "~", "")
	nonAlnumRun      = regexp.MustCompile(`[^a-z0-9]+`)
	fenceLine        = regexp.MustCompile("^\\s{0,3}(`{3,}|~{3,})")
	fenceRest        = regexp.MustCompile("^[ \t\r]*$")
	headerLine       = regexp.MustCompile(`^(#{1,6})\s+(.*\S)\s*$`)
)

// SlugifyHeader is the one slug rule: lower-cased; markdown emphasis/code markers stripped with
// the text kept; every run of non-alphanumerics becomes one hyphen; leading/trailing hyphens
// trimmed.
func SlugifyHeader(title string) string {
	s := strings.ToLower(markdownEmphasis.Replace(title))
	s = nonAlnumRun.ReplaceAllString(s, "-")
	return strings.Trim(s, "-")
}

// ParsedAddress is an address split into its pre-`#` ref and its slug path (0, 1 or 2 segments).
type ParsedAddress struct {
	// Ref is the pre-`#` reference; the caller's resolver owns what it names.
	Ref string
	// HeaderPath is 0 (whole file), 1 (H2) or 2 (H2/H3) slugs.
	HeaderPath []string
}

// ParseAddress parses the one grammar form `ref` / `ref#h2` / `ref#h2/h3`, failing loud on
// anything else.
func ParseAddress(address string) (ParsedAddress, error) {
	hashCount := strings.Count(address, "#")
	if hashCount > 1 {
		return ParsedAddress{}, &AddressResolutionError{Msg: fmt.Sprintf(
			"address %q has %d '#' separators — the one form is name#H2-slug/H3-slug (a single '#').", address, hashCount)}
	}
	ref, headerPart, hasHeader := strings.Cut(address, "#")
	if !hasHeader {
		headerPart = ""
	}
	if ref == "" {
		return ParsedAddress{}, &AddressResolutionError{Msg: fmt.Sprintf(
			"address %q has an empty ref before '#' — an address always names its file/ref.", address)}
	}
	if !hasHeader {
		return ParsedAddress{Ref: ref, HeaderPath: []string{}}, nil
	}
	headerPath := strings.Split(headerPart, "/")
	for _, seg := range headerPath {
		if seg == "" {
			return ParsedAddress{}, &AddressResolutionError{Msg: fmt.Sprintf(
				"address %q has an empty header segment — the form is name#H2-slug or name#H2-slug/H3-slug.", address)}
		}
	}
	if len(headerPath) > maxLevel-minLevel+1 {
		return ParsedAddress{}, &AddressResolutionError{Msg: fmt.Sprintf(
			"address %q goes %d levels deep — addresses target H2 and H3 only (Q1 ruling), so the deepest form is name#H2-slug/H3-slug.",
			address, len(headerPath))}
	}
	return ParsedAddress{Ref: ref, HeaderPath: headerPath}, nil
}

// MarkdownSection is one addressable H2/H3 section.
type MarkdownSection struct {
	// Level is the header level (2 or 3).
	Level int
	// Title is the header's raw title text.
	Title string
	// HeaderPath is this section's address path: [h2Slug] or [h2Slug, h3Slug].
	HeaderPath []string
	// HeaderLine is the 0-based line of the header itself.
	HeaderLine int
	// Text is the FULL span: the header line through the line before the next same-or-higher header.
	Text string
	// OwnText is the OWN text: the header line through the line before the next header of ANY level.
	OwnText string
}

type headerHit struct {
	level int
	title string
	line  int
}

type headerScan struct {
	hits []headerHit
	// unterminatedFenceLine is set when EOF arrives inside an open fence: every header after the
	// opener has been swallowed, and the gate must name it.
	unterminatedFenceLine *int
}

// scanHeaders finds real headers, skipping fenced code blocks (``` or ~~~, any info string; a
// fence closes only on the same marker at the same or greater length).
func scanHeaders(lines []string) headerScan {
	var hits []headerHit
	var fenceMarker string
	fenceLength := 0
	var openFenceAt *int

	for i, line := range lines {
		m := fenceLine.FindStringSubmatch(line)
		if m != nil {
			marker := m[1][:1]
			length := len(m[1])
			switch {
			case openFenceAt == nil:
				fenceMarker, fenceLength = marker, length
				at := i
				openFenceAt = &at
			case fenceMarker == marker && length >= fenceLength && fenceRest.MatchString(line[len(m[0]):]):
				fenceMarker, fenceLength, openFenceAt = "", 0, nil
			}
			continue
		}
		if openFenceAt != nil {
			continue
		}
		if h := headerLine.FindStringSubmatch(line); h != nil {
			hits = append(hits, headerHit{level: len(h[1]), title: h[2], line: i})
		}
	}
	return headerScan{hits: hits, unterminatedFenceLine: openFenceAt}
}

// ParseMarkdownSections parses the addressable H2/H3 section tree of a markdown text. A matched
// section is never empty by construction: the span includes the header line itself.
func ParseMarkdownSections(text string) []MarkdownSection {
	lines := strings.Split(text, "\n")
	headers := scanHeaders(lines).hits
	sections := make([]MarkdownSection, 0, len(headers))
	currentH2 := ""
	haveH2 := false

	for idx, h := range headers {
		if h.level < minLevel || h.level > maxLevel {
			if h.level < minLevel {
				haveH2 = false // an H1 resets the H2 scope
			}
			continue
		}
		slug := SlugifyHeader(h.title)
		if h.level == 2 {
			currentH2, haveH2 = slug, true
		}
		var headerPath []string
		switch {
		case h.level == 2:
			headerPath = []string{slug}
		case haveH2:
			headerPath = []string{currentH2, slug}
		default:
			headerPath = []string{slug}
		}
		// FULL span: to the next header with level <= this one (same-or-higher).
		fullEnd := len(lines)
		for _, n := range headers[idx+1:] {
			if n.level <= h.level {
				fullEnd = n.line
				break
			}
		}
		// OWN text: to the next header of ANY level.
		ownEnd := len(lines)
		if idx+1 < len(headers) {
			ownEnd = headers[idx+1].line
		}
		sections = append(sections, MarkdownSection{
			Level:      h.level,
			Title:      h.title,
			HeaderPath: headerPath,
			HeaderLine: h.line,
			Text:       strings.Join(lines[h.line:fullEnd], "\n"),
			OwnText:    strings.Join(lines[h.line:ownEnd], "\n"),
		})
	}
	return sections
}

// ResolveAddress resolves a header path against markdown text. FAIL-LOUD: no match is an error
// naming the miss and the real candidates at that altitude, and an ambiguous path (a duplicate
// header path) fails too rather than serving an arbitrary first match.
func ResolveAddress(text string, headerPath []string) (MarkdownSection, error) {
	if len(headerPath) == 0 {
		return MarkdownSection{}, &AddressResolutionError{Msg: "resolveAddress needs at least one header slug; a bare ref resolves to the whole file at the caller."}
	}
	sections := ParseMarkdownSections(text)
	wanted := strings.Join(headerPath, "/")
	var hits []MarkdownSection
	for _, s := range sections {
		if strings.Join(s.HeaderPath, "/") == wanted {
			hits = append(hits, s)
		}
	}
	if len(hits) > 1 {
		lines := make([]string, 0, len(hits))
		for _, h := range hits {
			lines = append(lines, fmt.Sprint(h.HeaderLine))
		}
		return MarkdownSection{}, &AddressResolutionError{Msg: fmt.Sprintf(
			"address '#%s' is AMBIGUOUS in this file — %d sections share the path (header lines %s). Fix the duplicate headers; serving any one of them would be a silent wrong answer.",
			wanted, len(hits), strings.Join(lines, ", "))}
	}
	if len(hits) == 1 {
		return hits[0], nil
	}
	parentPath := strings.Join(headerPath[:len(headerPath)-1], "/")
	var candidates []string
	for _, s := range sections {
		if strings.Join(s.HeaderPath[:max(0, len(s.HeaderPath)-1)], "/") == parentPath {
			candidates = append(candidates, strings.Join(s.HeaderPath, "/"))
		}
	}
	if len(candidates) > 0 {
		parentLabel := parentPath
		if parentLabel == "" {
			parentLabel = "(top)"
		}
		return MarkdownSection{}, &AddressResolutionError{Msg: fmt.Sprintf(
			"address '#%s' matches no header in this file — composition stops here rather than thinning the walk. Addressable sections under '%s': %s.",
			wanted, parentLabel, strings.Join(candidates, ", "))}
	}
	all := make([]string, 0, len(sections))
	for _, s := range sections {
		all = append(all, strings.Join(s.HeaderPath, "/"))
	}
	listed := strings.Join(all, ", ")
	if listed == "" {
		listed = "(none)"
	}
	return MarkdownSection{}, &AddressResolutionError{Msg: fmt.Sprintf(
		"address '#%s' matches no header in this file — composition stops here rather than thinning the walk. The file has %d addressable section(s): %s.",
		wanted, len(sections), listed)}
}

// AddressabilityFinding kinds.
const (
	FindingDuplicateHeaderPath = "duplicate-header-path"
	FindingUnaddressableHeader = "unaddressable-header"
	FindingUnterminatedFence   = "unterminated-fence"
)

// AddressabilityFinding is one structural defect of an addressable markdown text.
type AddressabilityFinding struct {
	Kind       string
	HeaderPath string
	Lines      []int
	Line       int
	Title      string
}

// ValidateMarkdownAddressability is the compose-gate validator: every H2/H3 must be uniquely
// addressable under the one slug rule and the file must not silently lose sections. Findings,
// not throws — the caller decides the gate.
func ValidateMarkdownAddressability(text string) []AddressabilityFinding {
	lines := strings.Split(text, "\n")
	scan := scanHeaders(lines)
	sections := ParseMarkdownSections(text)
	findings := []AddressabilityFinding{}

	// An unclosed fence swallows every later header; name the loss up front.
	if scan.unterminatedFenceLine != nil {
		findings = append(findings, AddressabilityFinding{Kind: FindingUnterminatedFence, Line: *scan.unterminatedFenceLine})
	}

	seen := map[string][]int{}
	order := []string{}
	for _, s := range sections {
		unaddressable := false
		for _, seg := range s.HeaderPath {
			if seg == "" {
				unaddressable = true
				break
			}
		}
		if unaddressable {
			findings = append(findings, AddressabilityFinding{
				Kind: FindingUnaddressableHeader, HeaderPath: strings.Join(s.HeaderPath, "/"),
				Line: s.HeaderLine, Title: s.Title,
			})
			continue
		}
		key := strings.Join(s.HeaderPath, "/")
		if _, ok := seen[key]; !ok {
			order = append(order, key)
		}
		seen[key] = append(seen[key], s.HeaderLine)
	}
	for _, key := range order {
		if nums := seen[key]; len(nums) > 1 {
			findings = append(findings, AddressabilityFinding{Kind: FindingDuplicateHeaderPath, HeaderPath: key, Lines: nums})
		}
	}
	return findings
}
