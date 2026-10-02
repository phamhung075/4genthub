package use_cases

import (
	"fmt"
	"os"
	"sort"
	"strings"
	"unicode/utf8"

	fastmcp "agenthub/fastmcp"
	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
	"agenthub/fastmcp/utilities"
)

// IRuleOrchestrationUseCase mirrors the abstract
// rule_orchestration_use_case.IRuleOrchestrationUseCase interface.
type IRuleOrchestrationUseCase interface {
	GetEnhancedRuleInfo() *entities.OrderedMap[any]
	ComposeNestedRules(rulePath string) *entities.OrderedMap[any]
	RegisterClient(clientConfig *entities.OrderedMap[any]) *entities.OrderedMap[any]
	SyncWithClient(clientID, operation string, clientRules *entities.OrderedMap[any]) *entities.OrderedMap[any]
	ListRules(target string) *entities.OrderedMap[any]
	BackupRules(target string) *entities.OrderedMap[any]
	RestoreRules(target string) *entities.OrderedMap[any]
	CleanRules(target string) *entities.OrderedMap[any]
	GetRuleInfo(target string) *entities.OrderedMap[any]
	LoadCoreRules(target string) *entities.OrderedMap[any]
	AnalyzeRuleHierarchy() *entities.OrderedMap[any]
	GetRuleDependencies(rulePath string) *entities.OrderedMap[any]
	ResolveRuleInheritance(rulePath string) *entities.OrderedMap[any]
	ValidateRuleHierarchy() *entities.OrderedMap[any]
	BuildRuleHierarchy() *entities.OrderedMap[any]
	LoadNestedRules(rootPath string) *entities.OrderedMap[any]
	GetCacheStatus() *entities.OrderedMap[any]
	AuthenticateClient(clientID string, credentials *entities.OrderedMap[any]) *entities.OrderedMap[any]
	GetClientDiff(clientID string) *entities.OrderedMap[any]
	ResolveClientConflicts(clientID string, conflictData *entities.OrderedMap[any]) *entities.OrderedMap[any]
	GetClientStatus(clientID string) *entities.OrderedMap[any]
	GetClientAnalytics(clientID string) *entities.OrderedMap[any]
}

// RuleOrchestrationUseCase mirrors rule_orchestration_use_case.RuleOrchestrationUseCase.
type RuleOrchestrationUseCase struct{}

// NewRuleOrchestrationUseCase mirrors RuleOrchestrationUseCase.__init__.
func NewRuleOrchestrationUseCase() *RuleOrchestrationUseCase {
	return &RuleOrchestrationUseCase{}
}

var _ IRuleOrchestrationUseCase = (*RuleOrchestrationUseCase)(nil)

// GetEnhancedRuleInfo mirrors get_enhanced_rule_info.
func (u *RuleOrchestrationUseCase) GetEnhancedRuleInfo() *entities.OrderedMap[any] {
	phase5 := entities.NewOrderedMap[any]()
	phase5.Set("enhanced_caching", true)
	phase5.Set("performance_monitoring", true)
	phase5.Set("cache_optimization", true)
	phase5.Set("benchmarking", true)

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("phase_5_features", phase5)
	m.Set("cache_type", "enhanced_performance")
	m.Set("performance_features_enabled", true)
	return m
}

// ComposeNestedRules mirrors compose_nested_rules.
func (u *RuleOrchestrationUseCase) ComposeNestedRules(rulePath string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "compose_nested_rules")
	m.Set("rule_path", rulePath)
	m.Set("composed_rules", []any{})
	return m
}

// RegisterClient mirrors register_client.
func (u *RuleOrchestrationUseCase) RegisterClient(clientConfig *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	var clientID any = "test_client"
	if v, ok := clientConfig.Get("client_id"); ok {
		clientID = v
	}
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "register_client")
	m.Set("client_id", clientID)
	return m
}

// SyncWithClient mirrors sync_with_client.
func (u *RuleOrchestrationUseCase) SyncWithClient(clientID, operation string, clientRules *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "sync_client")
	m.Set("client_id", clientID)
	m.Set("operation", operation)
	return m
}

// ListRules mirrors list_rules.
func (u *RuleOrchestrationUseCase) ListRules(target string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "list")
	m.Set("target", target)
	m.Set("rules", []any{})
	return m
}

// BackupRules mirrors backup_rules.
func (u *RuleOrchestrationUseCase) BackupRules(target string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "backup")
	m.Set("target", target)
	return m
}

