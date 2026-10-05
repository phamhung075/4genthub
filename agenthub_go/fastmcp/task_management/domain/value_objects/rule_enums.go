package value_objects

import "strings"

// RuleFormat: Supported rule file formats
type RuleFormat string

const (
	RuleFormatMdc  RuleFormat = "mdc"
	RuleFormatMd   RuleFormat = "md"
	RuleFormatJson RuleFormat = "json"
	RuleFormatYaml RuleFormat = "yaml"
	RuleFormatTxt  RuleFormat = "txt"
)

// RuleFormatValues lists all members in declaration order.
var RuleFormatValues = []RuleFormat{RuleFormatMdc, RuleFormatMd, RuleFormatJson, RuleFormatYaml, RuleFormatTxt}

func (e RuleFormat) String() string { return string(e) }

// RuleType: Rule classification types
type RuleType string

const (
	RuleTypeCore     RuleType = "core"
	RuleTypeWorkflow RuleType = "workflow"
	RuleTypeAgent    RuleType = "agent"
	RuleTypeProject  RuleType = "project"
	RuleTypeContext  RuleType = "context"
	RuleTypeCustom   RuleType = "custom"
)

// RuleTypeValues lists all members in declaration order.
var RuleTypeValues = []RuleType{RuleTypeCore, RuleTypeWorkflow, RuleTypeAgent, RuleTypeProject, RuleTypeContext, RuleTypeCustom}

func (e RuleType) String() string { return string(e) }

// ConflictResolution: Conflict resolution strategies
type ConflictResolution string

const (
	ConflictResolutionMerge    ConflictResolution = "merge"
	ConflictResolutionOverride ConflictResolution = "override"
	ConflictResolutionAppend   ConflictResolution = "append"
	ConflictResolutionManual   ConflictResolution = "manual"
)

// ConflictResolutionValues lists all members in declaration order.
var ConflictResolutionValues = []ConflictResolution{ConflictResolutionMerge, ConflictResolutionOverride, ConflictResolutionAppend, ConflictResolutionManual}

func (e ConflictResolution) String() string { return string(e) }

// InheritanceType: Types of rule inheritance
type InheritanceType string

const (
	InheritanceTypeFull      InheritanceType = "full"
	InheritanceTypeContent   InheritanceType = "content"
	InheritanceTypeMetadata  InheritanceType = "metadata"
	InheritanceTypeVariables InheritanceType = "variables"
	InheritanceTypeSelective InheritanceType = "selective"
)

// InheritanceTypeValues lists all members in declaration order.
var InheritanceTypeValues = []InheritanceType{InheritanceTypeFull, InheritanceTypeContent, InheritanceTypeMetadata, InheritanceTypeVariables, InheritanceTypeSelective}

func (e InheritanceType) String() string { return string(e) }

// SyncOperation: Types of synchronization operations
type SyncOperation string

const (
	SyncOperationPush          SyncOperation = "push"
	SyncOperationPull          SyncOperation = "pull"
	SyncOperationBidirectional SyncOperation = "bidirectional"
	SyncOperationMerge         SyncOperation = "merge"
)

// SyncOperationValues lists all members in declaration order.
var SyncOperationValues = []SyncOperation{SyncOperationPush, SyncOperationPull, SyncOperationBidirectional, SyncOperationMerge}

func (e SyncOperation) String() string { return string(e) }

// ClientAuthMethod: Client authentication methods
type ClientAuthMethod string

const (
	ClientAuthMethodApiKey      ClientAuthMethod = "api_key"
	ClientAuthMethodToken       ClientAuthMethod = "token"
	ClientAuthMethodOauth2      ClientAuthMethod = "oauth2"
	ClientAuthMethodCertificate ClientAuthMethod = "certificate"
)

// ClientAuthMethodValues lists all members in declaration order.
var ClientAuthMethodValues = []ClientAuthMethod{ClientAuthMethodApiKey, ClientAuthMethodToken, ClientAuthMethodOauth2, ClientAuthMethodCertificate}

