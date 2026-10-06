package facades

import (
	"os"
	"path/filepath"
	"time"
	"unicode/utf8"

	"agenthub/fastmcp/task_management/domain/entities"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// RulePathResolver is the consumer-side port of the
// task_management/interface/mcp_tools/path_resolver.PathResolver methods used by
// RuleApplicationFacade. Python returns pathlib.Path; the Go port returns the path
// string and existence/reading is done with the os package.
type RulePathResolver interface {
	GetAutoRulePath() string
	GetRulesDirectoryFromSettings() string
}

// RuleApplicationFacade mirrors rule_application_facade.RuleApplicationFacade.
type RuleApplicationFacade struct {
	pathResolver RulePathResolver
	// Test compatibility only, as in Python (always nil).
	enhancedOrchestrator any
}

// NewRuleApplicationFacade mirrors __init__(path_resolver=None). Python falls back to
// PathResolver(); that class has no Go port, so the caller always supplies a resolver.
func NewRuleApplicationFacade(pathResolver RulePathResolver) *RuleApplicationFacade {
	return &RuleApplicationFacade{pathResolver: pathResolver}
}

func ruleMap() *entities.OrderedMap[any] { return entities.NewOrderedMap[any]() }

// ValidateRules mirrors validate_rules(target="auto_rule").
func (f *RuleApplicationFacade) ValidateRules(target string) *entities.OrderedMap[any] {
	if target == "auto_rule" {
		return f.validateAutoRule()
	} else if target == "all" {
		return f.validateAllRules()
	}
	return f.validateSpecificRule(target)
}

// ManageRule mirrors manage_rule(action, target="", content="").
func (f *RuleApplicationFacade) ManageRule(action, target, content string) *entities.OrderedMap[any] {
	m := ruleMap()
	m.Set("success", false)
	m.Set("error", "Rule management functionality has been removed. Use cursor rules controller instead.")
	m.Set("action", action)
	m.Set("target", target)
	m.Set("content_length", utf8.RuneCountInString(content))
	metadata := ruleMap()
	metadata.Set("timestamp", value_objects.IsoFormatNaive(time.Now()))
	metadata.Set("note", "Rule orchestration controller has been deprecated and removed")
	m.Set("metadata", metadata)
	return m
}

// createBackup mirrors _create_backup(file_path): backup_path = file_path + ".backup"
// (Python with_suffix(suffix + ".backup") on an existing suffix appends ".backup").
func (f *RuleApplicationFacade) createBackup(filePath string) {
	if _, err := os.Stat(filePath); err != nil {
		return
	}
	backupPath := filePath + ".backup"
	if data, err := os.ReadFile(filePath); err == nil {
		_ = os.WriteFile(backupPath, data, 0o644)
	}
}

// validateAutoRule mirrors _validate_auto_rule.
func (f *RuleApplicationFacade) validateAutoRule() *entities.OrderedMap[any] {
	autoRulePath := f.pathResolver.GetAutoRulePath()
	if _, err := os.Stat(autoRulePath); err != nil {
		m := ruleMap()
		m.Set("success", false)
		m.Set("error", "Auto rule file does not exist")
		m.Set("file_path", autoRulePath)
		return m
	}
	data, err := os.ReadFile(autoRulePath)
	if err != nil {
		m := ruleMap()
		m.Set("success", false)
		m.Set("error", "Failed to read auto rule: "+err.Error())
		m.Set("file_path", autoRulePath)
		return m
	}
	m := ruleMap()
	m.Set("success", true)
	m.Set("message", "Auto rule validation passed")
	m.Set("file_path", autoRulePath)
	m.Set("content_length", utf8.RuneCountInString(string(data)))
	m.Set("encoding", "utf-8")
	return m
}

// validateAllRules mirrors _validate_all_rules (rules_dir.rglob("*.mdc")).
func (f *RuleApplicationFacade) validateAllRules() *entities.OrderedMap[any] {
	rulesDir := f.pathResolver.GetRulesDirectoryFromSettings()
	if _, err := os.Stat(rulesDir); err != nil {
		m := ruleMap()
		m.Set("success", false)
		m.Set("error", "Rules directory does not exist")
		m.Set("rules_directory", rulesDir)
		return m
	}
	results := []any{}
	// Python Path.rglob walks os.scandir order; filepath.WalkDir is lexical.
	_ = filepath.WalkDir(rulesDir, func(path string, d os.DirEntry, err error) error {
		if err != nil || d == nil || d.IsDir() {
			return nil
		}
		if filepath.Ext(path) != ".mdc" {
			return nil
		}
		data, rerr := os.ReadFile(path)
		if rerr != nil {
			entry := ruleMap()
			entry.Set("file", path)
			entry.Set("status", "error")
			entry.Set("error", rerr.Error())
			results = append(results, entry)
			return nil
		}
		entry := ruleMap()
		entry.Set("file", path)
		entry.Set("status", "valid")
		entry.Set("content_length", utf8.RuneCountInString(string(data)))
		results = append(results, entry)
		return nil
	})
	m := ruleMap()
	m.Set("success", true)
	m.Set("message", "Validated "+value_objects.PyStr(len(results))+" rule files")
	m.Set("rules_directory", rulesDir)
	m.Set("results", results)
	return m
}

// validateSpecificRule mirrors _validate_specific_rule.
func (f *RuleApplicationFacade) validateSpecificRule(target string) *entities.OrderedMap[any] {
	if _, err := os.Stat(target); err != nil {
		m := ruleMap()
		m.Set("success", false)
		m.Set("error", "Rule file does not exist: "+target)
		m.Set("file_path", target)
		return m
	}
	data, err := os.ReadFile(target)
	if err != nil {
		m := ruleMap()
		m.Set("success", false)
		m.Set("error", "Failed to read rule file: "+err.Error())
		m.Set("file_path", target)
		return m
	}
	m := ruleMap()
	m.Set("success", true)
	m.Set("message", "Rule validation passed")
	m.Set("file_path", target)
	m.Set("content_length", utf8.RuneCountInString(string(data)))
	m.Set("encoding", "utf-8")
	return m
}
