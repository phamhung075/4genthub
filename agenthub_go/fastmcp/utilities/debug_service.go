package utilities

import (
	"os"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// DebugService mirrors utilities.debug_service.DebugService: environment-based debug
// flags. The log_* methods and debug_decorator only emit Python logging calls, which
// have no Go meaning here, so they are omitted.
type DebugService struct {
	DebugEnabled     bool
	DebugHTTP        bool
	DebugAPIV2       bool
	DebugMCP         bool
	DebugAuth        bool
	DebugDatabase    bool
	DebugFrontend    bool
	DebugVerbose     bool
	DebugStackTraces bool
}

// NewDebugService reads the debug flags from the environment, exactly like the Python
// constructor (os.getenv(name, "false").lower() == "true").
func NewDebugService() *DebugService {
	return &DebugService{
		DebugEnabled:     envFlag("DEBUG_SERVICE_ENABLED"),
		DebugHTTP:        envFlag("DEBUG_HTTP_REQUESTS"),
		DebugAPIV2:       envFlag("DEBUG_API_V2"),
		DebugMCP:         envFlag("DEBUG_MCP_TOOLS"),
		DebugAuth:        envFlag("DEBUG_AUTHENTICATION"),
		DebugDatabase:    envFlag("DEBUG_DATABASE"),
		DebugFrontend:    envFlag("DEBUG_FRONTEND_ISSUES"),
		DebugVerbose:     envFlag("DEBUG_VERBOSE"),
		DebugStackTraces: envFlag("DEBUG_STACK_TRACES"),
	}
}

func envFlag(name string) bool {
	v := os.Getenv(name)
	if v == "" {
		v = "false"
	}
	return value_objects.PyLower(v) == "true"
}

// IsEnabled mirrors is_enabled: False unless the global flag is on, then the category flag.
func (d *DebugService) IsEnabled(category string) bool {
	if !d.DebugEnabled {
		return false
	}
	flags := map[string]bool{
		"general":  true,
		"http":     d.DebugHTTP,
		"api_v2":   d.DebugAPIV2,
		"mcp":      d.DebugMCP,
		"auth":     d.DebugAuth,
		"database": d.DebugDatabase,
		"frontend": d.DebugFrontend,
	}
	return flags[category]
}

// GetDebugStatus mirrors get_debug_status (a dict with insertion-ordered keys).
func (d *DebugService) GetDebugStatus() *entities.OrderedMap[any] {
	categories := entities.NewOrderedMap[any]()
	categories.Set("http", d.DebugHTTP)
	categories.Set("api_v2", d.DebugAPIV2)
	categories.Set("mcp", d.DebugMCP)
	categories.Set("auth", d.DebugAuth)
	categories.Set("database", d.DebugDatabase)
	categories.Set("frontend", d.DebugFrontend)

	options := entities.NewOrderedMap[any]()
	options.Set("verbose", d.DebugVerbose)
	options.Set("stack_traces", d.DebugStackTraces)

	out := entities.NewOrderedMap[any]()
	out.Set("debug_enabled", d.DebugEnabled)
	out.Set("categories", categories)
	out.Set("options", options)
	return out
}

// DebugServiceInstance is the module-level global (Python debug_service).
var DebugServiceInstance = NewDebugService()

// IsDebugEnabled is the is_debug_enabled convenience function. The Python default
// category ("general") is passed explicitly by Go callers.
func IsDebugEnabled(category string) bool { return DebugServiceInstance.IsEnabled(category) }

// GetDebugStatus is the get_debug_status convenience function.
func GetDebugStatus() *entities.OrderedMap[any] { return DebugServiceInstance.GetDebugStatus() }
