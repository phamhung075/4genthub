// Package skillblock defines the content payload of a skill module: the SKILL.md text a seat
// renders, plus the provenance of the source the block was published from. A skill module's
// content is always a block, never a bare markdown body, so a stale or plain-text skill module
// fails visibly at render instead of writing bytes no one can trace back to a source.
//
// The provenance is a path/digest pair: the path is relative to the root its publisher used
// (the skill library publishes paths relative to the OpenRig repository root; import-project
// publishes paths relative to the project root), and the digest is the sha256 of the file at
// that path when it was published. A drift check recomputes the digest and reports a mismatch
// rather than letting the two copies diverge silently. A skill committed on two edges records
// the second copy as an independent mirror pair, checked on its own.
package skillblock

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"regexp"
	"strings"

	"agenthub/fastmcp/seat_management/domain/secretscan"
)

// sha256Pattern is the lowercase hex form of a sha256 digest, the one digest rule the
// inventory states and the drift check recomputes.
var sha256Pattern = regexp.MustCompile(`^[0-9a-f]{64}$`)

// Block is the content of one skill module.
type Block struct {
	// Content is the SKILL.md text; the renderer writes it verbatim to skills/<slug>/SKILL.md.
	Content string `json:"content"`
	// SourcePath is the path of the skill's SKILL.md at the source it was published from,
	// relative to the publisher's root (repository root for the skill library, project root
	// for import-project).
	SourcePath string `json:"source_path"`
	// SHA256 is the lowercase hex sha256 of SourcePath's bytes at publish time.
	SHA256 string `json:"sha256"`
	// MirrorPath and MirrorSHA256 carry the second committed copy of a skill that lives on two
	// edges; both are empty for a skill with a single source. The mirror pair is checked
	// independently of the primary pair.
	MirrorPath   string `json:"mirror_path,omitempty"`
	MirrorSHA256 string `json:"mirror_sha256,omitempty"`
}

// Marshal encodes a block as the module content string. HTML escaping is disabled so the
// stored JSON keeps the SKILL.md text readable, the same way the client's json.dumps writes it.
func Marshal(block Block) (string, error) {
	var buf bytes.Buffer
	encoder := json.NewEncoder(&buf)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(block); err != nil {
		return "", err
	}
	return strings.TrimSuffix(buf.String(), "\n"), nil
}

// Parse validates one block's content. The payload is a single JSON object with only the
// fields above; an unknown field, a missing or contradictory field, or a credential-shaped
// value is an error, so a malformed block fails at the store, seed or render path instead of
// writing an untraceable SKILL.md into a seat.
func Parse(content string) (Block, error) {
	if secretscan.Contains(content) {
		return Block{}, errors.New("carries a credential-shaped value: reference a secret as ${ENV_VAR} instead of writing it into the block")
	}
	if !json.Valid([]byte(content)) {
		return Block{}, errors.New("content is not one JSON value")
	}
	decoder := json.NewDecoder(strings.NewReader(content))
	decoder.DisallowUnknownFields()
	var block Block
	if err := decoder.Decode(&block); err != nil {
		return Block{}, fmt.Errorf("content is not a skill block: %w", err)
	}
	if strings.TrimSpace(block.Content) == "" {
		return Block{}, errors.New("field content is required: it is the SKILL.md the seat renders")
	}
	if err := checkRelativePath("source_path", block.SourcePath); err != nil {
		return Block{}, err
	}
	if err := checkDigest("sha256", block.SHA256); err != nil {
		return Block{}, err
	}
	hasMirrorPath, hasMirrorSHA := block.MirrorPath != "", block.MirrorSHA256 != ""
	if hasMirrorPath != hasMirrorSHA {
		return Block{}, errors.New("fields mirror_path and mirror_sha256 must be set together")
	}
	if hasMirrorPath {
		if err := checkRelativePath("mirror_path", block.MirrorPath); err != nil {
			return Block{}, err
		}
		if err := checkDigest("mirror_sha256", block.MirrorSHA256); err != nil {
			return Block{}, err
		}
	}
	return block, nil
}

func checkRelativePath(field, value string) error {
	if value == "" {
		return fmt.Errorf("field %s is required", field)
	}
	if strings.HasPrefix(value, "/") || strings.Contains(value, "..") {
		return fmt.Errorf("field %s %q must be relative to its publisher's root", field, value)
	}
	return nil
}

func checkDigest(field, value string) error {
	if !sha256Pattern.MatchString(value) {
		return fmt.Errorf("field %s must be a lowercase hex sha256 digest", field)
	}
	return nil
}
