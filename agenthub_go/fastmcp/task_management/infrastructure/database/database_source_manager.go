// Package database ports task_management/infrastructure/database.
//
// database_source_manager.go ports database_source_manager.py: the legacy
// SQLite path manager. Python raises RuntimeError from __init__/on import; Go
// records the initialization error and surfaces it from GetDatabasePath.
package database

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	"agenthub/fastmcp/task_management/domain/entities"
)

// DatabaseMode mirrors DatabaseMode (the Python Enum values).
type DatabaseMode string

const (
	DatabaseModeTest   DatabaseMode = "test"
	DatabaseModeNormal DatabaseMode = "normal"
	DatabaseModeDocker DatabaseMode = "docker"
	DatabaseModeStdin  DatabaseMode = "stdin"
)

// DatabaseSourceManager mirrors DatabaseSourceManager. Python keeps the state in
// class-level singletons; the Go port keeps it on the instance and exposes one
// lazy process-wide instance through DatabaseSourceManagerInstance.
type DatabaseSourceManager struct {
	mu           sync.Mutex
	currentMode  DatabaseMode
	databasePath *string
	initErr      error
}

// NewDatabaseSourceManager mirrors __init__ + _detect_mode + _set_database_path.
func NewDatabaseSourceManager() *DatabaseSourceManager {
	m := &DatabaseSourceManager{}
	m.detectMode()
	m.initErr = m.setDatabasePath()
	return m
}

func (m *DatabaseSourceManager) detectMode() {
	if os.Getenv("PYTEST_CURRENT_TEST") != "" {
		m.currentMode = DatabaseModeTest
		return
	}
	if _, err := os.Stat("/.dockerenv"); err == nil || os.Getenv("DOCKER_CONTAINER") != "" {
		m.currentMode = DatabaseModeDocker
		return
	}
	if fi, err := os.Stdin.Stat(); err == nil && (fi.Mode()&os.ModeCharDevice) == 0 {
		m.currentMode = DatabaseModeStdin
		return
	}
	m.currentMode = DatabaseModeNormal
}

func (m *DatabaseSourceManager) findProjectRoot() string {
	exe, err := os.Executable()
	root := ""
	if err == nil {
		root = filepath.Dir(exe)
	}
	for root != "" {
		if _, err := os.Stat(filepath.Join(root, "agenthub_main")); err == nil {
			return root
		}
		parent := filepath.Dir(root)
		if parent == root {
			break
		}
		root = parent
	}

	if cwd, err := os.Getwd(); err == nil {
		if _, err := os.Stat(filepath.Join(cwd, "agenthub_main")); err == nil {
			return cwd
		}
	}

	if err == nil {
		current := filepath.Dir(exe)
		for {
			if filepath.Base(current) == "agenthub_main" {
				return filepath.Dir(current)
			}
			parent := filepath.Dir(current)
			if parent == current {
				break
			}
			current = parent
		}
	}

	if _, err := os.Stat("/.dockerenv"); err == nil || os.Getenv("DOCKER_CONTAINER") != "" {
		return "/app"
	}
	cwd, _ := os.Getwd()
	return cwd
}

func (m *DatabaseSourceManager) setDatabasePath() error {
	if explicit, ok := os.LookupEnv("MCP_DB_PATH"); ok && explicit != "" {
		v := explicit
		m.databasePath = &v
		return nil
	}

	projectRoot := m.findProjectRoot()

	switch m.currentMode {
	case DatabaseModeTest:
		p := filepath.Join(projectRoot, "agenthub_main", "database", "data", "agenthub_test.db")
		m.databasePath = &p
	case DatabaseModeDocker:
		p := os.Getenv("DOCKER_DB_PATH")
		if p == "" {
			p = "/data/agenthub.db"
		}
		if _, err := os.Stat(filepath.Dir(p)); err != nil {
			return fmt.Errorf("Docker database directory not accessible: %s. Server cannot start without Docker database access.", filepath.Dir(p))
		}
		m.databasePath = &p
	case DatabaseModeStdin:
		p := filepath.Join(projectRoot, "agenthub_main", "database", "data", "agenthub.db")
		m.databasePath = &p
	default: // NORMAL
		p := "/data/agenthub.db"
		if _, err := os.Stat(p); err == nil {
			m.databasePath = &p
		} else {
			return fmt.Errorf("Docker database not accessible: %s. Local development requires Docker database access for consistency. Please start Docker container first.", p)
		}
	}
	return nil
}