// RestoreRules mirrors restore_rules.
func (u *RuleOrchestrationUseCase) RestoreRules(target string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "restore")
	m.Set("target", target)
	return m
}

// CleanRules mirrors clean_rules.
func (u *RuleOrchestrationUseCase) CleanRules(target string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "clean")
	m.Set("target", target)
	return m
}

// GetRuleInfo mirrors get_rule_info.
func (u *RuleOrchestrationUseCase) GetRuleInfo(target string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "info")
	m.Set("target", target)
	m.Set("rule_info", entities.NewOrderedMap[any]())
	return m
}

// LoadCoreRules mirrors load_core_rules.
func (u *RuleOrchestrationUseCase) LoadCoreRules(target string) (result *entities.OrderedMap[any]) {
	defer func() {
		if r := recover(); r != nil {
			result = ruleOrchestrationLoadCoreError(target, fmt.Sprint(r))
		}
	}()

	// Get the rules directory based on runtime mode.
	rulesDir := fastmcp.GetRulesDirectory()

	// If target is specified, try to read that specific file.
	if target != "" {
		// Handle different target formats.
		var filename string
		if strings.HasPrefix(target, "rules/core/") {
			// Remove "rules/core/" prefix for file lookup (str.replace replaces all).
			filename = strings.ReplaceAll(target, "rules/core/", "")
		} else {
			filename = target
		}

		// Construct the full path (both Python branches are identical).
		var filePath string
		if fastmcp.IsHTTPMode() {
			// In Docker mode, rules are in /data/rules/core/.
			filePath = utilities.PyJoin(rulesDir, "core", filename)
		} else {
			// In stdio mode, rules might be in different structure.
			filePath = utilities.PyJoin(rulesDir, "core", filename)
		}

		// Try to read the file.
		if _, err := os.Stat(filePath); err == nil {
			content, readErr := ruleOrchestrationReadText(filePath)
			if readErr != nil {
				m := entities.NewOrderedMap[any]()
				m.Set("success", false)
				m.Set("action", "load_core")
				m.Set("target", target)
				m.Set("error", "Failed to read file content: "+readErr.Error())
				m.Set("file_path", filePath)
				return m
			}
			m := entities.NewOrderedMap[any]()
			m.Set("success", true)
			m.Set("action", "load_core")
			m.Set("target", target)
			m.Set("core_rules_loaded", true)
			m.Set("file_path", filePath)
			m.Set("content", content)
			m.Set("runtime_mode", ruleOrchestrationRuntimeMode())
			return m
		}

		// File doesn't exist, list available files for debugging.
		availableFiles := []string{}
		coreDir := utilities.PyJoin(rulesDir, "core")
		if entries, err := os.ReadDir(coreDir); err == nil {
			for _, entry := range entries {
				if info, err := entry.Info(); err == nil && info.Mode().IsRegular() {
					availableFiles = append(availableFiles, entry.Name())
				}
			}
		}
		// Python's iterdir() order is OS-dependent; sort names for determinism.
		sort.Strings(availableFiles)

		m := entities.NewOrderedMap[any]()
		m.Set("success", false)
		m.Set("action", "load_core")
		m.Set("target", target)
		m.Set("error", "Rule file not found: "+filename)
		m.Set("file_path", filePath)
		m.Set("rules_directory", rulesDir)
		m.Set("core_directory", coreDir)
		m.Set("available_files", availableFiles)
		m.Set("runtime_mode", ruleOrchestrationRuntimeMode())
		return m
	}

	// No specific target, return general success.
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "load_core")
	m.Set("core_rules_loaded", true)
	m.Set("rules_directory", rulesDir)
	m.Set("runtime_mode", ruleOrchestrationRuntimeMode())
	return m
}

// ruleOrchestrationLoadCoreError is the outer except branch of load_core_rules.
func ruleOrchestrationLoadCoreError(target, errText string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", false)
	m.Set("action", "load_core")
	m.Set("target", target)
	m.Set("error", "Failed to load core rules: "+errText)
	return m
}

// ruleOrchestrationRuntimeMode is "http" if is_http_mode() else "stdio".
func ruleOrchestrationRuntimeMode() string {
	if fastmcp.IsHTTPMode() {
		return "http"
	}
	return "stdio"
}

