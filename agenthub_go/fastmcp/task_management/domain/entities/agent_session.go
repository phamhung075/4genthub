package entities

import (
	"time"

	"agenthub/fastmcp/task_management/domain/entities/base"
	"agenthub/fastmcp/task_management/domain/exceptions"
	"agenthub/fastmcp/task_management/domain/value_objects"
)

// SessionState: agent session states.
type SessionState string

const (
	SessionStateInitializing SessionState = "initializing"
	SessionStateActive       SessionState = "active"
	SessionStateBusy         SessionState = "busy"
	SessionStateIdle         SessionState = "idle"
	SessionStateDisconnected SessionState = "disconnected"
	SessionStateTerminated   SessionState = "terminated"
)

// ResourceType: types of resources an agent can hold.
type ResourceType string

const (
	ResourceDatabaseConnection ResourceType = "database_connection"
	ResourceFileLock           ResourceType = "file_lock"
	ResourceAPIQuota           ResourceType = "api_quota"
	ResourceMemoryAllocation   ResourceType = "memory_allocation"
	ResourceCPUThread          ResourceType = "cpu_thread"
)

// ResourceTypeValues lists the members in declaration order.
var ResourceTypeValues = []ResourceType{ResourceDatabaseConnection, ResourceFileLock, ResourceAPIQuota, ResourceMemoryAllocation, ResourceCPUThread}

// ResourceUsage tracks resource usage for an agent session.
type ResourceUsage struct {
	ResourceType    ResourceType
	AllocatedAmount float64
	UsedAmount      float64
	AllocationTime  time.Time
	ResourceID      *string
}

func (r *ResourceUsage) UsagePercentage() float64 {
	if r.AllocatedAmount == 0 {
		return 0.0
	}
	return (r.UsedAmount / r.AllocatedAmount) * 100
}

// IsOverutilized compares the usage percentage to threshold (Python default 90.0).
func (r *ResourceUsage) IsOverutilized(threshold float64) bool {
	return r.UsagePercentage() > threshold
}

// CommunicationChannel is a channel for agent-to-agent messaging.
type CommunicationChannel struct {
	ChannelID    string
	ChannelType  string // websocket, message_queue, direct
	Participants []string
	CreatedAt    time.Time
	IsActive     bool
	Metadata     map[string]any
}

// NewCommunicationChannel applies the defaults (created now, active).
func NewCommunicationChannel(channelID, channelType string, participants []string) *CommunicationChannel {
	return &CommunicationChannel{ChannelID: channelID, ChannelType: channelType, Participants: participants,
		CreatedAt: utcNow(), IsActive: true, Metadata: map[string]any{}}
}

// AgentSessionOptions are AgentSession.__init__'s arguments; nil pointers take
// the Python defaults (heartbeat 30s, max idle 300s, no max duration).
type AgentSessionOptions struct {
	SessionID          string
	AgentID            string
	UserID             *string
	ProjectID          *string
	StartedAt          *time.Time
	HeartbeatInterval  *int
	MaxIdleTime        *int
	MaxSessionDuration *int
}

// Metrics is the session metrics dict, in Python key order.
type Metrics struct {
	MessagesSent          int
	MessagesReceived      int
	TasksCompleted        int
	TasksFailed           int
	AvgResponseTimeMs     int
	TotalProcessingTimeMs int
	ErrorCount            int
	RecoveryCount         int
}

func (m Metrics) ToDict() map[string]any {
	return map[string]any{
		"messages_sent": m.MessagesSent, "messages_received": m.MessagesReceived,
		"tasks_completed": m.TasksCompleted, "tasks_failed": m.TasksFailed,
		"avg_response_time_ms": m.AvgResponseTimeMs, "total_processing_time_ms": m.TotalProcessingTimeMs,
		"error_count": m.ErrorCount, "recovery_count": m.RecoveryCount,
	}
}

