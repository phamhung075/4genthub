// Package interfacelayer ports task_management/interface/consolidated_mcp_server.py.
package interfacelayer

// ConsolidatedMCPServer holds the DDD-compliant tools registered on an MCP server.
type ConsolidatedMCPServer struct {
	Tools *DDDCompliantMCPTools
}

// CreateConsolidatedMCPServer ports create_consolidated_mcp_server: build the DDD
// tools and register them on mcp. Python also constructs FastMCP("Task Management DDD")
// here and exposes main()/mcp_instance as the CLI runner; the FastMCP port and the
// runner belong to the server context, so the server is passed in.
func CreateConsolidatedMCPServer(mcp MCPServer, deps Dependencies, configOverrides map[string]any) (*ConsolidatedMCPServer, error) {
	tools, err := NewDDDCompliantMCPTools(deps, configOverrides)
	if err != nil {
		return nil, err
	}
	tools.RegisterTools(mcp)
	return &ConsolidatedMCPServer{Tools: tools}, nil
}
