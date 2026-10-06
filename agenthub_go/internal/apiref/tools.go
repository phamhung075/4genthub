package apiref

import (
	"fmt"

	"agenthub/fastmcp/server/httpapp"
	"agenthub/fastmcp/task_management/application/services"
	interfacelayer "agenthub/fastmcp/task_management/interface"
)

// ToolEntry is one MCP tool, in the shape the page renders and the drift test checks.
//
// Parameters carries the JSON Schema VERBATIM, as the server advertises it - not a translation, so
// the page cannot document a shape the server does not accept. Actions is the enum of the schema's
// `action` property, and it is EMPTY for a tool that takes no action parameter, which is a fact about
// the tool rather than missing data.
type ToolEntry struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	Parameters  map[string]any `json:"parameters"`
	Actions     []string       `json:"actions"`
}

// toolsFromServer returns the tool surface by CALLING the same builder the HTTP handler calls.
//
// THIS IS THE SECOND INSTRUMENT, and it is a call rather than a parse on purpose: the ten tools (six
// from ToolDefinitions plus four schemas appended inside MCPToolsList) reach this package because they
// reach the wire. A parse of the same source would be a second instrument inside one family, and the
// witness's independent reading is what keeps the producer honest - not a second producer.
//
// The registry is composed WITHOUT a database, the way the handler's own tests compose it: an empty
// FacadeService and DatabaseAvailable true. An App that reaches this call without its registry is a
// WIRING FAULT and the seam refuses it as a sentinel rather than answering with an empty surface - so
// every error here is fatal, and the sentinel is checked by identity rather than by matching prose.
func toolsFromServer() ([]ToolEntry, error) {
	facade := services.NewFacadeService(nil, nil, nil, nil, nil, nil, nil)
	registry, err := interfacelayer.NewDDDCompliantMCPTools(interfacelayer.Dependencies{
		FacadeService:     facade,
		DatabaseAvailable: true,
	}, nil)
	if err != nil {
		return nil, fmt.Errorf("cannot compose the MCP tool registry: %w", err)
	}

	app := &httpapp.App{}
	app.SetMCPTools(registry)

	advertised, err := app.MCPToolsList()
	if err != nil {
		return nil, fmt.Errorf("the MCP tool surface is unknown: %w", err)
	}
	if len(advertised) == 0 {
		return nil, fmt.Errorf("the MCP tool surface came back empty: a server with no tools is a " +
			"wiring fault rather than a fact this artefact may assert")
	}

	tools := make([]ToolEntry, 0, len(advertised))
	for index, raw := range advertised {
		entry := ToolEntry{Name: stringValue(raw["name"]), Description: stringValue(raw["description"])}
		if entry.Name == "" {
			return nil, fmt.Errorf("tool %d has no name: a nameless tool cannot be documented", index)
		}
		schema, ok := raw["inputSchema"].(map[string]any)
		if !ok {
			return nil, fmt.Errorf("tool %q advertises no input schema", entry.Name)
		}
		entry.Parameters = schema
		entry.Actions = actionEnum(schema)
		tools = append(tools, entry)
	}
	return tools, nil
}

// actionEnum reads the enum of the schema's `action` property, which is the one place a tool's
// actions are stated. A schema without it, or with a non-string enum, yields an empty list rather
// than an error: a tool with no actions is legitimate, and the shape is the schema's to define.
func actionEnum(schema map[string]any) []string {
	properties, ok := schema["properties"].(map[string]any)
	if !ok {
		return []string{}
	}
	action, ok := properties["action"].(map[string]any)
	if !ok {
		return []string{}
	}
	raw, ok := action["enum"].([]any)
	if !ok {
		return []string{}
	}
	actions := make([]string, 0, len(raw))
	for _, value := range raw {
		if text, ok := value.(string); ok {
			actions = append(actions, text)
		}
	}
	return actions
}

// stringValue reads a string field, and empty for anything else: a non-string where a string belongs
// is reported as absent rather than formatted into the artefact.
func stringValue(value any) string {
	if text, ok := value.(string); ok {
		return text
	}
	return ""
}
