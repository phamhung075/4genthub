package services

import (
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// auditSvcNow is the clock used by the audit service (Python datetime.now(UTC)).
var auditSvcNow = func() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }

// AuditService is the application service for audit trail and compliance monitoring
// (Python application/services/audit_service.py). Logging is dropped.
type AuditService struct {
	auditSvcUserID            *string
	auditSvcAuditLog          []*entities.OrderedMap[any]
	auditSvcComplianceMetrics *entities.OrderedMap[any]
}

// NewAuditService mirrors __init__(user_id=None).
func NewAuditService(userID *string) *AuditService {
	return &AuditService{
		auditSvcUserID:            userID,
		auditSvcAuditLog:          []*entities.OrderedMap[any]{},
		auditSvcComplianceMetrics: auditSvcNewMetrics(),
	}
}

// auditSvcNewMetrics builds the compliance metrics dict with Python's key order.
func auditSvcNewMetrics() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("total_operations", 0)
	m.Set("compliant_operations", 0)
	m.Set("violations", 0)
	m.Set("last_audit", nil)
	return m
}

// auditSvcDictGet is dict.get(key, default) for the dict-like results the service
// accepts (OrderedMap or plain map[string]any).
func auditSvcDictGet(result any, key string, def any) any {
	switch d := result.(type) {
	case *entities.OrderedMap[any]:
		if d == nil {
			return def
		}
		if v, ok := d.Get(key); ok {
			return v
		}
	case map[string]any:
		if v, ok := d[key]; ok {
			return v
		}
	}
	return def
}

// auditSvcTypeName is type(x).__name__ for the values that can reach a comparison.
func auditSvcTypeName(v any) string {
	switch v.(type) {
	case nil:
		return "NoneType"
	case bool:
		return "bool"
	case int, int8, int16, int32, int64, uint, uint8, uint16, uint32, uint64:
		return "int"
	case float32, float64:
		return "float"
	case string:
		return "str"
	case *entities.OrderedMap[any], map[string]any:
		return "dict"
	case []any:
		return "list"
	}
	return "object"
}

// auditSvcScoreAsFloat mirrors the `compliance_score >= 85` numeric comparison. A
// non-number (including None) raises TypeError exactly like Python.
func auditSvcScoreAsFloat(score any) (float64, error) {
	f, ok := value_objects.PyFloat(score)
	if !ok {
		return 0, &value_objects.TypeError{Msg: "'>=' not supported between instances of '" +
			auditSvcTypeName(score) + "' and 'int'"}
	}
	return f, nil
}

// auditSvcErrorString mirrors str(exception).
func auditSvcErrorString(r any) string {
	switch e := r.(type) {
	case error:
		return e.Error()
	case string:
		return e
	}
	return value_objects.PyStr(r)
}

// auditSvcGetUserScopedRepository mirrors _get_user_scoped_repository for the
// hasattr(repository, "with_user") branch. Python's remaining branches rebuild
// repo_class(repository.session, user_id=...) reflectively; that has no Go
// equivalent without the concrete repository type and is left unimplemented.
func (s *AuditService) auditSvcGetUserScopedRepository(repository any) any {
	if repository == nil {
		return repository
	}
	if r, ok := repository.(interface{ WithUser(string) any }); ok && s.auditSvcUserID != nil {
		return r.WithUser(*s.auditSvcUserID)
	}
	return repository
}

// WithUser creates a new service instance scoped to a specific user.
func (s *AuditService) WithUser(userID string) *AuditService { return NewAuditService(&userID) }

// LogOperation logs an operation for the audit trail. complianceLevel may be a
// value_objects.ComplianceLevel or a string (Python backwards compatibility).
func (s *AuditService) LogOperation(operation string, result any, complianceLevel any) error {
	var complianceLevelValue string
	if level, ok := complianceLevel.(value_objects.ComplianceLevel); ok {
		complianceLevelValue = string(level)
	} else {
		complianceLevelValue = value_objects.PyStr(complianceLevel)
		valid := false
		for _, level := range value_objects.ComplianceLevelValues {
			if string(level) == complianceLevelValue {
				valid = true
				break
			}
		}
		if !valid {
			complianceLevelValue = "low"
		}
	}

	timestamp := value_objects.IsoFormat(auditSvcNow())
	success := auditSvcDictGet(result, "success", false)
	score := auditSvcDictGet(result, "compliance_score", 0.0)

	auditEntry := entities.NewOrderedMap[any]()
	auditEntry.Set("timestamp", timestamp)
	auditEntry.Set("operation", operation)
	auditEntry.Set("compliance_level", complianceLevelValue)
	auditEntry.Set("success", success)
	auditEntry.Set("compliance_score", score)
	auditEntry.Set("details", result)

	s.auditSvcAuditLog = append(s.auditSvcAuditLog, auditEntry)

	total, _ := s.auditSvcComplianceMetrics.Get("total_operations")
	s.auditSvcComplianceMetrics.Set("total_operations", total.(int)+1)

	if value_objects.PyTruthy(success) {
		scoreValue, err := auditSvcScoreAsFloat(score)
		if err != nil {
			return err
		}
		if scoreValue >= 85 {
			compliant, _ := s.auditSvcComplianceMetrics.Get("compliant_operations")
			s.auditSvcComplianceMetrics.Set("compliant_operations", compliant.(int)+1)
		} else {
			violations, _ := s.auditSvcComplianceMetrics.Get("violations")
			s.auditSvcComplianceMetrics.Set("violations", violations.(int)+1)
		}
	} else {
		violations, _ := s.auditSvcComplianceMetrics.Get("violations")
		s.auditSvcComplianceMetrics.Set("violations", violations.(int)+1)
	}

	s.auditSvcComplianceMetrics.Set("last_audit", timestamp)
	return nil
}

