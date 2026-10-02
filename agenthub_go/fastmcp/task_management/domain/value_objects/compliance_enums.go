package value_objects

// ComplianceLevel: Compliance levels for audit and validation
type ComplianceLevel string

const (
	ComplianceLevelNone       ComplianceLevel = "none"
	ComplianceLevelBasic      ComplianceLevel = "basic"
	ComplianceLevelStandard   ComplianceLevel = "standard"
	ComplianceLevelStrict     ComplianceLevel = "strict"
	ComplianceLevelEnterprise ComplianceLevel = "enterprise"
	ComplianceLevelLow        ComplianceLevel = "low"
	ComplianceLevelMedium     ComplianceLevel = "medium"
	ComplianceLevelHigh       ComplianceLevel = "high"
)

// ComplianceLevelValues lists all members in declaration order.
var ComplianceLevelValues = []ComplianceLevel{ComplianceLevelNone, ComplianceLevelBasic, ComplianceLevelStandard, ComplianceLevelStrict, ComplianceLevelEnterprise, ComplianceLevelLow, ComplianceLevelMedium, ComplianceLevelHigh}

func (e ComplianceLevel) String() string { return string(e) }

// ValidationResult: Validation result types
type ValidationResult string

const (
	ValidationResultValid   ValidationResult = "valid"
	ValidationResultInvalid ValidationResult = "invalid"
	ValidationResultWarning ValidationResult = "warning"
	ValidationResultError   ValidationResult = "error"
	ValidationResultSkipped ValidationResult = "skipped"
)

// ValidationResultValues lists all members in declaration order.
var ValidationResultValues = []ValidationResult{ValidationResultValid, ValidationResultInvalid, ValidationResultWarning, ValidationResultError, ValidationResultSkipped}

func (e ValidationResult) String() string { return string(e) }

// AuditLevel: Audit detail levels
type AuditLevel string

const (
	AuditLevelMinimal       AuditLevel = "minimal"
	AuditLevelStandard      AuditLevel = "standard"
	AuditLevelDetailed      AuditLevel = "detailed"
	AuditLevelComprehensive AuditLevel = "comprehensive"
)

// AuditLevelValues lists all members in declaration order.
var AuditLevelValues = []AuditLevel{AuditLevelMinimal, AuditLevelStandard, AuditLevelDetailed, AuditLevelComprehensive}

func (e AuditLevel) String() string { return string(e) }

// ComplianceStatus: Overall compliance status
type ComplianceStatus string

const (
	ComplianceStatusCompliant        ComplianceStatus = "compliant"
	ComplianceStatusNonCompliant     ComplianceStatus = "non_compliant"
	ComplianceStatusPartialCompliant ComplianceStatus = "partial_compliant"
	ComplianceStatusPendingReview    ComplianceStatus = "pending_review"
	ComplianceStatusExempt           ComplianceStatus = "exempt"
)

// ComplianceStatusValues lists all members in declaration order.
var ComplianceStatusValues = []ComplianceStatus{ComplianceStatusCompliant, ComplianceStatusNonCompliant, ComplianceStatusPartialCompliant, ComplianceStatusPendingReview, ComplianceStatusExempt}

func (e ComplianceStatus) String() string { return string(e) }

// ValidationSeverity: Severity levels for validation issues
type ValidationSeverity string

const (
	ValidationSeverityInfo     ValidationSeverity = "info"
	ValidationSeverityLow      ValidationSeverity = "low"
	ValidationSeverityMedium   ValidationSeverity = "medium"
	ValidationSeverityHigh     ValidationSeverity = "high"
	ValidationSeverityCritical ValidationSeverity = "critical"
)

// ValidationSeverityValues lists all members in declaration order.
var ValidationSeverityValues = []ValidationSeverity{ValidationSeverityInfo, ValidationSeverityLow, ValidationSeverityMedium, ValidationSeverityHigh, ValidationSeverityCritical}

func (e ValidationSeverity) String() string { return string(e) }
