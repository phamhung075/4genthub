// Package server ports fastmcp/server/proxy.py.
package server

import (
	"context"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/tools"
)

// RemoteToolClient is the minimal client interface for remote tool listing and execution.
type RemoteToolClient interface {
	ListTools(ctx context.Context) ([]tools.Tool, error)
	CallTool(ctx context.Context, name string, args *entities.OrderedMap[any]) ([]any, error)
}

// ProxyTool forwards tool calls to a remote client.
type ProxyTool struct {
	tools.BaseTool
	Client RemoteToolClient
}

// Run executes the tool on the remote client.
func (p *ProxyTool) Run(ctx context.Context, args *entities.OrderedMap[any]) ([]any, error) {
	if p.Client != nil {
		return p.Client.CallTool(ctx, p.Name, args)
	}
	return p.BaseTool.Run(ctx, args)
}

// ProxyToolManager manages local and proxied remote tools.
type ProxyToolManager struct {
	*tools.ToolManager
	Client RemoteToolClient
}

// NewProxyToolManager creates a new ProxyToolManager.
func NewProxyToolManager(client RemoteToolClient) (*ProxyToolManager, error) {
	tm, err := tools.NewToolManager(nil, nil)
	if err != nil {
		return nil, err
	}
	return &ProxyToolManager{
		ToolManager: tm,
		Client:      client,
	}, nil
}