// GetDatabasePath mirrors get_database_path (the method).
func (m *DatabaseSourceManager) GetDatabasePath() (string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if explicit, ok := os.LookupEnv("MCP_DB_PATH"); ok && explicit != "" {
		if m.databasePath == nil || explicit != *m.databasePath {
			v := explicit
			m.databasePath = &v
		}
	}

	if m.initErr != nil {
		return "", m.initErr
	}
	if m.databasePath == nil {
		return "", fmt.Errorf("Database path not initialized")
	}

	m.validateSingleSource()
	return *m.databasePath, nil
}

// GetMode mirrors get_mode.
func (m *DatabaseSourceManager) GetMode() DatabaseMode { return m.currentMode }

// validateSingleSource mirrors _validate_single_source. It only computes the
// same conditions; Python logs warnings and never raises.
func (m *DatabaseSourceManager) validateSingleSource() {
	projectRoot := m.findProjectRoot()
	mainDB := filepath.Join(projectRoot, "agenthub_main", "database", "data", "agenthub.db")
	testDB := filepath.Join(projectRoot, "agenthub_main", "database", "data", "agenthub_test.db")

	mainInfo, mainErr := os.Stat(mainDB)
	testInfo, testErr := os.Stat(testDB)
	if mainErr != nil || testErr != nil {
		return
	}
	currentTime := time.Now().Unix()
	if (currentTime-mainInfo.ModTime().Unix()) < 3600 &&
		(currentTime-testInfo.ModTime().Unix()) < 3600 &&
		m.currentMode != DatabaseModeTest {
		// Python warns and returns; logging is dropped in the Go port.
		return
	}
}

// ForceMode mirrors force_mode.
func (m *DatabaseSourceManager) ForceMode(mode DatabaseMode) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.currentMode = mode
	m.initErr = m.setDatabasePath()
	return m.initErr
}

// GetInfo mirrors get_info (insertion order preserved).
func (m *DatabaseSourceManager) GetInfo() *entities.OrderedMap[any] {
	out := entities.NewOrderedMap[any]()
	mode := any(nil)
	if m.currentMode != "" {
		mode = string(m.currentMode)
	}
	out.Set("mode", mode)
	if m.databasePath == nil {
		out.Set("database_path", nil)
	} else {
		out.Set("database_path", *m.databasePath)
	}
	out.Set("is_docker", m.currentMode == DatabaseModeDocker)
	out.Set("is_test", m.currentMode == DatabaseModeTest)
	out.Set("is_stdin", m.currentMode == DatabaseModeStdin)
	out.Set("is_normal", m.currentMode == DatabaseModeNormal)
	return out
}

var (
	databaseSourceManagerOnce     sync.Once
	databaseSourceManagerInstance *DatabaseSourceManager
)

// DatabaseSourceManagerInstance is the module-level global instance.
func DatabaseSourceManagerInstance() *DatabaseSourceManager {
	databaseSourceManagerOnce.Do(func() {
		databaseSourceManagerInstance = NewDatabaseSourceManager()
	})
	return databaseSourceManagerInstance
}

// ClearDatabaseSourceManagerInstance mirrors clear_instance (mainly for testing).
func ClearDatabaseSourceManagerInstance() {
	databaseSourceManagerOnce = sync.Once{}
	databaseSourceManagerInstance = nil
}

// GetDatabasePath mirrors the module-level deprecated get_database_path.
func GetDatabasePath() (string, error) {
	return "", fmt.Errorf("LOCAL DATABASE PATH ACCESS NOT SUPPORTED!\n" +
		"This system uses PostgreSQL database connections.\n" +
		"✅ SOLUTION: Use PostgreSQL or Supabase database\n" +
		"🔧 Set DATABASE_TYPE=postgresql or supabase in your environment\n" +
		"📋 Configure DATABASE_URL with your connection string")
}

// GetDatabaseMode mirrors get_database_mode.
func GetDatabaseMode() DatabaseMode {
	return DatabaseSourceManagerInstance().GetMode()
}

// GetDatabaseInfo mirrors get_database_info.
func GetDatabaseInfo() *entities.OrderedMap[any] {
	return DatabaseSourceManagerInstance().GetInfo()
}