// AgentSession manages real-time agent coordination: lifecycle, resources,
// channels, metrics and recovery.
type AgentSession struct {
	base.BaseTimestampEntity
	SessionID          string
	AgentID            string
	UserID             *string
	ProjectID          *string
	StartedAt          time.Time
	State              SessionState
	LastHeartbeat      time.Time
	HeartbeatInterval  int
	MaxIdleTime        int
	MaxSessionDuration *int

	ActiveTasks    StringSet
	CompletedTasks StringSet
	FailedTasks    StringSet

	Resources     *OrderedMap[*ResourceUsage]
	ResourceLocks StringSet

	Channels        *OrderedMap[*CommunicationChannel]
	PendingMessages []value_objects.CoordinationMessage
	MessageHistory  []value_objects.CoordinationMessage

	Metrics  Metrics
	Metadata map[string]any
}

// NewAgentSession initializes the session; validation errors mirror Python's __init__.
func NewAgentSession(o AgentSessionOptions) (*AgentSession, error) {
	s := &AgentSession{
		SessionID: o.SessionID, AgentID: o.AgentID, UserID: o.UserID, ProjectID: o.ProjectID,
		HeartbeatInterval: 30, MaxIdleTime: 300, MaxSessionDuration: o.MaxSessionDuration,
		State: SessionStateInitializing,
	}
	if s.SessionID == "" {
		s.SessionID = value_objects.NewUUIDv4()
	}
	if o.HeartbeatInterval != nil {
		s.HeartbeatInterval = *o.HeartbeatInterval
	}
	if o.MaxIdleTime != nil {
		s.MaxIdleTime = *o.MaxIdleTime
	}
	current := utcNow()
	s.StartedAt, s.LastHeartbeat = current, current
	if o.StartedAt != nil {
		s.StartedAt = *o.StartedAt
	}
	s.Resources = NewOrderedMap[*ResourceUsage]()
	s.Channels = NewOrderedMap[*CommunicationChannel]()
	s.PendingMessages = []value_objects.CoordinationMessage{}
	s.MessageHistory = []value_objects.CoordinationMessage{}
	s.Metadata = map[string]any{}
	if err := s.Init(s); err != nil {
		return nil, err
	}
	return s, nil
}

func (s *AgentSession) GetEntityID() string { return s.SessionID }

func (s *AgentSession) ValidateEntity() error {
	switch {
	case s.SessionID == "":
		return value_objects.ValueErrorf("Session must have an identifier")
	case s.AgentID == "":
		return value_objects.ValueErrorf("Session agent_id cannot be empty")
	case s.HeartbeatInterval <= 0:
		return value_objects.ValueErrorf("heartbeat_interval must be greater than 0")
	case s.MaxIdleTime <= 0:
		return value_objects.ValueErrorf("max_idle_time must be greater than 0")
	}
	return nil
}

func (s *AgentSession) Activate() error {
	if s.State != SessionStateInitializing {
		return &exceptions.DomainException{Msg: "Cannot activate session in state " + string(s.State)}
	}
	s.State = SessionStateActive
	if err := s.UpdateHeartbeat(); err != nil {
		return err
	}
	return s.Touch("session_activated")
}

func (s *AgentSession) UpdateHeartbeat() error {
	s.LastHeartbeat = utcNow()
	if err := s.Touch("heartbeat_updated"); err != nil {
		return err
	}
	if s.State == SessionStateIdle {
		s.State = SessionStateActive
	}
	return nil
}

func (s *AgentSession) IsAlive() bool {
	if s.State == SessionStateDisconnected || s.State == SessionStateTerminated {
		return false
	}
	return value_objects.PyTotalSeconds(utcNow().Sub(s.LastHeartbeat)) < float64(s.HeartbeatInterval*2)
}

func (s *AgentSession) IsExpired() bool {
	if s.MaxSessionDuration == nil || *s.MaxSessionDuration == 0 {
		return false
	}
	return value_objects.PyTotalSeconds(utcNow().Sub(s.StartedAt)) > float64(*s.MaxSessionDuration)
}