// GenerateComplianceReport generates a comprehensive compliance report.
func (s *AuditService) GenerateComplianceReport() (report *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			report = entities.NewOrderedMap[any]()
			report.Set("report_id", value_objects.NewUUIDv4())
			report.Set("generated_at", value_objects.IsoFormat(auditSvcNow()))
			report.Set("error", auditSvcErrorString(r))
			report.Set("overall_compliance_rate", 0.0)
		}
	}()

	totalOps, _ := s.auditSvcComplianceMetrics.Get("total_operations")
	compliantOps, _ := s.auditSvcComplianceMetrics.Get("compliant_operations")
	totalInt := totalOps.(int)
	compliantInt := compliantOps.(int)

	denominator := totalInt
	if denominator < 1 {
		denominator = 1
	}
	complianceRate := float64(compliantInt) / float64(denominator) * 100

	start := len(s.auditSvcAuditLog) - 100
	if start < 0 {
		start = 0
	}
	recentViolations := []*entities.OrderedMap[any]{}
	for _, entry := range s.auditSvcAuditLog[start:] {
		success, _ := entry.Get("success")
		if !value_objects.PyTruthy(success) {
			recentViolations = append(recentViolations, entry)
			continue
		}
		score := auditSvcDictGet(entry, "compliance_score", 0)
		scoreValue, err := auditSvcScoreAsFloat(score)
		if err != nil {
			panic(err)
		}
		if scoreValue < 85 {
			recentViolations = append(recentViolations, entry)
		}
	}
	if len(recentViolations) > 10 {
		recentViolations = recentViolations[:10]
	}

	violations, _ := s.auditSvcComplianceMetrics.Get("violations")

	report = entities.NewOrderedMap[any]()
	report.Set("report_id", value_objects.NewUUIDv4())
	report.Set("generated_at", value_objects.IsoFormat(auditSvcNow()))
	report.Set("overall_compliance_rate", complianceRate)
	report.Set("total_operations", totalInt)
	report.Set("compliant_operations", compliantInt)
	report.Set("violations", violations)
	report.Set("recent_violations", recentViolations)
	report.Set("compliance_trend", s.auditSvcCalculateComplianceTrend())
	report.Set("recommendations", s.auditSvcGenerateRecommendations())
	return report
}

// GetAuditLog returns recent audit log entries (Python default limit 100).
func (s *AuditService) GetAuditLog(limit int) []*entities.OrderedMap[any] {
	if limit > 0 {
		if limit >= len(s.auditSvcAuditLog) {
			return s.auditSvcAuditLog
		}
		return s.auditSvcAuditLog[len(s.auditSvcAuditLog)-limit:]
	}
	return s.auditSvcAuditLog
}

// GetComplianceMetrics returns a copy of the current compliance metrics.
func (s *AuditService) GetComplianceMetrics() *entities.OrderedMap[any] {
	return s.auditSvcComplianceMetrics.Copy()
}

// ClearAuditLog clears the audit log (for testing or maintenance).
func (s *AuditService) ClearAuditLog() {
	s.auditSvcAuditLog = nil
	s.auditSvcComplianceMetrics = auditSvcNewMetrics()
}

// auditSvcCalculateComplianceTrend compares the last 10 operations with the previous 10.
func (s *AuditService) auditSvcCalculateComplianceTrend() string {
	if len(s.auditSvcAuditLog) < 20 {
		return "insufficient_data"
	}
	recent10 := s.auditSvcAuditLog[len(s.auditSvcAuditLog)-10:]
	previous10 := s.auditSvcAuditLog[len(s.auditSvcAuditLog)-20 : len(s.auditSvcAuditLog)-10]

	recentCompliance := float64(auditSvcCountSuccessful(recent10)) / 10
	previousCompliance := float64(auditSvcCountSuccessful(previous10)) / 10

	if recentCompliance > previousCompliance+0.1 {
		return "improving"
	} else if recentCompliance < previousCompliance-0.1 {
		return "declining"
	}
	return "stable"
}

// auditSvcCountSuccessful counts entries whose "success" is truthy.
func auditSvcCountSuccessful(entries []*entities.OrderedMap[any]) int {
	count := 0
	for _, entry := range entries {
		success, _ := entry.Get("success")
		if value_objects.PyTruthy(success) {
			count++
		}
	}
	return count
}

// auditSvcGenerateRecommendations generates compliance improvement recommendations.
func (s *AuditService) auditSvcGenerateRecommendations() []string {
	recommendations := []string{}

	totalOps, _ := s.auditSvcComplianceMetrics.Get("total_operations")
	compliantOps, _ := s.auditSvcComplianceMetrics.Get("compliant_operations")
	denominator := totalOps.(int)
	if denominator < 1 {
		denominator = 1
	}
	complianceRate := float64(compliantOps.(int)) / float64(denominator) * 100

	if complianceRate < 85 {
		recommendations = append(recommendations, "Overall compliance below target (85%). Review failed operations.")
	}

	violations, _ := s.auditSvcComplianceMetrics.Get("violations")
	if violations.(int) > 10 {
		recommendations = append(recommendations, "High number of violations detected. Implement additional validation.")
	}

	start := len(s.auditSvcAuditLog) - 50
	if start < 0 {
		start = 0
	}
	recentFailures := 0
	for _, entry := range s.auditSvcAuditLog[start:] {
		success, _ := entry.Get("success")
		if !value_objects.PyTruthy(success) {
			recentFailures++
		}
	}
	if recentFailures > 5 {
		recommendations = append(recommendations, "Frequent failures detected. Review system stability.")
	}

	if len(recommendations) == 0 {
		recommendations = append(recommendations, "Compliance is on track. Continue monitoring.")
	}

	return recommendations
}
