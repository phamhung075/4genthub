package services

import (
	"reflect"
	"strings"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
)

func zpEnfOrderedKeys(t *testing.T, m *entities.OrderedMap[any]) string {
	t.Helper()
	return strings.Join(m.Keys(), ",")
}

func zpEnfTestParams(entries ...any) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	for i := 0; i+1 < len(entries); i += 2 {
		m.Set(entries[i].(string), entries[i+1])
	}
	return m
}

func TestParameterEnforcementService_DisabledAllows(t *testing.T) {
	svc := NewParameterEnforcementService(zpEnfEnforcementLevelDisabled, nil)
	agent := "agent-1"
	result := svc.Enforce("update", zpEnfTestParams(), &agent, nil)

	if !result.Allowed {
		t.Error("disabled enforcement should allow")
	}
	if result.Level != zpEnfEnforcementLevelDisabled {
		t.Errorf("level = %v, want disabled", result.Level)
	}
	if result.Message != "Parameter enforcement disabled" {
		t.Errorf("message = %q", result.Message)
	}
	if result.ComplianceTracked {
		t.Error("disabled enforcement should not track compliance")
	}
	if svc.GetAgentCompliance("agent-1") != nil {
		t.Error("disabled enforcement should not create compliance stats")
	}
}

func TestParameterEnforcementService_SoftMissing(t *testing.T) {
	svc := NewParameterEnforcementService(zpEnfEnforcementLevelSoft, nil)
	agent := "agent-1"
	result := svc.Enforce("update", zpEnfTestParams(), &agent, nil)

	if !result.Allowed {
		t.Error("soft enforcement should allow")
	}
	if result.Message != "Operation allowed (soft enforcement - logging only)" {
		t.Errorf("message = %q", result.Message)
	}
	if !reflect.DeepEqual(result.MissingRequired, []string{"work_notes", "progress_made"}) {
		t.Errorf("missing_required = %v", result.MissingRequired)
	}
	if !reflect.DeepEqual(result.MissingRecommended, []string{"files_modified", "blockers_encountered", "decisions_made"}) {
		t.Errorf("missing_recommended = %v", result.MissingRecommended)
	}
	if !result.ComplianceTracked || result.AgentID == nil || *result.AgentID != "agent-1" {
		t.Errorf("compliance tracking not set: %+v", result)
	}

	compliance := svc.GetAgentCompliance("agent-1")
	if compliance == nil {
		t.Fatal("compliance not tracked")
	}
	if compliance.TotalOperations != 1 || compliance.WarningsIssued != 1 || compliance.OperationsBlocked != 0 {
		t.Errorf("compliance = %+v", compliance)
	}
}

func TestParameterEnforcementService_WarningMissingRequired(t *testing.T) {
	svc := NewParameterEnforcementService(zpEnfEnforcementLevelWarning, nil)
	result := svc.Enforce("complete", zpEnfTestParams(), nil, nil)

	if !result.Allowed {
		t.Error("warning enforcement should allow")
	}
	if result.Message != "Operation allowed with warnings" {
		t.Errorf("message = %q", result.Message)
	}
	wantHints := []string{
		"⚠️ Missing required parameters: completion_summary",
		"These parameters will be required in strict mode",
		"💡 Consider adding: testing_notes, deployment_notes, files_created, files_modified",
	}
	if !reflect.DeepEqual(result.Hints, wantHints) {
		t.Errorf("hints = %#v\nwant %#v", result.Hints, wantHints)
	}
	if got := zpEnfOrderedKeys(t, result.Examples); got != "completion_summary" {
		t.Errorf("examples key order = %q", got)
	}
	if v, _ := result.Examples.Get("completion_summary"); v != zpEnfParameterTemplates["completion_summary"] {
		t.Errorf("completion_summary template mismatch: %v", v)
	}
}

func TestParameterEnforcementService_WarningRecommendedOnly(t *testing.T) {
	svc := NewParameterEnforcementService(zpEnfEnforcementLevelWarning, nil)
	params := zpEnfTestParams("work_notes", "w", "progress_made", "p")
	result := svc.Enforce("update", params, nil, nil)

	if result.Message != "Operation allowed" {
		t.Errorf("message = %q, want Operation allowed", result.Message)
	}
	if len(result.MissingRequired) != 0 {
		t.Errorf("missing_required = %v, want empty", result.MissingRequired)
	}
	wantHints := []string{"💡 Consider adding: files_modified, blockers_encountered, decisions_made"}
	if !reflect.DeepEqual(result.Hints, wantHints) {
		t.Errorf("hints = %#v", result.Hints)
	}
	if result.Examples.Len() != 0 {
		t.Errorf("examples should be empty, got %v", result.Examples.Keys())
	}
}

