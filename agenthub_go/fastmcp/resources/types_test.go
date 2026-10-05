package resources_test

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"

	"agenthub/fastmcp"
	"agenthub/fastmcp/resources"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestTextAndBinaryRead(t *testing.T) {
	tr := &resources.TextResource{Text: "hello"}
	got, err := tr.Read()
	if err != nil || string(got) != "hello" {
		t.Fatalf("TextResource.Read = %q, %v", got, err)
	}
	br := &resources.BinaryResource{Data: []byte{1, 2, 3}}
	got, err = br.Read()
	if err != nil || string(got) != string([]byte{1, 2, 3}) {
		t.Fatalf("BinaryResource.Read = %v, %v", got, err)
	}
}

// Expectations read from types.py FileResource validators.
func TestFileResourceValidators(t *testing.T) {
	if _, err := resources.NewFileResource("relative/path.txt", false, ""); err == nil {
		t.Fatal("expected ValueError for relative path")
	} else {
		var ve *value_objects.ValueError
		if !errors.As(err, &ve) || ve.Msg != "Path must be absolute" {
			t.Fatalf("unexpected error: %v", err)
		}
	}

	abs := filepath.Join(t.TempDir(), "x.txt")
	r, err := resources.NewFileResource(abs, false, "application/octet-stream")
	if err != nil {
		t.Fatal(err)
	}
	if !r.IsBinary {
		t.Fatalf("is_binary should become true for non-text mime, got %v", r.IsBinary)
	}

	r, err = resources.NewFileResource(abs, false, "")
	if err != nil {
		t.Fatal(err)
	}
	if r.IsBinary || r.MimeType != "text/plain" {
		t.Fatalf("defaults: IsBinary=%v MimeType=%q", r.IsBinary, r.MimeType)
	}

	r, err = resources.NewFileResource(abs, true, "text/plain")
	if err != nil {
		t.Fatal(err)
	}
	if !r.IsBinary {
		t.Fatal("explicit is_binary=true must be preserved")
	}
}

func TestFileResourceReadError(t *testing.T) {
	abs := filepath.Join(t.TempDir(), "missing.txt")
	r, err := resources.NewFileResource(abs, false, "")
	if err != nil {
		t.Fatal(err)
	}
	_, err = r.Read()
	var re *fastmcp.ResourceError
	if !errors.As(err, &re) {
		t.Fatalf("expected ResourceError, got %v", err)
	}
	if re.Msg != "Error reading file "+abs {
		t.Fatalf("message = %q", re.Msg)
	}
}

func TestDirectoryResourceRead(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "a.txt"), []byte("a"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "b.txt"), []byte("b"), 0o644); err != nil {
		t.Fatal(err)
	}
	r := &resources.DirectoryResource{Path: dir}
	out, err := r.Read()
	if err != nil {
		t.Fatal(err)
	}
	var decoded struct {
		Files []string `json:"files"`
	}
	if err := json.Unmarshal(out, &decoded); err != nil {
		t.Fatalf("invalid JSON %q: %v", out, err)
	}
	if len(decoded.Files) != 2 || decoded.Files[0] == "" {
		t.Fatalf("files = %v", decoded.Files)
	}
}

// Expectations from types.py field defaults and validators.
func TestResourceDefaults(t *testing.T) {
	h := resources.NewHttpResource("http://example.com", "")
	if h.MimeType != "application/json" || h.URL != "http://example.com" {
		t.Fatalf("HttpResource defaults: %+v", h)
	}
	p := "*.txt"
	d, err := resources.NewDirectoryResource("/tmp", false, &p, "")
	if err != nil {
		t.Fatal(err)
	}
	if d.MimeType != "application/json" || d.Recursive || d.Pattern == nil || *d.Pattern != "*.txt" {
		t.Fatalf("DirectoryResource defaults: %+v", d)
	}
	if _, err := resources.NewDirectoryResource("relative", false, nil, ""); err == nil {
		t.Fatal("expected absolute path error")
	}
}

func TestDirectoryResourceNotADirectory(t *testing.T) {
	dir := t.TempDir()
	file := filepath.Join(dir, "f")
	if err := os.WriteFile(file, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	r := &resources.DirectoryResource{Path: file}
	if _, err := r.ListFiles(); err == nil {
		t.Fatal("expected error for non-directory")
	}
}
