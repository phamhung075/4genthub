package services

import (
	"encoding/json"
	"os"
	"reflect"
	"testing"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

type hrCase struct {
	Name string `json:"name"`
	Rule string `json:"rule"`
	Args struct {
		St   string `json:"st"`
		Pr   string `json:"pr"`
		Deps int    `json:"deps"`
		Subs int    `json:"subs"`
		Age  int    `json:"age"`
		Tl   bool   `json:"tl"`
		Ctx  bool   `json:"ctx"`
	} `json:"args"`
	Want struct {
		Error *string `json:"error"`
		Hint  *struct {
			Type       string         `json:"type"`
			Priority   string         `json:"priority"`
			Message    string         `json:"message"`
			Action     string         `json:"action"`
			Source     string         `json:"source"`
			Confidence float64        `json:"confidence"`
			Reasoning  string         `json:"reasoning"`
			Patterns   []string       `json:"patterns"`
			Related    []string       `json:"related"`
			Data       map[string]any `json:"data"`
			TaskID     string         `json:"task_id"`
		} `json:"hint"`
	} `json:"want"`
}

func hrRule(name string) HintRule {
	return map[string]HintRule{"stalled": NewStalledProgressRule(), "impl": NewImplementationReadyForTestingRule(),
		"missing": MissingContextRule{}, "deps": NewComplexDependencyRule(), "near": NewNearCompletionRule(),
		"collab": CollaborationNeededRule{}}[name]
}

func TestHintRulesMatchPython(t *testing.T) {
	raw, err := os.ReadFile("testdata/hint_rules_cases.json")
	if err != nil {
		t.Fatal(err)
	}
	var cases []hrCase
	if err := json.Unmarshal(raw, &cases); err != nil {
		t.Fatal(err)
	}
	for _, c := range cases {
		task := tvTask(t, func(k *entities.Task) {
			tvSetStatus(t, k, c.Args.St)
			tvSetPriority(k, c.Args.Pr)
			for i := 0; i < c.Args.Deps; i++ {
				id, _ := value_objects.NewTaskId(tvU + string(rune('1')) + string(rune('0'+i)))
				k.Dependencies = append(k.Dependencies, id)
			}
			for i := 0; i < c.Args.Subs; i++ {
				k.Subtasks = append(k.Subtasks, "s")
			}
			created := time.Now().Add(-time.Duration(c.Args.Age) * 24 * time.Hour)
			k.CreatedAt = &created
			if c.Args.Tl {
				k.ProgressTimeline = &value_objects.ProgressTimeline{}
			}
		})
		var tctx *entities.TaskContext
		if c.Args.Ctx {
			tctx = &entities.TaskContext{}
		}
		h, err := hrRule(c.Rule).Evaluate(NewRuleContext(task, tctx))
		if c.Want.Error != nil {
			if err == nil || err.Error() != *c.Want.Error {
				t.Errorf("%s: err %v want %q", c.Name, err, *c.Want.Error)
			}
			continue
		}
		if err != nil {
			t.Errorf("%s: unexpected err %v", c.Name, err)
			continue
		}
		if (h == nil) != (c.Want.Hint == nil) {
			t.Errorf("%s: hint %v want %v", c.Name, h, c.Want.Hint)
			continue
		}
		if h == nil {
			continue
		}
		w := c.Want.Hint
		gotData, _ := json.Marshal(h.ContextData)
		wantData, _ := json.Marshal(w.Data)
		if string(h.Type) != w.Type || string(h.Priority) != w.Priority || h.Message != w.Message ||
			h.SuggestedAction != w.Action || h.Metadata.Source != w.Source || h.Metadata.Confidence != w.Confidence ||
			h.Metadata.Reasoning != w.Reasoning || !reflect.DeepEqual(h.Metadata.PatternsDetected, w.Patterns) ||
			len(h.Metadata.RelatedTasks) != len(w.Related) || string(gotData) != string(wantData) || h.TaskID != w.TaskID {
			t.Errorf("%s: got %+v data=%s want %+v", c.Name, h, gotData, w)
		}
	}
}

func TestStalledHintBuilder(t *testing.T) {
	task := tvTask(t, func(k *entities.Task) { tvSetStatus(t, k, "blocked") })
	h := NewStalledProgressRule().stalledHint(task, 49*time.Hour)
	if h.Priority != value_objects.HintPriorityCritical || h.Type != value_objects.HintTypeBlockerResolution ||
		h.Message != "Task has been blocked for 49 hours" {
		t.Fatalf("%+v", h)
	}
}
