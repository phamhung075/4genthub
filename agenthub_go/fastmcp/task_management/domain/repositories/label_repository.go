package repositories

import (
	"context"
	"strings"
	"time"
)

// ILabelRepository is the repository interface for labels.
type ILabelRepository interface {
	// CreateLabel creates a label; category nil means none.
	CreateLabel(ctx context.Context, label string, category *string) (string, error)
	// FindLabel returns the label if found (nil otherwise).
	FindLabel(ctx context.Context, label string) (*string, error)
	GetAllLabels(ctx context.Context) ([]string, error)
	GetLabelsByCategory(ctx context.Context, category string) ([]string, error)
	SearchLabels(ctx context.Context, query string, limit int) ([]string, error)
	GetLabelUsageCount(ctx context.Context, label string) (int, error)
	DeleteUnusedLabels(ctx context.Context) (int, error)
	NormalizeLabel(ctx context.Context, label string) (string, error)
	ValidateAndCreateLabels(ctx context.Context, labels []string) ([]string, error)
}

// LabelInfo is the label information entity.
type LabelInfo struct {
	Label      string
	Category   *string
	UsageCount int
	CreatedAt  time.Time
	Normalized string
}

// NewLabelInfo builds a LabelInfo; a zero createdAt means now (UTC).
func NewLabelInfo(label string, category *string, usageCount int, createdAt time.Time) *LabelInfo {
	if createdAt.IsZero() {
		createdAt = time.Now().UTC().Truncate(time.Microsecond)
	}
	return &LabelInfo{Label: label, Category: category, UsageCount: usageCount, CreatedAt: createdAt, Normalized: normalizeLabelInfo(label)}
}

// normalizeLabelInfo lower-cases, collapses whitespace and replaces spaces by hyphens.
func normalizeLabelInfo(label string) string {
	return strings.ReplaceAll(strings.Join(strings.Fields(strings.ToLower(strings.TrimSpace(label))), " "), " ", "-")
}

func (l *LabelInfo) IncrementUsage() { l.UsageCount++ }

func (l *LabelInfo) DecrementUsage() {
	if l.UsageCount > 0 {
		l.UsageCount--
	}
}