// ruleOrchestrationReadText is file_path.read_text(encoding="utf-8"): an
// os.ReadFile error or a UTF-8 decode error becomes a Go error.
func ruleOrchestrationReadText(path string) (string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	if !utf8.Valid(data) {
		return "", fmt.Errorf("%s", ruleOrchestrationDecodeError(data))
	}
	return string(data), nil
}

// ruleOrchestrationDecodeError mirrors the message of a UnicodeDecodeError.
func ruleOrchestrationDecodeError(data []byte) string {
	for i := 0; i < len(data); {
		r, size := utf8.DecodeRune(data[i:])
		if r == utf8.RuneError && size == 1 {
			return fmt.Sprintf("'utf-8' codec can't decode byte 0x%02x in position %d: invalid start byte", data[i], i)
		}
		i += size
	}
	return "'utf-8' codec can't decode bytes: invalid data"
}

// AnalyzeRuleHierarchy mirrors analyze_rule_hierarchy.
func (u *RuleOrchestrationUseCase) AnalyzeRuleHierarchy() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "analyze_hierarchy")
	m.Set("hierarchy", entities.NewOrderedMap[any]())
	return m
}

// GetRuleDependencies mirrors get_rule_dependencies.
func (u *RuleOrchestrationUseCase) GetRuleDependencies(rulePath string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "get_dependencies")
	m.Set("rule_path", rulePath)
	m.Set("dependencies", []any{})
	return m
}

// ResolveRuleInheritance mirrors resolve_rule_inheritance.
func (u *RuleOrchestrationUseCase) ResolveRuleInheritance(rulePath string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "resolve_rule_inheritance")
	m.Set("rule_path", rulePath)
	m.Set("inheritance", entities.NewOrderedMap[any]())
	return m
}

// ValidateRuleHierarchy mirrors validate_rule_hierarchy.
func (u *RuleOrchestrationUseCase) ValidateRuleHierarchy() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "validate_rule_hierarchy")
	m.Set("validation_passed", true)
	return m
}

// BuildRuleHierarchy mirrors build_rule_hierarchy.
func (u *RuleOrchestrationUseCase) BuildRuleHierarchy() *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "build_hierarchy")
	m.Set("hierarchy_built", true)
	return m
}

// LoadNestedRules mirrors load_nested_rules.
func (u *RuleOrchestrationUseCase) LoadNestedRules(rootPath string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "load_nested")
	m.Set("root_path", value_objects.PyStr(rootPath))
	m.Set("nested_rules_loaded", true)
	return m
}

// GetCacheStatus mirrors get_cache_status.
func (u *RuleOrchestrationUseCase) GetCacheStatus() *entities.OrderedMap[any] {
	statistics := entities.NewOrderedMap[any]()
	statistics.Set("size", 0)
	statistics.Set("max_size", 1000)
	statistics.Set("hit_rate", 0.0)

	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "cache_status")
	m.Set("cache_type", "enhanced_performance")
	m.Set("performance_features_enabled", true)
	m.Set("cache_statistics", statistics)
	return m
}

// AuthenticateClient mirrors authenticate_client.
func (u *RuleOrchestrationUseCase) AuthenticateClient(clientID string, credentials *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "authenticate_client")
	m.Set("client_id", clientID)
	m.Set("authenticated", true)
	return m
}

// GetClientDiff mirrors get_client_diff.
func (u *RuleOrchestrationUseCase) GetClientDiff(clientID string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "client_diff")
	m.Set("client_id", clientID)
	m.Set("differences", []any{})
	return m
}

// ResolveClientConflicts mirrors resolve_client_conflicts.
func (u *RuleOrchestrationUseCase) ResolveClientConflicts(clientID string, conflictData *entities.OrderedMap[any]) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "resolve_conflicts")
	m.Set("client_id", clientID)
	m.Set("conflicts_resolved", true)
	return m
}

// GetClientStatus mirrors get_client_status.
func (u *RuleOrchestrationUseCase) GetClientStatus(clientID string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "client_status")
	m.Set("client_id", clientID)
	m.Set("status", "active")
	return m
}

// GetClientAnalytics mirrors get_client_analytics.
func (u *RuleOrchestrationUseCase) GetClientAnalytics(clientID string) *entities.OrderedMap[any] {
	m := entities.NewOrderedMap[any]()
	m.Set("success", true)
	m.Set("action", "client_analytics")
	m.Set("client_id", clientID)
	m.Set("analytics", entities.NewOrderedMap[any]())
	return m
}
