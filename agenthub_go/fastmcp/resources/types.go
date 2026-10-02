// Package resources ports fastmcp/resources/types.py — concrete resource implementations.
package resources

import (
	"io"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"agenthub/fastmcp"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Resource is the minimal base interface needed by the concrete resources.
// fastmcp/resources/resource.py has no Go port yet, so only the fields used by
// the concrete implementations are declared here.
type Resource struct {
	URI         string
	Name        string
	MimeType    string
	Description string
	Tags        []string
	Enabled     bool
}

// TextResource is a resource that reads from a string.
type TextResource struct {
	Resource
	Text string
}

// Read returns the text content.
func (r *TextResource) Read() ([]byte, error) { return []byte(r.Text), nil }

// BinaryResource is a resource that reads from bytes.
type BinaryResource struct {
	Resource
	Data []byte
}

// Read returns the binary content.
func (r *BinaryResource) Read() ([]byte, error) { return r.Data, nil }

// FileResource is a resource that reads from a file.
// Set IsBinary to read the file as binary data instead of text.
type FileResource struct {
	Resource
	Path     string
	IsBinary bool
}

// validateAbsolutePath mirrors the pydantic field validator on `path`.
func validateAbsolutePath(path string) error {
	if !filepath.IsAbs(path) {
		return &value_objects.ValueError{Msg: "Path must be absolute"}
	}
	return nil
}

// SetBinaryFromMimeType mirrors the pydantic validator: when IsBinary is
// falsy, it is derived from MimeType.
func (r *FileResource) SetBinaryFromMimeType() {
	if r.IsBinary {
		return
	}
	mimeType := r.MimeType
	if mimeType == "" {
		mimeType = "text/plain"
	}
	r.IsBinary = !strings.HasPrefix(mimeType, "text/")
}

// NewFileResource builds a FileResource applying the two pydantic field
// validators. isBinary is the explicitly supplied value; mimeType empty means
// the Python default "text/plain".
func NewFileResource(path string, isBinary bool, mimeType string) (*FileResource, error) {
	if err := validateAbsolutePath(path); err != nil {
		return nil, err
	}
	if mimeType == "" {
		mimeType = "text/plain"
	}
	r := &FileResource{
		Resource: Resource{MimeType: mimeType},
		Path:     path,
		IsBinary: isBinary,
	}
	r.SetBinaryFromMimeType()
	return r, nil
}

// Read reads the file content (binary or text).
func (r *FileResource) Read() ([]byte, error) {
	data, err := os.ReadFile(r.Path)
	if err != nil {
		return nil, &fastmcp.ResourceError{FastMCPError: fastmcp.FastMCPError{Msg: "Error reading file " + r.Path}}
	}
	return data, nil
}

// HttpResource is a resource that reads from an HTTP endpoint.
type HttpResource struct {
	Resource
	URL string
}

// NewHttpResource builds an HttpResource with the Python default mime type.
func NewHttpResource(url string, mimeType string) *HttpResource {
	if mimeType == "" {
		mimeType = "application/json"
	}
	return &HttpResource{Resource: Resource{MimeType: mimeType}, URL: url}
}

// Read fetches the HTTP content and returns the response text.
func (r *HttpResource) Read() ([]byte, error) {
	resp, err := http.Get(r.URL)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return nil, &httpError{status: resp.Status}
	}
	return io.ReadAll(resp.Body)
}

type httpError struct{ status string }

func (e *httpError) Error() string { return "HTTP error: " + e.status }

// DirectoryResource is a resource that lists files in a directory.
type DirectoryResource struct {
	Resource
	Path      string
	Recursive bool
	Pattern   *string
}

// validateAbsolutePath mirrors the pydantic field validator on `path`.
func (r *DirectoryResource) ValidateAbsolutePath() error { return validateAbsolutePath(r.Path) }

// NewDirectoryResource builds a DirectoryResource applying the absolute-path
// validator and the Python default mime type.
func NewDirectoryResource(path string, recursive bool, pattern *string, mimeType string) (*DirectoryResource, error) {
	if err := validateAbsolutePath(path); err != nil {
		return nil, err
	}
	if mimeType == "" {
		mimeType = "application/json"
	}
	return &DirectoryResource{
		Resource:  Resource{MimeType: mimeType},
		Path:      path,
		Recursive: recursive,
		Pattern:   pattern,
	}, nil
}

// ListFiles lists files in the directory.
func (r *DirectoryResource) ListFiles() ([]string, error) {
	info, err := os.Stat(r.Path)
	if err != nil {
		return nil, &os.PathError{Op: "stat", Path: r.Path, Err: os.ErrNotExist}
	}
	if !info.IsDir() {
		return nil, &notADirectoryError{path: r.Path}
	}

	pattern := "*"
	if r.Pattern != nil {
		pattern = *r.Pattern
	}

	var matches []string
	if !r.Recursive {
		matches, err = filepath.Glob(filepath.Join(r.Path, pattern))
	} else {
		matches, err = recursiveGlob(r.Path, pattern)
	}
	if err != nil {
		return nil, &fastmcp.ResourceError{FastMCPError: fastmcp.FastMCPError{Msg: "Error listing directory " + r.Path + ": " + err.Error()}}
	}
	sort.Strings(matches)
	return matches, nil
}

type notADirectoryError struct{ path string }

func (e *notADirectoryError) Error() string { return "Not a directory: " + e.path }

func recursiveGlob(root, pattern string) ([]string, error) {
	var out []string
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if path == root {
			return nil
		}
		if pattern != "*" {
			ok, mErr := filepath.Match(pattern, info.Name())
			if mErr != nil {
				return mErr
			}
			if !ok {
				return nil
			}
		}
		out = append(out, path)
		return nil
	})
	return out, err
}

// Read reads the directory listing as an indented JSON string.
func (r *DirectoryResource) Read() ([]byte, error) {
	files, err := r.ListFiles()
	if err != nil {
		return nil, &fastmcp.ResourceError{FastMCPError: fastmcp.FastMCPError{Msg: "Error reading directory " + r.Path}}
	}
	fileList := make([]any, 0, len(files))
	for _, f := range files {
		if info, statErr := os.Stat(f); statErr == nil && info.Mode().IsRegular() {
			rel, relErr := filepath.Rel(r.Path, f)
			if relErr == nil {
				fileList = append(fileList, rel)
			}
		}
	}
	payload := entities.NewOrderedMap[any]()
	payload.Set("files", fileList)
	s, err := value_objects.PyJSONDumps(payload, 2)
	if err != nil {
		return nil, err
	}
	return []byte(s), nil
}
