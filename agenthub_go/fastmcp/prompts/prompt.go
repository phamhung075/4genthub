// Package prompts ports fastmcp/prompts. The pydantic/MCP protocol classes are
// represented by plain structs; function-based prompt construction keeps the
// render/validation/conversion semantics.
package prompts

import (
	"fmt"
	"sort"
	"strings"

	"agenthub/fastmcp"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

// TextContent mirrors mcp.types.TextContent.
type TextContent struct {
	Type string
	Text string
}

// PromptMessage mirrors mcp.types.PromptMessage.
type PromptMessage struct {
	Role    string
	Content any
}

// MCPPromptArgument mirrors mcp.types.PromptArgument.
type MCPPromptArgument struct {
	Name        string
	Description *string
	Required    bool
}

// MCPPrompt mirrors mcp.types.Prompt.
type MCPPrompt struct {
	Name        string
	Description *string
	Arguments   []MCPPromptArgument
}

// GetPromptResult mirrors mcp.types.GetPromptResult.
type GetPromptResult struct {
	Description *string
	Messages    []*PromptMessage
}

// Message ports the Message() constructor: str content becomes TextContent and
// a nil role defaults to "user".
func Message(content any, role *string) *PromptMessage {
	if s, ok := content.(string); ok {
		content = TextContent{Type: "text", Text: s}
	}
	r := "user"
	if role != nil {
		r = *role
	}
	return &PromptMessage{Role: r, Content: content}
}

// PromptArgument mirrors prompts.prompt.PromptArgument.
type PromptArgument struct {
	Name        string
	Description *string
	Required    bool
}

// ToDict returns the pydantic model_dump key order: name, description, required.
func (a PromptArgument) ToDict() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("name", a.Name)
	m.Set("description", optional(a.Description))
	m.Set("required", a.Required)
	return m
}

func optional(s *string) any {
	if s == nil {
		return nil
	}
	return *s
}

// Prompt mirrors prompts.prompt.Prompt.
type Prompt struct {
	*utilities.FastMCPComponent
	Arguments []PromptArgument
}

// NewPrompt builds a prompt with the Python arguments default (None/empty).
func NewPrompt(component *utilities.FastMCPComponent, arguments []PromptArgument) *Prompt {
	return &Prompt{FastMCPComponent: component, Arguments: arguments}
}

// ToMCPPrompt ports to_mcp_prompt.
func (p *Prompt) ToMCPPrompt() *MCPPrompt {
	args := make([]MCPPromptArgument, 0, len(p.Arguments))
	for _, a := range p.Arguments {
		args = append(args, MCPPromptArgument{Name: a.Name, Description: a.Description, Required: a.Required})
	}
	return &MCPPrompt{Name: p.Name, Description: p.Description, Arguments: args}
}

// FunctionPrompt mirrors prompts.prompt.FunctionPrompt. Fn is the validated
// callable; the Go port passes the rendered argument map directly.
type FunctionPrompt struct {
	*Prompt
	Fn func(arguments map[string]any) (any, error)
}

// MissingRequired ports the `Missing required arguments: {missing}` ValueError.
func (p *Prompt) MissingRequired(arguments map[string]any) ([]string, bool) {
	required := map[string]bool{}
	for _, a := range p.Arguments {
		if a.Required {
			required[a.Name] = true
		}
	}
	for k := range arguments {
		delete(required, k)
	}
	if len(required) == 0 {
		return nil, false
	}
	missing := make([]string, 0, len(required))
	for k := range required {
		missing = append(missing, k)
	}
	sort.Strings(missing)
	return missing, true
}

// Render ports FunctionPrompt.render: validate required arguments, call the
// function and convert the result into messages.
func (f *FunctionPrompt) Render(arguments map[string]any) ([]*PromptMessage, error) {
	if len(f.Arguments) > 0 {
		if missing, ok := f.MissingRequired(arguments); ok {
			return nil, &value_objects.ValueError{Msg: "Missing required arguments: " + pySet(missing)}
		}
	}
	kwargs := map[string]any{}
	for k, v := range arguments {
		kwargs[k] = v
	}
	result, err := f.Fn(kwargs)
	if err != nil {
		return nil, &fastmcp.PromptError{FastMCPError: fastmcp.FastMCPError{Msg: fmt.Sprintf("Error rendering prompt %s.", f.Name)}}
	}
	return convertResult(result, f.Name)
}

// convertResult ports the per-message conversion inside Prompt.render. Any
// conversion failure becomes PromptError("Could not convert prompt result to message.").
func convertResult(result any, promptName string) ([]*PromptMessage, error) {
	items, err := asSequence(result)
	if err != nil {
		return nil, err
	}
	messages := make([]*PromptMessage, 0, len(items))
	for _, msg := range items {
		switch v := msg.(type) {
		case *PromptMessage:
			messages = append(messages, v)
		case string:
			messages = append(messages, &PromptMessage{Role: "user", Content: TextContent{Type: "text", Text: v}})
		default:
			text := value_objects.PyJSONDumpsDefaultStr(v, 2)
			messages = append(messages, &PromptMessage{Role: "user", Content: TextContent{Type: "text", Text: text}})
		}
	}
	return messages, nil
}

// asSequence mirrors `if not isinstance(result, list | tuple): result = [result]`.
func asSequence(result any) ([]any, error) {
	switch v := result.(type) {
	case []any:
		return v, nil
	case []*PromptMessage:
		out := make([]any, len(v))
		for i := range v {
			out[i] = v[i]
		}
		return out, nil
	case []string:
		out := make([]any, len(v))
		for i := range v {
			out[i] = v[i]
		}
		return out, nil
	default:
		return []any{result}, nil
	}
}

// pySet renders a Python set literal with sorted elements (set order is
// unspecified in Python, sorted is the deterministic Go rendering).
func pySet(items []string) string {
	if len(items) == 0 {
		return "set()"
	}
	parts := make([]string, len(items))
	for i, s := range items {
		parts[i] = value_objects.PyRepr(s)
	}
	return "{" + strings.Join(parts, ", ") + "}"
}

// WithKey mirrors FastMCPComponent.with_key returning the same prompt subclass.
func (p *Prompt) WithKey(key string) *Prompt {
	args := append([]PromptArgument{}, p.Arguments...)
	return &Prompt{FastMCPComponent: p.FastMCPComponent.WithKey(key), Arguments: args}
}

// PromptRenderer is the render() contract implemented by FunctionPrompt.
type PromptRenderer interface {
	Render(arguments map[string]any) ([]*PromptMessage, error)
}
