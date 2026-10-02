package git_branch_mcp_controller

import (
	"strings"
	"testing"
)

func TestManageGitBranchDescriptionShape(t *testing.T) {
	want := "\nGIT BRANCH MANAGEMENT - Branch operations: CRUD | agent assignment | lifecycle | statistics\n\nACTIONS: create | get | list | update | delete | assign_agent | unassign_agent | get_statistics | archive | restore\n\nKEY PARAMS: project_id (REQUIRED for all) | git_branch_name (REQUIRED for create) | git_branch_id (REQUIRED for most except create/list) | agent_id (REQUIRED for assign/unassign)\n\nAGENT ASSIGNMENT: Use git_branch_name OR git_branch_id for identification\n\nSTATISTICS: total_tasks | completed_tasks | progress_percentage\n\nERRORS: Missing fields→specific error | Duplicate names→rejected | Invalid UUIDs→clear error\n"
	if ManageGitBranchDescription != want {
		t.Fatalf("description mismatch")
	}
	if GetManageGitBranchDescription() != want {
		t.Fatalf("getter mismatch")
	}

	desc := ManageGitBranchParametersDescription
	if got := strings.Join(desc.Keys(), ","); got != "action,project_id,git_branch_id,git_branch_name,git_branch_description,agent_id,user_id" {
		t.Fatalf("parameter keys = %s", got)
	}

	if _, ok := GetManageGitBranchParameters().(interface{ Keys() []string }); !ok {
		t.Fatalf("properties is not a mapping")
	}

	required, _ := ManageGitBranchParams.Get("required")
	if len(required.([]any)) != 1 || required.([]any)[0] != "action" {
		t.Fatalf("required = %v", required)
	}
	additional, _ := ManageGitBranchParams.Get("additionalProperties")
	if additional != false {
		t.Fatalf("additionalProperties = %v", additional)
	}
}
