package value_objects

// TemplateType: Template type enumeration
type TemplateType string

const (
	TemplateTypeTask          TemplateType = "task"
	TemplateTypeProject       TemplateType = "project"
	TemplateTypeWorkflow      TemplateType = "workflow"
	TemplateTypeDocumentation TemplateType = "documentation"
	TemplateTypeCode          TemplateType = "code"
	TemplateTypeConfiguration TemplateType = "configuration"
	TemplateTypeScript        TemplateType = "script"
	TemplateTypeReport        TemplateType = "report"
	TemplateTypeEmail         TemplateType = "email"
	TemplateTypeNotification  TemplateType = "notification"
	TemplateTypeCustom        TemplateType = "custom"
)

// TemplateTypeValues lists all members in declaration order.
var TemplateTypeValues = []TemplateType{TemplateTypeTask, TemplateTypeProject, TemplateTypeWorkflow, TemplateTypeDocumentation, TemplateTypeCode, TemplateTypeConfiguration, TemplateTypeScript, TemplateTypeReport, TemplateTypeEmail, TemplateTypeNotification, TemplateTypeCustom}

func (e TemplateType) String() string { return string(e) }

// TemplateCategory: Template category enumeration
type TemplateCategory string

const (
	TemplateCategoryDevelopment   TemplateCategory = "development"
	TemplateCategoryTesting       TemplateCategory = "testing"
	TemplateCategoryDeployment    TemplateCategory = "deployment"
	TemplateCategoryDocumentation TemplateCategory = "documentation"
	TemplateCategoryCommunication TemplateCategory = "communication"
	TemplateCategoryAnalysis      TemplateCategory = "analysis"
	TemplateCategoryReporting     TemplateCategory = "reporting"
	TemplateCategoryAutomation    TemplateCategory = "automation"
	TemplateCategoryMonitoring    TemplateCategory = "monitoring"
	TemplateCategorySecurity      TemplateCategory = "security"
	TemplateCategoryMaintenance   TemplateCategory = "maintenance"
	TemplateCategoryGeneral       TemplateCategory = "general"
)

// TemplateCategoryValues lists all members in declaration order.
var TemplateCategoryValues = []TemplateCategory{TemplateCategoryDevelopment, TemplateCategoryTesting, TemplateCategoryDeployment, TemplateCategoryDocumentation, TemplateCategoryCommunication, TemplateCategoryAnalysis, TemplateCategoryReporting, TemplateCategoryAutomation, TemplateCategoryMonitoring, TemplateCategorySecurity, TemplateCategoryMaintenance, TemplateCategoryGeneral}

func (e TemplateCategory) String() string { return string(e) }

// TemplateStatus: Template status enumeration
type TemplateStatus string

const (
	TemplateStatusDraft           TemplateStatus = "draft"
	TemplateStatusActive          TemplateStatus = "active"
	TemplateStatusInactive        TemplateStatus = "inactive"
	TemplateStatusDeprecated      TemplateStatus = "deprecated"
	TemplateStatusArchived        TemplateStatus = "archived"
	TemplateStatusUnderReview     TemplateStatus = "under_review"
	TemplateStatusPendingApproval TemplateStatus = "pending_approval"
)

// TemplateStatusValues lists all members in declaration order.
var TemplateStatusValues = []TemplateStatus{TemplateStatusDraft, TemplateStatusActive, TemplateStatusInactive, TemplateStatusDeprecated, TemplateStatusArchived, TemplateStatusUnderReview, TemplateStatusPendingApproval}

func (e TemplateStatus) String() string { return string(e) }

// CacheStrategy: Cache strategy enumeration
type CacheStrategy string

const (
	CacheStrategyDefault    CacheStrategy = "default"
	CacheStrategyAggressive CacheStrategy = "aggressive"
	CacheStrategyMinimal    CacheStrategy = "minimal"
	CacheStrategyNone       CacheStrategy = "none"
	CacheStrategyCustom     CacheStrategy = "custom"
)

// CacheStrategyValues lists all members in declaration order.
var CacheStrategyValues = []CacheStrategy{CacheStrategyDefault, CacheStrategyAggressive, CacheStrategyMinimal, CacheStrategyNone, CacheStrategyCustom}

func (e CacheStrategy) String() string { return string(e) }

// TemplateCompatibility: Template compatibility enumeration
type TemplateCompatibility string

const (
	TemplateCompatibilityAll      TemplateCompatibility = "all"
	TemplateCompatibilitySpecific TemplateCompatibility = "specific"
	TemplateCompatibilityNone     TemplateCompatibility = "none"
)

// TemplateCompatibilityValues lists all members in declaration order.
var TemplateCompatibilityValues = []TemplateCompatibility{TemplateCompatibilityAll, TemplateCompatibilitySpecific, TemplateCompatibilityNone}

func (e TemplateCompatibility) String() string { return string(e) }

// TemplateValidationStatus: Template validation status enumeration
type TemplateValidationStatus string

const (
	TemplateValidationStatusValid        TemplateValidationStatus = "valid"
	TemplateValidationStatusInvalid      TemplateValidationStatus = "invalid"
	TemplateValidationStatusWarning      TemplateValidationStatus = "warning"
	TemplateValidationStatusNotValidated TemplateValidationStatus = "not_validated"
)

// TemplateValidationStatusValues lists all members in declaration order.
var TemplateValidationStatusValues = []TemplateValidationStatus{TemplateValidationStatusValid, TemplateValidationStatusInvalid, TemplateValidationStatusWarning, TemplateValidationStatusNotValidated}

func (e TemplateValidationStatus) String() string { return string(e) }

// TemplateRenderStatus: Template render status enumeration
type TemplateRenderStatus string

const (
	TemplateRenderStatusSuccess   TemplateRenderStatus = "success"
	TemplateRenderStatusFailed    TemplateRenderStatus = "failed"
	TemplateRenderStatusPartial   TemplateRenderStatus = "partial"
	TemplateRenderStatusPending   TemplateRenderStatus = "pending"
	TemplateRenderStatusCancelled TemplateRenderStatus = "cancelled"
)

// TemplateRenderStatusValues lists all members in declaration order.
var TemplateRenderStatusValues = []TemplateRenderStatus{TemplateRenderStatusSuccess, TemplateRenderStatusFailed, TemplateRenderStatusPartial, TemplateRenderStatusPending, TemplateRenderStatusCancelled}

func (e TemplateRenderStatus) String() string { return string(e) }

// TemplatePriority: Template priority enumeration (values are PriorityLevel labels).
type TemplatePriority string

const (
	TemplatePriorityLow      TemplatePriority = "low"
	TemplatePriorityMedium   TemplatePriority = "medium"
	TemplatePriorityHigh     TemplatePriority = "high"
	TemplatePriorityCritical TemplatePriority = "critical"
)

// TemplatePriorityValues lists all members in declaration order.
var TemplatePriorityValues = []TemplatePriority{
	TemplatePriorityLow, TemplatePriorityMedium, TemplatePriorityHigh, TemplatePriorityCritical,
}

func (e TemplatePriority) String() string { return string(e) }
