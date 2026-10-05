package value_objects

import (
	"math"
	"regexp"
	"strconv"
	"strings"
)

// EffortLevel is one standardized effort level.
type EffortLevel struct {
	Label   string
	Display string
	Hours   float64
}

// EffortLevels lists all levels in declaration order.
var EffortLevels = []EffortLevel{
	{"quick", "15m", 0.25},
	{"short", "30m", 0.5},
	{"small", "1h", 1.0},
	{"medium", "2h", 2.0},
	{"large", "4h", 4.0},
	{"xlarge", "8h", 8.0},
	{"epic", "16h", 16.0},
	{"massive", "40h", 40.0},
}

var (
	customEffortPattern = regexp.MustCompile(`^([0-9]+(?:\.[0-9]+)?[hm](?:\s+[0-9]+(?:\.[0-9]+)?[hm])*|[0-9]+(?:\.[0-9]+)?\s*(?:hours?|hrs?|minutes?|mins?))$`)
	hoursPattern        = regexp.MustCompile(`([0-9]+(?:\.[0-9]+)?)\s*h`)
	minutesPattern      = regexp.MustCompile(`([0-9]+(?:\.[0-9]+)?)\s*m`)
)

// EstimatedEffort is a task effort estimate; empty is allowed.
type EstimatedEffort struct{ Value string }

// NewEstimatedEffort accepts standard labels/displays, or custom time formats like "3h", "1h 30m".
func NewEstimatedEffort(value string) (EstimatedEffort, error) {
	if value == "" {
		return EstimatedEffort{}, nil
	}
	if _, ok := standardLevel(value); !ok && !customEffortPattern.MatchString(strings.TrimSpace(strings.ToLower(value))) {
		return EstimatedEffort{}, valueErrorf(
			"Invalid effort estimate: %s. Use standard levels or valid time format (e.g., '3h', '45m')", value)
	}
	return EstimatedEffort{value}, nil
}

func standardLevel(value string) (EffortLevel, bool) {
	for _, e := range EffortLevels {
		if value == e.Label || value == e.Display {
			return e, true
		}
	}
	return EffortLevel{}, false
}

func EstimatedEffortQuick() EstimatedEffort   { return EstimatedEffort{"quick"} }
func EstimatedEffortShort() EstimatedEffort   { return EstimatedEffort{"short"} }
func EstimatedEffortSmall() EstimatedEffort   { return EstimatedEffort{"small"} }
func EstimatedEffortMedium() EstimatedEffort  { return EstimatedEffort{"medium"} }
func EstimatedEffortLarge() EstimatedEffort   { return EstimatedEffort{"large"} }
func EstimatedEffortXlarge() EstimatedEffort  { return EstimatedEffort{"xlarge"} }
func EstimatedEffortEpic() EstimatedEffort    { return EstimatedEffort{"epic"} }
func EstimatedEffortMassive() EstimatedEffort { return EstimatedEffort{"massive"} }

// EstimatedEffortFromHours picks the standard level closest to hours (first wins on ties).
func EstimatedEffortFromHours(hours float64) EstimatedEffort {
	best := EffortLevels[0]
	for _, e := range EffortLevels[1:] {
		if math.Abs(e.Hours-hours) < math.Abs(best.Hours-hours) {
			best = e
		}
	}
	return EstimatedEffort{best.Label}
}

func (e EstimatedEffort) String() string { return e.Value }

// GetHours returns the estimated hours, or false when unknown.
func (e EstimatedEffort) GetHours() (float64, bool) {
	if l, ok := standardLevel(e.Value); ok {
		return l.Hours, true
	}
	return e.parseCustomHours()
}

func (e EstimatedEffort) parseCustomHours() (float64, bool) {
	if e.Value == "" {
		return 0, false
	}
	lower := strings.ToLower(e.Value)
	total := 0.0
	if m := hoursPattern.FindStringSubmatch(lower); m != nil {
		h, _ := strconv.ParseFloat(m[1], 64)
		total += h
	}
	if m := minutesPattern.FindStringSubmatch(lower); m != nil {
		mins, _ := strconv.ParseFloat(m[1], 64)
		total += mins / 60
	}
	return total, total > 0
}

func (e EstimatedEffort) IsQuick() bool { return e.Value == "quick" }

// IsLargeEffort: 4+ hours.
func (e EstimatedEffort) IsLargeEffort() bool {
	h, ok := e.GetHours()
	return ok && h >= 4.0
}

// GetLevel returns the level label, categorizing custom values by hours.
func (e EstimatedEffort) GetLevel() string {
	if l, ok := standardLevel(e.Value); ok {
		return l.Label
	}
	h, ok := e.GetHours()
	if !ok {
		return "medium"
	}
	for _, l := range EffortLevels[:len(EffortLevels)-1] {
		if h <= l.Hours {
			return l.Label
		}
	}
	return "massive"
}