func TestParameterEnforcementService_EmptyStringCountsMissing(t *testing.T) {
	svc := NewParameterEnforcementService(zpEnfEnforcementLevelWarning, nil)
	params := zpEnfTestParams("work_notes", "", "progress_made", "done")
	result := svc.Enforce("update", params, nil, nil)

	if !reflect.DeepEqual(result.MissingRequired, []string{"work_notes"}) {
		t.Errorf("missing_required = %v, want [work_notes]", result.MissingRequired)
	}
}

func TestParameterEnforcementService_StrictBlocks(t *testing.T) {
	svc := NewParameterEnforcementService(zpEnfEnforcementLevelStrict, nil)
	result := svc.Enforce("update", zpEnfTestParams(), nil, nil)

	if result.Allowed {
		t.Error("strict enforcement should block")
	}
	if result.Level != zpEnfEnforcementLevelStrict {
		t.Errorf("level = %v, want strict", result.Level)
	}
	wantMessage := "Operation blocked: Missing required parameters (work_notes, progress_made)"
	if result.Message != wantMessage {
		t.Errorf("message = %q, want %q", result.Message, wantMessage)
	}
	wantHints := []string{
		"❌ Operation blocked: Missing required parameters for update",
		"Required: work_notes, progress_made",
		"Please provide these parameters to proceed",
		"Also recommended: files_modified, blockers_encountered, decisions_made",
	}
	if !reflect.DeepEqual(result.Hints, wantHints) {
		t.Errorf("hints = %#v", result.Hints)
	}
	if got := zpEnfOrderedKeys(t, result.Examples); got != "work_notes,progress_made,example_command" {
		t.Errorf("examples key order = %q", got)
	}
	exampleCommand, _ := result.Examples.Get("example_command")
	ec := exampleCommand.(*entities.OrderedMap[any])
	if got := zpEnfOrderedKeys(t, ec); got != "action,task_id,work_notes,progress_made,files_modified" {
		t.Errorf("example_command key order = %q", got)
	}
	files, _ := ec.Get("files_modified")
	if !reflect.DeepEqual(files, []string{"auth/jwt.py", "auth/utils.py"}) {
		t.Errorf("files_modified = %v", files)
	}
}

func TestParameterEnforcementService_StrictSuccess(t *testing.T) {
	svc := NewParameterEnforcementService(zpEnfEnforcementLevelStrict, nil)
	agent := "agent-9"
	params := zpEnfTestParams(
		"work_notes", "w", "progress_made", "p",
		"files_modified", []string{"a.go"}, "blockers_encountered", []string{"b"}, "decisions_made", []string{"d"},
	)
	result := svc.Enforce("update", params, &agent, nil)

	if !result.Allowed {
		t.Error("strict enforcement with all parameters should allow")
	}
	if result.Message != "" {
		t.Errorf("message = %q, want empty", result.Message)
	}
	if len(result.Hints) != 0 {
		t.Errorf("hints = %v, want empty", result.Hints)
	}
	if !result.ComplianceTracked {
		t.Error("compliance should be tracked")
	}

	// Required only -> success hint about recommended parameters.
	result = svc.Enforce("update", zpEnfTestParams("work_notes", "w", "progress_made", "p"), nil, nil)
	if !result.Allowed {
		t.Error("should allow")
	}
	want := []string{"✅ All required parameters provided for update"}
	if !reflect.DeepEqual(result.Hints, want) {
		t.Errorf("hints = %#v, want %#v", result.Hints, want)
	}
}

func TestParameterEnforcementService_UnknownAction(t *testing.T) {
	svc := NewParameterEnforcementService(zpEnfEnforcementLevelWarning, nil)
	result := svc.Enforce("bogus", zpEnfTestParams(), nil, nil)

	if !result.Allowed || result.Message != "Operation allowed" {
		t.Errorf("result = %+v", result)
	}
	if len(result.MissingRequired) != 0 || len(result.MissingRecommended) != 0 {
		t.Errorf("missing = %v / %v", result.MissingRequired, result.MissingRecommended)
	}
	if result.Examples.Len() != 0 {
		t.Errorf("examples = %v", result.Examples.Keys())
	}
}

func TestParameterEnforcementService_ComplianceTracking(t *testing.T) {
	svc := NewParameterEnforcementService(zpEnfEnforcementLevelStrict, nil)
	agent := "agent-1"

	svc.Enforce("update", zpEnfTestParams(), &agent, nil)
	compliance := svc.GetAgentCompliance("agent-1")
	if compliance.TotalOperations != 1 || compliance.OperationsBlocked != 1 || compliance.CompliantOperations != 0 {
		t.Fatalf("compliance after block = %+v", compliance)
	}
	if compliance.ComplianceRate != 0.0 {
		t.Errorf("compliance rate = %v, want 0.0", compliance.ComplianceRate)
	}

	svc.Enforce("update", zpEnfTestParams("work_notes", "w", "progress_made", "p"), &agent, nil)
	compliance = svc.GetAgentCompliance("agent-1")
	if compliance.TotalOperations != 2 || compliance.CompliantOperations != 1 || compliance.ConsecutiveFailures != 0 {
		t.Fatalf("compliance after success = %+v", compliance)
	}
	if compliance.ComplianceRate != 0.5 {
		t.Errorf("compliance rate = %v, want 0.5", compliance.ComplianceRate)
	}
	if compliance.LastOperation == nil {
		t.Error("last_operation should be set")
	}

	// WARNING-level failures are warnings, not blocks.
	warnSvc := NewParameterEnforcementService(zpEnfEnforcementLevelWarning, nil)
	warnSvc.Enforce("update", zpEnfTestParams(), &agent, nil)
	warnCompliance := warnSvc.GetAgentCompliance(agent)
	if warnCompliance.WarningsIssued != 1 || warnCompliance.OperationsBlocked != 0 {
		t.Errorf("warning compliance = %+v", warnCompliance)
	}
}

