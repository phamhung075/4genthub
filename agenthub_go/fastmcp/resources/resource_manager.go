package resources

import (
	"fmt"

	"agenthub/fastmcp"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// ResourceSource is the server side of a mounted resource source. Prefix
// rewriting (add_resource_prefix/remove_resource_prefix) lives in the unported
// server/server.py package; the interface exposes it so this manager stays free
// of a hard dependency.
type ResourceSource interface {
	ListResourcesViaServer() ([]*Resource, error)
	ListResourcesUnfiltered() ([]*Resource, error)
	ListResourceTemplatesViaServer() ([]*ResourceTemplate, error)
	ListResourceTemplatesUnfiltered() ([]*ResourceTemplate, error)
	AddResourcePrefix(uri string) (string, error)
	RemoveResourcePrefix(uri string) (string, bool, error)
	ReadResourceViaServer(key string) ([]byte, error)
}

// MountedResourceServer mirrors server.server.MountedServer for resources.
type MountedResourceServer struct {
	Server ResourceSource
	Prefix string
}

// ResourceManager mirrors resources.resource_manager.ResourceManager.
type ResourceManager struct {
	resources         *entities.OrderedMap[*Resource]
	templates         *entities.OrderedMap[*ResourceTemplate]
	MountedServers    []MountedResourceServer
	MaskErrorDetails  bool
	DuplicateBehavior string
}

// NewResourceManager ports __init__.
func NewResourceManager(duplicateBehavior *string, maskErrorDetails *bool) (*ResourceManager, error) {
	m := &ResourceManager{
		resources:         entities.NewOrderedMap[*Resource](),
		templates:         entities.NewOrderedMap[*ResourceTemplate](),
		MountedServers:    []MountedResourceServer{},
		MaskErrorDetails:  false,
		DuplicateBehavior: "warn",
	}
	if maskErrorDetails != nil {
		m.MaskErrorDetails = *maskErrorDetails
	}
	if duplicateBehavior != nil {
		m.DuplicateBehavior = *duplicateBehavior
	}
	switch m.DuplicateBehavior {
	case "warn", "error", "replace", "ignore":
	default:
		return nil, &value_objects.ValueError{Msg: fmt.Sprintf(
			"Invalid duplicate_behavior: %s. Must be one of: %s",
			m.DuplicateBehavior, "warn, error, replace, ignore")}
	}
	return m, nil
}

// Mount ports mount.
func (m *ResourceManager) Mount(server MountedResourceServer) {
	m.MountedServers = append(m.MountedServers, server)
}

// LoadResources ports _load_resources.
func (m *ResourceManager) LoadResources(viaServer bool) (*entities.OrderedMap[*Resource], error) {
	all := entities.NewOrderedMap[*Resource]()
	for _, mounted := range m.MountedServers {
		var child []*Resource
		var err error
		if viaServer {
			child, err = mounted.Server.ListResourcesViaServer()
		} else {
			child, err = mounted.Server.ListResourcesUnfiltered()
		}
		if err != nil {
			continue
		}
		if mounted.Prefix != "" {
			for _, r := range child {
				prefixedURI, perr := mounted.Server.AddResourcePrefix(r.URI)
				if perr != nil {
					continue
				}
				clone := *r
				clone.URI = prefixedURI
				all.Set(clone.Key(), &clone)
			}
		} else {
			for _, r := range child {
				all.Set(r.Key(), r)
			}
		}
	}
	for _, k := range m.resources.Keys() {
		v, _ := m.resources.Get(k)
		all.Set(k, v)
	}
	return all, nil
}

// LoadResourceTemplates ports _load_resource_templates.
func (m *ResourceManager) LoadResourceTemplates(viaServer bool) (*entities.OrderedMap[*ResourceTemplate], error) {
	all := entities.NewOrderedMap[*ResourceTemplate]()
	for _, mounted := range m.MountedServers {
		var child []*ResourceTemplate
		var err error
		if viaServer {
			child, err = mounted.Server.ListResourceTemplatesViaServer()
		} else {
			child, err = mounted.Server.ListResourceTemplatesUnfiltered()
		}
		if err != nil {
			continue
		}
		if mounted.Prefix != "" {
			for _, t := range child {
				prefixed, perr := mounted.Server.AddResourcePrefix(t.URITemplate)
				if perr != nil {
					continue
				}
				clone := *t
				clone.URITemplate = prefixed
				all.Set(clone.Key(), &clone)
			}
		} else {
			for _, t := range child {
				all.Set(t.Key(), t)
			}
		}
	}
	for _, k := range m.templates.Keys() {
		v, _ := m.templates.Get(k)
		all.Set(k, v)
	}
	return all, nil
}

// GetResources ports get_resources (unfiltered).
func (m *ResourceManager) GetResources() (*entities.OrderedMap[*Resource], error) {
	return m.LoadResources(false)
}

// GetResourceTemplates ports get_resource_templates (unfiltered).
func (m *ResourceManager) GetResourceTemplates() (*entities.OrderedMap[*ResourceTemplate], error) {
	return m.LoadResourceTemplates(false)
}

// ListResources ports list_resources.
func (m *ResourceManager) ListResources() ([]*Resource, error) {
	r, err := m.LoadResources(true)
	if err != nil {
		return nil, err
	}
	return r.Values(), nil
}

// ListResourceTemplates ports list_resource_templates.
func (m *ResourceManager) ListResourceTemplates() ([]*ResourceTemplate, error) {
	t, err := m.LoadResourceTemplates(true)
	if err != nil {
		return nil, err
	}
	return t.Values(), nil
}

// AddResource ports add_resource duplicate handling.
func (m *ResourceManager) AddResource(resource *Resource) *Resource {
	existing, ok := m.resources.Get(resource.Key())
	if ok {
		switch m.DuplicateBehavior {
		case "warn", "replace":
			m.resources.Set(resource.Key(), resource)
		case "error":
			panic(&value_objects.ValueError{Msg: "Resource already exists: " + resource.Key()})
		case "ignore":
			return existing
		}
	}
	m.resources.Set(resource.Key(), resource)
	return resource
}

// AddTemplate ports add_template duplicate handling.
func (m *ResourceManager) AddTemplate(template *ResourceTemplate) *ResourceTemplate {
	existing, ok := m.templates.Get(template.Key())
	if ok {
		switch m.DuplicateBehavior {
		case "warn", "replace":
			m.templates.Set(template.Key(), template)
		case "error":
			panic(&value_objects.ValueError{Msg: "Template already exists: " + template.Key()})
		case "ignore":
			return existing
		}
	}
	m.templates.Set(template.Key(), template)
	return template
}

// HasResource ports has_resource.
func (m *ResourceManager) HasResource(uri string) (bool, error) {
	resources, err := m.GetResources()
	if err != nil {
		return false, err
	}
	if resources.Has(uri) {
		return true, nil
	}
	templates, err := m.GetResourceTemplates()
	if err != nil {
		return false, err
	}
	for _, key := range templates.Keys() {
		if matchURITemplate(uri, key) != nil {
			return true, nil
		}
	}
	return false, nil
}

// GetResource ports get_resource.
func (m *ResourceManager) GetResource(uri string) (*Resource, error) {
	resources, err := m.GetResources()
	if err != nil {
		return nil, err
	}
	if r, ok := resources.Get(uri); ok {
		return r, nil
	}
	templates, err := m.GetResourceTemplates()
	if err != nil {
		return nil, err
	}
	for _, storageKey := range templates.Keys() {
		if params := matchURITemplate(uri, storageKey); params != nil {
			t, _ := templates.Get(storageKey)
			return m.createResource(t, uri, params)
		}
	}
	return nil, &fastmcp.NotFoundError{Msg: "Unknown resource: " + uri}
}

// createResource ports ResourceTemplate.create_resource; only the read step is
// representable without the function template type.
func (m *ResourceManager) createResource(t *ResourceTemplate, uri string, params map[string]string) (*Resource, error) {
	return nil, &value_objects.ValueError{Msg: "Error creating resource from template"}
}

// ReadResource ports read_resource for local resources and templates. Mounted
// servers use the filtered path with prefix stripping.
func (m *ResourceManager) ReadResource(uri string) ([]byte, error) {
	if _, ok := m.resources.Get(uri); ok {
		resource, err := m.GetResource(uri)
		if err != nil {
			return nil, err
		}
		if resource == nil {
			return nil, &fastmcp.NotFoundError{Msg: "Resource " + fmt.Sprintf("%q", uri) + " not found"}
		}
		data, rerr := resource.Read()
		if rerr != nil {
			if _, ok := rerr.(*fastmcp.ResourceError); ok {
				return nil, rerr
			}
			if m.MaskErrorDetails {
				return nil, &fastmcp.ResourceError{FastMCPError: fastmcp.FastMCPError{Msg: "Error reading resource " + fmt.Sprintf("%q", uri)}}
			}
			return nil, &fastmcp.ResourceError{FastMCPError: fastmcp.FastMCPError{Msg: "Error reading resource " + fmt.Sprintf("%q", uri) + ": " + rerr.Error()}}
		}
		return data, nil
	}
	for _, key := range m.templates.Keys() {
		if params := matchURITemplate(uri, key); params != nil {
			t, _ := m.templates.Get(key)
			resource, cerr := m.createResource(t, uri, params)
			if cerr != nil {
				return nil, cerr
			}
			return resource.Read()
		}
	}
	for i := len(m.MountedServers) - 1; i >= 0; i-- {
		mounted := m.MountedServers[i]
		key := uri
		if mounted.Prefix != "" {
			stripped, ok, err := mounted.Server.RemoveResourcePrefix(key)
			if err != nil {
				continue
			}
			if !ok {
				continue
			}
			key = stripped
		}
		data, err := mounted.Server.ReadResourceViaServer(key)
		if err != nil {
			if _, ok := err.(*fastmcp.NotFoundError); ok {
				continue
			}
			continue
		}
		return data, nil
	}
	return nil, &fastmcp.NotFoundError{Msg: "Resource " + fmt.Sprintf("%q", uri) + " not found."}
}
