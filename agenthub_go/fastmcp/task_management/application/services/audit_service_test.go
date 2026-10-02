package services

import (
	"errors"
	"reflect"
	"testing"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

func TestAuditSvcLogOperationMetricsAndEntry(t *testing.T) {
	svc := NewAuditService(nil)
	result := map[string]any{"success": true, "compliance_score": 90.0}
	if err := svc.LogOperation("op1", result, value_objects.ComplianceLevelStrict); err != nil {
		t.Fatalf("LogOperation returned error: %v", err)
	}

	metrics := svc.GetComplianceMetrics()
	if got := auditSvcMustGet(t, metrics, "total_operations"); got != 1 {
		t.Fatalf("total_operations = %v, want 1", got)
	}
	if got := auditSvcMustGet(t, metrics, "compliant_operations"); got != 1 {
		t.Fatalf("compliant_operations = %v, want 1", got)
	}
	if got := auditSvcMustGet(t, metrics, "violations"); got != 0 {
		t.Fatalf("violations = %v, want 0", got)
	}
	if got := auditSvcMustGet(t, metrics, "last_audit"); got == nil {
		t.Fatalf("last_audit = nil, want timestamp")
	}

	log := svc.GetAuditLog(100)
	if len(log) != 1 {
		t.Fatalf("audit log length = %d, want 1", len(log))
	}
	entry := log[0]
	wantKeys := []string{"timestamp", "operation", "compliance_level", "success", "compliance_score", "details"}
	if got := entry.Keys(); !reflect.DeepEqual(got, wantKeys) {
		t.Fatalf("entry keys = %v, want %v", got, wantKeys)
	}
	if got := auditSvcMustGet(t, entry, "operation"); got != "op1" {
		t.Fatalf("operation = %v, want op1", got)
	}
	if got := auditSvcMustGet(t, entry, "compliance_level"); got != "strict" {
		t.Fatalf("compliance_level = %v, want strict", got)
	}
	if got := auditSvcMustGet(t, entry, "success"); got != true {
		t.Fatalf("success = %v, want true", got)
	}
	if got := auditSvcMustGet(t, entry, "compliance_score"); got != 90.0 {
		t.Fatalf("compliance_score = %v, want 90.0", got)
	}
}

func TestAuditSvcLogOperationStringComplianceFallback(t *testing.T) {
	svc := NewAuditService(nil)
	if err := svc.LogOperation("op2", map[string]any{"success": false}, "bogus"); err != nil {
		t.Fatalf("LogOperation returned error: %v", err)
	}
	entry := svc.GetAuditLog(1)[0]
	if got := auditSvcMustGet(t, entry, "compliance_level"); got != "low" {
		t.Fatalf("compliance_level = %v, want low", got)
	}
	if got := auditSvcMustGet(t, entry, "compliance_score"); got != 0.0 {
		t.Fatalf("compliance_score = %v, want 0.0", got)
	}
	metrics := svc.GetComplianceMetrics()
	if got := auditSvcMustGet(t, metrics, "violations"); got != 1 {
		t.Fatalf("violations = %v, want 1", got)
	}

	// A valid string level is kept; a score just below the threshold is a violation.
	if err := svc.LogOperation("op3", map[string]any{"success": true, "compliance_score": 84.9}, "high"); err != nil {
		t.Fatalf("LogOperation returned error: %v", err)
	}
	if got := auditSvcMustGet(t, svc.GetAuditLog(1)[0], "compliance_level"); got != "high" {
		t.Fatalf("compliance_level = %v, want high", got)
	}
}

func TestAuditSvcLogOperationNonNumericScoreIsTypeError(t *testing.T) {
	svc := NewAuditService(nil)
	err := svc.LogOperation("op", map[string]any{"success": true, "compliance_score": nil}, value_objects.ComplianceLevelLow)
	var typeErr *value_objects.TypeError
	if !errors.As(err, &typeErr) {
		t.Fatalf("error = %v, want *value_objects.TypeError", err)
	}
}

func TestAuditSvcGenerateComplianceReportShape(t *testing.T) {
	svc := NewAuditService(nil)
	if err := svc.LogOperation("op1", map[string]any{"success": true, "compliance_score": 90.0}, value_objects.ComplianceLevelStrict); err != nil {
		t.Fatalf("LogOperation returned error: %v", err)
	}

	report := svc.GenerateComplianceReport()
	wantKeys := []string{"report_id", "generated_at", "overall_compliance_rate", "total_operations",
		"compliant_operations", "violations", "recent_violations", "compliance_trend", "recommendations"}
	if got := report.Keys(); !reflect.DeepEqual(got, wantKeys) {
		t.Fatalf("report keys = %v, want %v", got, wantKeys)
	}
	if got := auditSvcMustGet(t, report, "overall_compliance_rate"); got != 100.0 {
		t.Fatalf("overall_compliance_rate = %v, want 100.0", got)
	}
	if got := auditSvcMustGet(t, report, "compliance_trend"); got != "insufficient_data" {
		t.Fatalf("compliance_trend = %v, want insufficient_data", got)
	}
	recommendations, _ := report.Get("recommendations")
	if got := recommendations.([]string); len(got) != 1 || got[0] != "Compliance is on track. Continue monitoring." {
		t.Fatalf("recommendations = %v", got)
	}
	recent, _ := report.Get("recent_violations")
	if got := recent.([]*entities.OrderedMap[any]); len(got) != 0 {
		t.Fatalf("recent_violations = %v, want empty", got)
	}
}

func TestAuditSvcClearAuditLogResetsMetrics(t *testing.T) {
	svc := NewAuditService(nil)
	if err := svc.LogOperation("op", map[string]any{"success": true, "compliance_score": 100.0}, value_objects.ComplianceLevelHigh); err != nil {
		t.Fatalf("LogOperation returned error: %v", err)
	}
	svc.ClearAuditLog()
	if got := len(svc.GetAuditLog(0)); got != 0 {
		t.Fatalf("audit log length = %d, want 0", got)
	}
	metrics := svc.GetComplianceMetrics()
	if got := auditSvcMustGet(t, metrics, "total_operations"); got != 0 {
		t.Fatalf("total_operations = %v, want 0", got)
	}
	if got := auditSvcMustGet(t, metrics, "last_audit"); got != nil {
		t.Fatalf("last_audit = %v, want nil", got)
	}
}

func auditSvcMustGet(t *testing.T, m *entities.OrderedMap[any], key string) any {
	t.Helper()
	v, ok := m.Get(key)
	if !ok {
		t.Fatalf("key %q missing", key)
	}
	return v
}
