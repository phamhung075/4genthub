package prompts

import (
	"fmt"

	"agenthub/fastmcp"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// PromptSource is the server side of a mounted prompt source. Python reaches
// mounted.server._list_prompts() (filtered) or
// mounted.server._prompt_manager.list_prompts() (unfiltered).
type PromptSource interface {
	ListPromptsViaServer() ([]*Prompt, error)
	ListPromptsUnfiltered() ([]*Prompt, error)
	GetPromptViaServer(name string, arguments map[string]any) (*GetPromptResult, error)
}

// MountedPromptServer mirrors server.server.MountedServer for prompts.
type MountedPromptServer struct {
	Server PromptSource
	Prefix string
}

// PromptManager mirrors prompts.prompt_manager.PromptManager.
type PromptManager struct {
	prompts           *entities.OrderedMap[*Prompt]
	MountedServers    []MountedPromptServer
	MaskErrorDetails  bool
	DuplicateBehavior string
}

// NewPromptManager ports __init__. duplicate nil defaults to "warn"; an invalid
// value raises the Python ValueError message.
func NewPromptManager(duplicateBehavior *string, maskErrorDetails *bool) (*PromptManager, error) {
	m := &PromptManager{
		prompts:           entities.NewOrderedMap[*Prompt](),
		MountedServers:    []MountedPromptServer{},
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
func (m *PromptManager) Mount(server MountedPromptServer) {
	m.MountedServers = append(m.MountedServers, server)
}

// LoadPrompts ports _load_prompts. viaServer chooses the communication path.
func (m *PromptManager) LoadPrompts(viaServer bool) (*entities.OrderedMap[*Prompt], error) {
	all := entities.NewOrderedMap[*Prompt]()
	for _, mounted := range m.MountedServers {
		var childResults []*Prompt
		var err error
		if viaServer {
			childResults, err = mounted.Server.ListPromptsViaServer()
		} else {
			childResults, err = mounted.Server.ListPromptsUnfiltered()
		}
		if err != nil {
			// Python skips failed mounts silently (logs a warning).
			continue
		}
		if mounted.Prefix != "" {
			for _, prompt := range childResults {
				prefixed := prompt.WithKey(mounted.Prefix + "_" + prompt.Key())
				all.Set(prefixed.Key(), prefixed)
			}
		} else {
			for _, prompt := range childResults {
				all.Set(prompt.Key(), prompt)
			}
		}
	}
	for _, k := range m.prompts.Keys() {
		v, _ := m.prompts.Get(k)
		all.Set(k, v)
	}
	return all, nil
}

// HasPrompt ports has_prompt.
func (m *PromptManager) HasPrompt(key string) (bool, error) {
	p, err := m.GetPrompts()
	if err != nil {
		return false, err
	}
	return p.Has(key), nil
}

// GetPrompt ports get_prompt.
func (m *PromptManager) GetPrompt(key string) (*Prompt, error) {
	p, err := m.GetPrompts()
	if err != nil {
		return nil, err
	}
	if v, ok := p.Get(key); ok {
		return v, nil
	}
	return nil, &fastmcp.NotFoundError{Msg: "Unknown prompt: " + key}
}

// GetPrompts ports get_prompts (unfiltered inventory).
func (m *PromptManager) GetPrompts() (*entities.OrderedMap[*Prompt], error) {
	return m.LoadPrompts(false)
}

// ListPrompts ports list_prompts (filtered protocol path).
func (m *PromptManager) ListPrompts() ([]*Prompt, error) {
	p, err := m.LoadPrompts(true)
	if err != nil {
		return nil, err
	}
	return p.Values(), nil
}

// AddPrompt ports add_prompt and the duplicate-behavior semantics.
func (m *PromptManager) AddPrompt(prompt *Prompt) *Prompt {
	existing, ok := m.prompts.Get(prompt.Key())
	if ok {
		switch m.DuplicateBehavior {
		case "warn":
			m.prompts.Set(prompt.Key(), prompt)
		case "replace":
			m.prompts.Set(prompt.Key(), prompt)
		case "error":
			panic(&value_objects.ValueError{Msg: "Prompt already exists: " + prompt.Key()})
		case "ignore":
			return existing
		}
	} else {
		m.prompts.Set(prompt.Key(), prompt)
	}
	return prompt
}

// RenderPrompt ports render_prompt for the local-prompt path. Mounted servers
// are asked through GetPromptViaServer; their NotFoundError falls through.
func (m *PromptManager) RenderPrompt(name string, arguments map[string]any) (*GetPromptResult, error) {
	if _, ok := m.prompts.Get(name); ok {
		prompt, err := m.GetPrompt(name)
		if err != nil {
			return nil, err
		}
		if prompt == nil {
			return nil, &fastmcp.NotFoundError{Msg: "Unknown prompt: " + name}
		}
		renderer, ok := interface{}(prompt).(PromptRenderer)
		if !ok {
			return nil, &fastmcp.PromptError{FastMCPError: fastmcp.FastMCPError{Msg: "Error rendering prompt " + fmt.Sprintf("%q", name) + "."}}
		}
		messages, rerr := renderer.Render(arguments)
		if rerr != nil {
			var perr *fastmcp.PromptError
			if ok := asPromptError(rerr, &perr); ok {
				return nil, perr
			}
			if m.MaskErrorDetails {
				return nil, &fastmcp.PromptError{FastMCPError: fastmcp.FastMCPError{Msg: "Error rendering prompt " + fmt.Sprintf("%q", name)}}
			}
			return nil, &fastmcp.PromptError{FastMCPError: fastmcp.FastMCPError{Msg: "Error rendering prompt " + fmt.Sprintf("%q", name) + ": " + rerr.Error()}}
		}
		return &GetPromptResult{Description: prompt.Description, Messages: messages}, nil
	}
	for i := len(m.MountedServers) - 1; i >= 0; i-- {
		mounted := m.MountedServers[i]
		promptKey := name
		if mounted.Prefix != "" {
			prefix := mounted.Prefix + "_"
			if len(name) < len(prefix) || name[:len(prefix)] != prefix {
				continue
			}
			promptKey = name[len(prefix):]
		}
		res, err := mounted.Server.GetPromptViaServer(promptKey, arguments)
		if err != nil {
			var nf *fastmcp.NotFoundError
			if asNotFound(err, &nf) {
				continue
			}
			return nil, err
		}
		return res, nil
	}
	return nil, &fastmcp.NotFoundError{Msg: "Unknown prompt: " + name}
}

func asPromptError(err error, target **fastmcp.PromptError) bool {
	if e, ok := err.(*fastmcp.PromptError); ok {
		*target = e
		return true
	}
	return false
}

func asNotFound(err error, target **fastmcp.NotFoundError) bool {
	if e, ok := err.(*fastmcp.NotFoundError); ok {
		*target = e
		return true
	}
	return false
}
