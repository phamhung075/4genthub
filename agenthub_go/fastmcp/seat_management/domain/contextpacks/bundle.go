package contextpacks

import (
	"fmt"
	"strings"
)

// Bundle assembly (OPR.0.5.3.5 Atom 3): concatenate a context pack's included files into one
// coherent paste-ready string, so the destination seat receives the pack as a single priming
// injection rather than N separate sends. The file reader is injected, which keeps this pure.

// ContextPackError codes used by this package.
const (
	CodeFileReadFailed = "file_read_failed"
)

// ContextPackError is a coded pack failure.
type ContextPackError struct {
	Code string
	Msg  string
}

func (e *ContextPackError) Error() string { return e.Msg }

// PlainComposeSeparator is the deliberately dumb composition separator: source bytes are
// otherwise untouched (no trim, no framing headers, no forced final newline).
const PlainComposeSeparator = "\n\n"

// PlainFileInput is one member of a plain assembly; a nil Content records an honestly missing
// member.
type PlainFileInput struct {
	Path    string
	Content *string
}

// PlainFileEntry is one present member's projection.
type PlainFileEntry struct {
	Path            string
	Bytes           int
	EstimatedTokens int
}

// PlainFileAssembly is the exact content a delivery verb can resolve without coupling the
// context noun to the transport.
type PlainFileAssembly struct {
	Text            string
	Bytes           int
	EstimatedTokens int
	Files           []PlainFileEntry
	MissingFiles    []string
}

// AssemblePlainFiles concatenates present file contents in declared order. The durable store
// keeps each source as its own member; this projection is the composed view.
func AssemblePlainFiles(files []PlainFileInput) PlainFileAssembly {
	present := make([]PlainFileInput, 0, len(files))
	for _, f := range files {
		if f.Content != nil {
			present = append(present, f)
		}
	}
	texts := make([]string, 0, len(present))
	entries := make([]PlainFileEntry, 0, len(present))
	for _, f := range present {
		texts = append(texts, *f.Content)
		fileBytes := len(*f.Content)
		entries = append(entries, PlainFileEntry{Path: f.Path, Bytes: fileBytes, EstimatedTokens: EstimateTokensFromBytes(fileBytes)})
	}
	text := strings.Join(texts, PlainComposeSeparator)
	missing := []string{}
	for _, f := range files {
		if f.Content == nil {
			missing = append(missing, f.Path)
		}
	}
	return PlainFileAssembly{
		Text: text, Bytes: len(text), EstimatedTokens: EstimateTokensOf(text),
		Files: entries, MissingFiles: missing,
	}
}

const (
	packHeaderPrefix = "# OpenRig Context Pack:"
	fileHeaderPrefix = "## File:"
)

// BundleFile is one manifest file as the assembler needs it. AbsolutePath nil means the manifest
// referenced a file that is missing on disk; it is surfaced rather than failing the assembly.
type BundleFile struct {
	Path         string
	Role         string
	Summary      string
	AbsolutePath *string
}

// BundlePack is the pack-level frame the assembly leads with.
type BundlePack struct {
	ID      string
	Name    string
	Version string
	Purpose string
	Files   []BundleFile
}

// BundleFileRef names a file that was skipped because it is missing.
type BundleFileRef struct {
	Path string
	Role string
}

// AssembledBundle is one paste-ready bundle plus its per-file projection.
type AssembledBundle struct {
	Text            string
	Bytes           int
	EstimatedTokens int
	Files           []BundleFileRef // present files, with the byte/token projection in FilesMeta
	FilesMeta       []PlainFileEntry
	MissingFiles    []BundleFileRef
}

// AssembleBundle concatenates a pack into one paste-ready string:
//
//	# OpenRig Context Pack: <name> v<version>
//	<purpose, if any>
//
//	## File: <path> (role: <role>)
//	<file contents>
//
// Each file is separated by a blank line so adjacent contents do not merge. Missing files are
// skipped and surfaced; a read error is loud (CodeFileReadFailed).
func AssembleBundle(pack BundlePack, readFile func(absPath string) (string, error)) (AssembledBundle, error) {
	if readFile == nil {
		return AssembledBundle{}, &ContextPackError{Code: CodeFileReadFailed, Msg: "AssembleBundle needs a file reader"}
	}
	sections := []string{fmt.Sprintf("%s %s v%s", packHeaderPrefix, pack.Name, pack.Version)}
	if pack.Purpose != "" {
		sections = append(sections, strings.TrimSpace(pack.Purpose))
	}

	files := []BundleFileRef{}
	meta := []PlainFileEntry{}
	missing := []BundleFileRef{}
	for _, f := range pack.Files {
		if f.AbsolutePath == nil {
			missing = append(missing, BundleFileRef{Path: f.Path, Role: f.Role})
			continue
		}
		content, err := readFile(*f.AbsolutePath)
		if err != nil {
			return AssembledBundle{}, &ContextPackError{Code: CodeFileReadFailed, Msg: fmt.Sprintf(
				"failed to read pack file %s: %v", *f.AbsolutePath, err)}
		}
		header := fmt.Sprintf("%s %s (role: %s)", fileHeaderPrefix, f.Path, f.Role)
		if f.Summary != "" {
			header += " — " + f.Summary
		}
		sections = append(sections, header)
		sections = append(sections, strings.TrimRight(content, " \t\r\n"))
		fileBytes := len(content)
		files = append(files, BundleFileRef{Path: f.Path, Role: f.Role})
		meta = append(meta, PlainFileEntry{Path: f.Path, Bytes: fileBytes, EstimatedTokens: EstimateTokensFromBytes(fileBytes)})
	}
	text := strings.Join(sections, "\n\n") + "\n"
	return AssembledBundle{
		Text: text, Bytes: len(text), EstimatedTokens: EstimateTokensOf(text),
		Files: files, FilesMeta: meta, MissingFiles: missing,
	}, nil
}