func (s *AgentSession) IsIdle() bool {
	if s.ActiveTasks.Len() == 0 {
		return value_objects.PyTotalSeconds(utcNow().Sub(s.LastHeartbeat)) > float64(s.MaxIdleTime)
	}
	return false
}

func (s *AgentSession) StartTask(taskID string) error {
	s.ActiveTasks.Add(taskID)
	s.State = SessionStateBusy
	if err := s.UpdateHeartbeat(); err != nil {
		return err
	}
	return s.Touch("task_started")
}

func (s *AgentSession) CompleteTask(taskID string, success bool) error {
	s.ActiveTasks.Remove(taskID)
	if success {
		s.CompletedTasks.Add(taskID)
		s.Metrics.TasksCompleted++
	} else {
		s.FailedTasks.Add(taskID)
		s.Metrics.TasksFailed++
	}
	s.LastHeartbeat = utcNow()
	if err := s.Touch("task_completed"); err != nil {
		return err
	}
	if s.ActiveTasks.Len() == 0 {
		s.State = SessionStateIdle
	} else {
		s.State = SessionStateBusy
	}
	return nil
}

func resourceKey(t ResourceType, id *string) string {
	if id == nil || *id == "" {
		return string(t) + "_default"
	}
	return string(t) + "_" + *id
}

func (s *AgentSession) AllocateResource(t ResourceType, amount float64, resourceID *string) *ResourceUsage {
	r := &ResourceUsage{ResourceType: t, AllocatedAmount: amount, AllocationTime: utcNow(), ResourceID: resourceID}
	s.Resources.Set(resourceKey(t, resourceID), r)
	if resourceID != nil && *resourceID != "" {
		s.ResourceLocks.Add(*resourceID)
	}
	return r
}

func (s *AgentSession) UpdateResourceUsage(t ResourceType, used float64, resourceID *string) {
	if r, ok := s.Resources.Get(resourceKey(t, resourceID)); ok {
		r.UsedAmount = used
	}
}

func (s *AgentSession) ReleaseResource(t ResourceType, resourceID *string) {
	s.Resources.Delete(resourceKey(t, resourceID))
	if resourceID != nil && *resourceID != "" {
		s.ResourceLocks.Remove(*resourceID)
	}
}

// resourceSummaryEntry keeps the summary in ResourceType declaration order.
type resourceSummaryEntry struct {
	Type    ResourceType
	Percent float64
}

func (s *AgentSession) resourceSummaryOrdered() []resourceSummaryEntry {
	out := []resourceSummaryEntry{}
	for _, rt := range ResourceTypeValues {
		allocated, used := 0.0, 0.0
		for _, u := range s.Resources.Values() {
			if u.ResourceType == rt {
				allocated += u.AllocatedAmount
				used += u.UsedAmount
			}
		}
		if allocated > 0 {
			out = append(out, resourceSummaryEntry{rt, (used / allocated) * 100})
		}
	}
	return out
}

// GetResourceUsageSummary maps resource type → usage percentage (only allocated types).
func (s *AgentSession) GetResourceUsageSummary() map[string]float64 {
	out := map[string]float64{}
	for _, e := range s.resourceSummaryOrdered() {
		out[string(e.Type)] = e.Percent
	}
	return out
}

func (s *AgentSession) OpenChannel(id, channelType string, participants []string) *CommunicationChannel {
	c := NewCommunicationChannel(id, channelType, participants)
	s.Channels.Set(id, c)
	return c
}

func (s *AgentSession) CloseChannel(id string) {
	if c, ok := s.Channels.Get(id); ok {
		c.IsActive = false
	}
}

// AddMessage appends to the history and keeps only the last 500 messages.
func (s *AgentSession) AddMessage(m value_objects.CoordinationMessage, outgoing bool) {
	s.MessageHistory = append(s.MessageHistory, m)
	if outgoing {
		s.Metrics.MessagesSent++
	} else {
		s.Metrics.MessagesReceived++
	}
	if len(s.MessageHistory) > 500 {
		s.MessageHistory = append([]value_objects.CoordinationMessage{}, s.MessageHistory[len(s.MessageHistory)-500:]...)
	}
}

