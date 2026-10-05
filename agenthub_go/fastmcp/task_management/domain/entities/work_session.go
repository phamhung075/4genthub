package entities

import (
	"fmt"
	"math"
	"sort"
	"strings"
	"time"

	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SessionStatus is the work session status.
type SessionStatus string

const (
	SessionStatusActive    SessionStatus = "active"
	SessionStatusPaused    SessionStatus = "paused"
	SessionStatusCompleted SessionStatus = "completed"
	SessionStatusCancelled SessionStatus = "cancelled"
	SessionStatusTimeout   SessionStatus = "timeout"
)

func utcNow() time.Time { return time.Now().UTC().Truncate(time.Microsecond) }

// WorkSession tracks an agent's work on a task. Entity constructors in this
// package treat zero values as the Python defaults (Status "" → ACTIVE,
// AutoSaveInterval 0 → 300, LastActivity zero → now).
type WorkSession struct {
	base.BaseTimestampEntity
	ID                  string
	AgentID             string
	TaskID              string
	GitBranchName       string
	StartedAt           *time.Time
	Status              SessionStatus
	EndedAt             *time.Time
	PausedAt            *time.Time
	TotalPausedDuration time.Duration
	SessionNotes        string
	ProgressUpdates     []map[string]any
	ResourcesLocked     []string
	MaxDuration         *time.Duration // auto-timeout after this duration
	AutoSaveInterval    int            // seconds between auto-saves
	LastActivity        time.Time
}

// NewWorkSession applies defaults, initializes timestamps and validates.
func NewWorkSession(ws WorkSession) (*WorkSession, error) {
	s := ws
	if s.Status == "" {
		s.Status = SessionStatusActive
	}
	if s.AutoSaveInterval == 0 {
		s.AutoSaveInterval = 300
	}
	if s.LastActivity.IsZero() {
		s.LastActivity = utcNow()
	}
	if s.ProgressUpdates == nil {
		s.ProgressUpdates = []map[string]any{}
	}
	if s.ResourcesLocked == nil {
		s.ResourcesLocked = []string{}
	}
	if err := s.Init(&s); err != nil {
		return nil, err
	}
	return &s, nil
}

func (s *WorkSession) GetEntityID() string { return s.ID }

func (s *WorkSession) ValidateEntity() error {
	switch {
	case strings.TrimSpace(s.ID) == "":
		return value_objects.ValueErrorf("WorkSession id cannot be empty")
	case strings.TrimSpace(s.AgentID) == "":
		return value_objects.ValueErrorf("WorkSession agent_id cannot be empty")
	case strings.TrimSpace(s.TaskID) == "":
		return value_objects.ValueErrorf("WorkSession task_id cannot be empty")
	case strings.TrimSpace(s.GitBranchName) == "":
		return value_objects.ValueErrorf("WorkSession git_branch_name cannot be empty")
	case s.StartedAt == nil:
		return value_objects.ValueErrorf("WorkSession started_at cannot be None")
	case s.AutoSaveInterval <= 0:
		return value_objects.ValueErrorf("auto_save_interval must be greater than 0")
	}
	return nil
}

func (s *WorkSession) touch(reason string) error { return s.Touch(reason) }

// PauseSession moves ACTIVE → PAUSED.
func (s *WorkSession) PauseSession(reason string) error {
	if s.Status != SessionStatusActive {
		return value_objects.ValueErrorf("Cannot pause session in %s state", s.Status)
	}
	s.Status = SessionStatusPaused
	t := utcNow()
	s.PausedAt = &t
	s.LastActivity = utcNow()
	if err := s.touch("session_paused"); err != nil {
		return err
	}
	if reason != "" {
		return s.AddProgressUpdate("session_paused", "Session paused: "+reason, nil)
	}
	return nil
}

// ResumeSession moves PAUSED → ACTIVE, accumulating the paused time.
func (s *WorkSession) ResumeSession() error {
	if s.Status != SessionStatusPaused {
		return value_objects.ValueErrorf("Cannot resume session in %s state", s.Status)
	}
	if s.PausedAt != nil {
		s.TotalPausedDuration += utcNow().Sub(*s.PausedAt)
		s.PausedAt = nil
	}
	s.Status = SessionStatusActive
	s.LastActivity = utcNow()
	if err := s.touch("session_resumed"); err != nil {
		return err
	}
	return s.AddProgressUpdate("session_resumed", "Session resumed", nil)
}

// CompleteSession moves ACTIVE/PAUSED → COMPLETED.
func (s *WorkSession) CompleteSession(success bool, notes string) error {
	if s.Status != SessionStatusActive && s.Status != SessionStatusPaused {
		return value_objects.ValueErrorf("Cannot complete session in %s state", s.Status)
	}
	s.Status = SessionStatusCompleted
	t := utcNow()
	s.EndedAt = &t
	s.LastActivity = utcNow()
	if err := s.touch("session_completed"); err != nil {
		return err
	}
	if notes != "" {
		s.SessionNotes += "\nCompletion notes: " + notes
	}
	kind := "successful"
	if !success {
		kind = "unsuccessful"
	}
	return s.AddProgressUpdate("session_completed", fmt.Sprintf("Session completed (%s)", kind), nil)
}

// CancelSession cancels from any state.
func (s *WorkSession) CancelSession(reason string) error {
	s.Status = SessionStatusCancelled
	t := utcNow()
	s.EndedAt = &t
	s.LastActivity = utcNow()
	if err := s.touch("session_cancelled"); err != nil {
		return err
	}
	if reason != "" {
		s.SessionNotes += "\nCancellation reason: " + reason
	}
	return s.AddProgressUpdate("session_cancelled", "Session cancelled: "+reason, nil)
}

// TimeoutSession marks the session as timed out.
func (s *WorkSession) TimeoutSession() error {
	s.Status = SessionStatusTimeout
	t := utcNow()
	s.EndedAt = &t
	if err := s.touch("session_timeout"); err != nil {
		return err
	}
	return s.AddProgressUpdate("session_timeout", "Session timed out", nil)
}

// AddProgressUpdate appends a timestamped update and touches the entity.
func (s *WorkSession) AddProgressUpdate(updateType, message string, metadata map[string]any) error {
	if metadata == nil {
		metadata = map[string]any{}
	}
	s.ProgressUpdates = append(s.ProgressUpdates, map[string]any{
		"timestamp": value_objects.IsoFormat(utcNow()), "type": updateType, "message": message, "metadata": metadata,
	})
	s.LastActivity = utcNow()
	return s.touch("progress_updated")
}

// LockResource locks a resource once.
func (s *WorkSession) LockResource(id string) error {
	for _, r := range s.ResourcesLocked {
		if r == id {
			return nil
		}
	}
	s.ResourcesLocked = append(s.ResourcesLocked, id)
	return s.AddProgressUpdate("resource_locked", "Locked resource: "+id, nil)
}

// UnlockResource unlocks a locked resource.
func (s *WorkSession) UnlockResource(id string) error {
	for i, r := range s.ResourcesLocked {
		if r == id {
			s.ResourcesLocked = append(s.ResourcesLocked[:i], s.ResourcesLocked[i+1:]...)
			return s.AddProgressUpdate("resource_unlocked", "Unlocked resource: "+id, nil)
		}
	}
	return nil
}

// UnlockAllResources unlocks every resource (iterating a copy).
func (s *WorkSession) UnlockAllResources() error {
	for _, r := range append([]string{}, s.ResourcesLocked...) {
		if err := s.UnlockResource(r); err != nil {
			return err
		}
	}
	return nil
}

// GetTotalDuration is elapsed time while active, else start→end, else zero.
func (s *WorkSession) GetTotalDuration() time.Duration {
	switch {
	case s.Status == SessionStatusActive:
		return utcNow().Sub(*s.StartedAt)
	case s.EndedAt != nil:
		return s.EndedAt.Sub(*s.StartedAt)
	}
	return 0
}

// GetActiveDuration is the total duration minus paused time.
func (s *WorkSession) GetActiveDuration() time.Duration {
	return s.GetTotalDuration() - s.TotalPausedDuration
}

func (s *WorkSession) IsActive() bool { return s.Status == SessionStatusActive }

// IsTimeoutDue: a max duration is set (non-zero) and the total duration exceeds it.
func (s *WorkSession) IsTimeoutDue() bool {
	if s.MaxDuration == nil || *s.MaxDuration == 0 {
		return false
	}
	return s.GetTotalDuration() > *s.MaxDuration
}

// GetSessionSummary returns the nested summary dictionary.
func (s *WorkSession) GetSessionSummary() map[string]any {
	var ended, paused, latest, maxDur any
	if s.EndedAt != nil {
		ended = value_objects.IsoFormat(*s.EndedAt)
	}
	if s.PausedAt != nil {
		paused = value_objects.IsoFormat(*s.PausedAt)
	}
	if n := len(s.ProgressUpdates); n > 0 {
		latest = s.ProgressUpdates[n-1]
	}
	if s.MaxDuration != nil && *s.MaxDuration != 0 {
		maxDur = value_objects.PyTimedeltaStr(*s.MaxDuration)
	}
	return map[string]any{
		"session_id": s.ID, "agent_id": s.AgentID, "task_id": s.TaskID, "git_branch_name": s.GitBranchName,
		"status": string(s.Status),
		"timing": map[string]any{
			"started_at": value_objects.IsoFormat(*s.StartedAt), "ended_at": ended, "paused_at": paused,
			"last_activity":         value_objects.IsoFormat(s.LastActivity),
			"active_duration":       value_objects.PyTimedeltaStr(s.GetActiveDuration()),
			"total_duration":        value_objects.PyTimedeltaStr(s.GetTotalDuration()),
			"total_paused_duration": value_objects.PyTimedeltaStr(s.TotalPausedDuration),
		},
		"progress":  map[string]any{"total_updates": len(s.ProgressUpdates), "latest_update": latest, "session_notes": s.SessionNotes},
		"resources": map[string]any{"locked_resources": s.ResourcesLocked, "total_locked": len(s.ResourcesLocked)},
		"configuration": map[string]any{
			"max_duration": maxDur, "auto_save_interval": s.AutoSaveInterval, "timeout_due": s.IsTimeoutDue(),
		},
	}
}

// GetProgressTimeline returns updates sorted by (ISO) timestamp, stably.
func (s *WorkSession) GetProgressTimeline() []map[string]any {
	out := append([]map[string]any{}, s.ProgressUpdates...)
	sort.SliceStable(out, func(i, j int) bool { return out[i]["timestamp"].(string) < out[j]["timestamp"].(string) })
	return out
}

// ExtendSession adds to (or sets) the max duration.
func (s *WorkSession) ExtendSession(additional time.Duration) error {
	if s.MaxDuration != nil && *s.MaxDuration != 0 {
		d := *s.MaxDuration + additional
		s.MaxDuration = &d
	} else {
		s.MaxDuration = &additional
	}
	return s.AddProgressUpdate("session_extended", "Session extended by "+value_objects.PyTimedeltaStr(additional), nil)
}

// UpdateActivity refreshes last_activity and touches the entity.
func (s *WorkSession) UpdateActivity() error {
	s.LastActivity = utcNow()
	return s.touch("activity_updated")
}

// CreateWorkSession builds a session with the generated ID
// "{agent}_{task}_{unix timestamp float}" and a "session_started" update.
// maxDurationHours of 0 means no limit (Python truthiness).
func CreateWorkSession(agentID, taskID, gitBranchName string, maxDurationHours float64) (*WorkSession, error) {
	started := utcNow()
	ts := value_objects.PyRepr(float64(started.UnixMicro()) / 1e6)
	var maxDur *time.Duration
	if maxDurationHours != 0 {
		d := time.Duration(math.Round(maxDurationHours*3.6e9)) * time.Microsecond
		maxDur = &d
	}
	s, err := NewWorkSession(WorkSession{ID: fmt.Sprintf("%s_%s_%s", agentID, taskID, ts), AgentID: agentID, TaskID: taskID,
		GitBranchName: gitBranchName, StartedAt: &started, MaxDuration: maxDur})
	if err != nil {
		return nil, err
	}
	return s, s.AddProgressUpdate("session_started", "Work session initiated", nil)
}
