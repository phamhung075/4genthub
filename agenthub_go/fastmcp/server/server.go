// Package server holds the Go port of src/fastmcp/server/server.py.
//
// server.py defines the FastMCP server class together with its MCP protocol
// handlers, asyncio lifespan wrappers, uvicorn/Starlette app factories and
// client/proxy/mount machinery. Those parts depend on anyio, uvicorn, Starlette
// routes, the low-level mcp.server.Server, httpx clients, fastmcp.client.Client and the
// FastMCPProxy objects; they have no Go meaning and are not ported here. ToolManager IS
// ported (tools/tool_manager.go), wired at server/proxy.go.
//
// The framework-independent behaviour is ported faithfully: URI prefix
// rewriting (add_resource_prefix, remove_resource_prefix, has_resource_prefix)
// and the component tag/enabled filter (_should_enable_component). The
// MountedServer dataclass and the URI_PATTERN constant are represented by the
// helpers below, where the Go surface is deliberately minimal because Python's
// MountedServer only carried a reference to the FastMCP class, which itself
// remains unported.
package server

import (
	"regexp"
	"strings"

	"agenthub/fastmcp"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

// uriPattern ports URI_PATTERN = re.compile(r"^([^:]+://)(.*?)$").
var uriPattern = regexp.MustCompile(`^([^:]+://)(.*?)$`)

// resolveResourcePrefixFormat ports the `prefix_format is None` fallback to
// _settings.resource_prefix_format.
func resolveResourcePrefixFormat(prefixFormat *string) string {
	if prefixFormat == nil {
		return fastmcp.Settings.ResourcePrefixFormat
	}
	return *prefixFormat
}

// AddResourcePrefix ports add_resource_prefix. A nil prefixFormat is Python's
// None and falls back to the global settings; a nil/empty prefix returns uri
// unchanged.
func AddResourcePrefix(uri, prefix string, prefixFormat *string) (string, error) {
	if prefix == "" {
		return uri, nil
	}

	format := resolveResourcePrefixFormat(prefixFormat)

	switch format {
	case "protocol":
		// Legacy style: prefix+protocol://path
		return prefix + "+" + uri, nil
	case "path":
		// New style: protocol://prefix/path
		match := uriPattern.FindStringSubmatch(uri)
		if match == nil {
			return "", &value_objects.ValueError{Msg: "Invalid URI format: " + uri + ". Expected protocol://path format."}
		}
		protocol, path := match[1], match[2]
		return protocol + prefix + "/" + path, nil
	default:
		return "", &value_objects.ValueError{Msg: "Invalid prefix format: " + format}
	}
}

// RemoveResourcePrefix ports remove_resource_prefix. It returns uri unchanged
// when the prefix is absent or does not match.
func RemoveResourcePrefix(uri, prefix string, prefixFormat *string) (string, error) {
	if prefix == "" {
		return uri, nil
	}

	format := resolveResourcePrefixFormat(prefixFormat)

	switch format {
	case "protocol":
		// Legacy style: prefix+protocol://path
		legacyPrefix := prefix + "+"
		if strings.HasPrefix(uri, legacyPrefix) {
			return uri[len(legacyPrefix):], nil
		}
		return uri, nil
	case "path":
		// New style: protocol://prefix/path
		match := uriPattern.FindStringSubmatch(uri)
		if match == nil {
			return "", &value_objects.ValueError{Msg: "Invalid URI format: " + uri + ". Expected protocol://path format."}
		}
		protocol, path := match[1], match[2]

		prefixPattern := regexp.MustCompile("^" + regexp.QuoteMeta(prefix) + "/(.*?)$")
		pathMatch := prefixPattern.FindStringSubmatch(path)
		if pathMatch == nil {
			return uri, nil
		}
		return protocol + pathMatch[1], nil
	default:
		return "", &value_objects.ValueError{Msg: "Invalid prefix format: " + format}
	}
}

// HasResourcePrefix ports has_resource_prefix.
func HasResourcePrefix(uri, prefix string, prefixFormat *string) (bool, error) {
	if prefix == "" {
		return false, nil
	}

	format := resolveResourcePrefixFormat(prefixFormat)

	switch format {
	case "protocol":
		// Legacy style: prefix+protocol://path
		return strings.HasPrefix(uri, prefix+"+"), nil
	case "path":
		// New style: protocol://prefix/path
		match := uriPattern.FindStringSubmatch(uri)
		if match == nil {
			return false, &value_objects.ValueError{Msg: "Invalid URI format: " + uri + ". Expected protocol://path format."}
		}
		path := match[2]

		prefixPattern := regexp.MustCompile("^" + regexp.QuoteMeta(prefix) + "/")
		return prefixPattern.MatchString(path), nil
	default:
		return false, &value_objects.ValueError{Msg: "Invalid prefix format: " + format}
	}
}

// ShouldEnableComponent ports FastMCP._should_enable_component. includeTags and
// excludeTags are pointers so nil is Python's None. Tags are Python sets, so
// membership ignores ordering.
func ShouldEnableComponent(component *utilities.FastMCPComponent, includeTags, excludeTags *entities.StringSet) bool {
	if !component.Enabled {
		return false
	}

	if includeTags == nil && excludeTags == nil {
		return true
	}

	if excludeTags != nil {
		for _, etag := range excludeTags.Items() {
			if componentHasTag(component, etag) {
				return false
			}
		}
	}

	if includeTags != nil {
		for _, itag := range includeTags.Items() {
			if componentHasTag(component, itag) {
				return true
			}
		}
		return false
	}

	return true
}

func componentHasTag(component *utilities.FastMCPComponent, tag string) bool {
	for _, t := range component.Tags {
		if t == tag {
			return true
		}
	}
	return false
}
