package subtask_mcp_controller

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestManageSubtaskDescriptionConstants(t *testing.T) {
	if GetSubtaskDescription() != MANAGE_SUBTASK_DESCRIPTION {
		t.Error("get_subtask_description must return the module description")
	}
	if SUBTASK_DESCRIPTION != MANAGE_SUBTASK_DESCRIPTION {
		t.Error("SUBTASK_DESCRIPTION alias mismatch")
	}
	if GetManageSubtaskDescription() != MANAGE_SUBTASK_DESCRIPTION {
		t.Error("get_manage_subtask_description mismatch")
	}

	props := GetManageSubtaskParameters()
	wantKeys := []string{
		"action", "task_id", "subtask_id", "title", "description", "status",
		"priority", "assignees", "acceptance_criteria", "scope", "progress_percentage", "progress_notes",
		"completion_summary", "testing_notes", "insights_found",
		"challenges_overcome", "skills_learned", "next_recommendations",
		"deliverables", "completion_quality", "blockers", "impact_on_parent", "user_id",
	}
	gotKeys := props.Keys()
	if len(gotKeys) != len(wantKeys) {
		t.Fatalf("properties len=%d want %d", len(gotKeys), len(wantKeys))
	}
	for i, k := range wantKeys {
		if gotKeys[i] != k {
			t.Fatalf("properties[%d]=%q want %q", i, gotKeys[i], k)
		}
	}

	action, _ := props.Get("action")
	actionMap, ok := action.(*entities.OrderedMap[any])
	if !ok {
		t.Fatalf("action property type %T", action)
	}
	if v, _ := actionMap.Get("type"); v != "string" {
		t.Errorf("action type=%v want string", v)
	}
	if v, _ := actionMap.Get("description"); v != omGetStr(MANAGE_SUBTASK_PARAMETERS_DESCRIPTION, "action") {
		t.Errorf("action description mismatch: %v", v)
	}

	required, _ := MANAGE_SUBTASK_PARAMS.Get("required")
	if req, ok := required.([]string); !ok || len(req) != 1 || req[0] != "action" {
		t.Errorf("required=%v want [action]", required)
	}
	if v, _ := MANAGE_SUBTASK_PARAMS.Get("additionalProperties"); v != false {
		t.Errorf("additionalProperties=%v want false", v)
	}
}
