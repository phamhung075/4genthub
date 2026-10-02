// Package utilities ports fastmcp/utilities.
package utilities

import (
	"regexp"
	"strings"
	"unicode"
	"unicode/utf8"

	"golang.org/x/text/unicode/norm"

	"agenthub/fastmcp/task_management/domain/value_objects"
)

// IDType is the enumeration of ID types in the system.
type IDType string

const (
	IDTypeUUID              IDType = "uuid"
	IDTypeMCPTaskID         IDType = "mcp_task_id"
	IDTypeApplicationTaskID IDType = "application_task_id"
	IDTypeGitBranchID       IDType = "git_branch_id"
	IDTypeProjectID         IDType = "project_id"
	IDTypeUserID            IDType = "user_id"
	IDTypeContextID         IDType = "context_id"
	IDTypeUnknown           IDType = "unknown"
)

// IDTypeValues lists the ID types in declaration order.
var IDTypeValues = []IDType{IDTypeUUID, IDTypeMCPTaskID, IDTypeApplicationTaskID, IDTypeGitBranchID,
	IDTypeProjectID, IDTypeUserID, IDTypeContextID, IDTypeUnknown}

// ValidationResult is the result of ID validation. Nil pointers/slices/maps are Python None.
type ValidationResult struct {
	IsValid         bool
	IDType          IDType
	OriginalValue   string
	NormalizedValue *string
	ErrorMessage    *string
	Warnings        []string
	Metadata        map[string]any
}

// IDValidationError is raised when ID validation fails critically. ExpectedType is nil for None.
type IDValidationError struct {
	Msg          string
	IDValue      string
	ExpectedType *IDType
}

func (e *IDValidationError) Error() string { return e.Msg }

