// openapi.go ports fastmcp/server/openapi.py.
//
// The Python module also defines OpenAPITool/OpenAPIResource/OpenAPIResourceTemplate and
// FastMCPOpenAPI, which are built on the FastMCP component framework (Tool/Resource/
// ResourceManager/FastMCP) and httpx.AsyncClient. None of those are ported to Go, so only
// the framework-independent routing logic is ported here: _slugify, the MCPType/RouteType
// enums, RouteMap (__post_init__ validation), _determine_route_type, _generate_default_name
// and _get_unique_name. The skipped classes are noted in the migration report.
package server

import (
	"regexp"
	"strings"

	"agenthub/fastmcp/task_management/domain/value_objects"
	openapi "agenthub/fastmcp/utilities"
)

// HttpMethod mirrors the Python Literal used by RouteMap.methods.
type HttpMethod = string

var (
	slugSeparators = regexp.MustCompile(`[\s\-\.]+`)
	slugNonWord    = regexp.MustCompile(`[^a-zA-Z0-9_]`)
	slugRepeats    = regexp.MustCompile(`_+`)
)

// Slugify converts text to a URL-friendly slug: lowercase/uppercase letters, numbers and
// underscores only. Mirrors _slugify.
func Slugify(text string) string {
	if text == "" {
		return ""
	}
	slug := slugSeparators.ReplaceAllString(text, "_")
	slug = slugNonWord.ReplaceAllString(slug, "")
	slug = slugRepeats.ReplaceAllString(slug, "_")
	return strings.Trim(slug, "_")
}

// MCPType mirrors the MCPType enum.
type MCPType string

// MCPType values.
const (
	MCPTypeTool             MCPType = "TOOL"
	MCPTypeResource         MCPType = "RESOURCE"
	MCPTypeResourceTemplate MCPType = "RESOURCE_TEMPLATE"
	MCPTypeExclude          MCPType = "EXCLUDE"
)

// RouteType mirrors the deprecated RouteType enum.
type RouteType string

// RouteType values.
const (
	RouteTypeTool             RouteType = "TOOL"
	RouteTypeResource         RouteType = "RESOURCE"
	RouteTypeResourceTemplate RouteType = "RESOURCE_TEMPLATE"
	RouteTypeIgnore           RouteType = "IGNORE"
)

// RouteMap mirrors RouteMap. Methods empty means Python's "*". Pattern nil means the
// Python default r".*". nil MCPType/RouteType represent Python None.
type RouteMap struct {
	Methods   []HttpMethod
	Pattern   *regexp.Regexp
	RouteType *RouteType
	Tags      map[string]struct{}
	MCPType   *MCPType
	MCPTags   map[string]struct{}
}

// PostInit mirrors RouteMap.__post_init__: it resolves mcp_type from the deprecated
// route_type and sets route_type to match mcp_type. It returns the Python ValueError for a
// missing mcp_type.
func (r *RouteMap) PostInit() error {
	if r.MCPType == nil && r.RouteType != nil {
		name := string(*r.RouteType)
		if name == string(RouteTypeIgnore) {
			name = string(MCPTypeExclude)
		}
		mt := MCPType(name)
		r.MCPType = &mt
	} else if r.MCPType == nil {
		return &value_objects.ValueError{Msg: "`mcp_type` must be provided"}
	}

	if r.RouteType == nil {
		rt := RouteType(*r.MCPType)
		r.RouteType = &rt
	}
	return nil
}

func containsMethod(methods []HttpMethod, method string) bool {
	for _, m := range methods {
		if m == method {
			return true
		}
	}
	return false
}

func containsAllTags(mapTags map[string]struct{}, routeTags []string) bool {
	if len(mapTags) == 0 {
		return true
	}
	set := make(map[string]struct{}, len(routeTags))
	for _, t := range routeTags {
		set[t] = struct{}{}
	}
	for t := range mapTags {
		if _, ok := set[t]; !ok {
			return false
		}
	}
	return true
}

// fallbackToolMap is the RouteMap(mcp_type=MCPType.TOOL) default fallback.
func fallbackToolMap() *RouteMap {
	mt := MCPTypeTool
	rt := RouteTypeTool
	return &RouteMap{MCPType: &mt, RouteType: &rt}
}

// DefaultRouteMappings mirrors DEFAULT_ROUTE_MAPPINGS.
var DefaultRouteMappings = []*RouteMap{fallbackToolMap()}

// DetermineRouteType mirrors _determine_route_type. It returns the first matching RouteMap
// (priority order), or a catch-all Tool RouteMap when nothing matches.
func DetermineRouteType(route *openapi.HTTPRoute, mappings []*RouteMap) *RouteMap {
	for _, routeMap := range mappings {
		if len(routeMap.Methods) == 0 || containsMethod(routeMap.Methods, string(route.Method)) {
			pattern := routeMap.Pattern
			matched := false
			if pattern != nil {
				matched = pattern.MatchString(route.Path)
			} else {
				matched = true // default r".*" always searches
			}
			if matched {
				if containsAllTags(routeMap.Tags, route.Tags) {
					return routeMap
				}
			}
		}
	}
	return fallbackToolMap()
}

// GenerateDefaultName mirrors FastMCPOpenAPI._generate_default_name.
func GenerateDefaultName(route *openapi.HTTPRoute, mcpNamesMap map[string]string) string {
	var name string
	if mcpNamesMap == nil {
		mcpNamesMap = map[string]string{}
	}

	if route.OperationID != nil {
		if custom, ok := mcpNamesMap[*route.OperationID]; ok {
			name = custom
		} else {
			name = strings.SplitN(*route.OperationID, "__", 2)[0]
		}
	} else if route.Summary != nil && *route.Summary != "" {
		name = *route.Summary
	} else {
		name = string(route.Method) + "_" + route.Path
	}

	name = Slugify(name)
	if len(name) > 56 {
		name = name[:56]
	}
	return name
}

// NewUsedNames mirrors FastMCPOpenAPI._used_names (Counter per component type).
func NewUsedNames() map[string]map[string]int {
	return map[string]map[string]int{
		"tool":              {},
		"resource":          {},
		"resource_template": {},
		"prompt":            {},
	}
}

// GetUniqueName mirrors FastMCPOpenAPI._get_unique_name: it increments the counter for the
// component type and appends "_<n>" on the second and later use.
func GetUniqueName(usedNames map[string]map[string]int, name, componentType string) string {
	counts := usedNames[componentType]
	counts[name]++
	if counts[name] == 1 {
		return name
	}
	return name + "_" + itoa(counts[name])
}

// itoa is str(int) without importing strconv for a single use.
func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var buf [20]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}