func (s *AgentSession) GetActiveChannels() []*CommunicationChannel {
	out := []*CommunicationChannel{}
	for _, c := range s.Channels.Values() {
		if c.IsActive {
			out = append(out, c)
		}
	}
	return out
}

// CalculateHealthScore returns the 0-100 health score.
func (s *AgentSession) CalculateHealthScore() float64 {
	score := 100.0
	if summary := s.resourceSummaryOrdered(); len(summary) > 0 {
		percents := make([]float64, len(summary))
		for i, e := range summary {
			percents[i] = e.Percent
		}
		switch avg := value_objects.PySum(percents) / float64(len(summary)); {
		case avg > 90:
			score -= 30
		case avg > 75:
			score -= 20
		case avg > 60:
			score -= 10
		}
	}
	m := s.Metrics
	if total := m.TasksCompleted + m.TasksFailed + m.MessagesSent; total > 0 {
		rate := float64(m.ErrorCount) / float64(total)
		score -= minFloat(rate*100, 30)
	}
	if total := m.TasksCompleted + m.TasksFailed; total > 0 {
		score -= minFloat(float64(m.TasksFailed)/float64(total)*40, 20)
	}
	if s.MaxSessionDuration != nil && *s.MaxSessionDuration != 0 {
		pct := (value_objects.PyTotalSeconds(utcNow().Sub(s.StartedAt)) / float64(*s.MaxSessionDuration)) * 100
		switch {
		case pct > 90:
			score -= 20
		case pct > 75:
			score -= 10
		}
	}
	if score < 0 {
		return 0
	}
	return score
}

func minFloat(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

func (s *AgentSession) NeedsRecovery() bool {
	return s.CalculateHealthScore() < 50 || s.Metrics.ErrorCount > 10 || !s.IsAlive()
}

func (s *AgentSession) Recover() error {
	s.Metrics.RecoveryCount++
	s.Metrics.ErrorCount = 0
	s.State = SessionStateActive
	if err := s.UpdateHeartbeat(); err != nil {
		return err
	}
	if err := s.Touch("session_recovered"); err != nil {
		return err
	}
	s.PendingMessages = s.PendingMessages[:0]
	for _, r := range s.Resources.Values() {
		if r.IsOverutilized(90.0) {
			r.UsedAmount = r.AllocatedAmount * 0.5
		}
	}
	return nil
}

// Terminate ends the session (Python default reason "Normal termination").
func (s *AgentSession) Terminate(reason string) error {
	s.State = SessionStateTerminated
	for _, id := range s.Channels.Keys() {
		s.CloseChannel(id)
	}
	s.ResourceLocks = StringSet{}
	s.Resources = NewOrderedMap[*ResourceUsage]()
	s.Metadata["termination_reason"] = reason
	s.Metadata["terminated_at"] = value_objects.IsoFormat(utcNow())
	return s.Touch("session_terminated")
}

func (s *AgentSession) ToDict() map[string]any {
	return map[string]any{
		"session_id": s.SessionID, "agent_id": s.AgentID, "user_id": strOrNil(s.UserID), "project_id": strOrNil(s.ProjectID),
		"state": string(s.State), "started_at": value_objects.IsoFormat(s.StartedAt),
		"last_heartbeat": value_objects.IsoFormat(s.LastHeartbeat), "active_tasks": s.ActiveTasks.Items(),
		"completed_tasks_count": s.CompletedTasks.Len(), "failed_tasks_count": s.FailedTasks.Len(),
		"health_score": s.CalculateHealthScore(), "metrics": s.Metrics.ToDict(),
		"resource_usage": s.GetResourceUsageSummary(), "active_channels": len(s.GetActiveChannels()),
		"is_alive": s.IsAlive(), "is_expired": s.IsExpired(), "metadata": s.Metadata,
	}
}