var (
	uuidPattern        = regexp.MustCompile(`(?i)^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`)
	uuidRelaxedPattern = regexp.MustCompile(`(?i)^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)
)

// IDValidator validates ID formats and prevents ID type confusion.
type IDValidator struct {
	StrictUUIDValidation bool
	uuidPattern          *regexp.Regexp
}

// NewIDValidator builds a validator; strict enforces UUID v4 (Python default True).
func NewIDValidator(strict bool) *IDValidator {
	p := uuidRelaxedPattern
	if strict {
		p = uuidPattern
	}
	return &IDValidator{StrictUUIDValidation: strict, uuidPattern: p}
}

func strPtr(s string) *string { return &s }

// htmlEscape is Python's html.escape(s, quote=True) (Go's html.EscapeString uses
// different entities for quotes).
var htmlEscape = strings.NewReplacer("&", "&amp;", "<", "&lt;", ">", "&gt;", `"`, "&quot;", "'", "&#x27;")

var dangerousPatterns = []string{"javascript:", "vbscript:", "data:", "onload=", "onerror=", "onclick=",
	"onmouseover=", "onfocus=", "onblur="}

var sensitivePatterns = []string{"/etc/", "/root/", "/home/", "/var/", "/usr/", `c:\`, `windows\`, `system32\`,
	"delete from", "drop table", "insert into", "select *", "union select", "password", "passwd", "secret",
	"key", "token", "auth", "credential", "api_key", "database", "config", "admin"}

// sanitizeForErrorMessage makes user input safe for error messages (NFKC normalize,
// strip control/format/surrogate/private-use characters, HTML-escape, remove script
// patterns, redact sensitive content, truncate to maxLength code points).
func (v *IDValidator) sanitizeForErrorMessage(value string, maxLength int) string {
	if value == "" {
		return "[empty]"
	}
	sanitized := norm.NFKC.String(value)
	var b strings.Builder
	for _, r := range sanitized {
		if unicode.In(r, unicode.Cc, unicode.Cf, unicode.Cs, unicode.Co) {
			continue
		}
		b.WriteRune(r)
	}
	sanitized = htmlEscape.Replace(b.String())
	for _, p := range dangerousPatterns {
		sanitized = strings.ReplaceAll(sanitized, p, "[removed]")
		sanitized = strings.ReplaceAll(sanitized, strings.ToUpper(p), "[removed]")
	}
	lower := value_objects.PyLower(sanitized)
	for _, p := range sensitivePatterns {
		if strings.Contains(lower, p) {
			sanitized = "[redacted-sensitive-content]"
			break
		}
	}
	if utf8.RuneCountInString(sanitized) > maxLength {
		sanitized = string([]rune(sanitized)[:maxLength]) + "..."
	}
	return sanitized
}

func (v *IDValidator) invalidUUID(value string) ValidationResult {
	return ValidationResult{IsValid: false, IDType: IDTypeUnknown, OriginalValue: value,
		ErrorMessage: strPtr("Invalid UUID format: " + v.sanitizeForErrorMessage(value, 50) +
			". Expected: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")}
}

func (v *IDValidator) uuidVersion() string {
	if v.StrictUUIDValidation {
		return "v4"
	}
	return "any"
}

// ValidateUUIDFormat validates that value is in proper UUID format.
func (v *IDValidator) ValidateUUIDFormat(value string) ValidationResult {
	if value == "" {
		return ValidationResult{IDType: IDTypeUnknown, ErrorMessage: strPtr("ID value cannot be empty or None")}
	}
	for _, r := range value {
		if r >= 128 {
			return v.invalidUUID(value)
		}
	}
	for _, r := range value {
		if r < 32 {
			return v.invalidUUID(value)
		}
	}
	normalized := strings.ToLower(value_objects.PyStrip(value))
	if v.uuidPattern.MatchString(normalized) {
		return ValidationResult{IsValid: true, IDType: IDTypeUUID, OriginalValue: value, NormalizedValue: &normalized,
			Metadata: map[string]any{"uuid_version": v.uuidVersion()}}
	}
	return v.invalidUUID(value)
}

// DetectIDType detects the ID type from format and an optional context hint ("" = None;
// Python truthiness also treats "" as no hint).
func (v *IDValidator) DetectIDType(value, contextHint string) ValidationResult {
	uuidResult := v.ValidateUUIDFormat(value)
	if !uuidResult.IsValid {
		return uuidResult
	}
	detected := IDTypeUUID
	var warnings []string
	if contextHint != "" {
		h := strings.ToLower(contextHint)
		has := func(s string) bool { return strings.Contains(h, s) }
		switch {
		case has("task") && !has("mcp"):
			detected = IDTypeApplicationTaskID
		case has("task") && has("mcp"):
			detected = IDTypeMCPTaskID
			warnings = append(warnings, "MCP task ID detected - ensure not used as application task ID")
		case has("git_branch") || has("branch"):
			detected = IDTypeGitBranchID
		case has("project"):
			detected = IDTypeProjectID
		case has("user"):
			detected = IDTypeUserID
		case has("context"):
			detected = IDTypeContextID
		}
	}
	var hint any
	if contextHint != "" {
		hint = contextHint
	}
	return ValidationResult{IsValid: true, IDType: detected, OriginalValue: value, NormalizedValue: uuidResult.NormalizedValue,
		Warnings: warnings, Metadata: map[string]any{"context_hint": hint, "uuid_version": v.uuidVersion()}}
}

// ValidateParameterMapping checks that task/branch/project/user IDs are not confused
// (nil = not provided).
func (v *IDValidator) ValidateParameterMapping(taskID, gitBranchID, projectID, userID *string) ValidationResult {
	type param struct {
		name  string
		value string
	}
	var provided []param
	for _, p := range []struct {
		name string
		v    *string
	}{{"task_id", taskID}, {"git_branch_id", gitBranchID}, {"project_id", projectID}, {"user_id", userID}} {
		if p.v != nil {
			provided = append(provided, param{p.name, *p.v})
		}
	}
	if len(provided) == 0 {
		return ValidationResult{IDType: IDTypeUnknown, ErrorMessage: strPtr("At least one parameter must be provided")}
	}
	var errs, warnings []string
	allValid := true
	for _, p := range provided {
		r := v.DetectIDType(p.value, p.name)
		if !r.IsValid {
			allValid = false
			errs = append(errs, p.name+": "+*r.ErrorMessage)
		}
		if p.name == "git_branch_id" && r.IDType == IDTypeMCPTaskID {
			allValid = false
			errs = append(errs, "CRITICAL: MCP task ID "+v.sanitizeForErrorMessage(p.value, 50)+
				" incorrectly passed as git_branch_id. This causes data integrity issues.")
		}
		if p.name == "task_id" && r.IDType == IDTypeGitBranchID {
			warnings = append(warnings, "WARNING: Git branch ID "+v.sanitizeForErrorMessage(p.value, 50)+
				" passed as task_id. Verify this is intentional.")
		}
		warnings = append(warnings, r.Warnings...)
	}
	unique := map[string]struct{}{}
	names := make([]any, 0, len(provided))
	reprParts := make([]string, 0, len(provided))
	for _, p := range provided {
		unique[p.value] = struct{}{}
		names = append(names, p.name)
		reprParts = append(reprParts, value_objects.PyRepr(p.name)+": "+value_objects.PyRepr(p.value))
	}
	if len(unique) < len(provided) {
		warnings = append(warnings, "Same ID value used for multiple parameters - verify this is intentional")
	}
	var errMsg *string
	if len(errs) > 0 {
		errMsg = strPtr(strings.Join(errs, "; "))
	}
	return ValidationResult{IsValid: allValid, IDType: IDTypeUUID, OriginalValue: "{" + strings.Join(reprParts, ", ") + "}",
		ErrorMessage: errMsg, Warnings: warnings,
		Metadata: map[string]any{"validated_parameters": names, "parameter_count": len(provided)}}
}

// ValidateTaskContext checks that task_id corresponds to a distinct, valid git branch ID
// (expectedGitBranchID "" = None).
func (v *IDValidator) ValidateTaskContext(taskID, expectedGitBranchID string) ValidationResult {
	taskResult := v.DetectIDType(taskID, "task_id")
	if !taskResult.IsValid {
		return taskResult
	}
	var warnings []string
	metadata := map[string]any{"validation_type": "task_context"}
	if taskResult.IDType == IDTypeMCPTaskID {
		warnings = append(warnings, "Task ID appears to be an MCP task ID. Ensure proper lookup "+
			"is performed to get the corresponding application task ID.")
	}
	if expectedGitBranchID != "" {
		branch := v.DetectIDType(expectedGitBranchID, "git_branch_id")
		both := "task_id: " + v.sanitizeForErrorMessage(taskID, 50) + ", git_branch_id: " + v.sanitizeForErrorMessage(expectedGitBranchID, 50)
		if !branch.IsValid {
			return ValidationResult{IDType: IDTypeUnknown, OriginalValue: both,
				ErrorMessage: strPtr("Invalid git_branch_id: " + *branch.ErrorMessage)}
		}
		if taskID == expectedGitBranchID {
			return ValidationResult{IDType: IDTypeUnknown, OriginalValue: both, ErrorMessage: strPtr(
				"CRITICAL: task_id and git_branch_id are identical. " +
					"This indicates parameter confusion that leads to data integrity issues.")}
		}
		metadata["git_branch_id_validated"] = true
	}
	return ValidationResult{IsValid: true, IDType: taskResult.IDType, OriginalValue: taskID,
		NormalizedValue: taskResult.NormalizedValue, Warnings: warnings, Metadata: metadata}
}

// SuggestFixForConfusion returns fix suggestions and a code example (context "" → "unknown").
func (v *IDValidator) SuggestFixForConfusion(confusedTaskID, context string) map[string]string {
	if context == "" {
		context = "unknown"
	}
	return map[string]string{
		"issue":         "ID confusion detected in " + context,
		"confused_id":   confusedTaskID,
		"root_cause":    "MCP task ID being used as application task ID",
		"immediate_fix": "Look up the correct git_branch_id from the task record before passing to facade service",
		"code_example": "\n# WRONG (causes data integrity issues):\n" +
			"facade = self._facade_service.get_subtask_facade(\n" +
			"    user_id=user_id,\n" +
			"    git_branch_id=task_id  # BUG: task_id ≠ git_branch_id\n" +
			")\n\n" +
			"# CORRECT (proper ID resolution):\n" +
			"task_facade = self._facade_service.get_task_facade(user_id=user_id)\n" +
			"task_response = task_facade.get_task(task_id=task_id)\n" +
			"git_branch_id = task_response['data']['task']['git_branch_id']\n\n" +
			"facade = self._facade_service.get_subtask_facade(\n" +
			"    user_id=user_id,\n" +
			"    git_branch_id=git_branch_id  # FIXED: Use correct git_branch_id\n" +
			")\n            ",
		"prevention": "Use IDValidator.validate_parameter_mapping() before facade calls to catch parameter confusion early",
	}
}

// ValidateUUID is the quick UUID check.
func ValidateUUID(value string, strict bool) bool {
	return NewIDValidator(strict).ValidateUUIDFormat(value).IsValid
}

// PreventIDConfusion validates parameters and returns *IDValidationError on failure.
// Python's logging of warnings is omitted.
func PreventIDConfusion(taskID, gitBranchID, projectID, userID *string) error {
	r := NewIDValidator(true).ValidateParameterMapping(taskID, gitBranchID, projectID, userID)
	if !r.IsValid {
		msg := "ID validation failed"
		if r.ErrorMessage != nil && *r.ErrorMessage != "" {
			msg = *r.ErrorMessage
		}
		return &IDValidationError{Msg: msg, IDValue: r.OriginalValue}
	}
	return nil
}

// IsMCPTaskID only checks UUID format (as in Python, without further context).
func IsMCPTaskID(value string) bool { return NewIDValidator(true).ValidateUUIDFormat(value).IsValid }

// DefaultValidator is the module-level strict validator.
var DefaultValidator = NewIDValidator(true)
