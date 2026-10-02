package tools

// Python tools/tool_path.py.
// find_project_root, _is_project_root and ensure_project_structure. The Python
// default start_path uses inspect.stack() to find the caller's file; Go has no
// equivalent, so a nil startPath falls back to the current working directory.

import (
	"os"
	"path/filepath"
)

// ToolPathMarkers is the project_markers list in tool_path.py.
var ToolPathMarkers = []string{
	"pyproject.toml",
	"package.json",
	"Cargo.toml",
	"go.mod",
	"requirements.txt",
	"cursor_agent",
}

const toolPathRootMarker = "___root___:Zone.Identifier"

// IsProjectRoot ports _is_project_root.
func IsProjectRoot(path string) bool {
	if toolPathExists(filepath.Join(path, toolPathRootMarker)) {
		return true
	}
	if toolPathExists(filepath.Join(path, ".git")) {
		return true
	}
	if toolPathExists(filepath.Join(path, ".cursor", "rules")) {
		return true
	}
	for _, marker := range ToolPathMarkers {
		if toolPathExists(filepath.Join(path, marker)) {
			return true
		}
	}
	return false
}

// FindProjectRoot ports find_project_root. A nil startPath is Python's None and
// uses the current working directory in this port.
func FindProjectRoot(startPath *string) string {
	if env, ok := os.LookupEnv("PROJECT_ROOT_PATH"); ok && env != "" {
		projectRoot := toolPathResolve(env)
		if toolPathExists(projectRoot) {
			return projectRoot
		}
	}

	cwd, _ := os.Getwd()
	cwd = toolPathResolve(cwd)
	if toolPathExists(filepath.Join(cwd, toolPathRootMarker)) {
		return cwd
	}

	current := cwd
	if startPath != nil {
		current = toolPathResolve(*startPath)
	}

	if info, err := os.Stat(current); err == nil && !info.IsDir() {
		current = filepath.Dir(current)
	}

	parents := toolPathParents(current)
	for _, parent := range parents {
		if toolPathExists(filepath.Join(parent, toolPathRootMarker)) {
			return parent
		}
	}
	for _, parent := range parents {
		if toolPathExists(filepath.Join(parent, ".git")) {
			return parent
		}
	}
	for _, parent := range parents {
		if IsProjectRoot(parent) {
			return parent
		}
	}
	return cwd
}

// EnsureProjectStructure ports ensure_project_structure.
func EnsureProjectStructure(root *string) string {
	var projectRoot string
	if root == nil {
		projectRoot = FindProjectRoot(nil)
	} else {
		projectRoot = toolPathResolve(*root)
	}
	for _, dir := range []string{
		filepath.Join(projectRoot, "database"),
		filepath.Join(projectRoot, ".cursor"),
	} {
		_ = os.MkdirAll(dir, 0o777)
	}
	return projectRoot
}

// --- helpers ---

func toolPathExists(path string) bool {
	_, err := os.Lstat(path)
	return err == nil
}

func toolPathResolve(path string) string {
	abs, err := filepath.Abs(path)
	if err != nil {
		abs = path
	}
	if resolved, err := filepath.EvalSymlinks(abs); err == nil {
		return resolved
	}
	return abs
}

func toolPathParents(current string) []string {
	out := []string{current}
	dir := current
	for {
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		out = append(out, parent)
		dir = parent
	}
	return out
}
