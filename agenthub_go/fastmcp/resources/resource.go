package resources

import (
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// MCPResource mirrors mcp.types.Resource.
type MCPResource struct {
	URI         string
	Name        string
	Description *string
	MimeType    *string
}

// Key ports Resource.key (self._key or str(self.uri)). The concrete Resource
// struct from types.go has no private key field, so the URI is always used.
func (r *Resource) Key() string { return r.URI }

// ToMCPResource ports to_mcp_resource.
func (r *Resource) ToMCPResource() *MCPResource {
	mime := r.MimeType
	desc := r.Description
	return &MCPResource{URI: r.URI, Name: r.Name, Description: &desc, MimeType: &mime}
}

// Repr ports Resource.__repr__.
func (r *Resource) Repr() string {
	return "Resource(uri=" + value_objects.PyRepr(r.URI) +
		", name=" + value_objects.PyRepr(r.Name) +
		", description=" + value_objects.PyRepr(r.Description) +
		", tags=" + value_objects.PyRepr(r.Tags) + ")"
}

// SetDefaultName ports the set_default_name model validator: the name falls
// back to the URI string, otherwise a ValueError is raised.
func (r *Resource) SetDefaultName() error {
	if r.Name != "" {
		return nil
	}
	if r.URI != "" {
		r.Name = r.URI
		return nil
	}
	return &value_objects.ValueError{Msg: "Either name or uri must be provided"}
}

// ResourceReader is the read() contract shared by concrete resources. The
// concrete implementations in types.go return bytes; Python returns str|bytes.
type ResourceReader interface {
	Read() ([]byte, error)
}

// NewResource builds the base Resource with the pydantic field defaults
// (name from uri, mime_type text/plain).
func NewResource(uri string, name string, description string, mimeType string, tags []string, enabled bool) (*Resource, error) {
	r := &Resource{URI: uri, Name: name, Description: description, MimeType: mimeType, Tags: tags, Enabled: enabled}
	if r.MimeType == "" {
		r.MimeType = "text/plain"
	}
	if err := r.SetDefaultName(); err != nil {
		return nil, err
	}
	return r, nil
}

// FunctionResource mirrors resources.resource.FunctionResource.
type FunctionResource struct {
	Resource
	Fn func() (any, error)
}

// NewFunctionResource builds a function resource applying the Python defaults:
// name falls back to the provided func name, description to the docstring,
// mime_type to text/plain and enabled to True.
func NewFunctionResource(fn func() (any, error), uri string, name string, description string, mimeType string, tags []string, enabled *bool) (*FunctionResource, error) {
	base, err := NewResource(uri, name, description, mimeType, tags, true)
	if err != nil {
		return nil, err
	}
	if enabled != nil {
		base.Enabled = *enabled
	}
	return &FunctionResource{Resource: *base, Fn: fn}, nil
}

// Read ports FunctionResource.read: a Resource result is read recursively,
// bytes and str are returned as-is, anything else is JSON (fallback=str,
// indent=2). The Go signature returns bytes.
func (f *FunctionResource) Read() ([]byte, error) {
	result, err := f.Fn()
	if err != nil {
		return nil, err
	}
	switch v := result.(type) {
	case *Resource:
		return v.Read()
	case Resource:
		return v.Read()
	case []byte:
		return v, nil
	case string:
		return []byte(v), nil
	default:
		return []byte(value_objects.PyJSONDumpsDefaultStr(v, 2)), nil
	}
}

// Read is the base abstract read(); subclasses in types.go implement it.
func (r *Resource) Read() ([]byte, error) {
	return nil, &value_objects.ValueError{Msg: "Resource.read() must be implemented by subclasses"}
}
