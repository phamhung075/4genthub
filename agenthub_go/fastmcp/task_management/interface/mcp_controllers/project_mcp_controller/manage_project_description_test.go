package project_mcp_controller

import (
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func TestManageProjectParametersOrderAndValues(t *testing.T) {
	params := ManageProjectParametersDescription()
	wantKeys := []string{"action", "project_id", "name", "description", "user_id", "force"}
	got := params.Keys()
	if len(got) != len(wantKeys) {
		t.Fatalf("keys = %v", got)
	}
	for i, k := range wantKeys {
		if got[i] != k {
			t.Fatalf("key[%d] = %s, want %s", i, got[i], k)
		}
	}
	if v := params.GetAny("action"); v != "Project management action to perform. Valid values: create, get, list, update, delete, project_health_check, cleanup_obsolete, validate_integrity, rebalance_agents" {
		t.Fatalf("action desc = %v", v)
	}
	if v := params.GetAny("force"); v != "Force parameter to bypass safety checks for maintenance and delete operations" {
		t.Fatalf("force desc = %v", v)
	}
}

func TestManageProjectParams(t *testing.T) {
	m := ManageProjectParams()
	if v := m.GetAny("type"); v != "object" {
		t.Fatalf("type = %v", v)
	}
	if v := m.GetAny("additionalProperties"); v != false {
		t.Fatalf("additionalProperties = %v", v)
	}
	required := m.GetAny("required").([]any)
	if len(required) != 1 || required[0] != "action" {
		t.Fatalf("required = %v", required)
	}
	if v := m.GetAny("_validation_note"); v != "Only action required at schema level - business logic validates per action" {
		t.Fatalf("validation note = %v", v)
	}
	props := GetManageProjectParameters()
	if props.Len() != 6 {
		t.Fatalf("properties len = %d", props.Len())
	}
	wantPropKeys := []string{"action", "project_id", "name", "description", "user_id", "force"}
	for i, k := range wantPropKeys {
		if got := props.Keys()[i]; got != k {
			t.Fatalf("prop key[%d] = %s, want %s", i, got, k)
		}
	}
	// each property is a dict with type + description in that order
	actionAny, _ := props.Get("action")
	action := actionAny.(*entities.OrderedMap[any])
	if action.Keys()[0] != "type" || action.Keys()[1] != "description" {
		t.Fatalf("action property keys = %v", action.Keys())
	}
	if v := action.GetAny("type"); v != "string" {
		t.Fatalf("action type = %v", v)
	}
	projectIDAny, _ := props.Get("project_id")
	projectID := projectIDAny.(*entities.OrderedMap[any])
	if v := projectID.GetAny("type"); v != "UUID" {
		t.Fatalf("project_id type = %v", v)
	}
}

func TestGetManageProjectDescription(t *testing.T) {
	if GetManageProjectDescription() != ManageProjectDescription {
		t.Fatal("description accessor mismatch")
	}
	if len(GetManageProjectDescription()) == 0 {
		t.Fatal("description must not be empty")
	}
}