func (e ClientAuthMethod) String() string { return string(e) }

// SyncStatus: Synchronization status
type SyncStatus string

const (
	SyncStatusPending    SyncStatus = "pending"
	SyncStatusInProgress SyncStatus = "in_progress"
	SyncStatusCompleted  SyncStatus = "completed"
	SyncStatusFailed     SyncStatus = "failed"
	SyncStatusConflict   SyncStatus = "conflict"
)

// SyncStatusValues lists all members in declaration order.
var SyncStatusValues = []SyncStatus{SyncStatusPending, SyncStatusInProgress, SyncStatusCompleted, SyncStatusFailed, SyncStatusConflict}

func (e SyncStatus) String() string { return string(e) }

// stringValues converts a typed enum slice to plain strings.
func stringValues[T ~string](vs []T) []string {
	out := make([]string, len(vs))
	for i, v := range vs {
		out[i] = string(v)
	}
	return out
}

func containsString(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}

// RuleFormatGetAllFormats lists all values.
func RuleFormatGetAllFormats() []string { return stringValues(RuleFormatValues) }

// RuleFormatIsValidFormat checks a string case-insensitively.
func RuleFormatIsValidFormat(s string) bool {
	return containsString(RuleFormatGetAllFormats(), strings.ToLower(s))
}

// RuleTypeGetAllTypes lists all values.
func RuleTypeGetAllTypes() []string { return stringValues(RuleTypeValues) }

// RuleTypeIsValidType checks a string case-insensitively.
func RuleTypeIsValidType(s string) bool {
	return containsString(RuleTypeGetAllTypes(), strings.ToLower(s))
}

// ConflictResolutionGetAllStrategies lists all values.
func ConflictResolutionGetAllStrategies() []string { return stringValues(ConflictResolutionValues) }

// ConflictResolutionIsValidStrategy checks a string case-insensitively.
func ConflictResolutionIsValidStrategy(s string) bool {
	return containsString(ConflictResolutionGetAllStrategies(), strings.ToLower(s))
}

// InheritanceTypeGetAllInheritanceTypes lists all values.
func InheritanceTypeGetAllInheritanceTypes() []string { return stringValues(InheritanceTypeValues) }

// InheritanceTypeIsValidInheritanceType checks a string case-insensitively.
func InheritanceTypeIsValidInheritanceType(s string) bool {
	return containsString(InheritanceTypeGetAllInheritanceTypes(), strings.ToLower(s))
}

// SyncOperationGetAllOperations lists all values.
func SyncOperationGetAllOperations() []string { return stringValues(SyncOperationValues) }

// SyncOperationIsValidOperation checks a string case-insensitively.
func SyncOperationIsValidOperation(s string) bool {
	return containsString(SyncOperationGetAllOperations(), strings.ToLower(s))
}

// ClientAuthMethodGetAllAuthMethods lists all values.
func ClientAuthMethodGetAllAuthMethods() []string { return stringValues(ClientAuthMethodValues) }

// ClientAuthMethodIsValidAuthMethod checks a string case-insensitively.
func ClientAuthMethodIsValidAuthMethod(s string) bool {
	return containsString(ClientAuthMethodGetAllAuthMethods(), strings.ToLower(s))
}

// SyncStatusGetAllStatuses lists all values.
func SyncStatusGetAllStatuses() []string { return stringValues(SyncStatusValues) }

// SyncStatusIsValidStatus checks a string case-insensitively.
func SyncStatusIsValidStatus(s string) bool {
	return containsString(SyncStatusGetAllStatuses(), strings.ToLower(s))
}

// IsTerminal: COMPLETED or FAILED.
func (s SyncStatus) IsTerminal() bool { return s == SyncStatusCompleted || s == SyncStatusFailed }

// IsActive: PENDING or IN_PROGRESS.
func (s SyncStatus) IsActive() bool { return s == SyncStatusPending || s == SyncStatusInProgress }