func TestParameterEnforcementService_AgentComplianceUpdateCompliance(t *testing.T) {
	compliance := &AgentCompliance{AgentID: "x"}
	compliance.UpdateCompliance(false, false)
	if compliance.TotalOperations != 1 || compliance.WarningsIssued != 1 || compliance.ConsecutiveFailures != 1 {
		t.Fatalf("after warning: %+v", compliance)
	}
	if compliance.ComplianceRate != 0.0 {
		t.Errorf("rate = %v, want 0.0", compliance.ComplianceRate)
	}
	compliance.UpdateCompliance(true, false)
	if compliance.CompliantOperations != 1 || compliance.ConsecutiveFailures != 0 {
		t.Fatalf("after compliance: %+v", compliance)
	}
	if compliance.ComplianceRate != 0.5 {
		t.Errorf("rate = %v, want 0.5", compliance.ComplianceRate)
	}
	compliance.UpdateCompliance(false, true)
	if compliance.OperationsBlocked != 1 {
		t.Errorf("operations_blocked = %d, want 1", compliance.OperationsBlocked)
	}
}

func TestParameterEnforcementService_GetAllComplianceStatsCopy(t *testing.T) {
	svc := NewParameterEnforcementService(zpEnfEnforcementLevelWarning, nil)
	agent := "a"
	svc.Enforce("update", zpEnfTestParams(), &agent, nil)

	stats := svc.GetAllComplianceStats()
	if stats.Len() != 1 {
		t.Fatalf("stats len = %d, want 1", stats.Len())
	}
	if v, ok := stats.Get("a"); !ok || v != svc.GetAgentCompliance("a") {
		t.Error("copy should hold the same AgentCompliance pointer")
	}
}

func TestParameterEnforcementService_WithUserAndSetLevel(t *testing.T) {
	svc := NewParameterEnforcementService(zpEnfEnforcementLevelWarning, nil)
	other := svc.WithUser("user-2")
	if other == svc {
		t.Fatal("WithUser should return a new instance")
	}
	if other.userID == nil || *other.userID != "user-2" {
		t.Fatalf("userID = %v", other.userID)
	}
	if other.EnforcementLevel != zpEnfEnforcementLevelWarning {
		t.Errorf("level = %v, want warning", other.EnforcementLevel)
	}

	svc.SetEnforcementLevel(zpEnfEnforcementLevelStrict)
	if svc.EnforcementLevel != zpEnfEnforcementLevelStrict {
		t.Errorf("level = %v, want strict", svc.EnforcementLevel)
	}
}

func TestParameterEnforcementService_GetParameterHints(t *testing.T) {
	svc := NewParameterEnforcementService(zpEnfEnforcementLevelWarning, nil)

	hints := svc.GetParameterHints("update")
	if got := zpEnfOrderedKeys(t, hints); got != "action,required,recommended,templates" {
		t.Fatalf("hints key order = %q", got)
	}
	if v, _ := hints.Get("required"); !reflect.DeepEqual(v, []string{"work_notes", "progress_made"}) {
		t.Errorf("required = %v", v)
	}
	templates, _ := hints.Get("templates")
	templatesMap := templates.(*entities.OrderedMap[any])
	if got := zpEnfOrderedKeys(t, templatesMap); got != "work_notes,progress_made,files_modified,blockers_encountered,decisions_made" {
		t.Errorf("templates key order = %q", got)
	}

	hints = svc.GetParameterHints("complete")
	templates, _ = hints.Get("templates")
	templatesMap = templates.(*entities.OrderedMap[any])
	if got := zpEnfOrderedKeys(t, templatesMap); got != "completion_summary,testing_notes,files_modified" {
		t.Errorf("complete templates key order = %q", got)
	}

	hints = svc.GetParameterHints("bogus")
	if v, _ := hints.Get("required"); !reflect.DeepEqual(v, []string{}) {
		t.Errorf("required = %#v, want []", v)
	}
	templates, _ = hints.Get("templates")
	if templates.(*entities.OrderedMap[any]).Len() != 0 {
		t.Errorf("templates should be empty")
	}
}
