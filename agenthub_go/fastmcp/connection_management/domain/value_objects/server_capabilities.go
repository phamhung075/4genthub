package value_objects

import (
	"agenthub/fastmcp/task_management/domain/entities"
	tmvo "agenthub/fastmcp/task_management/domain/value_objects"
)

// ServerCapabilities is the immutable set of server capabilities.
type ServerCapabilities struct {
	CoreFeatures     []string
	AvailableActions *entities.OrderedMap[[]string]
	// AuthenticationEnabled and MvpMode hold the raw `authentication` dict values
	// (Python does not coerce them to bool).
	AuthenticationEnabled any
	MvpMode               any
	Version               string
}

// NewServerCapabilities validates the values (dataclass __post_init__).
func NewServerCapabilities(coreFeatures []string, actions *entities.OrderedMap[[]string], authEnabled, mvpMode any, version string) (ServerCapabilities, error) {
	if len(coreFeatures) == 0 {
		return ServerCapabilities{}, &tmvo.ValueError{Msg: "Core features cannot be empty"}
	}
	if actions == nil || actions.Len() == 0 {
		return ServerCapabilities{}, &tmvo.ValueError{Msg: "Available actions cannot be empty"}
	}
	if version == "" {
		return ServerCapabilities{}, &tmvo.ValueError{Msg: "Version cannot be empty"}
	}
	return ServerCapabilities{coreFeatures, actions, authEnabled, mvpMode, version}, nil
}

func (c ServerCapabilities) GetTotalActionsCount() int {
	n := 0
	for _, k := range c.AvailableActions.Keys() {
		a, _ := c.AvailableActions.Get(k)
		n += len(a)
	}
	return n
}

func (c ServerCapabilities) HasFeature(feature string) bool {
	for _, f := range c.CoreFeatures {
		if f == feature {
			return true
		}
	}
	return false
}

func (c ServerCapabilities) HasActionCategory(category string) bool {
	return c.AvailableActions.Has(category)
}

func (c ServerCapabilities) ToDict() *entities.OrderedMap[any] {
	d := entities.NewOrderedMap[any]()
	d.Set("success", true)
	d.Set("core_features", c.CoreFeatures)
	d.Set("available_actions", c.AvailableActions)
	d.Set("authentication_enabled", c.AuthenticationEnabled)
	d.Set("mvp_mode", c.MvpMode)
	d.Set("version", c.Version)
	d.Set("total_actions", c.GetTotalActionsCount())
	return d
}
