// Package entities ports task_management/domain/entities.
package entities

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// Label categorizes and organizes tasks.
type Label struct {
	base.BaseTimestampEntity
	ID          int
	Name        string
	Color       string // default "#0066cc"
	Description string
}

// NewLabel builds and validates a label. An empty Color takes the Python default
// "#0066cc" (an explicit "" cannot be distinguished from omitted).
func NewLabel(id int, name, color, description string, createdAt, updatedAt *time.Time) (*Label, error) {
	if color == "" {
		color = "#0066cc"
	}
	l := &Label{ID: id, Name: name, Color: color, Description: description}
	l.CreatedAt, l.UpdatedAt = createdAt, updatedAt
	if err := l.Init(l); err != nil {
		return nil, err
	}
	return l, nil
}

func (l *Label) GetEntityID() string {
	if l.ID != 0 {
		return strconv.Itoa(l.ID)
	}
	return "unknown"
}

func (l *Label) ValidateEntity() error {
	if strings.TrimSpace(l.Name) == "" {
		return value_objects.ValueErrorf("Label name cannot be empty")
	}
	if l.Color != "" && !isValidHexColor(l.Color) {
		return value_objects.ValueErrorf("Invalid color format: %s. Expected hex color (e.g., #ff0000)", l.Color)
	}
	return nil
}

// isValidHexColor accepts "#" followed by 3 or 6 hex digits (Python int(x, 16)
// also tolerates signs/whitespace/underscores; Go is stricter).
func isValidHexColor(color string) bool {
	if !strings.HasPrefix(color, "#") {
		return false
	}
	hex := color[1:]
	if len(hex) != 3 && len(hex) != 6 {
		return false
	}
	_, err := strconv.ParseUint(hex, 16, 64)
	return err == nil
}

func (l *Label) String() string { return fmt.Sprintf("Label(%s)", l.Name) }

// GoString mirrors Python's __repr__.
func (l *Label) GoString() string {
	return fmt.Sprintf("Label(id=%d, name='%s', color='%s')", l.ID, l.Name, l.Color)
}
