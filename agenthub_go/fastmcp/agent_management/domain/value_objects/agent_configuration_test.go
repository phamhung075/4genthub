package value_objects_test

import (
	"testing"

	"agenthub/fastmcp/agent_management/domain/internal/amtest"
	"agenthub/fastmcp/agent_management/domain/value_objects"
	"agenthub/fastmcp/task_management/domain/entities"
)

func TestAgentConfigurationParity(t *testing.T) {
	for _, c := range amtest.Items(amtest.Field(amtest.Fixture(t), "config")) {
		in := amtest.Str(c, "in")
		parsed, err := entities.DecodeJSON([]byte(in))
		if err != nil {
			t.Fatal(err)
		}
		var got *entities.OrderedMap[any]
		cfg, err := value_objects.AgentConfigurationFromDict(parsed.(*entities.OrderedMap[any]))
		if err != nil {
			got = amtest.ErrMap(err)
		} else {
			js, _ := cfg.ToJSON()
			withPrompt, _ := cfg.WithSystemPrompt("new")
			_, emptyErr := cfg.WithSystemPrompt(" ")
			withTools, _ := cfg.WithTools([]string{"x", "y"})
			var merge any
			if cfg.Capabilities != nil {
				newCaps := amtest.Obj("a", int64(9), "new", []any{int64(1)})
				merged, _ := cfg.MergeCapabilities(newCaps)
				merge = merged.ToDict()
			}
			got = amtest.Result(amtest.Obj(
				"dict", cfg.ToDict(), "json", js, "with_prompt", withPrompt.ToDict(),
				"with_prompt_empty", amtest.Result(nil, emptyErr), "with_tools", withTools.ToDict(), "merge", merge), nil)
		}
		want := amtest.Field(c, "out")
		if g, w := amtest.Canon(t, got), amtest.Canon(t, want); g != w {
			t.Errorf("%s:\n got  %s\n want %s", in, g, w)
		}
	}
}
